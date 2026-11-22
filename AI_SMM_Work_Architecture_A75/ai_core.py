"""AI core: providers, 4-layer router, tool registry, action journal, budget.

Layers (work/PLAN.md, step 3):
  1. rules   — regex intents, no model
  2. local   — Ollama returns JSON {tool, args, confidence}
  3. cloud   — same contract, only when local is unsure/unavailable and budget allows
  4. editor  — no model: validates tool + args, asks a clarifying question instead of guessing

Every executed tool writes one `actions_log` row with an `undo` operation; undo itself
is journaled. Cloud spending is recorded in `data/app.db` (`ai_usage`) and hard-stopped
at the monthly limit from settings.
"""
from __future__ import annotations

import copy
import json
import logging
import os
import re
import shutil
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

CONFIDENCE_MIN = 0.7
APP_DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS ai_usage (
    id         TEXT PRIMARY KEY,
    ts         TEXT,
    project_id TEXT,
    purpose    TEXT,
    provider   TEXT,
    model      TEXT,
    tokens_in  INTEGER,
    tokens_out INTEGER,
    cost_usd   REAL,
    ok         INTEGER,
    error      TEXT
);
"""


@dataclass
class LLMResult:
    text: str
    provider: str
    model: str
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0
    error: str = ""


# === Providers ===

class OllamaProvider:
    """Local Ollama over /api/chat. No cost."""

    name = "ollama"

    def __init__(self, host: str = "http://localhost:11434", model: str = "qwen2.5:7b-instruct",
                 timeout: int = 120):
        self.host = host.rstrip("/")
        self.model = model
        self.timeout = timeout

    def available(self) -> bool:
        try:
            return requests.get(f"{self.host}/api/tags", timeout=3).status_code == 200
        except Exception:
            return False

    def chat(self, system: str, user: str, temperature: float = 0.2,
             max_tokens: int = 2048) -> LLMResult:
        started = time.time()
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        try:
            resp = requests.post(f"{self.host}/api/chat", json=payload, timeout=self.timeout)
            data = resp.json()
            text = (data.get("message") or {}).get("content", "")
            return LLMResult(text=text, provider=self.name, model=self.model,
                             tokens_in=int(data.get("prompt_eval_count") or 0),
                             tokens_out=int(data.get("eval_count") or 0),
                             latency_ms=int((time.time() - started) * 1000),
                             error="" if resp.status_code == 200 else f"HTTP {resp.status_code}")
        except Exception as exc:
            return LLMResult(text="", provider=self.name, model=self.model,
                             latency_ms=int((time.time() - started) * 1000), error=str(exc))


class CloudProvider:
    """OpenAI-compatible /chat/completions. Key comes from env, never from the project."""

    name = "cloud"

    def __init__(self, endpoint: str, model: str, api_key: str = "", timeout: int = 120,
                 input_price_per_1k: float = 0.0008, output_price_per_1k: float = 0.004):
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.api_key = api_key or os.environ.get("AI_SMM_CLOUD_KEY") or os.environ.get("OPENAI_API_KEY", "")
        self.timeout = timeout
        self.input_price = input_price_per_1k
        self.output_price = output_price_per_1k

    def available(self) -> bool:
        return bool(self.api_key and self.endpoint)

    def chat(self, system: str, user: str, temperature: float = 0.2,
             max_tokens: int = 2048) -> LLMResult:
        if not self.available():
            return LLMResult(text="", provider=self.name, model=self.model,
                             error="нет ключа или эндпоинта")
        started = time.time()
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        try:
            resp = requests.post(
                f"{self.endpoint}/chat/completions", json=payload, timeout=self.timeout,
                headers={"Content-Type": "application/json",
                         "Authorization": f"Bearer {self.api_key}"})
            data = resp.json()
            usage = data.get("usage") or {}
            tokens_in = int(usage.get("prompt_tokens") or 0)
            tokens_out = int(usage.get("completion_tokens") or 0)
            cost = tokens_in / 1000 * self.input_price + tokens_out / 1000 * self.output_price
            return LLMResult(
                text=data["choices"][0]["message"]["content"],
                provider=self.name, model=self.model,
                tokens_in=tokens_in, tokens_out=tokens_out, cost_usd=cost,
                latency_ms=int((time.time() - started) * 1000),
                error="" if resp.status_code == 200 else f"HTTP {resp.status_code}")
        except Exception as exc:
            return LLMResult(text="", provider=self.name, model=self.model,
                             latency_ms=int((time.time() - started) * 1000), error=str(exc))


class StubProvider:
    """Deterministic replies for tests and offline demos."""

    name = "stub"

    def __init__(self, replies: Optional[List[str]] = None):
        self.replies = list(replies or [])
        self.calls: List[Tuple[str, str]] = []

    def available(self) -> bool:
        return True

    def chat(self, system: str, user: str, temperature: float = 0.2,
             max_tokens: int = 2048) -> LLMResult:
        self.calls.append((system, user))
        text = self.replies.pop(0) if self.replies else "{}"
        return LLMResult(text=text, provider=self.name, model="stub",
                         tokens_in=len(user) // 4, tokens_out=len(text) // 4)


# === Budget ===

class BudgetGuard:
    """Monthly cloud spending, stored in the shared app.db."""

    def __init__(self, path: Path, limit: float):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.limit = float(limit or 0)
        self.conn = sqlite3.connect(str(self.path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(APP_DB_SCHEMA)
        self.conn.commit()

    def spent_month(self) -> float:
        month = datetime.now().strftime("%Y-%m")
        row = self.conn.execute(
            "SELECT COALESCE(SUM(cost_usd), 0) FROM ai_usage WHERE ts LIKE ?",
            (month + "%",)).fetchone()
        return float(row[0] or 0)

    def can_spend(self) -> bool:
        return self.limit <= 0 or self.spent_month() < self.limit

    def record(self, project_id: str, purpose: str, result: LLMResult) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT INTO ai_usage (id, ts, project_id, purpose, provider, model,"
                " tokens_in, tokens_out, cost_usd, ok, error) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (uuid.uuid4().hex[:12], datetime.now().isoformat(timespec="seconds"),
                 project_id, purpose, result.provider, result.model,
                 result.tokens_in, result.tokens_out, result.cost_usd,
                 0 if result.error else 1, result.error))

    def close(self) -> None:
        self.conn.close()


# === Journal ===

class ActionJournal:
    """actions_log rows: one per executed tool, with an undo operation."""

    def __init__(self, store):
        self.store = store

    def log(self, tool: str, args: Dict[str, Any], effect: Dict[str, Any],
            undo: Dict[str, Any], actor: str = "ai", status: str = "done") -> str:
        action_id = f"act_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:4]}"
        with self.store.conn:
            self.store.conn.execute(
                "INSERT INTO actions_log (id, ts, actor, tool, args, effect, undo, status)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (action_id, datetime.now().isoformat(timespec="seconds"), actor, tool,
                 json.dumps(args, ensure_ascii=False), json.dumps(effect, ensure_ascii=False),
                 json.dumps(undo, ensure_ascii=False), status))
        return action_id

    def list(self, limit: int = 10) -> List[Dict[str, Any]]:
        rows = self.store.conn.execute(
            "SELECT * FROM actions_log ORDER BY rowid DESC LIMIT ?", (limit,)).fetchall()
        return [{"id": r["id"], "ts": r["ts"], "tool": r["tool"], "status": r["status"],
                 "effect": _loads(r["effect"]), "undo": _loads(r["undo"])} for r in rows]

    def get(self, action_id: str) -> Optional[sqlite3.Row]:
        return self.store.conn.execute(
            "SELECT * FROM actions_log WHERE id = ?", (action_id,)).fetchone()

    def mark_undone(self, action_id: str) -> None:
        with self.store.conn:
            self.store.conn.execute("UPDATE actions_log SET status = 'undone' WHERE id = ?",
                                    (action_id,))


def _loads(raw: Any) -> Any:
    try:
        return json.loads(raw) if raw else {}
    except (TypeError, ValueError):
        return {}


# === Tools ===

@dataclass
class ToolSpec:
    name: str
    description: str
    args: Dict[str, type]
    handler: Callable[[Dict[str, Any]], Dict[str, Any]]
    needs_confirmation: Optional[Callable[[Dict[str, Any]], bool]] = None
    read_only: bool = False


class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        self.tools[spec.name] = spec

    def get(self, name: str) -> Optional[ToolSpec]:
        return self.tools.get(name)

    def names(self) -> List[str]:
        return sorted(self.tools)

    def description(self) -> str:
        return "\n".join(f"- {s.name}: {s.description} args={list(s.args)}"
                         for s in self.tools.values())


# === Plan readiness: one rule set for the GUI check and the legacy pipeline ===

NO_DATE, NO_CAPTION, NO_TASK = "без даты", "без подписи", "без ТЗ"
PLAN_FORMATS = {"пост": "Пост", "reels": "Reels", "рилс": "Reels", "карусель": "Карусель"}
CAPTION_LIMIT = 400


def _shorten_caption(text: str, limit: int = CAPTION_LIMIT) -> str:
    """Обрезка по границе предложения; если одно предложение не влезает — по последнему пробелу."""
    text = str(text or "").strip()
    if len(text) <= limit:
        return text
    cut = ""
    for sentence in re.split(r"(?<=[.!?…])\s+|\n+", text):
        candidate = f"{cut} {sentence}".strip() if cut else sentence
        if len(candidate) > limit:
            break
        cut = candidate
    if cut:
        return cut
    head = text[:limit - 1].rsplit(" ", 1)[0].rstrip(" ,;:—-\u00ab")
    return (head or text[:limit - 1]) + "…"

MAX_ISSUES = 15
NOOP_UNDO = {"op": "noop"}

# Photo processing (batch_photo): операции и их подписи для отчёта
PHOTO_OPERATIONS = ("crop", "color", "compress")
PHOTO_LABELS = {"crop": "кадрирование 4:5", "color": "цвет", "compress": "сжатие"}
PHOTO_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
PHOTO_MAX_SIDE = 1600
PHOTO_QUALITY = 85
MEDIA_IMAGES = Path(__file__).resolve().parent.parent / "media" / "images"

# Materials (other_files): фиксированные папки и тип файла по расширению
MATERIAL_FOLDERS = ("archive", "buffer", "documents", "references", "templates")
MATERIAL_KINDS = {
    ".png": "image", ".jpg": "image", ".jpeg": "image", ".webp": "image", ".gif": "image",
    ".mp4": "video", ".mov": "video", ".mkv": "video",
    ".pdf": "document", ".doc": "document", ".docx": "document", ".txt": "document",
    ".xls": "document", ".xlsx": "document", ".ppt": "document", ".pptx": "document",
    ".zip": "archive", ".rar": "archive", ".7z": "archive",
}


# Видео (process_video): площадка -> (подпись для отчёта, суффикс готового файла)
VIDEO_TARGETS = {
    "instagram_reels": ("Reels 9:16, до 90 сек", "reels"),
    "instagram_post": ("Пост 1:1, до 60 сек", "post"),
    "tiktok": ("TikTok 9:16, до 180 сек", "tiktok"),
    "youtube_shorts": ("Shorts 9:16, до 60 сек", "shorts"),
    "youtube_video": ("YouTube 16:9", "youtube"),
}
VIDEO_SUFFIXES = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}
MEDIA_ZONES = ("media_ready", "media_sources", "media_references")

_PATH_RE = re.compile(r"(?<![\w/])([~./][^\s\"'«»]*(?:\.(?:mp4|mov|mkv|avi|webm|m4v)))",
                      re.IGNORECASE)


def _video_paths(text: str) -> List[str]:
    """Пути к видеофайлам в тексте задачи: без них видео из чата не запустить."""
    found: List[str] = []
    for match in _PATH_RE.findall(text or ""):
        path = match.strip(",;:)]")
        if path and path not in found:
            found.append(path)
    return found


def _platform_from_text(low: str) -> str:
    """Слово площадки в тексте → ключ `VIDEO_TARGETS`."""
    for words, target in ((("тикток", "tiktok"), "tiktok"),
                          (("шортс", "shorts"), "youtube_shorts"),
                          (("ютуб", "youtube"), "youtube_video"),
                          (("пост", "1:1", "квадрат"), "instagram_post"),
                          (("рилс", "reels"), "instagram_reels")):
        if any(word in low for word in words):
            return target
    return "instagram_reels"


def material_kind(path: Path) -> str:
    return MATERIAL_KINDS.get(Path(path).suffix.lower(), "file")


def human_size(size: Any) -> str:
    value = float(size or 0)
    for unit in ("Б", "КБ", "МБ"):
        if value < 1024:
            return f"{int(value)} Б" if unit == "Б" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} ГБ"


def collect_plan_issues(dm) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """Plan positions that are not ready to publish, plus counters per problem kind."""
    linked_tasks = {str(task.get("content_plan_link") or "")
                    for task in dm.get_shooting_tasks()}
    by_kind = {NO_DATE: 0, NO_CAPTION: 0, NO_TASK: 0}
    issues: List[Dict[str, Any]] = []
    for item in dm.get_content_plan():
        item_id = str(item.get("id") or "")
        problems = []
        if not str(item.get("date") or "").strip():
            problems.append(NO_DATE)
        if not str(item.get("caption") or "").strip():
            problems.append(NO_CAPTION)
        if not (str(item.get("shooting_task_id") or "").strip() or item_id in linked_tasks):
            problems.append(NO_TASK)
        for problem in problems:
            by_kind[problem] += 1
        if problems:
            issues.append({"id": item_id,
                           "date": str(item.get("date") or "").strip() or "—",
                           "topic": item.get("topic") or "—",
                           "status": item.get("status") or "",
                           "problems": problems})
    return issues, by_kind


class AITools:
    """Concrete handlers. Mutations snapshot the affected section for undo."""

    def __init__(self, dm, router_ref):
        self.dm = dm
        self.router = router_ref
        self.video = None  # VideoProcessor создаётся при первом обращении (тесты подставляют свой)
        self.cloudinary = None  # клиент хостинга для D2; без него — из переменных окружения
        self.tokens = None  # TokenStore для D3; создаётся по app_db проекта
        self.app_db_path: Optional[Path] = None

    # --- helpers ---
    def _bump_version(self, note: str, author: str = "AI") -> None:
        strategy = self.dm.get_strategy()
        versions = strategy.setdefault("versions", [])
        numbers = []
        for source in [strategy.get("version")] + [v.get("version") for v in versions]:
            match = re.match(r"^1\.(\d+)$", str(source or "").strip())
            if match:
                numbers.append(int(match.group(1)))
        number = (max(numbers) if numbers else 0) + 1
        versions.append({"version": f"1.{number}", "date": datetime.now().strftime("%d.%m.%Y"),
                         "author": author, "changes": note})
        strategy["version"] = f"1.{number}"
        strategy["updated"] = datetime.now().strftime("%d.%m.%Y")

    def _media_records(self, media_ids: Optional[List[str]]) -> List[Tuple[str, str, Dict[str, Any]]]:
        """`(id, зона, запись)` только для существующих материалов, в порядке аргумента."""
        index = {str(record.get("id")): (zone, record) for zone in MEDIA_ZONES
                 for record in self.dm._data.get(zone, []) if record.get("id")}
        return [(str(media_id), *index[str(media_id)]) for media_id in (media_ids or [])
                if str(media_id) in index]

    def _section(self, key: str) -> Any:
        return self.dm._data.setdefault(key, [])

    def _mutate(self, key: str, fn: Callable[[Any], Dict[str, Any]]) -> Dict[str, Any]:
        section = self._section(key)
        before = copy.deepcopy(section)
        out = fn(section) or {}
        self.dm.save()
        return {"summary": out.get("summary", "готово"),
                "effect": out.get("effect", {}),
                "undo": {"op": "restore_section", "section": key, "data": before}}

    def context(self, scope: str = "all") -> Dict[str, Any]:
        strat = self.dm.get_strategy() or {}
        profile = self.dm.get_brand_profile() or {}
        plan = self.dm.get_content_plan()
        events = self.dm.get_calendar_events()
        summary = (f"Проект: {strat.get('project_name') or self.dm.project_id}. "
                   f"Блоков стратегии: {len(strat.get('sections') or [])}, "
                   f"позиций плана: {len(plan)}, событий: {len(events)}, "
                   f"медиа: {len(self.dm.get_media_sources()) + len(self.dm.get_media_ready())}.")
        if str(scope or "").lower() == "calendar":
            summary += self._calendar_lines(events)
        return {
            "summary": summary,
            "effect": {"profile_filled": bool(profile.get("client_name")),
                       "strategy_sections": len(strat.get("sections") or []),
                       "plan_items": len(plan)},
            "undo": {},
        }

    @staticmethod
    def _calendar_lines(events: List[Dict[str, Any]], limit: int = 10) -> str:
        """Строки календаря для чтения: дата, время, название. Ничего не меняет."""
        if not events:
            return "\nСобытий пока нет — план в календарь не переносили."

        def key(event: Dict[str, Any]) -> Tuple[int, datetime]:
            try:
                return 0, datetime.strptime(str(event.get("date") or "").strip(), "%d.%m.%Y")
            except ValueError:
                return 1, datetime.min

        ordered = sorted(events, key=key)
        lines = [f"\nСобытия календаря ({len(ordered)}):"]
        for event in ordered[:limit]:
            lines.append(f"· {event.get('date') or '—'} {event.get('time') or ''} — "
                         f"{event.get('title') or 'Событие'}".rstrip())
        if len(ordered) > limit:
            lines.append(f"… и ещё {len(ordered) - limit}")
        return "\n".join(lines)

    def search_knowledge(self, query: str = "", limit: int = 5) -> Dict[str, Any]:
        needle = str(query or "").lower().strip()
        found = []
        for item in self.dm.get_other_files() or {}:
            for entry in (self.dm.get_other_files(item) or []):
                if needle in str(entry.get("name", "")).lower():
                    found.append(f"{item}: {entry.get('name')}")
        for media in self.dm.get_media_sources() + self.dm.get_media_ready():
            if needle and needle in str(media.get("name", "")).lower():
                found.append(f"медиа: {media.get('name')}")
        for section in (self.dm.get_strategy() or {}).get("sections", []):
            if needle and needle in str(section.get("content", "")).lower():
                found.append(f"стратегия: {section.get('title')}")
        found = found[:max(1, int(limit or 5))]
        return {"summary": "Найдено: " + (", ".join(found) if found else "ничего"),
                "effect": {"found": found}, "undo": {}}

    def create_strategy(self, brief: str = "", sections: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        sections = sections or self.router.generate_strategy_sections(brief)
        if not sections:
            return {"summary": "Не смог собрать стратегию: нужна локальная модель (Ollama) "
                               "или облако. Заполните бренд-профиль и повторите.",
                    "effect": {}, "undo": {}}

        before = copy.deepcopy(self.dm.get_strategy())
        built = [{
            "id": s.get("id") or f"sec_{index:02d}",
            "title": s.get("title") or f"Блок {index}",
            "icon": s.get("icon") or "•",
            "content": s.get("content") or "",
        } for index, s in enumerate(sections, start=1)]
        strategy = self.dm.get_strategy()
        strategy["sections"] = built
        self._bump_version(f"стратегия собрана ({len(built)} блоков)")
        self.dm.save()
        return {"summary": f"Создал стратегию: {len(built)} блоков "
                           f"({', '.join(s['title'] for s in built[:3])}...)",
                "effect": {"sections": [s["id"] for s in built]},
                "undo": {"op": "restore_strategy", "data": before}}

    def update_strategy_section(self, section_id: str = "", content: str = "") -> Dict[str, Any]:
        strategy = self.dm.get_strategy()
        target = next((s for s in strategy.get("sections", []) if s.get("id") == section_id), None)
        if target is None:
            return {"summary": f"Блок {section_id} не найден", "effect": {}, "undo": {}}
        before = copy.deepcopy(strategy)
        target["content"] = content
        self._bump_version(f"блок «{target.get('title')}» обновлён")
        self.dm.save()
        return {"summary": f"Обновил блок «{target.get('title')}»",
                "effect": {"section_id": section_id},
                "undo": {"op": "restore_strategy", "data": before}}

    def update_kpis(self, kpis: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        before = copy.deepcopy(self.dm.get_strategy())
        cleaned = []
        for row in kpis or []:
            if not isinstance(row, dict) or not any(str(v or "").strip() for v in row.values()):
                continue
            cleaned.append({"metric": str(row.get("metric") or ""),
                            "current": str(row.get("current") or ""),
                            "target": str(row.get("target") or ""),
                            "deadline": str(row.get("deadline") or "")})
        strategy = self.dm.get_strategy()
        strategy["kpis"] = cleaned
        self._bump_version(f"KPI обновлены ({len(cleaned)} строк)")
        self.dm.save()
        return {"summary": f"KPI сохранены: {len(cleaned)} строк",
                "effect": {"kpis": len(cleaned)},
                "undo": {"op": "restore_strategy", "data": before}}

    # --- generic record tools for the content chain ---
    EDITABLE_SECTIONS = ("content_plan", "calendar_events", "shooting_tasks", "post_metrics")

    def _records(self, section: str) -> Optional[List[Dict[str, Any]]]:
        if section not in self.EDITABLE_SECTIONS:
            return None
        return self.dm._data.setdefault(section, [])

    def add_record(self, section: str = "", fields: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        records = self._records(section)
        if records is None:
            return {"summary": f"Раздел {section} недоступен", "effect": {}, "undo": {}}
        before = copy.deepcopy(records)
        record = dict(fields or {})
        record["id"] = record.get("id") or f"{section[:2]}_{uuid.uuid4().hex[:6]}"
        records.append(record)
        self.dm.save()
        return {"summary": f"Добавил запись в {section}",
                "effect": {"id": record["id"]},
                "undo": {"op": "restore_section", "section": section, "data": before}}

    def edit_record(self, section: str = "", item_id: str = "",
                    fields: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        records = self._records(section)
        if records is None:
            return {"summary": f"Раздел {section} недоступен", "effect": {}, "undo": {}}
        target = next((r for r in records if r.get("id") == item_id), None)
        if target is None:
            return {"summary": f"Запись {item_id} не найдена", "effect": {}, "undo": {}}
        before = copy.deepcopy(records)
        target.update({k: v for k, v in (fields or {}).items() if k != "id"})
        self.dm.save()
        return {"summary": "Изменения сохранены", "effect": {"id": item_id},
                "undo": {"op": "restore_section", "section": section, "data": before}}

    def delete_record(self, section: str = "", item_id: str = "") -> Dict[str, Any]:
        records = self._records(section)
        if records is None:
            return {"summary": f"Раздел {section} недоступен", "effect": {}, "undo": {}}
        before = copy.deepcopy(records)
        kept = [r for r in records if r.get("id") != item_id]
        if len(kept) == len(records):
            return {"summary": f"Запись {item_id} не найдена", "effect": {}, "undo": {}}
        records[:] = kept
        self.dm.save()
        return {"summary": "Запись удалена", "effect": {"id": item_id},
                "undo": {"op": "restore_section", "section": section, "data": before}}

    def sync_plan_events(self) -> Dict[str, Any]:
        """Calendar events for dated plan items; drafts with an event become planned."""
        plan_before = copy.deepcopy(self.dm.get_content_plan())
        events_before = copy.deepcopy(self.dm.get_calendar_events())
        events = self.dm._data.setdefault("calendar_events", [])
        linked = {str(e.get("link") or "") for e in events}
        created = 0
        for item in self.dm.get_content_plan():
            if not item.get("date") or str(item.get("id")) in linked:
                continue
            events.append({
                "id": f"ev_{uuid.uuid4().hex[:6]}",
                "date": item.get("date"), "time": "12:00", "type": "publication",
                "title": item.get("topic") or "Публикация",
                "description": f"Из плана: {item.get('rubric') or '—'}",
                "link": item.get("id"),
            })
            linked.add(str(item.get("id")))
            created += 1

        planned = 0
        for item in self.dm.get_content_plan():
            if str(item.get("id")) not in linked:
                continue
            if (item.get("status") or "Черновик") in ("", "Черновик"):
                item["status"] = "Запланировано"
                planned += 1

        if not created and not planned:
            return {"summary": "Все позиции плана уже есть в календаре", "effect": {}, "undo": {}}
        self.dm.save()
        parts = []
        if created:
            parts.append(f"событий: {created}")
        if planned:
            parts.append(f"в «Запланировано»: {planned}")
        return {"summary": "Из плана — " + ", ".join(parts),
                "effect": {"created": created, "planned": planned},
                "undo": {"op": "restore_sections",
                         "sections": {"content_plan": plan_before,
                                      "calendar_events": events_before}}}

    def validate_plan(self) -> Dict[str, Any]:
        """Pre-publish check: plan items without a date, a caption or a shooting task."""
        plan = self.dm.get_content_plan()
        if not plan:
            return {"summary": "Проверка: контент-план пуст — проверять нечего",
                    "effect": {"checked": 0, "issues": 0, "empty": True},
                    "undo": NOOP_UNDO}
        issues, by_kind = collect_plan_issues(self.dm)
        if not issues:
            return {"summary": f"Проверка: {len(plan)} позиций в порядке — даты, подписи и ТЗ на месте",
                    "effect": {"checked": len(plan), "issues": 0},
                    "undo": NOOP_UNDO}
        counts = ", ".join(f"{kind}: {count}" for kind, count in by_kind.items() if count)
        lines = [f"Проверка: {len(issues)} из {len(plan)} позиций требуют доработки ({counts})"]
        lines += [f"· {issue['date']} · {issue['topic']} — {', '.join(issue['problems'])}"
                  for issue in issues[:MAX_ISSUES]]
        if len(issues) > MAX_ISSUES:
            lines.append(f"… и ещё {len(issues) - MAX_ISSUES}")
        return {"summary": "\n".join(lines),
                "effect": {"checked": len(plan), "issues": len(issues),
                           "by_kind": by_kind,
                           "ids": [issue["id"] for issue in issues]},
                "undo": NOOP_UNDO}

    def analyze_performance(self, period_days: int = 30) -> Dict[str, Any]:
        """Сводка по метрикам: охват, вовлечённость, лучшая рубрика, топ и слабый пост."""
        plan = {str(item.get("id")): item for item in self.dm.get_content_plan()}
        metrics = [m for m in self.dm.get_post_metrics() if str(m.get("plan_id")) in plan]
        if not metrics:
            return {"summary": "Аналитика: метрик пока нет — впишите охват и реакции "
                               "по опубликованным постам в разделе «Аналитика»",
                    "effect": {}, "undo": {}}

        cutoff = None
        if int(period_days or 0) > 0:
            cutoff = (datetime.now() - timedelta(days=int(period_days))).date()

        rows = []
        for row in metrics:
            item = plan[str(row.get("plan_id"))]
            try:
                day = datetime.strptime(str(item.get("date") or ""), "%d.%m.%Y").date()
            except ValueError:
                day = None
            if cutoff and day and day < cutoff:  # посты без даты не отбрасываем
                continue
            reach = int(row.get("reach") or 0)
            reactions = sum(int(row.get(key) or 0) for key in ("likes", "comments", "saves"))
            rows.append({
                "date": str(item.get("date") or "—"),
                "topic": str(item.get("topic") or "—"),
                "rubric": str(item.get("rubric") or "—"),
                "reach": reach, "reactions": reactions,
                "er": (reactions / reach * 100) if reach else 0.0,
            })
        if not rows:
            return {"summary": f"Аналитика: за последние {int(period_days)} дней метрик нет",
                    "effect": {}, "undo": {}}

        total_reach = sum(row["reach"] for row in rows)
        avg_er = sum(row["er"] for row in rows) / len(rows)
        lines = [f"Аналитика: {len(rows)} постов · охват {total_reach:,}".replace(",", " ")
                 + f" · средняя вовлечённость {avg_er:.1f}%"]

        by_rubric: Dict[str, List[float]] = {}
        for row in rows:
            by_rubric.setdefault(row["rubric"], []).append(row["er"])
        best_rubric, best_values = max(by_rubric.items(),
                                       key=lambda kv: sum(kv[1]) / len(kv[1]))
        lines.append(f"Лучшая рубрика: «{best_rubric}» — ER "
                     f"{sum(best_values) / len(best_values):.1f}% на {len(best_values)} постах")

        top = sorted(rows, key=lambda r: r["er"], reverse=True)[:3]
        lines.append("Топ по вовлечённости:")
        lines += [f"· {row['date']} · {row['topic']} — охват {row['reach']}, ER {row['er']:.1f}%"
                  for row in top]
        weakest = min(rows, key=lambda r: r["er"])
        if weakest["er"] < avg_er:
            lines.append(f"Слабее остальных: {weakest['date']} · {weakest['topic']} — "
                         f"охват {weakest['reach']}, ER {weakest['er']:.1f}%")

        measured = {str(m.get("plan_id")) for m in metrics}
        missing = [item for item in self.dm.get_content_plan()
                   if item.get("status") == "Опубликовано"
                   and str(item.get("id")) not in measured]
        if missing:
            lines.append(f"Без метрик: {len(missing)} опубликованных постов")

        return {"summary": "\n".join(lines),
                "effect": {"posts": len(rows), "reach": total_reach,
                           "avg_er": round(avg_er, 1), "without_metrics": len(missing)},
                "undo": NOOP_UNDO}

    def _next_plan_date(self) -> datetime:
        """Новый план продолжается от последней даты в плане, а не начинается сегодня."""
        dates = []
        for item in self.dm.get_content_plan():
            try:
                dates.append(datetime.strptime(str(item.get("date") or "").strip(), "%d.%m.%Y"))
            except ValueError:
                continue
        today = datetime.now()
        if not dates:
            return today
        return max(max(dates) + timedelta(days=1), today)

    def _plan_topics(self, topics: Optional[List[Any]], count: int, brief: str) -> List[Dict[str, Any]]:
        """Темы из аргумента, иначе — от модели; пустой список, если модель недоступна."""
        prepared: List[Dict[str, Any]] = []
        for raw in topics or []:
            if isinstance(raw, str) and raw.strip():
                prepared.append({"topic": raw.strip()})
            elif isinstance(raw, dict) and str(raw.get("topic") or "").strip():
                prepared.append(raw)
        if not prepared and getattr(self, "router", None) is not None:
            prepared = self.router.generate_plan_topics(count, brief)
        return prepared[:count]

    def create_content_plan(self, count: int = 5, rubrics: Optional[List[str]] = None,
                            start: Optional[str] = None, period_days: int = 7,
                            topics: Optional[List[Any]] = None) -> Dict[str, Any]:
        count = max(1, min(int(count or 5), 60))
        rubrics = [r for r in (rubrics or []) if str(r).strip()] or ["Полезное"]
        suggested = self._plan_topics(topics, count, ", ".join(rubrics if rubrics != ["Полезное"] else []))
        try:
            start_date = datetime.strptime(start, "%d.%m.%Y") if start else self._next_plan_date()
        except ValueError:
            start_date = datetime.now()
        step = max(1, int(period_days or 7) // count)

        def apply(current: List[Dict[str, Any]]) -> Dict[str, Any]:
            created = []
            for index in range(count):
                item_id = f"cp_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:5]}"
                idea = suggested[index] if index < len(suggested) else {}
                rubric = str(idea.get("rubric") or "").strip() or rubrics[index % len(rubrics)]
                current.append({
                    "id": item_id,
                    "date": (start_date + timedelta(days=index * step)).strftime("%d.%m.%Y"),
                    "rubric": rubric,
                    "topic": str(idea.get("topic") or "").strip()
                             or f"{rubrics[index % len(rubrics)]}: идея {index + 1}",
                    "format": PLAN_FORMATS.get(str(idea.get("format") or "").strip().lower(), "Пост"),
                    "status": "Черновик",
                    "responsible": "SMM",
                    "strategy_link": "",
                    "shooting_task_id": "",
                })
                created.append(item_id)
            return {"summary": f"Создал {len(created)} позиций контент-плана",
                    "effect": {"plan_ids": created}}

        return self._mutate("content_plan", apply)

    def schedule_posts(self, plan_ids: Optional[List[str]] = None,
                       dates: Optional[List[str]] = None) -> Dict[str, Any]:
        plan_ids = plan_ids or []
        dates = dates or []

        def apply_plan(current: List[Dict[str, Any]]) -> Dict[str, Any]:
            changed = []
            for item in current:
                if item.get("id") in plan_ids:
                    before = item.get("date")
                    if dates:
                        item["date"] = dates[len(changed) % len(dates)]
                    item["status"] = "Запланировано"
                    changed.append({"id": item["id"], "before": before,
                                    "after": item.get("date")})
            return {"summary": f"Запланировал {len(changed)} постов",
                    "effect": {"items": changed}}

        return self._mutate("content_plan", apply_plan)

    def create_shooting_task(self, plan_id: str = "") -> Dict[str, Any]:
        before_tasks = copy.deepcopy(self.dm.get_shooting_tasks())
        before_events = copy.deepcopy(self.dm.get_calendar_events())
        before_plan = copy.deepcopy(self.dm.get_content_plan())
        task = self.dm.create_shooting_task_from_content_plan(plan_id)
        if not task:
            return {"summary": f"Позиция {plan_id} не найдена", "effect": {}, "undo": {}}
        return {"summary": f"Создал ТЗ {task.get('id')} на {task.get('date')}",
                "effect": {"task_id": task.get("id")},
                "undo": {"op": "restore_sections",
                         "sections": {"shooting_tasks": before_tasks,
                                      "content_plan": before_plan,
                                      "calendar_events": before_events}}}

    def write_captions(self, plan_id: str = "") -> Dict[str, Any]:
        item = self.dm.get_content_plan_item(plan_id)
        if not item:
            return {"summary": f"Позиция {plan_id} не найдена", "effect": {}, "undo": {}}
        brief = f"тема: {item.get('topic')}; рубрика: {item.get('rubric')}"

        def apply(current: List[Dict[str, Any]]) -> Dict[str, Any]:
            for entry in current:
                if entry.get("id") == plan_id:
                    entry["caption"] = self.router.write_caption(brief)
                    return {"summary": "Подпись готова", "effect": {"plan_id": plan_id}}
            return {"summary": "Позиция не найдена", "effect": {}}

        return self._mutate("content_plan", apply)

    MEDIA_ZONES = {"sources": "media_sources", "references": "media_references",
                   "ready": "media_ready"}

    def _add_media_record(self, path: Path, zone_key: str) -> Optional[Dict[str, Any]]:
        """Скопировать файл в проект и завести запись в зоне; исходный путь — в `source_path`."""
        try:
            dest = self._copy_media(path)
        except OSError as exc:
            logger.warning("import copy failed: %s", exc)
            return None
        record = {
            "id": f"{zone_key[:5]}_{datetime.now().strftime('%H%M%S%f')[:10]}",
            "name": dest.name,
            "type": "video" if dest.suffix.lower() in VIDEO_SUFFIXES else "image",
            "size": "unknown",
            "path": str(dest),
            "source_path": str(path),
        }
        if zone_key == "media_references":
            record["category"] = "референс"
        else:
            record.update({"status": "pending",
                           "date": datetime.now().strftime("%d.%m.%Y")})
        self.dm._data.setdefault(zone_key, []).append(record)
        return record

    def _video_batch(self, media_ids: Optional[List[str]], paths: Optional[List[str]],
                     ffmpeg_need: str, verb: str
                     ) -> Tuple[Any, List[Tuple[str, str, Dict[str, Any]]], List[str], Dict[str, Any]]:
        """ffmpeg, пути из чата и найденные записи для видео-инструментов; отказ — в `refusal`."""
        processor = self._video_processor()
        if not processor.ffmpeg_available:
            return processor, [], [], {"summary": f"Нужен ffmpeg: без него {ffmpeg_need}",
                                       "effect": {}, "undo": {}}
        from_paths, problems = self._ids_from_paths(paths)
        found = self._media_records(list(media_ids or []) + from_paths)
        if not found:
            return processor, [], problems, {
                "summary": f"Нечего {verb}: " +
                           ("; ".join(problems[:3]) or "материалы не найдены"),
                "effect": {}, "undo": {}}
        return processor, found, problems, {}

    def _ids_from_paths(self, paths: Optional[List[str]]) -> Tuple[List[str], List[str]]:
        """Записи по путям из чата: знакомые файлы — по записи, чужие копируются в проект."""
        wanted = [str(path).strip() for path in (paths or []) if str(path).strip()]
        if not wanted:
            return [], []
        by_path: Dict[str, str] = {}
        for zone in MEDIA_ZONES:
            for record in self.dm._data.get(zone, []):
                if not record.get("id"):
                    continue
                for key in ("path", "source_path"):
                    value = str(record.get(key) or "").strip()
                    if value:
                        by_path.setdefault(value, str(record["id"]))
        ids: List[str] = []
        problems: List[str] = []
        created = False
        for raw in wanted:
            path = Path(raw).expanduser()
            known = by_path.get(str(path)) or by_path.get(str(path.absolute()))
            if known:
                if known not in ids:
                    ids.append(known)
                continue
            if not path.is_file():
                problems.append(f"{path.name}: файл не найден")
                continue
            record = self._add_media_record(path, "media_ready")
            if record is None:
                problems.append(f"{path.name}: не удалось скопировать в проект")
                continue
            created = True
            if record["id"] not in ids:
                ids.append(record["id"])
        if created:
            self.dm.save()
        return ids, problems

    def import_media(self, paths: Optional[List[str]] = None, zone: str = "sources") -> Dict[str, Any]:
        zone_key = self.MEDIA_ZONES.get(str(zone or "sources"), "media_sources")
        before = copy.deepcopy(self.dm._data.get(zone_key, []))
        added, missing = [], []
        for raw_path in paths or []:
            path = Path(str(raw_path))
            if not path.exists():
                missing.append(path.name)
                continue
            if zone_key == "media_sources":
                entry = self.dm.add_media_source(str(path))
                if entry:
                    added.append(entry.get("name"))
                continue
            record = self._add_media_record(path, zone_key)
            if record is None:
                missing.append(path.name)
                continue
            added.append(record["name"])
        if not added:
            return {"summary": "Файлы не добавлены: укажите существующие пути",
                    "effect": {}, "undo": {}}
        self.dm.save()
        summary = f"Импортировал файлов: {len(added)} в «{zone}»"
        if missing:
            summary += f". Не найдено: {', '.join(missing[:3])}"
        return {"summary": summary, "effect": {"names": added, "zone": zone_key},
                "undo": {"op": "restore_section", "section": zone_key, "data": before}}

    @staticmethod
    def _copy_media(path: Path) -> Path:
        MEDIA_IMAGES.mkdir(parents=True, exist_ok=True)
        dest = MEDIA_IMAGES / path.name
        counter = 1
        while dest.exists():
            dest = MEDIA_IMAGES / f"{path.stem}_{counter}{path.suffix}"
            counter += 1
        import shutil
        shutil.copy2(path, dest)
        return dest

    def batch_photo(self, media_ids: Optional[List[str]] = None,
                    operations: Optional[List[str]] = None) -> Dict[str, Any]:
        """Обрабатывает выбранные материалы и переводит записи на готовый файл.

        Всегда считается от исходника (`source_path`): повторный прогон перезаписывает
        тот же готовый файл, а не создаёт `_web_web`. Исходник остаётся на диске.
        """
        ops = [op for op in (operations or list(PHOTO_OPERATIONS)) if op in PHOTO_OPERATIONS]
        if not ops:
            return {"summary": "Неизвестные операции: " + ", ".join(operations or []),
                    "effect": {}, "undo": {}}
        found = self._media_records(media_ids)
        if not found:
            return {"summary": "Нечего обрабатывать: материалы не найдены",
                    "effect": {}, "undo": {}}

        before: Dict[str, Any] = {}
        done: List[str] = []
        files: List[str] = []
        skipped: List[str] = []
        for media_id, zone, record in found:
            try:
                rendered = self._process_photo(record, ops)
            except (OSError, ValueError) as exc:
                logger.warning("batch_photo %s: %s", media_id, exc)
                skipped.append(f"{record.get('name')}: {exc}")
                continue
            if rendered is None:
                skipped.append(f"{record.get('name')}: файл не найден или это не фото")
                continue
            dest, source = rendered
            before.setdefault(zone, copy.deepcopy(self.dm._data.get(zone, [])))
            record["path"] = str(dest)
            record["name"] = dest.name
            record["size"] = f"{max(1, dest.stat().st_size // 1024)} КБ"
            record["source_path"] = str(source)
            record["processed"] = list(ops)
            done.append(media_id)
            files.append(str(dest))

        if not done:
            return {"summary": "Не обработал ни одного файла: " + "; ".join(skipped[:3]),
                    "effect": {}, "undo": {}}
        self.dm.save()
        summary = (f"Обработал фото: {len(done)} "
                   f"({', '.join(PHOTO_LABELS[op] for op in ops)})")
        if skipped:
            summary += f". Пропущено: {len(skipped)}"
        return {"summary": summary,
                "effect": {"ids": done, "files": [Path(f).name for f in files],
                           "skipped": skipped},
                "undo": {"op": "restore_sections", "sections": before, "files": files}}

    @staticmethod
    def _process_photo(record: Dict[str, Any],
                       operations: List[str]) -> Optional[Tuple[Path, Path]]:
        """Считает исходник и пишет `<имя>_web.<ext>` в media/images.

        Возвращает `(готовый файл, исходник)`; `None` — запись не фото или файла нет.
        Прозрачность PNG сохраняется (выход в PNG); остальное — JPEG.
        """
        name = str(record.get("name") or "").strip()
        candidates = [str(record.get("source_path") or "").strip(),
                      str(record.get("path") or "").strip()]
        if name:
            candidates.append(str(MEDIA_IMAGES / name))
        paths = [Path(raw) for raw in candidates if raw]
        source = next((path for path in paths if path.is_file()), None)
        if source is None or source.suffix.lower() not in PHOTO_SUFFIXES:
            return None
        # Записи без source_path ссылаются на готовый файл: исходник ищем рядом,
        # расширение могло смениться (png → jpg).
        if source.stem.endswith("_web"):
            base = source.stem[:-4]
            source = next((found for suffix in [source.suffix, *sorted(PHOTO_SUFFIXES)]
                           if (found := MEDIA_IMAGES / f"{base}{suffix}").is_file()), source)

        from PIL import Image, ImageEnhance

        MEDIA_IMAGES.mkdir(parents=True, exist_ok=True)
        with Image.open(source) as image:
            transparent = (image.mode in ("RGBA", "LA")
                           or "transparency" in image.info)
            picture = image.convert("RGBA" if transparent else "RGB")
            if "crop" in operations:
                picture = AITools._crop_4x5(picture)
            if "color" in operations:
                picture = ImageEnhance.Color(picture).enhance(1.08)
                picture = ImageEnhance.Contrast(picture).enhance(1.05)
            if "compress" in operations:
                picture.thumbnail((PHOTO_MAX_SIDE, PHOTO_MAX_SIDE), Image.LANCZOS)
            dest = MEDIA_IMAGES / f"{source.stem}_web{'.png' if transparent else '.jpg'}"
            if transparent:
                picture.save(dest, "PNG", optimize=True)
            else:
                picture.save(dest, "JPEG", quality=PHOTO_QUALITY, optimize=True)
        return dest, source

    @staticmethod
    def _crop_4x5(image: Any) -> Any:
        """Central crop to the Instagram feed ratio 4:5, never upscaling."""
        width, height = image.size
        if width * 5 > height * 4:
            new_width = max(1, round(height * 4 / 5))
            left = (width - new_width) // 2
            return image.crop((left, 0, left + new_width, height))
        new_height = max(1, round(width * 5 / 4))
        top = (height - new_height) // 2
        return image.crop((0, top, width, top + new_height))

    # --- video ---
    def _video_processor(self):
        if self.video is None:
            from video_processor import VideoProcessor
            self.video = VideoProcessor()
        return self.video

    @staticmethod
    def _remember(record: Dict[str, Any], *keys: str) -> None:
        """Дописать операции в `processed`: старые сохраняются, дублей не появляется."""
        marks = [str(mark) for mark in record.get("processed") or []]
        for key in keys:
            if key and key not in marks:
                marks.append(key)
        record["processed"] = marks

    def process_video(self, media_ids: Optional[List[str]] = None,
                      platform: str = "instagram_reels",
                      paths: Optional[List[str]] = None) -> Dict[str, Any]:
        """Подготовить видео под площадку: размер, кадры, сжатие — всегда от исходника."""
        target = str(platform or "").strip().lower()
        if target not in VIDEO_TARGETS:
            return {"summary": f"Неизвестная площадка: {platform or '—'}",
                    "effect": {}, "undo": {}}
        processor, found, problems, refusal = self._video_batch(
            media_ids, paths, "видео не обработать", "обрабатывать")
        if refusal:
            return refusal

        label, suffix = VIDEO_TARGETS[target]
        before: Dict[str, Any] = {}
        done: List[str] = []
        files: List[str] = []
        skipped: List[str] = list(problems)
        for media_id, zone, record in found:
            source = self._video_source(record)
            if source is None:
                skipped.append(f"{record.get('name')}: файл не найден или это не видео")
                continue
            dest = MEDIA_IMAGES / f"{self._video_stem(source)}_{suffix}.mp4"
            if not processor.export_for_platform(str(source), target, str(dest)):
                skipped.append(f"{record.get('name')}: ffmpeg не смог обработать")
                continue
            info = processor.get_video_info(str(dest)) or {}
            before.setdefault(zone, copy.deepcopy(self.dm._data.get(zone, [])))
            record["path"] = str(dest)
            record["name"] = dest.name
            if info.get("width") and info.get("height"):
                record["size"] = f"{info['width']}x{info['height']}"
            record["source_path"] = str(source)
            self._remember(record, target)
            done.append(media_id)
            files.append(str(dest))

        if not done:
            return {"summary": "Не обработал ни одного видео: " + "; ".join(skipped[:3]),
                    "effect": {}, "undo": {}}
        self.dm.save()
        summary = f"Обработал видео: {len(done)} ({label})"
        if skipped:
            summary += f". Пропущено: {len(skipped)}"
        return {"summary": summary,
                "effect": {"ids": done, "files": [Path(name).name for name in files],
                           "platform": target, "skipped": skipped},
                "undo": {"op": "restore_sections", "sections": before, "files": files}}

    @staticmethod
    def _video_source(record: Dict[str, Any]) -> Optional[Path]:
        """Исходный видеофайл записи: `source_path` → `path` → файл по имени в media/images."""
        for raw in (record.get("source_path"), record.get("path"),
                    MEDIA_IMAGES / str(record.get("name") or "")):
            path = Path(raw) if raw else None
            if path is not None and path.is_file() and path.suffix.lower() in VIDEO_SUFFIXES:
                return path
        return None

    @staticmethod
    def _video_stem(source: Path) -> str:
        """Имя без уже добавленного суффикса площадки: повтор не даёт `_reels_reels`."""
        for _label, token in VIDEO_TARGETS.values():
            if source.stem.endswith(f"_{token}"):
                return source.stem[: -len(token) - 1]
        return source.stem

    def make_subtitles(self, media_ids: Optional[List[str]] = None,
                       language: str = "ru", burn: bool = True,
                       paths: Optional[List[str]] = None) -> Dict[str, Any]:
        """Распознать речь: `.srt` в проект и, если нужно, видео с выжженными субтитрами."""
        processor, found, problems, refusal = self._video_batch(
            media_ids, paths, "субтитры не собрать", "распознавать")
        if refusal:
            return refusal

        subtitles = Path(self.dm.data_dir) / "subtitles"
        before: Dict[str, Any] = {}
        done: List[str] = []
        files: List[str] = []
        skipped: List[str] = list(problems)
        srt_count = 0
        for media_id, zone, record in found:
            source = self._video_source(record)
            if source is None:
                skipped.append(f"{record.get('name')}: файл не найден или это не видео")
                continue
            audio = processor.extract_audio(str(source))
            if not audio:
                skipped.append(f"{record.get('name')}: не смог достать звуковую дорожку")
                continue
            recognised = processor.transcribe(audio, language=language or "ru")
            Path(audio).unlink(missing_ok=True)
            if not recognised or not recognised.get("segments"):
                skipped.append(f"{record.get('name')}: речь не распознана (нужен Whisper)")
                continue
            stem = self._video_stem(source)
            subtitles.mkdir(parents=True, exist_ok=True)
            srt = subtitles / f"{stem}.srt"
            if not processor.generate_srt(recognised["segments"], str(srt)):
                skipped.append(f"{record.get('name')}: не удалось записать .srt")
                continue
            srt_count += 1
            files.append(str(srt))
            if not burn:
                continue
            dest = MEDIA_IMAGES / f"{stem}_subs.mp4"
            if not processor.burn_subtitles(str(source), str(srt), str(dest)):
                skipped.append(f"{record.get('name')}: субтитры не выжглись, .srt сохранён")
                continue
            before.setdefault(zone, copy.deepcopy(self.dm._data.get(zone, [])))
            record["path"] = str(dest)
            record["name"] = dest.name
            record["source_path"] = str(source)
            self._remember(record, "subtitles")
            done.append(media_id)
            files.append(str(dest))

        if not files:
            return {"summary": "Субтитры не сделаны: " + "; ".join(skipped[:3]),
                    "effect": {}, "undo": {}}
        if before:
            self.dm.save()
        summary = f"Субтитры: .srt {srt_count}"
        if burn:
            summary += f", выжжено в видео: {len(done)}"
        if skipped:
            summary += f". Пропущено: {len(skipped)}"
        return {"summary": summary,
                "effect": {"ids": done, "srt": srt_count,
                           "files": [Path(name).name for name in files]},
                "undo": {"op": "restore_sections", "sections": before, "files": files}}

    def export_package(self, date_from: str = "", date_to: str = "",
                       dest: str = "") -> Dict[str, Any]:
        """Собрать пакет публикаций: в `dest`, если папка выбрана, иначе в проект."""
        base = Path(dest) if str(dest).strip() else Path(self.dm.data_dir) / "exports"
        folder = base / datetime.now().strftime("%Y%m%d-%H%M%S")
        folder.mkdir(parents=True, exist_ok=True)
        items = [i for i in self.dm.get_content_plan() if i.get("status") == "Запланировано"]
        (folder / "package.txt").write_text(
            "\n".join(f"{i.get('date')} — {i.get('topic')}" for i in items) or "пусто",
            encoding="utf-8")
        return {"summary": f"Собрал пакет в {folder} (позиций: {len(items)})",
                "effect": {"path": str(folder)},
                "undo": {"op": "delete_folder", "path": str(folder)}}

    # --- Instagram: хостинг медиа (шаг D2) ---
    def _token_store(self):
        """Хранилище токена Instagram в общей базе приложения (не в базе проекта)."""
        if self.tokens is None:
            import instagram_auth

            path = self.app_db_path or Path(__file__).resolve().parent.parent / "data" / "app.db"
            self.tokens = instagram_auth.TokenStore(path)
        return self.tokens

    def instagram_status(self) -> Dict[str, Any]:
        """Read-only проверка доступа к Instagram: без публикации и без трат."""
        import instagram_auth

        try:
            token = self._token_store().load_token()
        except instagram_auth.TokenError as exc:
            return {"summary": str(exc), "effect": {}, "undo": {}}
        if not token:
            return {"summary": "Токен Instagram не сохранён — впишите в «Настройках»",
                    "effect": {}, "undo": {}}
        result = instagram_auth.check_access(token)
        if not result.get("ok"):
            return {"summary": "Доступ не готов: " + str(result.get("reason") or "неизвестно"),
                    "effect": {}, "undo": {}}
        summary = (f"Доступ есть: @{result['username'] or result['ig_user_id']}"
                   f" ({result['account_type']}), токен {instagram_auth.mask(token)}")
        return {"summary": summary,
                "effect": {"username": result["username"],
                           "account_type": result["account_type"],
                           "ig_user_id": result["ig_user_id"]},
                "undo": NOOP_UNDO}

    def _cloudinary_client(self):
        """Клиент Cloudinary: подставленный (тест/будущий UI) или из переменных окружения."""
        if self.cloudinary is not None:
            return self.cloudinary
        import cloudinary_client

        return cloudinary_client.CloudinaryClient.from_env()

    def host_media(self, media_id: str = "") -> Dict[str, Any]:
        """Выложить готовый материал на публичный URL: без него Graph API не публикует."""
        found = self._media_records([media_id])
        if not found:
            return {"summary": f"Материал {media_id or '—'} не найден",
                    "effect": {}, "undo": {}}
        client = self._cloudinary_client()
        if client is None:
            return {"summary": "Нужны CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY и "
                                "CLOUDINARY_API_SECRET — без них медиа некуда выложить",
                    "effect": {}, "undo": {}}
        _, zone, record = found[0]
        path = Path(str(record.get("path") or ""))
        if not path.is_file():
            return {"summary": f"{record.get('name')}: файл не найден",
                    "effect": {}, "undo": {}}

        public_id = f"smm/{datetime.now():%Y%m%d%H%M%S}_{self._slug(path.stem)}"
        try:
            hosted = client.upload(str(path), public_id)
        except Exception as exc:
            return {"summary": f"Cloudinary не принял файл: {exc}", "effect": {}, "undo": {}}

        before = copy.deepcopy(self.dm._data.get(zone, []))
        record["remote_url"] = hosted["url"]
        record["remote_public_id"] = hosted["public_id"]
        self._remember(record, "hosted")
        self.dm.save()
        return {"summary": f"Выложил {record.get('name')} на публичный URL",
                "effect": {"id": media_id, "url": hosted["url"],
                           "resource_type": hosted.get("resource_type", "")},
                "undo": {"op": "restore_sections", "sections": {zone: before},
                         "remote": {"public_id": hosted["public_id"],
                                    "resource_type": hosted.get("resource_type", "image")}}}

    def instagram_publish(self, media_id: str = "", dry_run: str = "1", again: str = "") -> Dict[str, Any]:
        """Опубликовать выложенный материал в Instagram. По умолчанию — только проверка, без публикации."""
        import instagram_auth

        found = self._media_records([media_id])
        if not found:
            return {"summary": f"Материал {media_id or '—'} не найден", "effect": {}, "undo": {}}
        _, zone, record = found[0]
        url = str(record.get("remote_url") or "")
        name = record.get("name") or media_id
        if not url:
            return {"summary": f"{name}: сначала выложите на публичный URL (host_media)",
                    "effect": {}, "undo": {}}
        if record.get("published_id") and str(again).lower() not in ("1", "true", "да"):
            return {"summary": f"{name} уже опубликован (id {record['published_id']}) — "
                                "повторно только по вашему подтверждению",
                    "effect": {}, "undo": {}}
        try:
            token = self._token_store().load_token()
        except instagram_auth.TokenError as exc:
            return {"summary": str(exc), "effect": {}, "undo": {}}
        if not token:
            return {"summary": "Токен Instagram не сохранён — впишите в «Настройках»",
                    "effect": {}, "undo": {}}
        access = instagram_auth.check_access(token)
        if not access.get("ok"):
            return {"summary": "Доступ не готов: " + str(access.get("reason") or "неизвестно"),
                    "effect": {}, "undo": {}}
        ig_user = access["ig_user_id"]
        try:
            left = instagram_auth.publishing_limit(token, ig_user)
        except instagram_auth.PublishError as exc:
            return {"summary": f"Не смог проверить лимит: {exc}", "effect": {}, "undo": {}}
        if left["left"] <= 0:
            return {"summary": f"Лимит публикаций исчерпан ({left['used']} из {left['total']} за 24 ч)",
                    "effect": {}, "undo": {}}
        is_video = Path(str(record.get("path") or "")).suffix.lower() in VIDEO_SUFFIXES
        media_type = "REELS" if is_video else "IMAGE"
        caption = str(record.get("caption") or "").strip()
        preview = (f"{name}: @{access['username'] or ig_user}, {media_type}, "
                   f"осталось публикаций {left['left']} из {left['total']}")
        if str(dry_run).lower() not in ("0", "false", "нет"):
            return {"summary": "Проверка прошла, публикация не запущена: " + preview,
                    "effect": {"dry_run": True, "url": url, "caption_chars": len(caption)},
                    "undo": {}}
        try:
            container = instagram_auth.create_container(
                token, ig_user, {"url": url, "is_video": is_video, "media_type": media_type})
            instagram_auth.wait_container(token, container)
            published = instagram_auth.media_publish(token, ig_user, container)
        except instagram_auth.PublishError as exc:
            return {"summary": f"Instagram не опубликовал {name}: {exc}", "effect": {}, "undo": {}}

        before = copy.deepcopy(self.dm._data.get(zone, []))
        record["published_id"] = published
        self._remember(record, "published")
        self.dm.save()
        return {"summary": f"Опубликовал {name} в Instagram (id {published}). "
                            "Пост в Instagram API не удаляется — откат только локальный",
                "effect": {"id": media_id, "published_id": published},
                "undo": {"op": "restore_sections", "sections": {zone: before}}}

    @staticmethod
    def _slug(text: str, fallback: str = "материал", limit: int = 40) -> str:
        """Имя файла из темы или имени: без пробелов и лишних знаков."""
        slug = re.sub(r"[^\w\-]+", "-", str(text or "").strip().lower())
        slug = re.sub(r"-{2,}", "-", slug).strip("-_")[:limit].strip("-_")
        return slug or fallback

    @staticmethod
    def _pair_captions(records: List[Dict[str, Any]], plan: List[Dict[str, Any]]
                       ) -> Tuple[List[Tuple[Dict[str, Any], Optional[Dict[str, Any]]]],
                                  List[Dict[str, Any]]]:
        """Связать файл с позицией плана: ссылка `media_id`, затем дата, затем порядок плана."""
        free = sorted(plan, key=lambda item: (str(item.get("date") or "~"),
                                             str(item.get("topic") or "")))
        matched: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
        waiting: List[Dict[str, Any]] = []
        for record in records:
            date = str(record.get("date") or "")
            match = next((item for item in free
                          if item.get("media_id") and str(item["media_id"]) == str(record.get("id"))),
                         None)
            match = match or next((item for item in free
                                   if date and str(item.get("date") or "") == date), None)
            if match is None:
                waiting.append(record)
                continue
            free.remove(match)
            matched.append((record, match))
        while waiting and free:
            matched.append((waiting.pop(0), free.pop(0)))
        order = {id(record): index for index, record in enumerate(records)}
        pairs = matched + [(record, None) for record in waiting]
        return sorted(pairs, key=lambda pair: order[id(pair[0])]), free

    def instagram_pack(self, dest: str = "") -> Dict[str, Any]:
        """Собрать пакет под Instagram: файлы одобренных материалов, подписи и замечания."""
        approved = [m for m in self.dm.get_media_ready() if m.get("status") == "approved"]
        plan = self.dm.get_content_plan()
        if not approved and not plan:
            return {"summary": "Пакет не собран: нет ни готовых материалов, ни плана",
                    "effect": {}, "undo": {}}
        base = Path(dest) if str(dest).strip() else Path(self.dm.data_dir) / "instagram"
        folder = base / datetime.now().strftime("%Y%m%d-%H%M%S")
        media_dir = folder / "media"
        media_dir.mkdir(parents=True, exist_ok=True)

        pairs, orphan_captions = self._pair_captions(approved, plan)
        problems: List[str] = [f"{item.get('topic')}: нет файла под подпись"
                               for item in orphan_captions]
        captions_dir = folder / "captions"
        captions_dir.mkdir(parents=True, exist_ok=True)
        manifest = ["файл;дата;тема;подпись;тип;формат;размер;операции"]
        blocks: List[str] = []
        copied = 0
        for record, plan_item in pairs:
            position = plan_item or {}
            path = Path(str(record.get("path") or ""))
            if not path.is_file():
                problems.append(f"{record.get('name')}: файл не найден")
                continue
            name = (f"{datetime.now():%Y%m%d}_"
                    f"{self._slug(Path(str(record.get('name') or '')).stem)}{path.suffix.lower()}")
            try:
                shutil.copy2(path, media_dir / name)
            except OSError as exc:
                problems.append(f"{record.get('name')}: не скопировался ({exc})")
                continue
            copied += 1
            caption = str(position.get("caption") or "").strip()
            tags = " ".join(position.get("hashtags") or [])
            if caption or tags:
                (captions_dir / f"{Path(name).stem}.txt").write_text(
                    "\n".join(part for part in (caption, tags) if part), encoding="utf-8")
            else:
                problems.append(f"{name}: нет подписи в плане")
            if not tags:
                problems.append(f"{name}: нет хэштегов")
            blocks += [f"=== {name} ===",
                       f"{position.get('date') or '—'} · "
                       f"{position.get('topic') or 'без позиции плана'}", caption, tags, ""]
            cells = [name, str(position.get("date") or ""),
                     str(position.get("topic") or ""), "да" if caption else "нет",
                     str(record.get("type") or ""), str(record.get("size") or ""),
                     human_size(path.stat().st_size), " ".join(record.get("processed") or [])]
            manifest.append(";".join(cell.replace(";", ",") for cell in cells))

        (folder / "captions.txt").write_text("\n".join(blocks), encoding="utf-8")
        (folder / "manifest.csv").write_text("\n".join(manifest), encoding="utf-8")
        (folder / "problems.txt").write_text("\n".join(problems) or "замечаний нет",
                                              encoding="utf-8")
        summary = f"Пакет в Instagram: файлов {copied}, позиций плана {len(plan)}"
        if problems:
            summary += f". Замечаний: {len(problems)}"
        return {"summary": summary,
                "effect": {"path": str(folder), "files": copied, "problems": len(problems)},
                "undo": {"op": "delete_folder", "path": str(folder)}}

    # --- PDF documents: plan and strategy ---
    PDF_KINDS = {"plan": "план публикаций", "strategy": "стратегию проекта"}
    PDF_EMPTY = {"plan": "Контент-план пуст — выгружать нечего",
                 "strategy": "Стратегии пока нет — выгружать нечего"}

    def export_pdf(self, kind: str = "plan", dest: str = "") -> Dict[str, Any]:
        """План или стратегия в PDF: в `dest`, если папка выбрана, иначе в проект."""
        import pdf_export

        name = str(kind or "").strip().lower()
        if name not in self.PDF_KINDS:
            return {"summary": f"Неизвестный документ «{kind}»: нужен plan или strategy",
                    "effect": {}, "undo": {}}
        content = {"plan": self.dm.get_content_plan,
                   "strategy": lambda: (self.dm.get_strategy() or {}).get("sections") or []}
        if not content[name]():
            return {"summary": self.PDF_EMPTY[name], "effect": {}, "undo": {}}
        exporters = {"plan": pdf_export.export_content_plan_pdf,
                     "strategy": pdf_export.export_strategy_pdf}

        base = Path(dest) if str(dest).strip() else Path(self.dm.data_dir) / "exports"
        base.mkdir(parents=True, exist_ok=True)
        path = base / f"{datetime.now():%Y%m%d-%H%M%S}-{name}.pdf"
        try:
            exporters[name](self.dm, str(path))
        except RuntimeError as exc:  # нет fpdf2 или шрифта — говорим что именно
            return {"summary": str(exc), "effect": {}, "undo": {}}
        return {"summary": f"Выгрузил {self.PDF_KINDS[name]} в {path}",
                "effect": {"path": str(path), "kind": name},
                "undo": {"op": "delete_file", "path": str(path)}}

    # --- materials: files of the project, not ready media ---
    def import_materials(self, paths: Optional[List[str]] = None,
                         folder: str = "buffer") -> Dict[str, Any]:
        """Скопировать файлы в `<проект>/materials/<папка>` и добавить их в «Материалы»."""
        folder = str(folder or "").strip().lower()
        if folder not in MATERIAL_FOLDERS:
            return {"summary": f"Неизвестная папка материалов: {folder or '—'}",
                    "effect": {}, "undo": {}}
        sources = [path for path in map(Path, paths or []) if path.exists()]
        if not sources:
            return {"summary": "Файлы не найдены — импортировать нечего", "effect": {}, "undo": {}}

        before = copy.deepcopy(self.dm.get_other_files())
        target = Path(self.dm.data_dir) / "materials" / folder
        target.mkdir(parents=True, exist_ok=True)
        records = self.dm._data.setdefault("other_files", {}).setdefault(folder, [])
        copied = []
        for source in sources:
            dest = target / source.name
            counter = 1
            while dest.exists():
                dest = target / f"{source.stem}_{counter}{source.suffix}"
                counter += 1
            shutil.copy2(source, dest)
            copied.append(str(dest))
            records.append({"id": f"of_{uuid.uuid4().hex[:6]}", "name": dest.name,
                            "type": material_kind(dest),
                            "size": human_size(dest.stat().st_size),
                            "date": datetime.now().strftime("%d.%m.%Y"),
                            "tags": [], "path": str(dest)})
        self.dm.save()
        return {"summary": f"Добавил материалов: {len(copied)} в «{folder}»",
                "effect": {"files": copied, "folder": folder},
                "undo": {"op": "restore_sections",
                         "sections": {"other_files": before}, "files": copied}}

    def delete_material(self, item_id: str = "") -> Dict[str, Any]:
        """Убрать запись материала; файл на диске остаётся — его не теряем молча."""
        folders = self.dm._data.get("other_files") or {}
        folder = next((name for name, records in folders.items()
                       if any(str(record.get("id")) == str(item_id) for record in records)), None)
        if folder is None:
            return {"summary": f"Материал {item_id} не найден", "effect": {}, "undo": {}}
        before = copy.deepcopy(self.dm.get_other_files())
        folders[folder] = [record for record in folders[folder]
                          if str(record.get("id")) != str(item_id)]
        self.dm.save()
        return {"summary": f"Убрал материал из «{folder}» (файл остался на диске)",
                "effect": {"id": item_id, "folder": folder},
                "undo": {"op": "restore_sections", "sections": {"other_files": before}}}

    # --- undo dispatcher ---
    def undo(self, action: Dict[str, Any]) -> str:
        spec = action.get("undo") or {}
        op = spec.get("op")
        if op == "restore_section":
            self.dm._data[spec["section"]] = spec.get("data", [])
            self.dm.save()
            return f"Откатил «{action.get('tool')}» ({spec['section']})"
        if op == "restore_strategy":
            self.dm._data["strategy"] = spec.get("data", {})
            self.dm.save()
            return f"Откатил «{action.get('tool')}» (стратегия)"
        if op == "restore_brand_profile":
            self.dm.store.save_brand_profile(spec.get("data") or {})
            return f"Откатил «{action.get('tool')}» (бренд-профиль)"
        if op == "restore_sections":
            for key, value in (spec.get("sections") or {}).items():
                self.dm._data[key] = value
            for name in spec.get("files") or []:
                Path(name).unlink(missing_ok=True)
            self.dm.save()
            removed = self._drop_remote(spec.get("remote"))
            if removed:
                return f"Откатил «{action.get('tool')}» — {removed}"
            return f"Откатил «{action.get('tool')}»"
        if op == "delete_file":
            path = Path(spec.get("path", ""))
            path.unlink(missing_ok=True)
            return f"Удалил файл {path.name}"
        if op == "delete_folder":
            import shutil
            shutil.rmtree(spec.get("path", ""), ignore_errors=True)
            return f"Удалил пакет {Path(spec.get('path', '')).name}"
        if op == "noop":
            return f"«{action.get('tool')}» данные не менял — откатывать нечего"
        return "У этой записи нет обратной операции"

    def _drop_remote(self, spec: Optional[Dict[str, Any]]) -> str:
        """Убрать файл с хостинга при откате: без клиента говорим честно, что остался."""
        if not spec or not spec.get("public_id"):
            return ""
        client = self._cloudinary_client()
        if client is None:
            return f"файл на хостинге остался ({spec['public_id']}): нет ключей Cloudinary"
        if client.delete(str(spec["public_id"]), str(spec.get("resource_type") or "image")):
            return "файл с хостинга удалён"
        return f"хостинг не подтвердил удаление {spec['public_id']} — уберите вручную"


# === Router: rules → local → cloud → editor ===

@dataclass
class RouteDecision:
    tool: str
    args: Dict[str, Any]
    layer: str
    confidence: float = 1.0
    clarify: str = ""


class AIRouter:
    """Turns text into a tool call. Never invents arguments silently."""

    def __init__(self, registry: ToolRegistry, settings, budget: Optional[BudgetGuard],
                 project_id: str, local: Optional[object] = None, cloud: Optional[object] = None,
                 system_context: Callable[[], str] = lambda: ""):
        self.registry = registry
        self.settings = settings
        self.budget = budget
        self.project_id = project_id
        self.local = local
        self.cloud = cloud
        self.system_context = system_context

    # --- layer 1: rules ---
    def _rules(self, text: str) -> Optional[RouteDecision]:
        low = text.lower()
        if re.search(r"бренд.?профил|профил[ья] бренда|заполни профиль", low):
            return RouteDecision("brand_profile_interview", {}, "rules")
        if re.search(r"отмени последн|откати последн|undo", low):
            return RouteDecision("undo_last", {}, "rules")
        if re.search(r"журнал|история действий|что ты сделал", low):
            return RouteDecision("show_journal", {}, "rules")
        if re.search(r"сколько (постов|позиций|событий|медиа)|что в проекте|контекст проекта", low):
            return RouteDecision("get_project_context", {"scope": "all"}, "rules")
        if re.search(r"(сделай|собери|создай|разработай).{0,20}стратеги", low):
            return RouteDecision("create_strategy", {"brief": text}, "rules")
        if re.search(r"(придумай|предложи|подбери).{0,25}(тем|идеи)", low):
            return RouteDecision("create_content_plan",
                                 {"count": _first_int(low) or 10,
                                  "period_days": _period_days(low)}, "rules")
        if re.search(r"(создай|сделай|составь).{0,25}(контент.?план|план на)", low):
            count = _first_int(low) or 5
            return RouteDecision("create_content_plan",
                                 {"count": count, "period_days": _period_days(low)}, "rules")
        if re.search(r"(создай|сделай).{0,15}(тз|задание на съемку)", low):
            plan_id = self._latest_plan_without_task()
            if not plan_id:
                return RouteDecision("create_shooting_task", {},
                                     "rules", 0.4,
                                     "Нет позиции плана без ТЗ. Сначала добавьте пост в план.")
            return RouteDecision("create_shooting_task", {"plan_id": plan_id}, "rules")
        video_ask = re.search(r"видео.{0,30}(рилс|reels|тикток|tiktok|шортс|shorts|пост|1:1|ютуб|youtube)"
                              r"|(рилс|reels|тикток|tiktok|шортс|shorts).{0,30}видео", low)
        if video_ask or re.search(r"субтитр", low):
            paths = _video_paths(text)
            if not paths:
                return RouteDecision("", {}, "rules", 0.4,
                                     "Пришли путь к видеофайлу или выбери видео в «Публикациях».")
            if video_ask:
                return RouteDecision("process_video",
                                     {"platform": _platform_from_text(low), "paths": paths},
                                     "rules")
            return RouteDecision("make_subtitles",
                                 {"paths": paths, "language": "ru",
                                  "burn": "srt" not in low}, "rules")
        if re.search(r"pdf|печатн", low) and re.search(r"план|стратег|выгруз", low):
            return RouteDecision("export_pdf",
                                 {"kind": "strategy" if "стратег" in low else "plan"},
                                 "rules")
        if re.search(r"проверь.{0,20}(доступ|инстаграм|instagram)|доступ к инстаграм", low):
            return RouteDecision("instagram_status", {}, "rules")
        if re.search(r"календар", low) and re.search(r"добав|перенес|синхрон|расстав|постав", low):
            return RouteDecision("sync_plan_events", {}, "rules")
        if re.search(r"календар", low) and re.search(r"покажи|открой|посмотри|что в|какие|список", low):
            return RouteDecision("get_project_context", {"scope": "calendar"}, "rules")
        if re.search(r"(проверь|проверить|проверка).{0,25}(план|публикац|позиц)"
                     r"|(план|публикац).{0,20}провер", low):
            return RouteDecision("validate_plan", {}, "rules")
        if re.search(r"инстаграм|instagram", low) and re.search(r"пакет|публикац|выгруз|собери|подготовь", low):
            return RouteDecision("instagram_pack", {}, "rules")
        if re.search(r"(собери|сделай|подготовь).{0,20}(пакет|выгруз)|экспорт", low):
            return RouteDecision("export_package", {}, "rules")
        if re.search(r"аналитик|что зашло|что сработал|метрик|вовлеч[её]нност", low):
            return RouteDecision("analyze_performance",
                                 {"period_days": _period_days(low)}, "rules")
        if re.search(r"подпись|подписи|caption|хэштег", low):
            plan_id, problem = self._plan_id_from_text(text)
            if problem:
                return RouteDecision("", {}, "rules", 0.4, problem)
            if not plan_id:
                return RouteDecision("write_captions", {}, "rules", 0.4,
                                     "В плане пока нет позиций — не к чему писать подпись.")
            return RouteDecision("write_captions", {"plan_id": plan_id}, "rules")
        return None

    # --- layer 2/3: models ---
    def _prompt(self, text: str) -> Tuple[str, str]:
        system = (
            "Ты диспетчер SMM-менеджера. Верни ТОЛЬКО JSON без пояснений:\n"
            '{"tool": "<имя>", "args": {...}, "confidence": 0.0-1.0}\n'
            "Если задача непонятна или не хватает данных — "
            '{"clarify": "<один уточняющий вопрос>", "confidence": 0.0}\n'
            f"Доступные инструменты:\n{self.registry.description()}\n"
            f"Контекст проекта:\n{self.system_context()}")
        return system, text

    def _from_model(self, result: LLMResult, layer: str) -> Optional[RouteDecision]:
        if not result.text or result.error:
            return None
        data = None
        for candidate in _json_candidates(result.text):
            if not isinstance(candidate, dict):
                continue
            if candidate.get("clarify"):
                return RouteDecision("", {}, layer, 0.0, str(candidate["clarify"]))
            if str(candidate.get("tool") or "") in self.registry.tools:
                data = candidate
                break
        if data is None:
            return None
        try:
            confidence = float(data.get("confidence", 0))
        except (TypeError, ValueError):
            confidence = 0.0
        args = data.get("args") if isinstance(data.get("args"), dict) else {}
        return RouteDecision(str(data.get("tool") or ""), args, layer, confidence)

    def _ask(self, provider, purpose: str) -> Optional[RouteDecision]:
        if provider is None or not provider.available():
            return None
        if getattr(provider, "name", "") == "cloud":
            if self.budget is None or not self.budget.can_spend():
                logger.warning("budget stop: cloud provider skipped")
                return None
        system, user = self._prompt(purpose)
        result = provider.chat(system, user, temperature=0.1, max_tokens=512)
        if self.budget is not None:
            self.budget.record(self.project_id, "route", result)
        return self._from_model(result, getattr(provider, "name", "model"))

    def route(self, text: str) -> RouteDecision:
        decision = self._rules(text)
        if decision and (decision.tool or decision.clarify):
            return decision

        local = self._ask(self.local, text)
        editor = self._editor(local)
        if editor and editor.confidence >= CONFIDENCE_MIN:
            return editor
        if local and local.clarify:
            return local

        cloud = self._ask(self.cloud, text)
        editor = self._editor(cloud)
        if editor and editor.confidence >= CONFIDENCE_MIN:
            return editor
        if cloud and cloud.clarify:
            return cloud
        return RouteDecision("", {}, "editor", 0.0,
                             "Не понял задачу. Скажи иначе: например «создай стратегию», "
                             "«создай контент-план на 10 постов», «заполни бренд-профиль».")

    def _editor(self, decision: Optional[RouteDecision]) -> Optional[RouteDecision]:
        """Layer 4: validate the model's tool call without any model."""
        if not decision or not decision.tool:
            return decision
        spec = self.registry.get(decision.tool)
        if not spec:
            return None
        cleaned: Dict[str, Any] = {}
        for arg_name, arg_type in spec.args.items():
            if arg_name not in decision.args:
                continue
            value = decision.args[arg_name]
            try:
                if arg_type is int:
                    value = int(value)
                elif arg_type is list and not isinstance(value, list):
                    value = [value]
                elif arg_type is str:
                    value = str(value)
            except (TypeError, ValueError):
                return RouteDecision("", {}, "editor", 0.0,
                                     f"Не разобрал аргумент «{arg_name}». Уточни запрос.")
            cleaned[arg_name] = value
        return RouteDecision(decision.tool, cleaned, decision.layer, decision.confidence)

    # --- generation helpers ---
    def _generate(self, system: str, user: str, purpose: str) -> str:
        for provider in (self.local, self.cloud):
            if provider is None or not provider.available():
                continue
            if getattr(provider, "name", "") == "cloud" and self.budget and not self.budget.can_spend():
                continue
            result = provider.chat(system, user, temperature=0.5, max_tokens=1600)
            if self.budget is not None:
                self.budget.record(self.project_id, purpose, result)
            if result.text and not result.error:
                return result.text.strip()
        return ""

    def generate_text(self, system: str, user: str, purpose: str) -> str:
        return self._generate(system, user, purpose)

    def generate_strategy_sections(self, brief: str) -> List[Dict[str, Any]]:
        profile = {}
        if hasattr(self, "profile_getter"):
            profile = self.profile_getter() or {}
        system = ("Ты SMM-стратег. Верни JSON: {\"sections\": [{\"id\": \"about\", \"title\": \"О проекте\", "
                  "\"content\": \"...\"}]} — 5 блоков: about, audience, positioning, usp, tone. "
                  "Пиши по-русски, 2–4 предложения на блок.")
        user = f"Бриф: {brief}\nБренд-профиль: {json.dumps(profile, ensure_ascii=False)}"
        raw = self._generate(system, user, "strategy")
        for data in _json_candidates(raw):
            sections = data.get("sections") if isinstance(data, dict) else None
            if isinstance(sections, list):
                built = [s for s in sections if isinstance(s, dict)]
                if built:
                    return built
        return []

    def generate_plan_topics(self, count: int = 10, brief: str = "") -> List[Dict[str, Any]]:
        """Темы для контент-плана от модели: тема, рубрика, формат. Без модели — пусто."""
        profile = (self.profile_getter() if hasattr(self, "profile_getter") else {}) or {}
        strategy = (self.strategy_getter() if hasattr(self, "strategy_getter") else {}) or {}
        sections = [f"{s.get('title')}: {s.get('content')}" for s in strategy.get("sections") or []]
        system = ("Ты SMM-стратег. Верни JSON: {\"topics\": [{\"topic\": \"...\", \"rubric\": \"...\", "
                  "\"format\": \"Пост\"}]}. Темы конкретные и разные, без нумерации и без слова «идея». "
                  "Каждая тема — про гостя и его выгоду: что он получит, попробует, сэкономит или почувствует. "
                  "Не предлагай темы про то, как гость готовит или обжаривает кофе дома, и про внутренние "
                  "процессы без пользы для гостя. "
                  "format — только «Пост», «Reels» или «Карусель». Пиши по-русски.")
        user = (f"Бренд-профиль: {json.dumps(profile, ensure_ascii=False)}\n"
                f"Стратегия: {' | '.join(sections) or 'нет'}\n"
                f"Задача: {brief or 'контент на ближайшие дни'}\nТем: {count}")
        raw = self._generate(system, user, "plan_topics")
        for data in _json_candidates(raw):
            topics = data.get("topics") if isinstance(data, dict) else None
            if not isinstance(topics, list):
                continue
            built = []
            for item in topics:
                if isinstance(item, str) and item.strip():
                    built.append({"topic": item.strip()})
                elif isinstance(item, dict) and str(item.get("topic") or "").strip():
                    built.append(item)
            if built:
                return built[:count]
        return []

    def write_caption(self, brief: str) -> str:
        profile = (self.profile_getter() if hasattr(self, "profile_getter") else {}) or {}
        tone = str(profile.get("tone_of_voice") or "").strip()
        system = ("Ты SMM-копирайтер. Дай подпись до 400 символов, 3–5 хэштегов и CTA. "
                  "Без markdown. Обращайся к читателю на «вы», одно обращение на весь текст.")
        if tone:
            system += f" Тон голоса бренда: {tone}."
        if profile.get("client_name"):
            system += f" Бренд: {profile['client_name']}, ниша: {profile.get('niche') or '—'}."
        text = self._generate(system, brief, "caption")
        if not text:
            return f"{brief}\n\nПодпишитесь, чтобы не пропустить новые посты.\n#smm #контент"
        return self._fit_caption(text.strip(), system, brief)

    def _fit_caption(self, text: str, system: str, brief: str) -> str:
        """Подпись не длиннее CAPTION_LIMIT: сначала просим сократить, потом режем по предложению."""
        if len(text) <= CAPTION_LIMIT:
            return text
        shorter = self._generate(
            f"{system} Ответь только подписью не длиннее {CAPTION_LIMIT} символов, сохрани 3–5 хэштегов и CTA.",
            f"{brief}\nСократи этот вариант до {CAPTION_LIMIT} символов:\n{text}", "caption_short")
        if shorter and len(shorter.strip()) <= CAPTION_LIMIT:
            return shorter.strip()
        return _shorten_caption(shorter or text)

    # --- small lookups ---
    def _latest_plan_id(self) -> str:
        items = self.dm_plan()
        return items[-1]["id"] if items else ""

    def _plan_id_from_text(self, text: str) -> Tuple[str, str]:
        """Позиция плана из фразы: по дате, по номеру (с 1) или последняя. Возвращает id и текст отказа."""
        items = self.dm_plan()
        if not items:
            return "", ""
        for item in items:
            date = str(item.get("date") or "").strip()
            if date and date in text:
                return str(item.get("id") or ""), ""
        low = text.lower()
        match = (re.search(r"(?:№|номер\s*|пост\s*|позици[яи]\s*)(\d{1,3})", low)
                 or re.search(r"(\d{1,3})(?:-?[йоге])?\s*(?:пост|позици)", low))
        if match:
            number = int(match.group(1))
            if 1 <= number <= len(items):
                return str(items[number - 1].get("id") or ""), ""
            return "", f"В плане {len(items)} позиций — номера {number} нет."
        return self._latest_plan_id(), ""

    def _latest_plan_without_task(self) -> str:
        for item in reversed(self.dm_plan()):
            if not item.get("shooting_task_id"):
                return item["id"]
        return ""

    def dm_plan(self) -> List[Dict[str, Any]]:
        return list(getattr(self, "plan_getter", lambda: [])())


def _first_int(text: str) -> Optional[int]:
    match = re.search(r"\b(\d{1,3})\b", text)
    return int(match.group(1)) if match else None


def _period_days(text: str) -> int:
    match = re.search(r"на\s+(\d{1,2})\s*(дн|недел|месяц)", text)
    if not match:
        return 7
    amount = int(match.group(1))
    unit = match.group(2)
    return amount * 7 if unit.startswith("недел") else amount * 30 if unit.startswith("месяц") else amount


THINK_BLOCK = re.compile(r"<think(?:ing)?>.*?(?:</think(?:ing)?>|\Z)", re.S | re.I)


def _strip_thinking(text: str) -> str:
    """Убрать блок рассуждений Qwen3: в нём бывают примеры JSON и лишние скобки."""
    return THINK_BLOCK.sub("", str(text or "")).strip()


def _balanced_objects(text: str) -> List[Any]:
    """Все объекты и массивы в тексте, границы — по вложенности и строкам, без угадывания."""
    found: List[Any] = []
    for start, char in enumerate(text):
        if char not in "{[":
            continue
        closing = "}" if char == "{" else "]"
        depth, in_string, escaped = 0, False, False
        for index in range(start, len(text)):
            symbol = text[index]
            if in_string:
                if escaped:
                    escaped = False
                elif symbol == "\\":
                    escaped = True
                elif symbol == '"':
                    in_string = False
                continue
            if symbol == '"':
                in_string = True
            elif symbol == char:
                depth += 1
            elif symbol == closing:
                depth -= 1
                if depth == 0:
                    try:
                        found.append(json.loads(text[start:index + 1]))
                    except ValueError:
                        pass
                    break
    return found


def _json_candidates(text: str) -> List[Any]:
    """Все варианты JSON из ответа модели: в рассуждениях Qwen3 бывают свои примеры."""
    if not text:
        return []
    cleaned = _strip_thinking(text)
    blocks = [cleaned, re.sub(r"^```[a-zA-Z]*\n?|```$", "", cleaned).strip()]
    blocks += [block.strip() for block in re.findall(r"```[a-zA-Z]*\n?(.*?)```", cleaned, re.S)]
    found: List[Any] = []
    for candidate in blocks:
        try:
            value = json.loads(candidate)
        except ValueError:
            continue
        if value not in found:
            found.append(value)
    found.extend(_balanced_objects(cleaned))
    return found


def _extract_json(text: str) -> Optional[Any]:
    candidates = _json_candidates(text)
    return candidates[0] if candidates else None


# === Brand interview ===

BRAND_QUESTIONS: List[Tuple[str, str]] = [
    ("client_name", "Как называется клиент или бренд?"),
    ("niche", "Ниша и продукт: чем занимается клиент?"),
    ("city", "География: город или регион?"),
    ("audience", "Кто целевая аудитория?"),
    ("positioning", "Чем клиент отличается от конкурентов?"),
    ("tone_of_voice", "Какой tone of voice: строгий, дружелюбный, экспертный?"),
    ("languages", "Языки контента: RU или RU + KZ?"),
    ("stop_words", "Стоп-слова и запрещённые темы? (можно «нет»)"),
]


@dataclass
class AIReply:
    text: str
    layer: str = "editor"
    actions: List[Dict[str, Any]] = field(default_factory=list)
    needs_confirmation: bool = False
    pending_tool: str = ""
    pending_args: Dict[str, Any] = field(default_factory=dict)


class AICore:
    """One entry point for the chat panel."""

    def __init__(self, dm, settings, app_db_path: Optional[Path] = None,
                 local_provider=None, cloud_provider=None, providers=None):
        self.dm = dm
        self.settings = settings
        self.journal = ActionJournal(dm.store)
        limit = float(settings.get("monthly_budget_usd") or 0) if settings else 0
        if app_db_path is None:
            app_db_path = Path(__file__).resolve().parent.parent / "data" / "app.db"
        self.budget = BudgetGuard(app_db_path, limit)

        if providers is not None:
            local_provider, cloud_provider = providers

        self.local = local_provider if local_provider is not None else OllamaProvider(
            model=(settings.get("local_model") if settings else None) or "qwen2.5:7b-instruct")
        if cloud_provider is None:
            cloud_provider = CloudProvider(
                endpoint=(settings.get("cloud_endpoint") if settings else "") or "",
                model=(settings.get("cloud_model") if settings else "") or "")
        self.cloud = cloud_provider

        self.tools = AITools(dm, self)
        self.tools.app_db_path = Path(app_db_path)
        self.registry = ToolRegistry()
        self._register_tools()
        self.router = AIRouter(self.registry, settings, self.budget, dm.project_id,
                               self.local, self.cloud,
                               system_context=self._context_text)
        self.router.plan_getter = dm.get_content_plan
        self.router.profile_getter = dm.get_brand_profile
        self.router.strategy_getter = dm.get_strategy
        self.tools.router = self.router

        self.interview: Dict[str, Any] = {}
        self.pending: Optional[Tuple[str, Dict[str, Any]]] = None

    # --- setup ---
    def _register_tools(self) -> None:
        self.registry.register(ToolSpec("get_project_context", "прочитать профиль, стратегию, план, календарь",
                                        {"scope": str}, self.tools.context, read_only=True))
        self.registry.register(ToolSpec("search_knowledge", "поиск по материалам и документам",
                                        {"query": str, "limit": int}, self.tools.search_knowledge,
                                        read_only=True))
        self.registry.register(ToolSpec("create_strategy", "создать блоки стратегии",
                                        {"brief": str, "sections": list}, self.tools.create_strategy,
                                        needs_confirmation=lambda a: bool(
                                            (self.dm.get_strategy() or {}).get("sections"))))
        self.registry.register(ToolSpec("update_strategy_section", "править блок стратегии",
                                        {"section_id": str, "content": str},
                                        self.tools.update_strategy_section))
        self.registry.register(ToolSpec("create_content_plan", "создать позиции контент-плана",
                                        {"count": int, "rubrics": list, "start": str,
                                         "period_days": int, "topics": list},
                                        self.tools.create_content_plan))
        self.registry.register(ToolSpec("schedule_posts", "расставить даты и события",
                                        {"plan_ids": list, "dates": list},
                                        self.tools.schedule_posts,
                                        needs_confirmation=lambda a: len(a.get("dates") or []) > 3))
        self.registry.register(ToolSpec("create_shooting_task", "ТЗ на съёмку из позиции плана",
                                        {"plan_id": str}, self.tools.create_shooting_task))
        self.registry.register(ToolSpec("update_kpis", "обновить KPI стратегии",
                                        {"kpis": list}, self.tools.update_kpis))
        self.registry.register(ToolSpec("add_record", "добавить запись в план/календарь/ТЗ",
                                        {"section": str, "fields": dict}, self.tools.add_record))
        self.registry.register(ToolSpec("edit_record", "изменить запись плана/календаря/ТЗ",
                                        {"section": str, "item_id": str, "fields": dict},
                                        self.tools.edit_record))
        self.registry.register(ToolSpec("delete_record", "удалить запись плана/календаря/ТЗ",
                                        {"section": str, "item_id": str}, self.tools.delete_record))
        self.registry.register(ToolSpec("sync_plan_events", "события календаря из позиций плана",
                                        {}, self.tools.sync_plan_events))
        self.registry.register(ToolSpec("validate_plan", "проверка плана: даты, подписи, ТЗ",
                                        {}, self.tools.validate_plan, read_only=True))
        self.registry.register(ToolSpec("analyze_performance",
                                        "сводка по метрикам: охват, вовлечённость, топ постов",
                                        {"period_days": int},
                                        self.tools.analyze_performance, read_only=True))
        self.registry.register(ToolSpec("write_captions", "подпись, хэштеги, CTA",
                                        {"plan_id": str}, self.tools.write_captions))
        self.registry.register(ToolSpec("import_media", "импорт файлов в проект",
                                        {"paths": list, "zone": str}, self.tools.import_media))
        self.registry.register(ToolSpec("batch_photo", "кадрирование, цвет, сжатие",
                                        {"media_ids": list, "operations": list},
                                        self.tools.batch_photo,
                                        needs_confirmation=lambda a: len(a.get("media_ids") or []) > 10))
        self.registry.register(ToolSpec("process_video",
                                        "видео под площадку: 9:16 или 1:1, сжатие",
                                        {"media_ids": list, "platform": str, "paths": list},
                                        self.tools.process_video,
                                        needs_confirmation=lambda a: len(a.get("media_ids") or []) > 5))
        self.registry.register(ToolSpec("make_subtitles",
                                        "распознать речь: .srt и видео с субтитрами",
                                        {"media_ids": list, "language": str, "burn": bool,
                                         "paths": list},
                                        self.tools.make_subtitles,
                                        needs_confirmation=lambda a: len(a.get("media_ids") or []) > 3))
        self.registry.register(ToolSpec("instagram_status",
                                        "проверить доступ к Instagram (read-only)",
                                        {}, self.tools.instagram_status, read_only=True))
        self.registry.register(ToolSpec("host_media",
                                        "выложить материал на публичный URL для публикации",
                                        {"media_id": str}, self.tools.host_media))
        self.registry.register(ToolSpec("instagram_publish",
                                        "опубликовать выложенный материал в Instagram (сначала проверка)",
                                        {"media_id": str, "dry_run": str, "again": str},
                                        self.tools.instagram_publish,
                                        needs_confirmation=lambda a: str(a.get("dry_run", "1")).lower()
                                        not in ("0", "false", "нет")))
        self.registry.register(ToolSpec("instagram_pack",
                                        "пакет под Instagram: файлы, подписи, замечания",
                                        {"dest": str}, self.tools.instagram_pack))
        self.registry.register(ToolSpec("export_pdf", "план или стратегия в PDF",
                                        {"kind": str, "dest": str}, self.tools.export_pdf))
        self.registry.register(ToolSpec("import_materials", "импорт файлов в «Материалы»",
                                        {"paths": list, "folder": str},
                                        self.tools.import_materials))
        self.registry.register(ToolSpec("delete_material", "убрать материал из списка",
                                        {"item_id": str}, self.tools.delete_material))
        self.registry.register(ToolSpec("export_package", "пакет публикаций за период",
                                        {"date_from": str, "date_to": str, "dest": str},
                                        self.tools.export_package,
                                        needs_confirmation=lambda a: True))

    def _context_text(self) -> str:
        strat = self.dm.get_strategy() or {}
        profile = self.dm.get_brand_profile() or {}
        bits = [f"проект {self.dm.project_id}",
                f"блоков стратегии {len(strat.get('sections') or [])}",
                f"позиций плана {len(self.dm.get_content_plan())}"]
        if profile.get("client_name"):
            bits.append(f"бренд {profile['client_name']}, ниша {profile.get('niche')}, "
                        f"языки {profile.get('languages')}")
        return "; ".join(bits)

    # --- public API ---
    def handle(self, text: str) -> AIReply:
        text = (text or "").strip()
        if not text:
            return AIReply("Напишите задачу.")

        if self.interview:
            return self._interview_step(text)
        if self.pending:
            if re.match(r"^(да|yes|ок|ok|подтверждаю)\b", text.lower()):
                tool, args = self.pending
                self.pending = None
                return self._execute(tool, args, "confirm")
            if re.match(r"^(нет|no|отмена)\b", text.lower()):
                self.pending = None
                return AIReply("Отменил, ничего не записал.")
            self.pending = None

        decision = self.router.route(text)

        if decision.tool == "undo_last":
            return self._undo_last()
        if decision.tool == "show_journal":
            return self._journal_reply()
        if decision.tool == "brand_profile_interview":
            return self._start_interview()
        if not decision.tool:
            return AIReply(decision.clarify or "Уточните задачу.", decision.layer)

        spec = self.registry.get(decision.tool)
        missing = [name for name in spec.args if name not in decision.args
                   and name in ("plan_id", "section_id")]
        if missing:
            return AIReply(f"Не хватает данных: {', '.join(missing)}. Уточните запрос.",
                           decision.layer)
        if spec.needs_confirmation and spec.needs_confirmation(decision.args):
            self.pending = (decision.tool, decision.args)
            return AIReply(f"План: {decision.tool} с аргументами "
                           f"{json.dumps(decision.args, ensure_ascii=False)}.\n"
                           "Подтвердите: «да» или «нет».",
                           decision.layer, needs_confirmation=True,
                           pending_tool=decision.tool, pending_args=decision.args)
        return self._execute(decision.tool, decision.args, decision.layer)

    def _execute(self, tool: str, args: Dict[str, Any], layer: str) -> AIReply:
        spec = self.registry.get(tool)
        if spec is None:
            return AIReply(f"Инструмент {tool} не зарегистрирован.", layer)
        try:
            outcome = spec.handler(**args) or {}
        except Exception as exc:
            logger.exception("tool %s failed", tool)
            self.journal.log(tool, args, {"error": str(exc)}, {}, status="failed")
            return AIReply(f"Не смог выполнить «{tool}»: {exc}", layer)

        undo = outcome.get("undo") or {}
        effect = outcome.get("effect") or {}
        if spec.read_only:
            # чтение ничего не меняет: журнал и действия не нужны, ответ — только сводка
            return AIReply(outcome.get("summary", "Готово"), layer)
        if not effect and not undo:
            # nothing changed (no model, unknown id, validation failure) — nothing to journal
            return AIReply(outcome.get("summary", "Ничего не изменил."), layer)

        action_id = self.journal.log(tool, args, effect, undo)
        actions = [{"id": action_id, "tool": tool, "summary": outcome.get("summary", "")}]
        self._refresh_ui()
        return AIReply(f"{outcome.get('summary', 'Готово')}\nЖурнал: {action_id}", layer, actions)

    def _undo_last(self) -> AIReply:
        entries = [a for a in self.journal.list(20) if a["status"] == "done"]
        if not entries:
            return AIReply("В журнале нет действий для отката.")
        last = entries[0]
        message = self.tools.undo(last)
        self.journal.mark_undone(last["id"])
        self.journal.log("undo", {"action_id": last["id"]}, {"undone": last["id"]}, {},
                         actor="user")
        self._refresh_ui()
        return AIReply(message, "journal", [{"id": last["id"], "tool": "undo", "summary": message}])

    def undo(self, action_id: str) -> AIReply:
        row = self.journal.get(action_id)
        if row is None:
            return AIReply("Запись не найдена.")
        action = {"id": row["id"], "tool": row["tool"], "undo": _loads(row["undo"])}
        message = self.tools.undo(action)
        self.journal.mark_undone(action_id)
        self.journal.log("undo", {"action_id": action_id}, {"undone": action_id}, {}, actor="user")
        self._refresh_ui()
        return AIReply(message, "journal")

    def _journal_reply(self) -> AIReply:
        entries = self.journal.list(8)
        if not entries:
            return AIReply("Журнал пуст: действий ещё не было.", "journal")
        lines = [f"{e['ts'][11:16]} · {e['tool']} · {e['status']} · {e['id']}" for e in entries]
        return AIReply("Последние действия:\n" + "\n".join(lines), "journal")

    def _refresh_ui(self) -> None:
        panel_refresh = getattr(self, "on_change", None)
        if callable(panel_refresh):
            panel_refresh()

    # --- public API for sections ---
    def run_tool(self, tool: str, **args) -> AIReply:
        """Execute one tool by name (used by GUI sections); journaling included."""
        if self.registry.get(tool) is None:
            return AIReply(f"Инструмент {tool} не зарегистрирован.")
        return self._execute(tool, args, "gui")

    def rewrite_section(self, section_id: str, mode: str = "rewrite") -> AIReply:
        """Ask the model to improve one strategy block and write it back."""
        strategy = self.dm.get_strategy() or {}
        section = next((s for s in strategy.get("sections", []) if s.get("id") == section_id), None)
        if section is None:
            return AIReply(f"Блок {section_id} не найден.")
        prompts = {
            "rewrite": "Перепиши блок стратегии яснее и конкретнее, сохрани смысл.",
            "deepen": "Углуби блок стратегии: добавь детали, примеры и цифры, если уместно.",
            "alternative": "Предложи альтернативный вариант блока стратегии.",
        }
        instruction = prompts.get(mode, prompts["rewrite"])
        profile = self.dm.get_brand_profile() or {}
        system = "Ты SMM-стратег. Верни только новый текст блока, без заголовка и markdown."
        user = (f"{instruction}\n\nБлок «{section.get('title')}»:\n{section.get('content', '')}\n\n"
                f"Бренд-профиль: {json.dumps(profile, ensure_ascii=False)}")
        text = self.router.generate_text(system, user, f"strategy_{mode}")
        if not text:
            return AIReply("Нужна модель: локальная Ollama или облако. Проверьте настройки.")
        return self._execute("update_strategy_section",
                             {"section_id": section_id, "content": text}, "gui")

    # --- brand interview ---
    def _start_interview(self) -> AIReply:
        self.interview = {"answers": {}, "index": 0}
        return AIReply("Заполним бренд-профиль. " + BRAND_QUESTIONS[0][1] + " (8 вопросов, "
                       "можно ответить «пропустить»)", "rules")

    def _interview_step(self, text: str) -> AIReply:
        key, question = BRAND_QUESTIONS[self.interview["index"]]
        if text.lower() not in ("пропустить", "skip", "-"):
            self.interview["answers"][key] = text
        self.interview["index"] += 1

        if self.interview["index"] < len(BRAND_QUESTIONS):
            next_question = BRAND_QUESTIONS[self.interview["index"]][1]
            return AIReply(f"{next_question} ({self.interview['index'] + 1}/8)")

        answers = self.interview["answers"]
        self.interview = {}
        if not answers:
            return AIReply("Ответов нет — профиль не изменил.")
        before = self.dm.get_brand_profile() or {}
        self.dm.save_brand_profile(answers)
        self.journal.log("brand_profile_save", answers,
                         {"fields": sorted(answers)},
                         {"op": "restore_brand_profile", "data": before})
        self._refresh_ui()
        filled = ", ".join(sorted(answers))
        return AIReply(f"Бренд-профиль сохранён ({filled}). Теперь он подставляется в каждый запрос.",
                       "rules", [{"id": "brand_profile", "tool": "brand_profile_save",
                                  "summary": "профиль сохранён"}])

    def close(self) -> None:
        try:
            self.budget.close()
        except Exception:
            pass
