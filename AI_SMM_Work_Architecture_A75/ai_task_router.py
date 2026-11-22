"""AI Task Router: Parses user requests into structured tasks for distribution."""
import logging
import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class SubTask:
    """Single sub-task extracted from user request."""
    id: str
    task_type: str  # strategy, content_plan, media_generation, text_generation, validation
    description: str
    target_section: str  # Which DataManager section to update
    parameters: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)  # IDs of tasks that must complete first
    status: str = "pending"  # pending, in_progress, completed, failed
    result: Optional[Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "task_type": self.task_type,
            "description": self.description,
            "target_section": self.target_section,
            "parameters": self.parameters,
            "dependencies": self.dependencies,
            "status": self.status,
            "result": self.result,
        }


@dataclass
class ParsedRequest:
    """Result of parsing a user request."""
    original_text: str
    main_intent: str  # campaign_creation, strategy_update, content_generation, etc.
    sub_tasks: List[SubTask]
    project_context: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def get_execution_order(self) -> List[SubTask]:
        """Return tasks in dependency-resolved order."""
        resolved = []
        remaining = {t.id: t for t in self.sub_tasks}
        
        while remaining:
            # Find tasks with no unmet dependencies
            ready = []
            for tid, task in remaining.items():
                deps_met = all(dep not in remaining or dep in resolved for dep in task.dependencies)
                if deps_met:
                    ready.append(task)
            
            if not ready:
                logger.error("Circular dependency detected in task graph")
                break
            
            for task in ready:
                resolved.append(task)
                del remaining[task.id]
        
        return resolved


class AITaskRouter:
    """Routes and parses AI requests into executable sub-tasks."""
    
    def __init__(self):
        self._counter = 0
    
    def parse_request(self, user_text: str, project_context: Optional[Dict[str, Any]] = None) -> ParsedRequest:
        """Parse natural language request into structured sub-tasks.
        
        Examples:
        - "Создай рекламную кампанию для кофейни карамельный латте на 7 дней"
          → [strategy, content_plan, media_gen, text_gen, validation]
        - "Обнови позиционирование проекта 'Acme'"
          → [strategy_update]
        - "Сгенерируй 3 идеи контента на неделю"
          → [content_plan]
        """
        lower_text = user_text.lower()
        
        # Detect main intent
        main_intent = self._detect_main_intent(lower_text)
        
        # Extract entities (product name, duration, platform, etc.)
        entities = self._extract_entities(user_text)
        
        # Generate sub-tasks based on intent + entities
        sub_tasks = self._generate_sub_tasks(main_intent, entities, project_context)
        
        parsed = ParsedRequest(
            original_text=user_text,
            main_intent=main_intent,
            sub_tasks=sub_tasks,
            project_context=project_context or {},
        )
        
        logger.info(f"Parsed request '{user_text[:50]}...' → {len(sub_tasks)} sub-tasks (intent: {main_intent})")
        return parsed
    
    def _detect_main_intent(self, text_lower: str) -> str:
        """Classify the overall goal of the request."""
        if any(w in text_lower for w in ["кампани", "реклам", "продвижени"]):
            return "campaign_creation"
        if any(w in text_lower for w in ["стратег", "позицион", "целев"]):
            return "strategy_update"
        if any(w in text_lower for w in ["контент", "план", "публикац", "идеи"]):
            return "content_generation"
        if any(w in text_lower for w in ["медиа", "изображен", "фото", "видео"]):
            return "media_generation"
        if any(w in text_lower for w in ["текст", "описан", "хэштег"]):
            return "text_generation"
        if any(w in text_lower for w in ["провер", "валид", "качеств"]):
            return "validation"
        return "general_query"
    
    def _extract_entities(self, text: str) -> Dict[str, Any]:
        """Extract key information from request using regex/heuristics."""
        entities = {}
        
        # Product/service name (look for quoted phrases or capitalized words after prepositions)
        product_match = re.search(r'для\s+([А-Яа-яЁёA-Za-z0-9\s\-]+?)(?:\s+(?:на|в|по)|$)', text)
        if product_match:
            entities["product_name"] = product_match.group(1).strip()
        
        # Duration/timeframe
        duration_match = re.search(r'\b(\d+)\s*(день|недел|месяц|год)s?\b', text, re.IGNORECASE)
        if duration_match:
            num = int(duration_match.group(1))
            unit = duration_match.group(2).lower()
            if "недел" in unit:
                entities["duration_days"] = num * 7
            elif "месяц" in unit:
                entities["duration_days"] = num * 30
            else:
                entities["duration_days"] = num
        
        # Platforms
        platforms = []
        if "instagram" in text.lower() or "инстаграм" in text.lower():
            platforms.append("Instagram")
        if "tiktok" in text.lower() or "тикток" in text.lower():
            platforms.append("TikTok")
        if "vk" in text.lower() or "вконтакте" in text.lower():
            platforms.append("VK")
        if platforms:
            entities["platforms"] = platforms
        
        # Quantity hints
        qty_match = re.search(r'\b(\d+)\s*(шт|изображен|вариант|идея|публикаци)s?\b', text, re.IGNORECASE)
        if qty_match:
            entities["quantity"] = int(qty_match.group(1))
        
        return entities
    
    def _generate_sub_tasks(
        self, 
        intent: str, 
        entities: Dict[str, Any], 
        context: Optional[Dict[str, Any]]
    ) -> List[SubTask]:
        """Create sequence of sub-tasks based on intent and extracted info."""
        tasks = []
        base_id = f"req_{int(datetime.now().timestamp())}"
        
        if intent == "campaign_creation":
            # Full campaign workflow
            prod = entities.get("product_name", "продукт")
            dur = entities.get("duration_days", 7)
            plats = entities.get("platforms", ["Instagram"])
            qty = entities.get("quantity", 3)
            
            # 1. Strategy foundation
            tasks.append(SubTask(
                id=f"{base_id}_1",
                task_type="strategy",
                description=f"Разработать стратегию продвижения для '{prod}' на {dur} дней",
                target_section="strategy",
                parameters={"product": prod, "duration_days": dur, "platforms": plats},
            ))
            
            # 2. Content plan depends on strategy
            tasks.append(SubTask(
                id=f"{base_id}_2",
                task_type="content_plan",
                description=f"Составить контент-план на {dur} дней для платформ: {', '.join(plats)}",
                target_section="content_plan",
                parameters={"product": prod, "duration_days": dur, "platforms": plats},
                dependencies=[f"{base_id}_1"],
            ))
            
            # 3. Media generation depends on content plan
            tasks.append(SubTask(
                id=f"{base_id}_3",
                task_type="media_generation",
                description=f"Сгенерировать {qty} изображений/видео в разных стилях для публикаций",
                target_section="media_content",
                parameters={"product": prod, "quantity": qty, "platforms": plats, "styles": ["photorealistic", "minimalist", "premium"]},
                dependencies=[f"{base_id}_2"],
            ))
            
            # 4. Text generation can run parallel to media but needs plan
            tasks.append(SubTask(
                id=f"{base_id}_4",
                task_type="text_generation",
                description=f"Подготовить тексты публикаций с хэштегами и призывами к действию",
                target_section="publications",
                parameters={"product": prod, "platforms": plats, "with_hashtags": True, "include_cta": True},
                dependencies=[f"{base_id}_2"],
            ))
            
            # 5. Validation runs last
            tasks.append(SubTask(
                id=f"{base_id}_5",
                task_type="validation",
                description=f"Проверить качество всех материалов: соответствие стратегии, техническим требованиям, tone-of-voice",
                target_section="all_sections",
                parameters={"check_consistency": True, "verify_quality": True},
                dependencies=[f"{base_id}_3", f"{base_id}_4"],
            ))
        
        elif intent == "strategy_update":
            prod = entities.get("product_name", "проект")
            tasks.append(SubTask(
                id=f"{base_id}_1",
                task_type="strategy",
                description=f"Обновить стратегический документ для '{prod}'",
                target_section="strategy",
                parameters={"update_existing": True},
            ))
        
        elif intent == "content_generation":
            dur = entities.get("duration_days", 7)
            tasks.append(SubTask(
                id=f"{base_id}_1",
                task_type="content_plan",
                description=f"Создать контент-план на {dur} дней",
                target_section="content_plan",
                parameters={"duration_days": dur},
            ))
        
        elif intent == "media_generation":
            qty = entities.get("quantity", 1)
            tasks.append(SubTask(
                id=f"{base_id}_1",
                task_type="media_generation",
                description=f"Сгенерировать {qty} медиа-материалов",
                target_section="media_content",
                parameters={"quantity": qty},
            ))
        
        elif intent == "text_generation":
            tasks.append(SubTask(
                id=f"{base_id}_1",
                task_type="text_generation",
                description="Подготовить текстовые материалы",
                target_section="publications",
                parameters={},
            ))
        
        else:  # general_query
            tasks.append(SubTask(
                id=f"{base_id}_1",
                task_type="analysis",
                description=f"Ответить на общий запрос пользователя",
                target_section="none",
                parameters={"query": entities.get("original_text", "")},
            ))
        
        return tasks
    
    def execute_parsed_request(
        self, 
        parsed: ParsedRequest, 
        data_manager,
        ai_client=None
    ) -> Dict[str, Any]:
        """Execute all sub-tasks in order and write the results into DataManager.

        Every handler below performs a real change in the project data
        (strategy, content plan, calendar, shooting tasks, captions).
        """
        results = {}
        ordered_tasks = parsed.get_execution_order()
        
        logger.info(f"Executing {len(ordered_tasks)} sub-tasks for request: {parsed.original_text[:50]}...")
        
        for task in ordered_tasks:
            logger.info(f"Starting task: {task.id} ({task.task_type})")
            task.status = "in_progress"
            
            try:
                task.result = self._execute_task(task, parsed, data_manager, ai_client)
                task.status = "completed"
                results[task.id] = task.result
                logger.info(f"Completed task: {task.id}")
            except Exception as e:
                logger.error(f"Failed task {task.id}: {e}")
                task.status = "failed"
                results[task.id] = {"error": str(e)}
        
        if data_manager is not None:
            data_manager.save()
        
        return {
            "request_summary": parsed.original_text,
            "total_tasks": len(ordered_tasks),
            "completed": sum(1 for t in ordered_tasks if t.status == "completed"),
            "failed": sum(1 for t in ordered_tasks if t.status == "failed"),
            "results_by_task": results,
            "execution_log": [t.to_dict() for t in ordered_tasks],
        }

    def _execute_task(self, task: SubTask, parsed: ParsedRequest, dm, ai_client=None) -> Dict[str, Any]:
        """Run a single sub-task against the project data."""
        if dm is None:
            raise RuntimeError("DataManager is not connected to the AI panel")

        if task.task_type == "strategy":
            return self._run_strategy(task, dm, ai_client)
        if task.task_type == "content_plan":
            return self._run_content_plan(task, dm)
        if task.task_type == "media_generation":
            return self._run_shooting_plan(dm)
        if task.task_type == "text_generation":
            return self._run_captions(task, dm)
        if task.task_type == "validation":
            return self._run_validation(dm)
        return {"message": f"Запрос принят: {parsed.original_text[:120]}"}

    # === Handlers ===
    def _campaign_params(self, task: SubTask) -> Dict[str, Any]:
        p = task.parameters or {}
        return {
            "product": p.get("product") or "проект",
            "duration_days": max(1, int(p.get("duration_days", 7))),
            "platforms": p.get("platforms") or ["Instagram"],
            "quantity": max(1, int(p.get("quantity", 3))),
        }

    def _run_strategy(self, task: SubTask, dm, ai_client=None) -> Dict[str, Any]:
        params = self._campaign_params(task)
        product = params["product"]
        duration = params["duration_days"]
        platforms = params["platforms"]

        blocks = self._ai_strategy_blocks(ai_client, product, duration, platforms) or {}

        updated = []
        defaults = {
            "positioning": (
                f"Кампания «{product}» на {duration} дней для платформ {', '.join(platforms)}. "
                "Фокус — понятная выгода для аудитории и единый визуальный стиль публикаций."
            ),
            "utp": (
                f"Серия публикаций по теме «{product}» с регулярным ритмом и измеримыми целями "
                f"на {duration} дней: охват, вовлечённость и заявки."
            ),
            "tone": "Дружелюбный, уверенный, без канцелярита. Говорим о пользе для клиента и подкрепляем слова примерами.",
            "channels": ", ".join(platforms),
        }
        for section_id in ("positioning", "utp", "tone", "channels"):
            content = blocks.get(section_id) or defaults[section_id]
            if dm.update_strategy_section(section_id, content):
                updated.append(section_id)

        strategy = dm.get_strategy()
        versions = strategy.setdefault("versions", [])
        new_version = f"{len(versions) + 1}.0"
        strategy["version"] = new_version
        versions.append({
            "version": new_version,
            "date": datetime.now().strftime("%d.%m.%Y"),
            "author": "AI",
            "changes": f"Кампания «{product}»: стратегия на {duration} дней",
        })
        dm.save()
        return {"sections_updated": updated, "version": new_version, "product": product}

    def _ai_strategy_blocks(self, ai_client, product, duration, platforms) -> Dict[str, str]:
        """Ask the local LLM for strategy blocks and parse them; None if unavailable."""
        if ai_client is None or not getattr(ai_client, "available", False):
            return {}
        prompt = (
            f"Составь краткие блоки стратегии SMM-кампании для «{product}» на {duration} дней "
            f"для платформ {', '.join(platforms)}. Ответ строго в формате, по 1-3 предложения:"
            "\nПОЗИЦИОНИРОВАНИЕ: ...\nУТП: ...\nTONE OF VOICE: ...\nКАНАЛЫ: ..."
        )
        try:
            raw = ai_client.generate(prompt, system_prompt="Ты опытный SMM-стратег. Отвечай по-русски, только требуемые блоки.")
        except Exception as e:
            logger.warning(f"LLM strategy generation failed: {e}")
            return {}
        if not raw:
            return {}
        mapping = {
            "positioning": r"ПОЗИЦИОНИРОВАНИЕ\s*:\s*(.+?)(?=\n(?:УТП|TONE|КАНАЛЫ)\s*:|$)",
            "utp": r"УТП\s*:\s*(.+?)(?=\n(?:ПОЗИЦИОНИРОВАНИЕ|TONE|КАНАЛЫ)\s*:|$)",
            "tone": r"TONE\s+OF\s+VOICE\s*:\s*(.+?)(?=\n(?:ПОЗИЦИОНИРОВАНИЕ|УТП|КАНАЛЫ)\s*:|$)",
            "channels": r"КАНАЛЫ\s*:\s*(.+?)$",
        }
        blocks = {}
        for key, pattern in mapping.items():
            m = re.search(pattern, raw, re.IGNORECASE | re.DOTALL)
            if m and m.group(1).strip():
                blocks[key] = m.group(1).strip()
        return blocks

    def _run_content_plan(self, task: SubTask, dm) -> Dict[str, Any]:
        params = self._campaign_params(task)
        product = params["product"]
        duration = params["duration_days"]
        platforms = params["platforms"]

        rubric_cycle = [
            ("Польза", "Пост", "utp", "3 практических совета по теме «{p}»{platforms}"),
            ("Развлечение", "Reels", "tone", "Закулисье «{p}»: живой момент, эмоции, движение{platforms}"),
            ("Продажа", "Stories", "utp", "Предложение «{p}»: что получить и как записаться{platforms}"),
            ("Личное", "Пост", "about", "История клиента «{p}»: путь и результат{platforms}"),
        ]
        platform_note = f" для {', '.join(platforms)}" if platforms else ""
        start = datetime.now() + timedelta(days=1)
        created = []
        for i in range(duration):
            day = start + timedelta(days=i)
            rubric, fmt, strategy_link, topic_tpl = rubric_cycle[i % len(rubric_cycle)]
            topic = topic_tpl.format(p=product, platforms=platform_note)
            new_id = dm.add_content_plan_item({
                "date": day.strftime("%d.%m.%Y"),
                "rubric": rubric,
                "topic": topic,
                "format": fmt,
                "status": "Запланировано",
                "responsible": "AI",
                "source": "AI",
                "strategy_link": strategy_link,
                "platforms": platforms,
                "shooting_task_id": None,
            })
            dm.add_calendar_event({
                "date": day.strftime("%d.%m.%Y"),
                "time": "12:00",
                "type": "publication",
                "title": topic[:80],
                "description": f"{fmt} · {rubric} · {', '.join(platforms)}",
                "link": new_id,
            })
            created.append(new_id)
        dm.save()
        return {"items_added": len(created), "ids": created, "duration_days": duration}

    def _run_shooting_plan(self, dm) -> Dict[str, Any]:
        created = []
        for item in list(dm.get_content_plan()):
            if item.get("shooting_task_id"):
                continue
            if item.get("format") == "Пост" and not item.get("needs_media", True):
                continue
            task = dm.create_shooting_task_from_content_plan(item["id"])
            if task:
                created.append(task["id"])
        dm.save()
        return {"shooting_tasks_created": len(created), "ids": created}

    def _run_captions(self, task: SubTask, dm) -> Dict[str, Any]:
        params = self._campaign_params(task)
        product = params["product"]
        platforms = params["platforms"]
        cta_by_rubric = {
            "Продажа": "Запишитесь или напишите в личные сообщения — расскажем детали.",
            "Польза": "Сохраните пост, чтобы вернуться к советам позже.",
            "Развлечение": "Отметьте того, с кем это стоит повторить.",
            "Личное": "Поделитесь своим опытом в комментариях.",
        }
        tag_base = re.sub(r"[^\wа-яА-ЯёЁ]+", "", product.lower()) or "проект"
        updated = 0
        for item in dm.get_content_plan():
            if item.get("caption"):
                continue
            rubric = item.get("rubric", "Польза")
            caption = (
                f"{item.get('topic', product)}.\n\n"
                f"{cta_by_rubric.get(rubric, cta_by_rubric['Польза'])}\n\n"
                f"#{tag_base} #smm #контент"
            )
            item["caption"] = caption
            item["hashtags"] = [f"#{tag_base}", "#smm", "#контент"]
            item["platforms"] = item.get("platforms") or platforms
            updated += 1
        dm.save()
        return {"captions_created": updated}

    def _run_validation(self, dm) -> Dict[str, Any]:
        """Same plan rules as `validate_plan`, plus empty strategy blocks."""
        from ai_core import collect_plan_issues

        plan = dm.get_content_plan()
        issues = [f"{issue['topic']}: {', '.join(issue['problems'])}"
                  for issue in collect_plan_issues(dm)[0]]
        if not plan:
            issues.insert(0, "Контент-план пуст")
        issues += [f"Стратегия: пустой блок «{section.get('title') or section.get('id') or '—'}»"
                   for section in dm.get_strategy().get("sections", [])
                   if not (section.get("content") or "").strip()]
        return {
            "issues_found": len(issues),
            "issues": issues[:15],
            "quality_score": max(0, 100 - 5 * len(issues)),
            "checked_items": len(plan),
        }
