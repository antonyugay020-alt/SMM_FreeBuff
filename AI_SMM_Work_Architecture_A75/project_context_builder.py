"""Builds a compact project context string for the LLM system prompt."""
import logging

logger = logging.getLogger(__name__)

MAX_CHARS = 2500


def _clip(text, limit):
    text = (text or "").strip()
    if len(text) > limit:
        text = text[:limit].rstrip() + "..."
    return text


def build_context(dm, max_chars=MAX_CHARS):
    """Collect key project facts from DataManager into a short text block.

    Uses duck-typing and defensive access so it never crashes the chat
    even if DataManager structure changes.
    """
    parts = []

    data = getattr(dm, "_data", None) or getattr(dm, "data", None) or {}
    if not isinstance(data, dict):
        data = {}

    project_name = (
        getattr(dm, "project_name", None)
        or getattr(dm, "project_id", None)
        or data.get("project_name")
        or "без названия"
    )
    parts.append(f"Проект: {project_name}")

    # --- Strategy blocks ---
    strat = {}
    try:
        if hasattr(dm, "get_strategy"):
            strat = dm.get_strategy() or {}
        elif isinstance(data.get("strategy"), dict):
            strat = data["strategy"]
    except Exception:
        strat = {}
    if not isinstance(strat, dict):
        strat = {}

    label_map = [
        ("about", "О проекте"),
        ("audience", "Целевая аудитория"),
        ("positioning", "Позиционирование"),
        ("usp", "УТП"),
        ("tone_of_voice", "Tone of Voice"),
    ]
    for key, label in label_map:
        val = strat.get(key)
        if isinstance(val, str) and val.strip():
            parts.append(f"{label}: {_clip(val, 300)}")
        elif isinstance(val, dict):
            inner = val.get("text") or val.get("content") or ""
            if isinstance(inner, str) and inner.strip():
                parts.append(f"{label}: {_clip(inner, 300)}")

    # DataManager stores the strategy as a list of document sections
    sections = strat.get("sections")
    if isinstance(sections, list):
        for section in sections:
            if not isinstance(section, dict):
                continue
            label = section.get("title") or section.get("id") or "Блок"
            content = section.get("content") or ""
            if isinstance(content, str) and content.strip():
                parts.append(f"{label}: {_clip(content, 300)}")

    # --- Recent content plan items ---
    plan = []
    try:
        if hasattr(dm, "get_content_plan"):
            plan = dm.get_content_plan() or []
        elif isinstance(data.get("content_plan"), list):
            plan = data["content_plan"]
    except Exception:
        plan = []
    if isinstance(plan, list) and plan:
        lines = []
        for item in plan[-5:]:
            if isinstance(item, dict):
                topic = item.get("topic") or item.get("title") or ""
                date = item.get("date") or ""
                line = f"- {date} {topic}".strip()
                if line != "-":
                    lines.append(line)
        if lines:
            parts.append("Последние пункты контент-плана:\n" + "\n".join(lines))

    # --- Media stats ---
    media = data.get("media") or data.get("media_sources") or []
    if isinstance(media, list) and media:
        parts.append(f"Медиа-файлов в проекте: {len(media)}")

    ctx = "\n".join(parts)
    if len(ctx) > max_chars:
        ctx = ctx[:max_chars].rstrip() + "\n...(контекст обрезан)"
    return ctx
