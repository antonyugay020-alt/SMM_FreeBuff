"""Живой прогон агента на настоящей Ollama (qwen3:8b).

    python work/tests/run_tests.py --live

Проверяет, что свободная задача выполняется шагами на живой модели, а не только
на заглушках. Пишет во временный проект, ничего не публикует и не трогает
config/settings.json.
"""
import atexit
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

APP = Path(__file__).resolve().parents[2] / "AI_SMM_Work_Architecture_A75"
sys.path.insert(0, str(APP))

from ai_core import AGENT_STEPS, AICore, OllamaProvider
from data_manager import DataManager
from gui_settings import Settings

fails = []


def check(name, cond, extra=""):
    print(("OK   " if cond else "FAIL ") + name + ("" if cond else f" :: {extra}"))
    if not cond:
        fails.append(name)


TMP = Path(tempfile.mkdtemp(prefix="live_agent_"))
atexit.register(lambda: shutil.rmtree(TMP, ignore_errors=True))

settings = Settings()
MODEL = os.environ.get("LIVE_AGENT_MODEL") or str(settings.get("local_model") or "qwen3:8b")
HOST = os.environ.get("LIVE_AGENT_HOST") or "http://localhost:11434"
print(f"модель: {MODEL} ({HOST})")

dm = DataManager("live_agent", str(TMP / "proj"))
dm.save_brand_profile({
    "client_name": "Кофейня у дома", "niche": "кофейня и обжарка",
    "city": "Алматы", "audience": "жители района 25–40 лет",
    "positioning": "своя обжарка и свежая выпечка",
    "tone_of_voice": "дружелюбный, без пафоса", "languages": "RU",
    "stop_words": "нет",
})

core = AICore(dm, settings, app_db_path=TMP / "app.db",
              local_provider=OllamaProvider(host=HOST, model=MODEL, timeout=300))
state = core.ensure_local_model()
print(f"модель: {state.get('model')} — {state.get('message')}")
if state.get("state") != "ready":
    print("\nЖивой прогон не начат: локальная модель не готова.")
    print("  1) ollama serve")
    print("  2) ollama pull qwen3:8b")
    print("  3) python work/tests/run_tests.py --live")
    raise SystemExit(2)

print(f"шагов на задачу: до {AGENT_STEPS}\n")


def run_task(text):
    """Одна задача: время, инструменты из журнала, ответ."""
    before = {entry["id"] for entry in core.journal.list(300)}
    started = time.monotonic()
    reply = core.handle(text)
    took = time.monotonic() - started
    tools = [entry["tool"] for entry in core.journal.list(300)
             if entry["id"] not in before]
    tools.reverse()
    print(f"  шаги: {', '.join(tools) or 'нет'}")
    print(f"  ответ ({took:.0f} с): {(reply.text or '').splitlines()[0][:160]}")
    return reply, took, tools


# --- 1. свободная задача: стратегия → план → подписи ---
strategy_before = len(dm.get_strategy().get("sections") or [])
print('1. «подготовь кофейне контент на неделю»')
reply1, took1, tools1 = run_task("подготовь кофейне контент на неделю")
plan = dm.get_content_plan()
sections = len(dm.get_strategy().get("sections") or [])
plan_count = len(plan)
captions = sum(1 for item in plan if str(item.get("caption") or "").strip())
tasks = sum(1 for item in plan if item.get("shooting_task_id"))
check("живая модель отработала задачу", reply1.text.strip() != "" and took1 > 0)
check("сделано больше одного шага", len(tools1) >= 2, tools1)
check("стратегия или план созданы", sections > strategy_before or bool(plan),
      (sections, len(plan)))
check("план непустой", bool(plan), len(plan))
if plan:
    check("есть подписи у постов", captions > 0, f"{captions} из {len(plan)}")
    check("есть ТЗ у постов", tasks > 0, f"{tasks} из {len(plan)}")

# --- 2. проверка плана правилом, без модели ---
print('\n2. «проверь план»')
reply2, took2, tools2 = run_task("проверь план")
check("проверка плана ответила", "роверка" in reply2.text, reply2.text[:160])

# --- 3. ещё одна свободная формулировка ---
print('\n3. «нужно 5 постов для инстаграма»')
reply3, took3, tools3 = run_task("нужно 5 постов для инстаграма")
check("постов стало больше", len(dm.get_content_plan()) > plan_count,
      f"{plan_count} → {len(dm.get_content_plan())}")

# --- 4. вопрос по состоянию: не должно быть падения ---
print('\n4. «что сейчас в плане?»')
reply4, took4, tools4 = run_task("что сейчас в плане?")
check("ответ на вопрос не пустой", bool(reply4.text.strip()), reply4.text[:160])

print(f"\nживых тестов: {4 + 5}, провалов: {len(fails)}")
if fails:
    print("провалились: " + ", ".join(fails))
raise SystemExit(1 if fails else 0)
