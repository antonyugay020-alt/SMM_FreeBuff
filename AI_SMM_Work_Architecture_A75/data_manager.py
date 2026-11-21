"""DataManager: Single source of truth for project data.
Shared across all sections to enable cross-section integration.
"""
import logging
import json
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class DataManager:
    """Central data store for a project. All sections read/write through this."""

    def __init__(self, project_id: str = "default", data_dir: Optional[str] = None):
        self.project_id = project_id
        self.data_dir = Path(data_dir) if data_dir else Path(__file__).resolve().parent.parent / "data" / "projects" / project_id
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory data (loaded from disk or initialized with demo data)
        self._data = {
            "strategy": self._default_strategy(),
            "content_plan": self._default_content_plan(),
            "calendar_events": self._default_calendar_events(),
            "shooting_tasks": self._default_shooting_tasks(),
            "media_sources": self._default_media_sources(),
            "media_references": self._default_media_references(),
            "media_ready": self._default_media_ready(),
            "publications": self._default_publications(),
            "other_files": self._default_other_files(),
        }
        
        self._load_from_disk()
        logger.info(f"DataManager initialized for project '{project_id}'")

    # === Default demo data ===
    def _default_strategy(self) -> Dict[str, Any]:
        return {
            "project_name": "Теннис",
            "version": "1.1",
            "updated": "12.11.2026",
            "sections": [
                {"id": "about", "title": "О проекте", "icon": "📋",
                 "content": "Семейный теннисный клуб «Чемпион» работает с 2018 года. Основная специализация — обучение детей и взрослых теннису с нуля до соревновательного уровня. В клубе 4 корта (2 закрытых, 2 открытых), профессиональные тренеры с опытом работы в детских спортивных школах."},
                {"id": "audience", "title": "Целевая аудитория", "icon": "👥",
                 "content": "Основной сегмент — родители детей 6-14 лет, которые ищут секцию для развития ребёнка. Они ценят профессиональный подход, безопасность и возможность отслеживать прогресс. Вторичный сегмент — взрослые любители 30-45 лет, играющие для здоровья и удовольствия."},
                {"id": "positioning", "title": "Позиционирование", "icon": "🎯",
                 "content": "«Первый шаг к большому теннису» — клуб, где каждый ученик получает персональный план развития. Мы не просто учим бить по мячу, мы воспитываем характер через спорт."},
                {"id": "utp", "title": "Уникальное торговое предложение", "icon": "💎",
                 "content": "Первое занятие бесплатно + персональный план развития для каждого ученика. Родители получают ежемесячный отчёт о прогрессе ребёнка с видеоанализом техники."},
                {"id": "tone", "title": "Tone of Voice", "icon": "🗣️",
                 "content": "Дружелюбный, мотивирующий, экспертный но не занудный. Мы говорим на языке родителей и детей, избегаем спортивного жаргона."},
                {"id": "visual", "title": "Визуальный стиль", "icon": "🎨",
                 "content": "Яркие цвета (оранжевый, синий, белый), динамичные фото, минимум текста на изображениях. Акцент на эмоциях."},
                {"id": "competitors", "title": "Анализ конкурентов", "icon": "🏆",
                 "content": "Клуб «А» — известный бренд, но дорого и нет детских групп. Школа «Б» — дешевле, но старые корты. Наше преимущество — баланс цены и качества, фокус на детях."},
                {"id": "channels", "title": "Каналы коммуникации", "icon": "📱",
                 "content": "Instagram — основной канал. VK — дополнительная аудитория. Telegram — быстрые новости. YouTube — длинные видео с советами тренеров."},
            ],
            "kpis": [
                {"metric": "Подписчики Instagram", "current": "3200", "target": "5000", "deadline": "31.12.2026"},
                {"metric": "Охват постов", "current": "7500", "target": "10000", "deadline": "31.12.2026"},
                {"metric": "Записи на пробное", "current": "35/мес", "target": "50/мес", "deadline": "31.12.2026"},
            ],
            "versions": [
                {"version": "1.0", "date": "10.11.2026", "author": "AI + Антон", "changes": "Первичная версия"},
                {"version": "1.1", "date": "12.11.2026", "author": "Антон", "changes": "Добавлен сегмент 'молодые мамы'"},
            ],
        }

    def _default_content_plan(self) -> List[Dict[str, Any]]:
        return [
            {"id": "cp_001", "date": "15.11.2026", "rubric": "Польза", "topic": "5 упражнений для укрепления запястья", "format": "Пост", "status": "Одобрено", "responsible": "Антон", "strategy_link": "utp", "shooting_task_id": "st_001"},
            {"id": "cp_002", "date": "16.11.2026", "rubric": "Развлечение", "topic": "Смешные моменты с тренировок", "format": "Reels", "status": "В работе", "responsible": "Марина", "strategy_link": "tone", "shooting_task_id": None},
            {"id": "cp_003", "date": "17.11.2026", "rubric": "Продажа", "topic": "Акция: первое занятие бесплатно", "format": "Stories", "status": "Запланировано", "responsible": "Антон", "strategy_link": "utp", "shooting_task_id": None},
            {"id": "cp_004", "date": "18.11.2026", "rubric": "Личное", "topic": "История успеха ученика Максима", "format": "Пост", "status": "Черновик", "responsible": "Марина", "strategy_link": "about", "shooting_task_id": None},
            {"id": "cp_005", "date": "19.11.2026", "rubric": "Польза", "topic": "Как выбрать ракетку новичку", "format": "Reels", "status": "Запланировано", "responsible": "Антон", "strategy_link": "audience", "shooting_task_id": None},
            {"id": "cp_006", "date": "20.11.2026", "rubric": "Развлечение", "topic": "Закулисье турнира", "format": "Stories", "status": "В работе", "responsible": "Марина", "strategy_link": "visual", "shooting_task_id": "st_002"},
            {"id": "cp_007", "date": "21.11.2026", "rubric": "Продажа", "topic": "Открытие новой группы для детей 6-8 лет", "format": "Пост", "status": "Черновик", "responsible": "Антон", "strategy_link": "audience", "shooting_task_id": "st_003"},
        ]

    def _default_calendar_events(self) -> List[Dict[str, Any]]:
        return [
            {"id": "ev_001", "date": "15.11.2026", "time": "10:00", "type": "publication", "title": "Пост: 5 упражнений для запястья", "description": "Публикация в Instagram", "link": "cp_001"},
            {"id": "ev_002", "date": "15.11.2026", "time": "14:00", "type": "shooting", "title": "Съёмка тренировки группы 6-8 лет", "description": "Фото и видео для Stories", "link": "st_001"},
            {"id": "ev_003", "date": "16.11.2026", "time": "12:00", "type": "meeting", "title": "Встреча с тренером Мариной", "description": "Обсуждение плана на декабрь", "link": None},
            {"id": "ev_004", "date": "17.11.2026", "time": "09:00", "type": "publication", "title": "Stories: Акция первое занятие бесплатно", "description": "Серия из 3 stories", "link": "cp_003"},
            {"id": "ev_005", "date": "18.11.2026", "time": "16:00", "type": "brand_event", "title": "Турнир среди юниоров", "description": "Ежемесячный турнир клуба", "link": None},
            {"id": "ev_006", "date": "19.11.2026", "time": "11:00", "type": "publication", "title": "Reels: Как выбрать ракетку новичку", "description": "Видео-совет от тренера", "link": "cp_005"},
            {"id": "ev_007", "date": "20.11.2026", "time": "15:00", "type": "shooting", "title": "Съёмка закулисья турнира", "description": "Фотоотчёт для ленты", "link": "st_002"},
            {"id": "ev_008", "date": "21.11.2026", "time": "10:00", "type": "publication", "title": "Пост: Открытие новой группы 6-8 лет", "description": "Анонс новой группы", "link": "cp_007"},
            {"id": "ev_009", "date": "22.11.2026", "time": "12:00", "type": "meeting", "title": "Планёрка команды", "description": "Еженедельная встреча", "link": None},
            {"id": "ev_010", "date": "25.11.2026", "time": "18:00", "type": "brand_event", "title": "День открытых дверей", "description": "Бесплатные пробные занятия", "link": None},
        ]

    def _default_shooting_tasks(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "st_001", "date": "15.11.2026", "time": "14:00", "location": "Корт №2 (закрытый)",
                "type": "Фото + Видео", "content_plan_link": "cp_001", "status": "Снято",
                "team": "Фотограф: Марина, Модель: Максим (ученик)", "priority": "Высокий",
                "budget": "5000 ₽", "duration": "2 часа",
                "shots": [
                    {"num": 1, "desc": "Крупный план: упражнение с эспандером", "ref": "ref_wrist_01.jpg", "priority": "Высокий", "status": "Снято"},
                    {"num": 2, "desc": "Средний план: тренер показывает технику", "ref": "ref_coach_02.jpg", "priority": "Высокий", "status": "Снято"},
                    {"num": 3, "desc": "Общий план: ребёнок выполняет упражнение", "ref": None, "priority": "Средний", "status": "Снято"},
                    {"num": 4, "desc": "Детали: руки, ракетка, мяч", "ref": "ref_details_03.jpg", "priority": "Низкий", "status": "Снято"},
                ],
                "tech_req": "Формат: JPEG + RAW, Ориентация: вертикальная 4:5, Разрешение: 4000x5000",
                "notes": "Свет естественный + софтбокс. Акцент на эмоциях ребёнка.",
            },
            {
                "id": "st_002", "date": "20.11.2026", "time": "15:00", "location": "Турнирный корт",
                "type": "Видео", "content_plan_link": "cp_006", "status": "Согласовано",
                "team": "Оператор: Антон, Ассистент: Ирина", "priority": "Средний",
                "budget": "3000 ₽", "duration": "3 часа",
                "shots": [
                    {"num": 1, "desc": "Подготовка участников (разминка)", "ref": None, "priority": "Высокий", "status": "Нужен"},
                    {"num": 2, "desc": "Эмоции во время матча", "ref": "ref_emotions_01.jpg", "priority": "Высокий", "status": "Нужен"},
                    {"num": 3, "desc": "Награждение победителей", "ref": None, "priority": "Средний", "status": "Нужен"},
                    {"num": 4, "desc": "Интервью с участниками", "ref": None, "priority": "Низкий", "status": "Нужен"},
                ],
                "tech_req": "Формат: MP4 (H.264), Разрешение: 1080x1920 (вертикальное), FPS: 30",
                "notes": "Снимать на стабилизатор. Звук через петличку.",
            },
            {
                "id": "st_003", "date": "25.11.2026", "time": "10:00", "location": "Главный корт + раздевалка",
                "type": "Фото", "content_plan_link": "cp_007", "status": "Черновик",
                "team": "Фотограф: Марина", "priority": "Высокий",
                "budget": "4000 ₽", "duration": "2 часа",
                "shots": [
                    {"num": 1, "desc": "Групповое фото детей с тренером", "ref": None, "priority": "Высокий", "status": "Нужен"},
                    {"num": 2, "desc": "Дети играют в теннис (динамика)", "ref": "ref_kids_play_01.jpg", "priority": "Высокий", "status": "Нужен"},
                    {"num": 3, "desc": "Детали: детская ракетка, мячи, форма", "ref": None, "priority": "Средний", "status": "Нужен"},
                    {"num": 4, "desc": "Интерьер: корт, раздевалка, зона ожидания", "ref": None, "priority": "Низкий", "status": "Нужен"},
                ],
                "tech_req": "Формат: JPEG + RAW, Ориентация: горизонтальная 16:9 и квадрат 1:1",
                "notes": "Яркие цвета, акцент на радости детей. Минимум постановки.",
            },
        ]

    def _default_media_sources(self) -> List[Dict[str, Any]]:
        return [
            {"id": "src_001", "name": "raw_001.jpg", "type": "image", "size": "4032x3024", "date": "15.11.2026", "shooting_task": "st_001"},
            {"id": "src_002", "name": "raw_002.jpg", "type": "image", "size": "4032x3024", "date": "15.11.2026", "shooting_task": "st_001"},
            {"id": "src_003", "name": "raw_003.mp4", "type": "video", "size": "1920x1080", "date": "14.10.2026", "shooting_task": None},
            {"id": "src_004", "name": "raw_004.jpg", "type": "image", "size": "3024x4032", "date": "14.10.2026", "shooting_task": None},
            {"id": "src_005", "name": "raw_005.jpg", "type": "image", "size": "4032x3024", "date": "13.10.2026", "shooting_task": None},
            {"id": "src_006", "name": "raw_006.mp4", "type": "video", "size": "1080x1920", "date": "13.10.2026", "shooting_task": None},
        ]

    def _default_media_references(self) -> List[Dict[str, Any]]:
        return [
            {"id": "ref_001", "name": "ref_cafe_style.jpg", "type": "image", "category": "Лента", "size": "1080x1080"},
            {"id": "ref_002", "name": "ref_reels_example.mp4", "type": "video", "category": "Reels", "size": "1080x1920"},
            {"id": "ref_003", "name": "ref_stories_mood.jpg", "type": "image", "category": "Stories", "size": "1080x1920"},
            {"id": "ref_004", "name": "ref_color_palette.jpg", "type": "image", "category": "Общий", "size": "1920x1080"},
        ]

    def _default_media_ready(self) -> List[Dict[str, Any]]:
        return [
            {"id": "ready_001", "name": "tennis_001.jpg", "status": "approved", "type": "image", "size": "1920x2560", "date": "15.11.2026"},
            {"id": "ready_002", "name": "tennis_002.jpg", "status": "approved", "type": "image", "size": "1920x2560", "date": "15.11.2026"},
            {"id": "ready_003", "name": "reels_001.mp4", "status": "approved", "type": "video", "size": "1080x1920", "date": "16.11.2026"},
            {"id": "ready_004", "name": "coffee_story.jpg", "status": "pending", "type": "image", "size": "1080x1920", "date": "17.11.2026"},
            {"id": "ready_005", "name": "room_001.jpg", "status": "rejected", "type": "image", "size": "1920x2560", "date": "17.11.2026"},
        ]

    def _default_publications(self) -> Dict[str, Any]:
        return {
            "folders": {
                "stories": {"name": "Stories", "icon": "📷", "desc": "Фото и короткие видео (до 60 сек)", "color": "#9e6a03",
                            "items": [{"name": "coffee_story.jpg", "time": "18:00", "date": "17.11.2026"}]},
                "reels": {"name": "Reels", "icon": "🎬", "desc": "Вертикальные видео (до 90 сек)", "color": "#1f6feb",
                          "items": [{"name": "reels_001.mp4", "time": "15:45", "date": "16.11.2026"}]},
                "feed": {"name": "Лента", "icon": "📰", "desc": "Фото и видео (1:1, 4:5, 16:9)", "color": "#238636",
                         "items": [{"name": "tennis_001.jpg", "time": "12:00", "date": "15.11.2026"},
                                   {"name": "tennis_002.jpg", "time": "12:00", "date": "15.11.2026"}]},
            },
            "schedule": {"timezone": "(UTC+6:00) Алматы", "period": "Ежедневно", "times": ["12:00", "18:00"]},
        }

    def _default_other_files(self) -> Dict[str, List[Dict[str, Any]]]:
        return {
            "archive": [
                {"name": "campaign_summer_2025.zip", "type": "archive", "size": "245 MB", "date": "15.08.2025", "tags": ["архив", "лето2025"]},
                {"name": "old_logo_variants.psd", "type": "image", "size": "12 MB", "date": "10.03.2025", "tags": ["логотип", "дизайн"]},
            ],
            "buffer": [
                {"name": "random_photo_001.jpg", "type": "image", "size": "3.2 MB", "date": "10.11.2026", "tags": ["буфер"]},
                {"name": "meeting_notes.docx", "type": "document", "size": "156 KB", "date": "08.11.2026", "tags": ["встреча", "заметки"]},
            ],
            "documents": [
                {"name": "brand_guidelines_v2.pdf", "type": "document", "size": "8.5 MB", "date": "01.09.2026", "tags": ["бренд", "гайдлайн"]},
                {"name": "contract_photographer.pdf", "type": "document", "size": "245 KB", "date": "15.10.2026", "tags": ["договор", "фотограф"]},
                {"name": "brief_november.docx", "type": "document", "size": "89 KB", "date": "01.11.2026", "tags": ["бриф", "ноябрь"]},
            ],
            "references": [
                {"name": "moodboard_tennis.jpg", "type": "image", "size": "5.1 MB", "date": "20.10.2026", "tags": ["мудборд", "теннис"]},
                {"name": "color_palette.png", "type": "image", "size": "1.2 MB", "date": "20.10.2026", "tags": ["цвета", "палитра"]},
                {"name": "font_examples.pdf", "type": "document", "size": "3.4 MB", "date": "20.10.2026", "tags": ["шрифты", "типографика"]},
            ],
            "templates": [
                {"name": "instagram_post_template.psd", "type": "image", "size": "15 MB", "date": "01.10.2026", "tags": ["шаблон", "instagram"]},
                {"name": "stories_template.psd", "type": "image", "size": "8 MB", "date": "01.10.2026", "tags": ["шаблон", "stories"]},
            ],
        }

    # === Persistence ===
    def _load_from_disk(self):
        data_file = self.data_dir / "project_data.json"
        if data_file.exists():
            try:
                with open(data_file, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                self._data.update(saved)
                logger.info(f"Loaded project data from {data_file}")
            except Exception as e:
                logger.warning(f"Failed to load project data: {e}")

    def update_strategy(self, new_data: Dict[str, Any]) -> bool:
        """Update strategy section with new content from AI."""
        if not isinstance(new_data, dict):
            logger.warning("update_strategy expects a dict")
            return False
        
        current = self._data.get("strategy", {})
        current.update(new_data)
        self._data["strategy"] = current
        self.save()
        logger.info(f"Strategy updated: keys={list(new_data.keys())}")
        return True

    def add_content_plan_item(self, item: Dict[str, Any]) -> str:
        """Add a single item to content plan. Returns created ID."""
        existing_ids = [cp["id"] for cp in self._data.get("content_plan", [])]
        
        # Generate unique ID
        counter = len(existing_ids) + 1
        new_id = f"cp_{counter:03d}"
        while new_id in existing_ids:
            counter += 1
            new_id = f"cp_{counter:03d}"
        
        item["id"] = new_id
        item.setdefault("status", "Planned")
        item.setdefault("source", "Manual")
        
        self._data.setdefault("content_plan", []).append(item)
        self.save()
        logger.info(f"Added content plan item: {new_id} ({item.get('topic', '')[:30]})")
        return new_id

    def get_calendar_events(self):
        """Return calendar events list."""
        return self._data.setdefault("calendar", [])

    def add_calendar_event(self, event):
        """Add event to calendar section. Returns created id."""
        events = self._data.setdefault("calendar", [])
        existing = [e.get("id") for e in events if isinstance(e, dict)]
        counter = len(events) + 1
        new_id = f"ev_{counter:03d}"
        while new_id in existing:
            counter += 1
            new_id = f"ev_{counter:03d}"
        event["id"] = new_id
        event.setdefault("status", "Planned")
        event.setdefault("source", "Manual")
        events.append(event)
        self.save()
        logger.info(f"Added calendar event: {new_id} ({event.get('date','')} {str(event.get('title',''))[:30]})")
        return new_id

    def save(self):
        data_file = self.data_dir / "project_data.json"
        try:
            with open(data_file, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved project data to {data_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to save project data: {e}")
            return False

    # === Getters (sections read through these) ===
    def get_strategy(self) -> Dict[str, Any]:
        return self._data["strategy"]

    def get_content_plan(self) -> List[Dict[str, Any]]:
        return self._data["content_plan"]

    def get_content_plan_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        for item in self._data["content_plan"]:
            if item.get("id") == item_id:
                return item
        return None

    def get_calendar_events(self) -> List[Dict[str, Any]]:
        return self._data["calendar_events"]

    def get_shooting_tasks(self) -> List[Dict[str, Any]]:
        return self._data["shooting_tasks"]

    def get_shooting_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        for task in self._data["shooting_tasks"]:
            if task.get("id") == task_id:
                return task
        return None

    def get_media_sources(self) -> List[Dict[str, Any]]:
        return self._data["media_sources"]

    def get_media_references(self) -> List[Dict[str, Any]]:
        return self._data["media_references"]

    def get_media_ready(self) -> List[Dict[str, Any]]:
        return self._data["media_ready"]

    def get_publications(self) -> Dict[str, Any]:
        return self._data["publications"]

    def get_other_files(self, folder: str = None) -> Any:
        if folder:
            return self._data["other_files"].get(folder, [])
        return self._data["other_files"]

    # === Actions (cross-section integration) ===
    def create_shooting_task_from_content_plan(self, cp_item_id: str) -> Dict[str, Any]:
        """Create a new shooting task linked to a content plan item."""
        cp_item = self.get_content_plan_item(cp_item_id)
        if not cp_item:
            return None

        # Generate new task ID
        existing_ids = [t["id"] for t in self._data["shooting_tasks"]]
        new_num = len(existing_ids) + 1
        new_id = f"st_{new_num:03d}"

        # Auto-fill from content plan
        new_task = {
            "id": new_id,
            "date": cp_item["date"],
            "time": "10:00",
            "location": "Уточнить",
            "type": "Фото" if cp_item["format"] == "Пост" else "Видео" if cp_item["format"] == "Reels" else "Фото + Видео",
            "content_plan_link": cp_item_id,
            "status": "Черновик",
            "team": "Уточнить",
            "priority": "Средний",
            "budget": "0 ₽",
            "duration": "2 часа",
            "shots": [
                {"num": 1, "desc": f"Основной кадр: {cp_item['topic']}", "ref": None, "priority": "Высокий", "status": "Нужен"},
            ],
            "tech_req": "Уточнить по формату",
            "notes": f"Создано из контент-плана: {cp_item['topic']}",
        }

        self._data["shooting_tasks"].append(new_task)

        # Also create a calendar event for the shooting
        new_event = {
            "id": f"ev_sh_{new_num:03d}",
            "date": cp_item["date"],
            "time": new_task["time"],
            "type": "shooting",
            "title": f"Съёмка: {cp_item['topic']}",
            "description": f"Для публикации: {cp_item['topic']}",
            "link": new_id,
        }
        self._data["calendar_events"].append(new_event)

        # Link content plan item to the new task
        cp_item["shooting_task_id"] = new_id

        self.save()
        logger.info(f"Created shooting task {new_id} from content plan {cp_item_id}")
        return new_task

    def move_media_ready_to_publication(self, media_id: str, folder_id: str, time: str = "12:00"):
        """Move a ready media item to a publication folder."""
        media = None
        for m in self._data["media_ready"]:
            if m.get("id") == media_id:
                media = m
                break
        if not media:
            return False

        folders = self._data["publications"]["folders"]
        if folder_id not in folders:
            return False

        # Add to folder
        folders[folder_id]["items"].append({
            "name": media["name"],
            "time": time,
            "date": datetime.now().strftime("%d.%m.%Y"),
        })

        # Also add to calendar if not already there
        today = datetime.now().strftime("%d.%m.%Y")
        already_in_calendar = any(
            e.get("type") == "publication" and e.get("date") == today
            for e in self._data["calendar_events"]
        )
        if not already_in_calendar:
            self._data["calendar_events"].append({
                "id": f"ev_pub_{len(self._data['calendar_events']) + 1:03d}",
                "date": today,
                "time": time,
                "type": "publication",
                "title": f"Публикация: {media['name']}",
                "description": f"Папка: {folders[folder_id]['name']}",
                "link": None,
            })

        self.save()
        logger.info(f"Moved {media['name']} to publication folder {folder_id}")
        return True

    def get_strategy_section_by_id(self, section_id: str) -> Optional[Dict[str, Any]]:
        """Get a strategy section by its ID (for linking from content plan)."""
        for section in self._data["strategy"].get("sections", []):
            if section.get("id") == section_id:
                return section
        return None

    def add_media_source(self, file_path: str) -> Dict[str, Any]:
        """Import a real file into media sources. Returns the new source record."""
        src = Path(file_path)
        if not src.exists():
            return None
        
        # Copy to media/images/
        media_dir = Path(__file__).resolve().parent / "media" / "images"
        media_dir.mkdir(parents=True, exist_ok=True)
        dest = media_dir / src.name
        
        # Avoid overwriting
        counter = 1
        while dest.exists():
            stem = src.stem
            suffix = src.suffix
            dest = media_dir / f"{stem}_{counter}{suffix}"
            counter += 1
        
        shutil.copy2(src, dest)
        
        # Detect type
        ftype = "video" if dest.suffix.lower() in (".mp4", ".mov", ".avi", ".mkv") else "image"
        
        # Create record
        new_source = {
            "id": f"src_{len(self._data['media_sources']) + 1:03d}",
            "name": dest.name,
            "type": ftype,
            "size": "unknown",
            "date": Path(src).stat().st_mtime and __import__('datetime').datetime.fromtimestamp(
                Path(src).stat().st_mtime
            ).strftime("%d.%m.%Y"),
            "shooting_task": None,
        }
        
        self._data["media_sources"].append(new_source)
        self.save()
        
        logger.info(f"Imported {src.name} -> {dest.name}")
        return new_source

    def create_shooting_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new shooting task from form data. Returns the created task."""
        existing_ids = [t["id"] for t in self._data["shooting_tasks"]]
        new_num = len(existing_ids) + 1
        new_id = f"st_{new_num:03d}"
        
        new_task = {
            "id": new_id,
            "date": task_data.get("date", ""),
            "time": task_data.get("time", "10:00"),
            "location": task_data.get("location", ""),
            "type": task_data.get("type", "Фото"),
            "content_plan_link": task_data.get("content_plan_link", None),
            "status": "Черновик",
            "team": task_data.get("team", ""),
            "priority": task_data.get("priority", "Средний"),
            "budget": task_data.get("budget", "0 ₽"),
            "duration": task_data.get("duration", "2 часа"),
            "shots": [],
            "tech_req": task_data.get("tech_req", ""),
            "notes": task_data.get("notes", ""),
        }
        
        self._data["shooting_tasks"].append(new_task)
        
        # Also create a calendar event for the shooting
        new_event = {
            "id": f"ev_sh_{new_num:03d}",
            "date": new_task["date"],
            "time": new_task["time"],
            "type": "shooting",
            "title": f"Съёмка: {new_task['location'] or 'ТЗ'}",
            "description": f"Задание {new_id} · {new_task['type']}",
            "link": new_id,
        }
        self._data["calendar_events"].append(new_event)
        
        # If linked to content plan, update that item
        if new_task["content_plan_link"]:
            cp_item = self.get_content_plan_item(new_task["content_plan_link"])
            if cp_item:
                cp_item["shooting_task_id"] = new_id
        
        self.save()
        logger.info(f"Created shooting task {new_id} with calendar event")
        return new_task


    def get_stats(self) -> Dict[str, int]:
        """Get project stats for the left panel."""
        return {
            "sources": len(self._data["media_sources"]),
            "ready": len(self._data["media_ready"]),
            "pending": sum(1 for m in self._data["media_ready"] if m.get("status") == "pending"),
            "scheduled": sum(1 for item in self._data["content_plan"] if item.get("status") in ("Запланировано", "В работе")),
        }
