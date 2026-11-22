"""DataManager: Single source of truth for project data.
Shared across all sections to enable cross-section integration.
"""
import logging
import json
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from storage import ProjectStore

logger = logging.getLogger(__name__)


class DataManager:
    """Central data store for a project. All sections read/write through this."""

    def __init__(self, project_id: str = "default", data_dir: Optional[str] = None):
        self.project_id = project_id
        self.data_dir = Path(data_dir) if data_dir else Path(__file__).resolve().parent.parent / "data" / "projects" / project_id
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.store = ProjectStore(self.data_dir)
        
        # In-memory data (loaded from disk or initialized with demo data)
        self._data = {
            "strategy": self._default_strategy(),
            "content_plan": self._default_content_plan(),
            "post_metrics": [],
            "calendar_events": self._default_calendar_events(),
            "shooting_tasks": self._default_shooting_tasks(),
            "media_sources": self._default_media_sources(),
            "media_references": self._default_media_references(),
            "media_ready": self._default_media_ready(),
            "publications": self._default_publications(),
            "other_files": self._default_other_files(),
        }
        
        self._load_from_disk()
        self._migrate_legacy_calendar()
        logger.info(f"DataManager initialized for project '{project_id}'")

    def _migrate_legacy_calendar(self):
        """Merge events saved under the old 'calendar' key into 'calendar_events'."""
        legacy = self._data.pop("calendar", None)
        if not legacy:
            return
        target = self._data.setdefault("calendar_events", [])
        known = {e.get("id") for e in target if isinstance(e, dict)}
        for event in legacy:
            if not isinstance(event, dict):
                continue
            if not event.get("id") or event.get("id") in known:
                # Overlapping IDs are common: keep the event with a fresh ID
                counter = len(target) + 1
                new_id = f"ev_legacy_{counter:03d}"
                while new_id in known:
                    counter += 1
                    new_id = f"ev_legacy_{counter:03d}"
                event["id"] = new_id
            event.setdefault("time", "12:00")
            event.setdefault("description", "")
            event.setdefault("type", "publication")
            event.setdefault("title", "Событие")
            known.add(event["id"])
            target.append(event)
        self.save()

    # === Default (empty) project template ===
    def _default_strategy(self) -> Dict[str, Any]:
        return {
            "project_name": "",
            "version": "",
            "updated": "",
            "sections": [],
            "kpis": [],
            "versions": [],
        }

    def _default_content_plan(self) -> List[Dict[str, Any]]:
        return []

    def _default_calendar_events(self) -> List[Dict[str, Any]]:
        return []

    def _default_shooting_tasks(self) -> List[Dict[str, Any]]:
        return []

    def _default_media_sources(self) -> List[Dict[str, Any]]:
        return []

    def _default_media_references(self) -> List[Dict[str, Any]]:
        return []

    def _default_media_ready(self) -> List[Dict[str, Any]]:
        return []

    def _default_publications(self) -> Dict[str, Any]:
        return {
            "folders": {
                "stories": {"name": "Stories", "icon": "📷",
                            "desc": "Фото и короткие видео (до 60 сек)",
                            "color": "#9e6a03", "items": []},
                "reels": {"name": "Reels", "icon": "🎬",
                          "desc": "Вертикальные видео (до 90 сек)",
                          "color": "#1f6feb", "items": []},
                "feed": {"name": "Лента", "icon": "📰",
                         "desc": "Фото и видео (1:1, 4:5, 16:9)",
                         "color": "#238636", "items": []},
            },
            "schedule": {"timezone": "(UTC+6:00) Алматы", "period": "Ежедневно",
                         "times": ["12:00", "18:00"]},
        }

    def _default_other_files(self) -> Dict[str, List[Dict[str, Any]]]:
        return {"archive": [], "buffer": [], "documents": [], "references": [], "templates": []}

    # === Persistence ===
    def _load_from_disk(self):
        """Load from SQLite. The first run imports legacy project_data.json once."""
        data_file = self.data_dir / "project_data.json"
        try:
            if self.store.migrate_if_needed(data_file):
                logger.info(f"Migrated project '{self.project_id}' from JSON to SQLite")
        except Exception as e:
            logger.error(f"Migration failed, falling back to JSON: {e}")

        try:
            loaded = self.store.load()
            if loaded:
                self._data.update(loaded)
                logger.info(f"Loaded project data from {self.store.path}")
                return
        except Exception as e:
            logger.error(f"Failed to load project from SQLite: {e}")

        if data_file.exists():
            try:
                with open(data_file, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                self._data.update(saved)
                logger.warning(f"Loaded project data from legacy JSON {data_file}")
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
        item.setdefault("status", "Запланировано")
        item.setdefault("source", "Manual")
        
        self._data.setdefault("content_plan", []).append(item)
        self.save()
        logger.info(f"Added content plan item: {new_id} ({item.get('topic', '')[:30]})")
        return new_id

    def add_calendar_event(self, event):
        """Add event to calendar section. Returns created id."""
        events = self._data.setdefault("calendar_events", [])
        existing = [e.get("id") for e in events if isinstance(e, dict)]
        counter = len(events) + 1
        new_id = f"ev_{counter:03d}"
        while new_id in existing:
            counter += 1
            new_id = f"ev_{counter:03d}"
        event["id"] = new_id
        event.setdefault("status", "Запланировано")
        event.setdefault("source", "Manual")
        events.append(event)
        self.save()
        logger.info(f"Added calendar event: {new_id} ({event.get('date','')} {str(event.get('title',''))[:30]})")
        return new_id

    def save(self):
        """Write the whole project into SQLite in one transaction."""
        try:
            self.store.save(self._data)
            logger.info(f"Saved project data to {self.store.path}")
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

    def get_post_metrics(self) -> List[Dict[str, Any]]:
        """Замеры по опубликованным постам (одна запись на позицию плана)."""
        return self._data.get("post_metrics", [])

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

    def get_brand_profile(self) -> Dict[str, Any]:
        try:
            return self.store.load_brand_profile() or {}
        except Exception as e:
            logger.error(f"Failed to load brand profile: {e}")
            return {}

    def save_brand_profile(self, profile: Dict[str, Any]) -> bool:
        try:
            self.store.save_brand_profile(profile)
            return True
        except Exception as e:
            logger.error(f"Failed to save brand profile: {e}")
            return False

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

    def update_strategy_section(self, section_id: str, content: str) -> bool:
        """Write text into an existing strategy section. Returns True if found."""
        section = self.get_strategy_section_by_id(section_id)
        if section is None or not content:
            return False
        section["content"] = content.strip()
        self._data["strategy"]["updated"] = datetime.now().strftime("%d.%m.%Y")
        self.save()
        return True

    def add_media_source(self, file_path: str) -> Dict[str, Any]:
        """Import a real file into media sources. Returns the new source record."""
        src = Path(file_path)
        if not src.exists():
            return None
        
        # Copy to the shared media/images/ folder used by the GUI sections
        media_dir = Path(__file__).resolve().parent.parent / "media" / "images"
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
            "path": str(dest),
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
