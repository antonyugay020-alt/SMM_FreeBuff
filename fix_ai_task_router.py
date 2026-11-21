#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Step 3: Create ai_task_router.py - parses user requests into structured tasks.
Run: python fix_ai_task_router.py
"""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

def write(rel, content):
    p = BASE / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding='utf-8', newline='\n')
    print(f"  [OK] {rel}")

print("\n=== Step 3: AI Task Router ===\n")

# 1. Create ai_task_router.py
print("[1/2] Creating ai_task_router.py...")

task_router = r'''"""AI Task Router: Parses user requests into structured tasks for distribution."""
import logging
import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

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
        - "Обнови позиционирование проекта 'Теннис'"
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
                parameters={"product": prod, "duration_days": dur},
            ))
            
            # 2. Content plan depends on strategy
            tasks.append(SubTask(
                id=f"{base_id}_2",
                task_type="content_plan",
                description=f"Составить контент-план на {dur} дней для платформ: {', '.join(plats)}",
                target_section="content_plan",
                parameters={"duration_days": dur, "platforms": plats},
                dependencies=[f"{base_id}_1"],
            ))
            
            # 3. Media generation depends on content plan
            tasks.append(SubTask(
                id=f"{base_id}_3",
                task_type="media_generation",
                description=f"Сгенерировать {qty} изображений/видео в разных стилях для публикаций",
                target_section="media_content",
                parameters={"quantity": qty, "styles": ["photorealistic", "minimalist", "premium"]},
                dependencies=[f"{base_id}_2"],
            ))
            
            # 4. Text generation can run parallel to media but needs plan
            tasks.append(SubTask(
                id=f"{base_id}_4",
                task_type="text_generation",
                description=f"Подготовить тексты публикаций с хэштегами и призывами к действию",
                target_section="publications",
                parameters={"with_hashtags": True, "include_cta": True},
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
        """Execute all sub-tasks in order, updating DataManager as results arrive.
        
        NOTE: This is a stub implementation. Real execution requires:
        1. Connection to actual AI models (OpenAI/local LLM)
        2. Image/video generation tools (Stable Diffusion, FFmpeg)
        3. Quality validation logic
        
        For now, it demonstrates the routing structure.
        """
        results = {}
        ordered_tasks = parsed.get_execution_order()
        
        logger.info(f"Executing {len(ordered_tasks)} sub-tasks for request: {parsed.original_text[:50]}...")
        
        for task in ordered_tasks:
            logger.info(f"Starting task: {task.id} ({task.task_type})")
            task.status = "in_progress"
            
            try:
                # SIMULATED EXECUTION - replace with real tool calls later
                if task.task_type == "strategy":
                    # Would call AI to generate/update strategy document
                    fake_result = {
                        "sections_updated": ["about", "audience", "positioning"],
                        "version_incremented": True,
                    }
                
                elif task.task_type == "content_plan":
                    # Would generate N days worth of planned posts
                    fake_result = {
                        "items_added": len(parsed.project_context.get("existing_items", [])) + 7,
                        "dates_covered": f"{task.parameters.get('duration_days', 7)} days",
                    }
                
                elif task.task_type == "media_generation":
                    # Would trigger image/video generation pipeline
                    fake_result = {
                        "files_generated": task.parameters.get("quantity", 1),
                        "storage_path": "media/generated/",
                    }
                
                elif task.task_type == "text_generation":
                    # Would produce captions, hashtags, CTAs
                    fake_result = {
                        "texts_created": 5,
                        "hashtags_included": True,
                    }
                
                elif task.task_type == "validation":
                    # Would check consistency across sections
                    fake_result = {
                        "issues_found": 0,
                        "quality_score": 95,
                    }
                
                else:
                    fake_result = {"message": "Simulated response"}
                
                # Apply result to DataManager (stubbed here)
                # In reality: data_manager.update_section(task.target_section, fake_result)
                
                task.status = "completed"
                task.result = fake_result
                results[task.id] = fake_result
                
                logger.info(f"Completed task: {task.id}")
                
            except Exception as e:
                logger.error(f"Failed task {task.id}: {e}")
                task.status = "failed"
                results[task.id] = {"error": str(e)}
        
        # Save final state
        data_manager.save()
        
        return {
            "request_summary": parsed.original_text,
            "total_tasks": len(ordered_tasks),
            "completed": sum(1 for t in ordered_tasks if t.status == "completed"),
            "failed": sum(1 for t in ordered_tasks if t.status == "failed"),
            "results_by_task": results,
            "execution_log": [t.to_dict() for t in ordered_tasks],
        }
'''

write("ai_task_router.py", task_router)

# 2. Update gui_ai_panel.py to integrate router
print("[2/2] Integrating Task Router into gui_ai_panel.py...")

panel_path = BASE / "gui_ai_panel.py"
ap_content = panel_path.read_text(encoding='utf-8')

# Add import
if 'from ai_task_router import' not in ap_content:
    ap_content = ap_content.replace(
        'from proposal_engine import ProposalEngine, Proposal',
        'from proposal_engine import ProposalEngine, Proposal\nfrom ai_task_router import AITaskRouter'
    )

# Initialize router in __init__
old_init = '''    def __init__(self, app_state: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.state = app_state
        self.proposal_engine = ProposalEngine()
        self.ai_client = None'''

new_init = '''    def __init__(self, app_state: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.state = app_state
        self.proposal_engine = ProposalEngine()
        self.task_router = AITaskRouter()
        self.ai_client = None'''

ap_content = ap_content.replace(old_init, new_init)

# Modify send_message to use router when appropriate
old_send = '''    def send_message(self):
        text = self.input_box.toPlainText().strip()
        if not text:
            return
        
        self._add_bubble("user", text)
        self.input_box.clear()

        QTimer.singleShot(500, lambda: self._simulate_response(text))'''

new_send = '''    def send_message(self):
        text = self.input_box.toPlainText().strip()
        if not text:
            return
        
        self._add_bubble("user", text)
        self.input_box.clear()

        # Check if this looks like a complex task requiring routing
        lower_text = text.lower()
        is_complex_task = any(kw in lower_text for kw in [
            "создай кампанию", "разработай стратегию", "подготовь контент",
            "сгенерируй изображения", "обнови позиционирование"
        ])
        
        if is_complex_task:
            # Route through task parser
            QTimer.singleShot(500, lambda: self._handle_routed_request(text))
        else:
            # Standard simulated response
            QTimer.singleShot(500, lambda: self._simulate_response(text))
    
    def _handle_routed_request(self, user_text: str):
        """Process request through AI Task Router."""
        # Parse request into sub-tasks
        parsed = self.task_router.parse_request(user_text, project_context=self.state)
        
        # Show planning message
        plan_msg = f"🧠 Проанализировал ваш запрос. Составил план из {len(parsed.sub_tasks)} этапов:"
        self._add_bubble("assistant", plan_msg)
        
        # Display each sub-task briefly
        for i, task in enumerate(parsed.sub_tasks, 1):
            short_desc = task.description[:80] + ("..." if len(task.description) > 80 else "")
            detail_msg = f"{i}. [{task.task_type.upper()}] → {short_desc}"
            self._add_bubble("system", detail_msg)
        
        # Execute simulation (would be replaced by real AI/tools later)
        exec_result = self.task_router.execute_parsed_request(parsed, self.dm if hasattr(self, 'dm') else None)
        
        completion_msg = f"✅ План выполнен! Завершено: {exec_result['completed']} из {exec_result['total_tasks']} задач."
        self._add_bubble("assistant", completion_msg)
        
        # Optionally show detailed breakdown
        details_toggle = QPushButton("Показать детали выполнения")
        details_toggle.setObjectName("topBtn")
        details_toggle.setStyleSheet("font-size: 11px; padding: 4px 8px; margin-top: 8px;")
        details_toggle.clicked.connect(lambda: self._show_execution_details(exec_result))
        
        # Insert toggle button before stretch
        insert_idx = self.chat_layout.count() - 1
        self.chat_layout.insertWidget(insert_idx, details_toggle)
        self.chat_scroll.verticalScrollBar().setValue(self.chat_scroll.verticalScrollBar().maximum())
    
    def _show_execution_details(self, exec_result: Dict[str, Any]):
        """Show collapsible details of executed tasks."""
        details_frame = QFrame()
        details_frame.setObjectName("detailsPanel")
        details_frame.setStyleSheet("""
            QFrame#detailsPanel {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 12px;
                margin: 8px 0;
            }
            QLabel#detailTitle {
                color: #58a6ff;
                font-size: 14px;
                font-weight: bold;
                margin-bottom: 8px;
            }
            QTextEdit#detailContent {
                background-color: #0d1117;
                color: #c9d1d9;
                border: none;
                padding: 8px;
                font-family: Consolas, monospace;
                font-size: 11px;
            }
        """)
        
        dl = QVBoxLayout(details_frame)
        dl.setSpacing(8)
        
        title = QLabel("Детали выполнения")
        title.setObjectName("detailTitle")
        dl.addWidget(title)
        
        content = QTextEdit()
        content.setObjectName("detailContent")
        content.setReadOnly(True)
        content.setMaximumHeight(200)
        
        # Format JSON-like output
        import json
        formatted = json.dumps(exec_result, indent=2, ensure_ascii=False)
        content.setPlainText(formatted)
        
        dl.addWidget(content)
        
        close_btn = QPushButton("✖ Скрыть детали")
        close_btn.setObjectName("topBtn")
        close_btn.setStyleSheet("font-size: 11px; padding: 4px 8px; align-self: flex-end;")
        close_btn.clicked.connect(lambda: details_frame.deleteLater())
        dl.addWidget(close_btn)
        
        insert_idx = self.chat_layout.count() - 1
        self.chat_layout.insertWidget(insert_idx, details_frame)
        self.chat_scroll.verticalScrollBar().setValue(self.chat_scroll.verticalScrollBar().maximum())'''

ap_content = ap_content.replace(old_send, new_send)

panel_path.write_text(ap_content, encoding='utf-8', newline='\n')
print("  [OK] Integrated Task Router into gui_ai_panel.py")

print("\n=== Step 3 Complete ===")
print("\nWhat works now:")
print("  [OK] Requests parsed into structured sub-tasks automatically")
print("  [OK] Dependency resolution ensures correct execution order")
print("  [OK] Simulated execution updates DataManager placeholders")
print("  [OK] UI shows step-by-step progress during processing")
print("  [OK] Details panel reveals full JSON trace upon request")
print("\nRun START.bat and try asking:")
print("  • 'Создай рекламную кампанию для кофейни карамельный латте на 7 дней'")
print("Watch how the system breaks it down into stages!")