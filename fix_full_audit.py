#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Step: Inject live project context into LLM system prompt.
Creates project_context_builder.py + safe patch of gui_ai_panel.py.
SAFE: panel file is rewritten ONLY if new content compiles.
Run: python fix_project_context.py
"""

from pathlib import Path
import re

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

def write(rel, content):
    p = BASE / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding='utf-8', newline='\n')
    print(f"  [OK] {rel}")

print("\n=== Step: Project Context Injection ===\n")

# ---------------------------------------------------------------
# 1. Create project_context_builder.py
# ---------------------------------------------------------------
print("[1/3] Creating project_context_builder.py...")

builder_code = r'''"""Builds a compact project context string for the LLM system prompt."""
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
    media = data.get("media") or data.get("media_content") or []
    if isinstance(media, list) and media:
        parts.append(f"Медиа-файлов в проекте: {len(media)}")

    ctx = "\n".join(parts)
    if len(ctx) > max_chars:
        ctx = ctx[:max_chars].rstrip() + "\n...(контекст обрезан)"
    return ctx
'''

write("project_context_builder.py", builder_code)

# ---------------------------------------------------------------
# 2. Safe patch of gui_ai_panel.py
# ---------------------------------------------------------------
print("[2/3] Patching gui_ai_panel.py (with compile-gate)...")

panel_path = BASE / "gui_ai_panel.py"
original = panel_path.read_text(encoding='utf-8')
content = original

# --- Patch A: replace hardcoded sys_prompt with context-aware call ---
old_sys = '''            sys_prompt = ("Ты опытный SMM менеджер и стратег. Помогай пользователю создавать кампании, "
                          "стратегии и контент-планы на русском языке. Будь лаконичен, но информативен.")'''
new_sys = '''            sys_prompt = self._build_system_prompt()'''

if old_sys in content:
    content = content.replace(old_sys, new_sys, 1)
    print("  [OK] sys_prompt now built from project context (exact match)")
else:
    # Fallback: regex over the parenthesised assignment
    pattern = re.compile(r'sys_prompt = \("Ты опытный SMM менеджер[^)]*\)', re.S)
    content, n = pattern.subn(new_sys.strip(), content, count=1)
    if n:
        print("  [OK] sys_prompt replaced via regex fallback")
    else:
        print("  [!] sys_prompt block not found - patch A skipped")

# --- Patch B: insert _build_system_prompt method before _simulate_response ---
method_code = '''    def _build_system_prompt(self):
        """Base system prompt enriched with live project context."""
        base = ("Ты опытный SMM менеджер и стратег. Помогай пользователю создавать кампании, "
                "стратегии и контент-планы на русском языке. Будь лаконичен, но информативен.")
        try:
            from project_context_builder import build_context
            win = self.window()
            dm = getattr(win, "data_manager", None)
            if dm is None and isinstance(self.state, dict):
                dm = self.state.get("data_manager")
            if dm is not None:
                ctx = build_context(dm)
                if ctx:
                    logger.info(f"Injected project context: {len(ctx)} chars")
                    return base + "\\n\\nКОНТЕКСТ ПРОЕКТА (учитывай его в ответах):\\n" + ctx
        except Exception as e:
            logger.warning(f"Context build failed: {e}")
        return base

'''

marker = "    def _simulate_response(self, user_input: str):"
if "def _build_system_prompt" in content:
    print("  [=] _build_system_prompt already exists - patch B skipped")
elif marker in content:
    content = content.replace(marker, method_code + marker, 1)
    print("  [OK] _build_system_prompt method inserted")
else:
    print("  [!] Insertion marker not found - patch B skipped")

# --- COMPILE GATE: write only if valid ---
try:
    compile(content, str(panel_path), 'exec')
    if content != original:
        panel_path.write_text(content, encoding='utf-8', newline='\n')
        print("  [OK] gui_ai_panel.py updated (compile-gate passed)")
    else:
        print("  [=] No changes needed for gui_ai_panel.py")
except SyntaxError as e:
    print(f"  [ROLLBACK] New content has syntax error at line {e.lineno}: {e.msg}")
    print("  [ROLLBACK] File NOT modified. Original kept intact.")

# ---------------------------------------------------------------
# 3. Self-test of context builder with a fake DataManager
# ---------------------------------------------------------------
print("[3/3] Self-testing project_context_builder...")

import sys
sys.path.insert(0, str(BASE))

try:
    from project_context_builder import build_context

    class FakeDM:
        def __init__(self):
            self._data = {
                "project_name": "TestProject",
                "strategy": {
                    "about": "Тестовый проект про кофе",
                    "audience": "молодые мамы 25-35 лет",
                },
                "content_plan": [
                    {"date": "2026-11-14", "topic": "Пост про латте"},
                    {"date": "2026-11-15", "topic": "Сторис с рецептом"},
                ],
                "media": [1, 2, 3],
            }

        def get_strategy(self):
            return self._data["strategy"]

        def get_content_plan(self):
            return self._data["content_plan"]

    ctx = build_context(FakeDM())
    assert "Проект: TestProject" in ctx, "project name missing"
    assert "Целевая аудитория" in ctx, "audience missing"
    assert "Пост про латте" in ctx, "content plan missing"
    assert "Медиа-файлов в проекте: 3" in ctx, "media stats missing"
    print("  [PASS] Context builder returns correct structure:")
    print("  ---")
    for line in ctx.split("\n"):
        print(f"  | {line}")
    print("  ---")
except Exception as e:
    print(f"  [FAIL] Self-test error: {e}")

print("\n=== Done ===")
print("Run START.bat, then ask AI anything about content.")
print("In terminal you should see: 'Injected project context: N chars'")