"""SQLite storage for a project: schema, JSON migration, load and save.

The GUI and DataManager keep working with the legacy dict shape; this module is the
only place that knows about tables. Dates are stored as ISO (YYYY-MM-DD) and exposed
to the app as DD.MM.YYYY, as agreed in work/DECISIONS.md.
"""
from __future__ import annotations

import json
import logging
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS project_meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS brand_profile (
    id            INTEGER PRIMARY KEY CHECK (id = 1),
    client_name   TEXT,
    niche         TEXT,
    city          TEXT,
    audience      TEXT,
    positioning   TEXT,
    tone_of_voice TEXT,
    languages     TEXT,
    stop_words    TEXT,
    banned_topics TEXT,
    visual_rules  TEXT,
    updated_at    TEXT
);

CREATE TABLE IF NOT EXISTS strategy_sections (
    id         TEXT PRIMARY KEY,
    title      TEXT,
    icon       TEXT,
    content    TEXT,
    position   INTEGER,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS strategy_kpis (
    id       TEXT PRIMARY KEY,
    metric   TEXT,
    current  TEXT,
    target   TEXT,
    deadline TEXT,
    position INTEGER
);

CREATE TABLE IF NOT EXISTS strategy_versions (
    id      TEXT PRIMARY KEY,
    version TEXT,
    date    TEXT,
    author  TEXT,
    note    TEXT
);

CREATE TABLE IF NOT EXISTS content_plan (
    id              TEXT PRIMARY KEY,
    date            TEXT,
    rubric          TEXT,
    topic           TEXT,
    format          TEXT,
    status          TEXT,
    responsible     TEXT,
    strategy_link   TEXT,
    shooting_task_id TEXT,
    caption         TEXT,
    source          TEXT
);

CREATE TABLE IF NOT EXISTS post_metrics (
    id          TEXT PRIMARY KEY,
    plan_id     TEXT,
    reach       INTEGER,
    likes       INTEGER,
    comments    INTEGER,
    saves       INTEGER,
    measured_at TEXT
);

CREATE TABLE IF NOT EXISTS calendar_events (
    id          TEXT PRIMARY KEY,
    date        TEXT,
    time        TEXT,
    type        TEXT,
    title       TEXT,
    description TEXT,
    link        TEXT,
    source      TEXT
);

CREATE TABLE IF NOT EXISTS shooting_tasks (
    id               TEXT PRIMARY KEY,
    date             TEXT,
    time             TEXT,
    location         TEXT,
    type             TEXT,
    content_plan_link TEXT,
    status           TEXT,
    team             TEXT,
    priority         TEXT,
    budget_amount    INTEGER,
    budget_currency  TEXT,
    duration         TEXT,
    tech_req         TEXT,
    notes            TEXT
);

CREATE TABLE IF NOT EXISTS shooting_shots (
    id          TEXT PRIMARY KEY,
    task_id     TEXT REFERENCES shooting_tasks(id) ON DELETE CASCADE,
    num         INTEGER,
    description TEXT,
    ref         TEXT,
    priority    TEXT,
    status      TEXT
);

CREATE TABLE IF NOT EXISTS media (
    id               TEXT PRIMARY KEY,
    zone             TEXT,
    name             TEXT,
    kind             TEXT,
    category         TEXT,
    width            INTEGER,
    height           INTEGER,
    bytes            INTEGER,
    path             TEXT,
    status           TEXT,
    shooting_task_id TEXT,
    created_at       TEXT
);

CREATE TABLE IF NOT EXISTS publication_folders (
    id          TEXT PRIMARY KEY,
    name        TEXT,
    icon        TEXT,
    description TEXT,
    color       TEXT,
    position    INTEGER
);

CREATE TABLE IF NOT EXISTS publication_items (
    id        TEXT PRIMARY KEY,
    folder_id TEXT REFERENCES publication_folders(id) ON DELETE CASCADE,
    media_id  TEXT,
    name      TEXT,
    date      TEXT,
    time      TEXT,
    position  INTEGER
);

CREATE TABLE IF NOT EXISTS schedule (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS other_files (
    id     TEXT PRIMARY KEY,
    folder TEXT,
    name   TEXT,
    kind   TEXT,
    size   TEXT,
    date   TEXT,
    tags   TEXT,
    path   TEXT
);

CREATE TABLE IF NOT EXISTS actions_log (
    id     TEXT PRIMARY KEY,
    ts     TEXT,
    actor  TEXT,
    tool   TEXT,
    args   TEXT,
    effect TEXT,
    undo   TEXT,
    status TEXT
);

CREATE TABLE IF NOT EXISTS ai_runs (
    id         TEXT PRIMARY KEY,
    ts         TEXT,
    purpose    TEXT,
    provider   TEXT,
    model      TEXT,
    tokens_in  INTEGER,
    tokens_out INTEGER,
    cost_usd   REAL,
    latency_ms INTEGER,
    ok         INTEGER,
    error      TEXT
);

CREATE INDEX IF NOT EXISTS idx_plan_date  ON content_plan(date);
CREATE INDEX IF NOT EXISTS idx_metrics_plan ON post_metrics(plan_id);
CREATE INDEX IF NOT EXISTS idx_event_date ON calendar_events(date);
CREATE INDEX IF NOT EXISTS idx_media_zone ON media(zone);
CREATE INDEX IF NOT EXISTS idx_items_folder ON publication_items(folder_id);
"""

# --- enums: display value <-> canonical code (work/DECISIONS.md, 5.4) ---

FORMAT_TO_CODE = {
    "Пост": "post", "Post": "post", "пост": "post",
    "Reels": "reels", "reels": "reels", "Рилс": "reels",
    "Stories": "stories", "stories": "stories", "Сторис": "stories",
    "Карусель": "carousel", "carousel": "carousel",
    "Видео": "video", "video": "video",
}
FORMAT_TO_LABEL = {
    "post": "Пост", "reels": "Reels", "stories": "Stories",
    "carousel": "Карусель", "video": "Видео",
}

PLAN_STATUS_TO_CODE = {
    "Черновик": "draft", "Draft": "draft", "draft": "draft",
    "Запланировано": "planned", "Planned": "planned", "planned": "planned",
    "В работе": "in_progress", "in_progress": "in_progress",
    "Одобрено": "approved", "approved": "approved",
    "Опубликовано": "published", "published": "published",
}
PLAN_STATUS_TO_LABEL = {
    "draft": "Черновик", "planned": "Запланировано", "in_progress": "В работе",
    "approved": "Одобрено", "published": "Опубликовано",
}

TASK_STATUS_TO_CODE = {
    "Черновик": "draft", "draft": "draft",
    "Согласовано": "planned", "Запланировано": "planned", "planned": "planned",
    "Снято": "shot", "shot": "shot",
    "Монтаж": "editing", "editing": "editing",
    "Готово": "done", "done": "done",
    "Отменено": "cancelled", "cancelled": "cancelled",
}
TASK_STATUS_TO_LABEL = {
    "draft": "Черновик", "planned": "Согласовано", "shot": "Снято",
    "editing": "Монтаж", "done": "Готово", "cancelled": "Отменено",
}

PRIORITY_TO_CODE = {
    "Низкий": "low", "low": "low",
    "Средний": "medium", "medium": "medium",
    "Высокий": "high", "high": "high",
}
PRIORITY_TO_LABEL = {"low": "Низкий", "medium": "Средний", "high": "Высокий"}

EVENT_TYPE_TO_CODE = {
    "publication": "publication", "shooting": "shooting",
    "meeting": "meeting", "brand_event": "brand_event",
    "Контент": "publication", "Публикация": "publication",
    "Съёмка": "shooting", "Встреча": "meeting", "Событие": "brand_event",
}


# --- helpers ---

def _iso(value: Any) -> Optional[str]:
    """DD.MM.YYYY -> YYYY-MM-DD. Already-ISO and empty values pass through."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return text


def _display(value: Any) -> Optional[str]:
    """YYYY-MM-DD -> DD.MM.YYYY. Anything else passes through."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d").strftime("%d.%m.%Y")
    except ValueError:
        return text


def _count(value: Any) -> Optional[int]:
    """Counter from a GUI cell: '', None -> None; '1 200' -> 1200."""
    if value is None:
        return None
    text = str(value).replace(" ", "").replace("\u00a0", "").strip()
    if not text:
        return None
    try:
        return int(round(float(text)))
    except ValueError:
        return None


def _size_to_wh(size: Any) -> Tuple[Optional[int], Optional[int]]:
    if not size:
        return None, None
    text = str(size).lower().replace("×", "x")
    if "x" not in text:
        return None, None
    left, right = text.split("x", 1)
    try:
        return int(left.strip()), int(right.strip())
    except ValueError:
        return None, None


def _wh_to_size(width: Optional[int], height: Optional[int]) -> str:
    if width and height:
        return f"{width}x{height}"
    return "unknown"


def _parse_budget(value: Any) -> Tuple[int, str]:
    if isinstance(value, (int, float)):
        return int(value), "KZT"
    text = str(value or "")
    digits = "".join(ch for ch in text if ch.isdigit())
    amount = int(digits) if digits else 0
    currency = "RUB" if ("₽" in text or "руб" in text.lower()) else "KZT"
    return amount, currency


def _format_budget(amount: Any, currency: Any) -> str:
    try:
        amount_int = int(amount or 0)
    except (TypeError, ValueError):
        amount_int = 0
    symbol = "₽" if currency == "RUB" else "₸"
    return f"{amount_int} {symbol}"


def _code(mapping: Dict[str, str], value: Any, fallback: str) -> str:
    if value is None:
        return fallback
    return mapping.get(str(value), fallback)


def _json_or_none(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def _loads(value: Any, default: Any = None) -> Any:
    if value in (None, ""):
        return default
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return default


class ProjectStore:
    """Owns project.db. One instance per DataManager."""

    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.data_dir / "project.db"
        self.conn = sqlite3.connect(str(self.path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.executescript(SCHEMA)
        self._ensure_columns()
        self.conn.commit()

    def _ensure_columns(self) -> None:
        """Add columns introduced after the first projects were created."""
        added = {"content_plan": {"caption": "TEXT"}, "other_files": {"path": "TEXT"}}
        for table, columns in added.items():
            have = {row["name"] for row in
                    self.conn.execute(f"PRAGMA table_info({table})")}
            for name, kind in columns.items():
                if name not in have:
                    self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {kind}")

    # --- lifecycle ---

    def is_empty(self) -> bool:
        for table in ("strategy_sections", "content_plan", "calendar_events",
                      "shooting_tasks", "media", "publication_folders"):
            if self.conn.execute(f"SELECT 1 FROM {table} LIMIT 1").fetchone():
                return False
        return True

    def migrate_if_needed(self, json_path: Path) -> bool:
        """Import legacy project_data.json once. Always keeps a timestamped copy."""
        if not self.is_empty() or not json_path.exists():
            return False
        backup_dir = self.data_dir / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = backup_dir / f"project_data_{stamp}.json"
        shutil.copy2(json_path, backup)
        with open(json_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        self.save(data)
        logger.info("Migrated %s -> %s (backup %s)", json_path, self.path, backup.name)
        return True

    # --- save ---

    def save(self, data: Dict[str, Any]) -> None:
        conn = self.conn
        strategy = data.get("strategy", {}) or {}
        publications = data.get("publications", {}) or {}
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with conn:  # one transaction: either the whole project is written or nothing
            for table in ("project_meta", "strategy_sections", "strategy_kpis",
                          "strategy_versions", "content_plan", "post_metrics",
                          "calendar_events",
                          "shooting_shots", "shooting_tasks", "media",
                          "publication_items", "publication_folders", "schedule",
                          "other_files"):
                conn.execute(f"DELETE FROM {table}")

            meta = {
                "project_name": strategy.get("project_name", ""),
                "strategy_version": strategy.get("version", ""),
                "strategy_updated": strategy.get("updated", ""),
                "saved_at": now,
            }
            conn.executemany("INSERT INTO project_meta(key, value) VALUES (?, ?)",
                             list(meta.items()))

            conn.executemany(
                "INSERT INTO strategy_sections(id, title, icon, content, position, updated_at)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                [(s.get("id"), s.get("title"), s.get("icon"), s.get("content"),
                  index, _iso(strategy.get("updated")))
                 for index, s in enumerate(strategy.get("sections", []))])

            conn.executemany(
                "INSERT INTO strategy_kpis(id, metric, current, target, deadline, position)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                [(k.get("id") or f"kpi_{index:02d}", k.get("metric"), k.get("current"),
                  k.get("target"), _iso(k.get("deadline")), index)
                 for index, k in enumerate(strategy.get("kpis", []))])

            conn.executemany(
                "INSERT INTO strategy_versions(id, version, date, author, note)"
                " VALUES (?, ?, ?, ?, ?)",
                [(v.get("id") or f"ver_{index:02d}", v.get("version"), _iso(v.get("date")),
                  v.get("author"), v.get("changes") or v.get("note"))
                 for index, v in enumerate(strategy.get("versions", []))])

            conn.executemany(
                "INSERT INTO content_plan(id, date, rubric, topic, format, status, responsible,"
                " strategy_link, shooting_task_id, caption, source)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [(i.get("id"), _iso(i.get("date")), i.get("rubric"), i.get("topic"),
                  _code(FORMAT_TO_CODE, i.get("format"), "post"),
                  _code(PLAN_STATUS_TO_CODE, i.get("status"), "draft"),
                  i.get("responsible"), i.get("strategy_link"), i.get("shooting_task_id"),
                  i.get("caption"), i.get("source"))
                 for i in data.get("content_plan", [])])

            conn.executemany(
                "INSERT INTO post_metrics(id, plan_id, reach, likes, comments, saves, measured_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                [(m.get("id"), m.get("plan_id"), _count(m.get("reach")),
                  _count(m.get("likes")), _count(m.get("comments")),
                  _count(m.get("saves")), _iso(m.get("measured_at")))
                 for m in data.get("post_metrics", [])])

            conn.executemany(
                "INSERT INTO calendar_events(id, date, time, type, title, description, link, source)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [(e.get("id"), _iso(e.get("date")), e.get("time") or "12:00",
                  _code(EVENT_TYPE_TO_CODE, e.get("type"), "publication"),
                  e.get("title") or "Событие", e.get("description"), e.get("link"),
                  e.get("source"))
                 for e in data.get("calendar_events", [])])

            tasks = data.get("shooting_tasks", [])
            conn.executemany(
                "INSERT INTO shooting_tasks(id, date, time, location, type, content_plan_link,"
                " status, team, priority, budget_amount, budget_currency, duration, tech_req, notes)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [(t.get("id"), _iso(t.get("date")), t.get("time") or "10:00", t.get("location"),
                  t.get("type") or "Фото", t.get("content_plan_link"),
                  _code(TASK_STATUS_TO_CODE, t.get("status"), "draft"),
                  t.get("team"), _code(PRIORITY_TO_CODE, t.get("priority"), "medium"),
                  *_parse_budget(t.get("budget")), t.get("duration"), t.get("tech_req"),
                  t.get("notes"))
                 for t in tasks])

            shots = []
            for task in tasks:
                for index, shot in enumerate(task.get("shots", []), start=1):
                    shots.append((
                        shot.get("id") or f"{task.get('id')}_shot_{index:02d}",
                        task.get("id"), shot.get("num", index), shot.get("desc"),
                        shot.get("ref"), _code(PRIORITY_TO_CODE, shot.get("priority"), "medium"),
                        _code(TASK_STATUS_TO_CODE, shot.get("status"), "planned"),
                    ))
            conn.executemany(
                "INSERT INTO shooting_shots(id, task_id, num, description, ref, priority, status)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)", shots)

            media_rows = []
            for zone in ("media_sources", "media_references", "media_ready"):
                zone_key = {"media_sources": "sources", "media_references": "references",
                            "media_ready": "ready"}[zone]
                for item in data.get(zone, []):
                    width, height = _size_to_wh(item.get("size"))
                    status = item.get("status") if zone_key == "ready" else None
                    media_rows.append((
                        item.get("id"), zone_key, item.get("name"), item.get("type", "image"),
                        item.get("category"), width, height, item.get("bytes"),
                        item.get("path"), status,
                        item.get("shooting_task") or item.get("shooting_task_id"),
                        _iso(item.get("date")),
                    ))
            conn.executemany(
                "INSERT INTO media(id, zone, name, kind, category, width, height, bytes, path,"
                " status, shooting_task_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                media_rows)

            folders = publications.get("folders", {}) or {}
            conn.executemany(
                "INSERT INTO publication_folders(id, name, icon, description, color, position)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                [(folder_id, folder.get("name"), folder.get("icon"),
                  folder.get("desc") or folder.get("description"), folder.get("color"), index)
                 for index, (folder_id, folder) in enumerate(folders.items())])

            item_rows = []
            for folder_id, folder in folders.items():
                for index, item in enumerate(folder.get("items", [])):
                    item_rows.append((
                        item.get("id") or f"pi_{folder_id}_{index:03d}", folder_id,
                        item.get("media_id"), item.get("name"), _iso(item.get("date")),
                        item.get("time") or "12:00", index,
                    ))
            conn.executemany(
                "INSERT INTO publication_items(id, folder_id, media_id, name, date, time, position)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)", item_rows)

            schedule = publications.get("schedule", {}) or {}
            conn.executemany(
                "INSERT INTO schedule(key, value) VALUES (?, ?)",
                [(key, _json_or_none(value)) for key, value in schedule.items()])

            other_rows = []
            for folder, files in (data.get("other_files", {}) or {}).items():
                for index, item in enumerate(files):
                    other_rows.append((
                        item.get("id") or f"of_{folder}_{index:03d}", folder, item.get("name"),
                        item.get("type"), item.get("size"), _iso(item.get("date")),
                        _json_or_none(item.get("tags") or []), item.get("path"),
                    ))
            conn.executemany(
                "INSERT INTO other_files(id, folder, name, kind, size, date, tags, path)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)", other_rows)

    # --- load ---

    def load(self) -> Dict[str, Any]:
        if self.is_empty():
            return {}
        conn = self.conn

        meta = {row["key"]: row["value"] for row in conn.execute("SELECT key, value FROM project_meta")}

        sections = [
            {"id": row["id"], "title": row["title"], "icon": row["icon"],
             "content": row["content"]}
            for row in conn.execute("SELECT * FROM strategy_sections ORDER BY position, id")
        ]
        kpis = [
            {"metric": row["metric"], "current": row["current"], "target": row["target"],
             "deadline": _display(row["deadline"])}
            for row in conn.execute("SELECT * FROM strategy_kpis ORDER BY position, id")
        ]
        versions = [
            {"version": row["version"], "date": _display(row["date"]), "author": row["author"],
             "changes": row["note"]}
            for row in conn.execute("SELECT * FROM strategy_versions ORDER BY date, id")
        ]

        strategy = {
            "project_name": meta.get("project_name", ""),
            "version": meta.get("strategy_version", ""),
            "updated": meta.get("strategy_updated", ""),
            "sections": sections,
            "kpis": kpis,
            "versions": versions,
        }

        content_plan = [
            {"id": row["id"], "date": _display(row["date"]), "rubric": row["rubric"],
             "topic": row["topic"],
             "format": FORMAT_TO_LABEL.get(row["format"], row["format"]),
             "status": PLAN_STATUS_TO_LABEL.get(row["status"], row["status"]),
             "responsible": row["responsible"], "strategy_link": row["strategy_link"],
             "shooting_task_id": row["shooting_task_id"], "caption": row["caption"] or ""}
            for row in conn.execute("SELECT * FROM content_plan ORDER BY date IS NULL, date, id")
        ]

        post_metrics = [
            {"id": row["id"], "plan_id": row["plan_id"] or "",
             "reach": row["reach"] or 0, "likes": row["likes"] or 0,
             "comments": row["comments"] or 0, "saves": row["saves"] or 0,
             "measured_at": _display(row["measured_at"])}
            for row in conn.execute("SELECT * FROM post_metrics ORDER BY measured_at, id")
        ]

        calendar_events = [
            {"id": row["id"], "date": _display(row["date"]), "time": row["time"],
             "type": row["type"], "title": row["title"], "description": row["description"],
             "link": row["link"]}
            for row in conn.execute("SELECT * FROM calendar_events ORDER BY date IS NULL, date, time, id")
        ]

        shots_by_task: Dict[str, List[Dict[str, Any]]] = {}
        for row in conn.execute("SELECT * FROM shooting_shots ORDER BY task_id, num"):
            shots_by_task.setdefault(row["task_id"], []).append({
                "num": row["num"], "desc": row["description"], "ref": row["ref"],
                "priority": PRIORITY_TO_LABEL.get(row["priority"], row["priority"]),
                "status": TASK_STATUS_TO_LABEL.get(row["status"], row["status"]),
            })

        shooting_tasks = [
            {"id": row["id"], "date": _display(row["date"]), "time": row["time"],
             "location": row["location"], "type": row["type"],
             "content_plan_link": row["content_plan_link"],
             "status": TASK_STATUS_TO_LABEL.get(row["status"], row["status"]),
             "team": row["team"],
             "priority": PRIORITY_TO_LABEL.get(row["priority"], row["priority"]),
             "budget": _format_budget(row["budget_amount"], row["budget_currency"]),
             "duration": row["duration"], "shots": shots_by_task.get(row["id"], []),
             "tech_req": row["tech_req"], "notes": row["notes"]}
            for row in conn.execute("SELECT * FROM shooting_tasks ORDER BY date IS NULL, date, time, id")
        ]

        media_sources, media_references, media_ready = [], [], []
        for row in conn.execute("SELECT * FROM media ORDER BY created_at, id"):
            base = {"id": row["id"], "name": row["name"], "type": row["kind"],
                    "size": _wh_to_size(row["width"], row["height"]),
                    "path": row["path"] or ""}
            if row["zone"] == "sources":
                base["date"] = _display(row["created_at"])
                base["shooting_task"] = row["shooting_task_id"]
                media_sources.append(base)
            elif row["zone"] == "references":
                base["category"] = row["category"]
                media_references.append(base)
            else:
                base["status"] = row["status"] or "pending"
                base["date"] = _display(row["created_at"])
                media_ready.append(base)

        folders: Dict[str, Any] = {}
        for row in conn.execute("SELECT * FROM publication_folders ORDER BY position, id"):
            folders[row["id"]] = {"name": row["name"], "icon": row["icon"],
                                  "desc": row["description"], "color": row["color"],
                                  "items": []}
        for row in conn.execute("SELECT * FROM publication_items ORDER BY folder_id, position, id"):
            if row["folder_id"] in folders:
                folders[row["folder_id"]]["items"].append({
                    "name": row["name"], "time": row["time"], "date": _display(row["date"]),
                })

        schedule = {}
        for row in conn.execute("SELECT key, value FROM schedule"):
            loaded = _loads(row["value"], row["value"])
            schedule[row["key"]] = loaded

        other_files: Dict[str, List[Dict[str, Any]]] = {}
        for row in conn.execute("SELECT * FROM other_files ORDER BY folder, date, id"):
            other_files.setdefault(row["folder"], []).append({
                "id": row["id"], "name": row["name"], "type": row["kind"],
                "size": row["size"], "date": _display(row["date"]),
                "tags": _loads(row["tags"], []), "path": row["path"] or "",
            })

        return {
            "strategy": strategy,
            "content_plan": content_plan,
            "post_metrics": post_metrics,
            "calendar_events": calendar_events,
            "shooting_tasks": shooting_tasks,
            "media_sources": media_sources,
            "media_references": media_references,
            "media_ready": media_ready,
            "publications": {"folders": folders, "schedule": schedule},
            "other_files": other_files,
        }

    # --- brand profile: одна строка, живёт отдельно от save() ---

    BRAND_FIELDS = ("client_name", "niche", "city", "audience", "positioning",
                    "tone_of_voice", "languages", "stop_words", "banned_topics", "visual_rules")

    def load_brand_profile(self) -> Dict[str, Any]:
        row = self.conn.execute("SELECT * FROM brand_profile WHERE id = 1").fetchone()
        if not row:
            return {}
        return {key: row[key] for key in row.keys() if key != "id"}

    def save_brand_profile(self, profile: Dict[str, Any]) -> None:
        fields = self.BRAND_FIELDS
        values = [profile.get(field, "") or "" for field in fields]
        placeholders = ", ".join("?" for _ in range(len(fields) + 1))
        with self.conn:
            self.conn.execute(
                f"INSERT OR REPLACE INTO brand_profile (id, {', '.join(fields)}, updated_at)"
                f" VALUES (1, {placeholders})",
                (*values, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    def close(self) -> None:
        self.conn.close()
