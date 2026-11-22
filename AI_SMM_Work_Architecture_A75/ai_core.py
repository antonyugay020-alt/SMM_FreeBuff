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
        return {
            "summary": (f"Проект: {strat.get('project_name') or self.dm.project_id}. "
                        f"Блоков стратегии: {len(strat.get('sections') or [])}, "
                        f"позиций плана: {len(plan)}, событий: {len(self.dm.get_calendar_events())}, "
                        f"медиа: {len(self.dm.get_media_sources()) + len(self.dm.get_media_ready())}."),
            "effect": {"profile_filled": bool(profile.get("client_name")),
                       "strategy_sections": len(strat.get("sections") or []),
                       "plan_items": len(plan)},
            "undo": {},
        }

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

    def create_content_plan(self, count: int = 5, rubrics: Optional[List[str]] = None,
                            start: Optional[str] = None, period_days: int = 7) -> Dict[str, Any]:
        count = max(1, min(int(count or 5), 60))
        rubrics = [r for r in (rubrics or []) if str(r).strip()] or ["Полезное"]
        try:
            start_date = datetime.strptime(start, "%d.%m.%Y") if start else datetime.now()
        except ValueError:
            start_date = datetime.now()
        step = max(1, int(period_days or 7) // count)

        def apply(current: List[Dict[str, Any]]) -> Dict[str, Any]:
            created = []
            for index in range(count):
                item_id = f"cp_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:5]}"
                current.append({
                    "id": item_id,
                    "date": (start_date + timedelta(days=index * step)).strftime("%d.%m.%Y"),
                    "rubric": rubrics[index % len(rubrics)],
                    "topic": f"{rubrics[index % len(rubrics)]}: идея {index + 1}",
                    "format": "Пост",
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
            try:
                dest = self._copy_media(path)
            except OSError as exc:
                logger.warning("import copy failed: %s", exc)
                missing.append(path.name)
                continue
            record = {
                "id": f"{zone_key[:5]}_{datetime.now().strftime('%H%M%S%f')[:10]}",
                "name": dest.name,
                "type": "video" if dest.suffix.lower() in (".mp4", ".mov", ".avi", ".mkv") else "image",
                "size": "unknown",
                "path": str(dest),
            }
            if zone_key == "media_references":
                record["category"] = "референс"
            else:
                record.update({"status": "pending",
                               "date": datetime.now().strftime("%d.%m.%Y")})
            self.dm._data.setdefault(zone_key, []).append(record)
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
        zones = ("media_ready", "media_sources", "media_references")
        index = {str(record.get("id")): (zone, record) for zone in zones
                 for record in self.dm._data.get(zone, []) if record.get("id")}
        ids = [str(media_id) for media_id in (media_ids or []) if str(media_id) in index]
        if not ids:
            return {"summary": "Нечего обрабатывать: материалы не найдены",
                    "effect": {}, "undo": {}}

        before: Dict[str, Any] = {}
        done: List[str] = []
        files: List[str] = []
        skipped: List[str] = []
        for media_id in ids:
            zone, record = index[media_id]
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

    def process_video(self, media_ids: Optional[List[str]] = None,
                      platform: str = "instagram_reels") -> Dict[str, Any]:
        """Подготовить видео под площадку: размер, кадры, сжатие — всегда от исходника."""
        target = str(platform or "").strip().lower()
        if target not in VIDEO_TARGETS:
            return {"summary": f"Неизвестная площадка: {platform or '—'}",
                    "effect": {}, "undo": {}}
        zones = ("media_ready", "media_sources", "media_references")
        index = {str(record.get("id")): (zone, record) for zone in zones
                 for record in self.dm._data.get(zone, []) if record.get("id")}
        ids = [str(media_id) for media_id in (media_ids or []) if str(media_id) in index]
        if not ids:
            return {"summary": "Нечего обрабатывать: материалы не найдены",
                    "effect": {}, "undo": {}}
        processor = self._video_processor()
        if not processor.ffmpeg_available:
            return {"summary": "Нужен ffmpeg: без него видео не обработать",
                    "effect": {}, "undo": {}}

        label, suffix = VIDEO_TARGETS[target]
        before: Dict[str, Any] = {}
        done: List[str] = []
        files: List[str] = []
        skipped: List[str] = []
        for media_id in ids:
            zone, record = index[media_id]
            source = self._video_source(record)
            if source is None:
                skipped.append(f"{record.get('name')}: файл не найден или это не видео")
                continue
            dest = MEDIA_IMAGES / f"{source.stem}_{suffix}.mp4"
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
            record["processed"] = [target]
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
        if re.search(r"pdf|печатн", low) and re.search(r"план|стратег|выгруз", low):
            return RouteDecision("export_pdf",
                                 {"kind": "strategy" if "стратег" in low else "plan"},
                                 "rules")
        if re.search(r"(собери|сделай|подготовь).{0,20}(пакет|выгруз)|экспорт", low):
            return RouteDecision("export_package", {}, "rules")
        if re.search(r"аналитик|что зашло|что сработал|метрик|вовлеч[её]нност", low):
            return RouteDecision("analyze_performance",
                                 {"period_days": _period_days(low)}, "rules")
        if re.search(r"подпись|подписи|caption|хэштег", low):
            plan_id = self._latest_plan_id()
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
        data = _extract_json(result.text)
        if not isinstance(data, dict):
            return None
        if data.get("clarify"):
            return RouteDecision("", {}, layer, 0.0, str(data["clarify"]))
        tool = str(data.get("tool") or "")
        if tool not in self.registry.tools:
            return None
        try:
            confidence = float(data.get("confidence", 0))
        except (TypeError, ValueError):
            confidence = 0.0
        args = data.get("args") if isinstance(data.get("args"), dict) else {}
        return RouteDecision(tool, args, layer, confidence)

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
        if decision and decision.tool:
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
        data = _extract_json(raw) or {}
        sections = data.get("sections") if isinstance(data, dict) else None
        if isinstance(sections, list) and sections:
            return [s for s in sections if isinstance(s, dict)]
        return []

    def write_caption(self, brief: str) -> str:
        system = ("Ты SMM-копирайтер. Дай подпись до 400 символов, 3–5 хэштегов и CTA. "
                  "Без markdown.")
        text = self._generate(system, brief, "caption")
        return text or f"{brief}\n\nПодпишитесь, чтобы не пропустить новые посты.\n#smm #контент"

    # --- small lookups ---
    def _latest_plan_id(self) -> str:
        items = self.dm_plan()
        return items[-1]["id"] if items else ""

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


def _extract_json(text: str) -> Optional[Any]:
    if not text:
        return None
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\n?|```$", "", cleaned).strip()
    try:
        return json.loads(cleaned)
    except ValueError:
        pass
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(cleaned[start:end + 1])
        except ValueError:
            return None
    return None


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
        self.registry = ToolRegistry()
        self._register_tools()
        self.router = AIRouter(self.registry, settings, self.budget, dm.project_id,
                               self.local, self.cloud,
                               system_context=self._context_text)
        self.router.plan_getter = dm.get_content_plan
        self.router.profile_getter = dm.get_brand_profile
        self.tools.router = self.router

        self.interview: Dict[str, Any] = {}
        self.pending: Optional[Tuple[str, Dict[str, Any]]] = None

    # --- setup ---
    def _register_tools(self) -> None:
        self.registry.register(ToolSpec("get_project_context", "прочитать профиль, стратегию, план, календарь",
                                        {"scope": str}, self.tools.context))
        self.registry.register(ToolSpec("search_knowledge", "поиск по материалам и документам",
                                        {"query": str, "limit": int}, self.tools.search_knowledge))
        self.registry.register(ToolSpec("create_strategy", "создать блоки стратегии",
                                        {"brief": str, "sections": list}, self.tools.create_strategy,
                                        needs_confirmation=lambda a: bool(
                                            (self.dm.get_strategy() or {}).get("sections"))))
        self.registry.register(ToolSpec("update_strategy_section", "править блок стратегии",
                                        {"section_id": str, "content": str},
                                        self.tools.update_strategy_section))
        self.registry.register(ToolSpec("create_content_plan", "создать позиции контент-плана",
                                        {"count": int, "rubrics": list, "start": str,
                                         "period_days": int}, self.tools.create_content_plan))
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
                                        {}, self.tools.validate_plan))
        self.registry.register(ToolSpec("analyze_performance",
                                        "сводка по метрикам: охват, вовлечённость, топ постов",
                                        {"period_days": int},
                                        self.tools.analyze_performance))
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
                                        {"media_ids": list, "platform": str},
                                        self.tools.process_video,
                                        needs_confirmation=lambda a: len(a.get("media_ids") or []) > 5))
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
