"""Приёмка из плана на подставных данных: новый клиент → 10 постов в календаре → ТЗ → перезапуск.

Живой публикации и сети нет. Локальная модель — StubProvider с детерминированными ответами.
Каждый шаг печатает OK/BREAK и не прерывает прогон: цель — показать, где цепочка рвётся.
"""
import sys, tempfile
from pathlib import Path
APP = Path(__file__).resolve().parents[2] / "AI_SMM_Work_Architecture_A75"
PROJECT = APP.parent
WORK = Path(tempfile.mkdtemp(prefix="smm_test_"))
import sys, time, tempfile, json
from pathlib import Path

ROOT = APP
sys.path.insert(0, str(APP))
from data_manager import DataManager
from ai_core import AICore, StubProvider

breaks, notes = [], []
t0 = time.time()

STRATEGY_JSON = json.dumps({"sections": [
    {"id": "about", "title": "О проекте", "content": "Кофейня у дома, 2 точки."},
    {"id": "audience", "title": "Аудитория", "content": "Жители района 25–40 лет."},
    {"id": "positioning", "title": "Позиционирование", "content": "Свежая обжарка рядом."},
    {"id": "usp", "title": "УТП", "content": "Своя обжарка и доставка за 20 минут."},
    {"id": "tone", "title": "Тон", "content": "Тёплый, без снобизма."},
]}, ensure_ascii=False)


def step(name, fn):
    try:
        value = fn()
        print(f"OK   {name}")
        return value
    except Exception as exc:
        print(f"BREAK {name}: {type(exc).__name__}: {exc}")
        breaks.append(f"{name}: {exc}")
        return None


tmp = Path(tempfile.mkdtemp(prefix="accept_"))
project_dir = tmp / "client_coffee"

# --- 1. Новый клиент с нуля ---
dm = step("1. создать проект клиента", lambda: DataManager("client_coffee", str(project_dir)))
profile = {"client_name": "Кофейня «Пар»", "niche": "кофейня", "languages": "ru",
           "tone": "тёплый", "audience": "жители района 25–40", "city": "Алматы"}
step("2. сохранить бренд-профиль", lambda: dm.save_brand_profile(profile))

local = StubProvider([STRATEGY_JSON])
core = AICore(dm, {"monthly_budget_usd": 0}, providers=(local, None))

# --- 2. Стратегия обычной фразой ---
reply = step("3. фраза «сделай стратегию»", lambda: core.handle("сделай стратегию для кофейни"))
if reply is not None:
    print(f"     ответ: {reply.text.splitlines()[0][:110]}")
sections = dm.get_strategy().get("sections") or []
print(f"     блоков стратегии: {len(sections)}")
if len(sections) != 5:
    breaks.append(f"стратегия: ожидалось 5 блоков, получено {len(sections)}")
prompt = next((user for system, user in local.calls if '"sections"' in system), "")
if "Кофейня" not in prompt:
    breaks.append("стратегия: бренд-профиль не попал в запрос к модели")

step("4. KPI стратегии", lambda: core.tools.update_kpis(
    [{"metric": "Подписчики", "current": "0", "target": "1000", "deadline": "31.01.2027"}]))

# --- 3. Контент-план на 10 постов обычной фразой ---
reply = step("5. фраза «создай контент-план на 10 постов»", lambda: core.handle("создай контент-план на 10 постов"))
if reply is not None:
    print(f"     ответ: {reply.text.splitlines()[0][:110]}")
plan = dm.get_content_plan()
print(f"     позиций в плане: {len(plan)}")
if len(plan) != 10:
    breaks.append(f"план: ожидалось 10 позиций, получено {len(plan)}")

# --- 4. Календарь ---
events_before = len(dm.get_calendar_events())
step("6. календарь из плана (кнопка «В календарь»)", lambda: core.tools.sync_plan_events())
events = dm.get_calendar_events()
new_events = [e for e in events if str(e.get("link") or "") in {i.get("id") for i in plan}]
print(f"     событий по плану: {len(new_events)} (было {events_before})")
if len(new_events) < len(plan):
    breaks.append(f"календарь: событий по плану {len(new_events)} из {len(plan)}")
planned = [i for i in plan if i.get("status") == "Запланировано"]
print(f"     позиций в статусе «Запланировано»: {len(planned)}")

# --- 5. Подписи (в GUI — по одной, для приёмки все 10) ---
caption_ok = 0
for item in plan:
    outcome = core.tools.write_captions(item["id"])
    if (dm.get_content_plan_item(item["id"]) or {}).get("caption"):
        caption_ok += 1
print(f"OK  7. подписи: {caption_ok} из {len(plan)}")
if caption_ok < len(plan):
    breaks.append(f"подписи: {caption_ok} из {len(plan)}")

# --- 6. ТЗ обычной фразой, по одному (как в чате) ---
for index in range(len(plan)):
    reply = core.handle("создай ТЗ")
    if reply and "Не хватает" in reply.text:
        breaks.append(f"ТЗ #{index + 1}: {reply.text}")
        break
tasks = dm.get_shooting_tasks()
linked = {str(t.get("content_plan_link") or "") for t in tasks}
covered = [i for i in plan if str(i.get("shooting_task_id") or "") or str(i.get("id")) in linked]
print(f"OK  8. ТЗ: {len(tasks)} задач, покрывают {len(covered)} из {len(plan)} позиций")
if len(covered) < len(plan):
    breaks.append(f"ТЗ: покрыто {len(covered)} из {len(plan)}")

# --- 7. Проверка плана ---
reply = step("9. проверка плана", lambda: core.tools.validate_plan())
if reply is not None:
    print(f"     {reply.get('summary', '')[:160]}")
    if reply.get("effect", {}).get("issues"):
        breaks.append(f"проверка плана: {reply['effect']['issues']} замечаний")

# --- 8. Перезапуск: читаем те же данные заново ---
dm2 = step("10. перезагрузить проект с диска", lambda: DataManager("client_coffee", str(project_dir)))
if dm2 is not None:
    plan2, tasks2, strat2 = dm2.get_content_plan(), dm2.get_shooting_tasks(), dm2.get_strategy()
    events2 = dm2.get_calendar_events()
    prof2 = dm2.get_brand_profile()
    print(f"     после перезапуска: план {len(plan2)}, ТЗ {len(tasks2)}, "
          f"события {len(events2)}, блоки {len(strat2.get('sections') or [])}, "
          f"KPI {len(strat2.get('kpis') or [])}, профиль {bool(prof2.get('client_name'))}")
    if len(plan2) != 10:
        breaks.append(f"после перезапуска: план {len(plan2)} вместо 10")
    if len(tasks2) != len(tasks):
        breaks.append(f"после перезапуска: ТЗ {len(tasks2)} вместо {len(tasks)}")
    if not prof2.get("client_name"):
        breaks.append("после перезапуска: бренд-профиль не сохранился")
    if len(events2) < len(new_events):
        breaks.append("после перезапуска: события календаря потерялись")
    captions2 = [i for i in plan2 if i.get("caption")]
    if len(captions2) != 10:
        breaks.append(f"после перезапуска: подписи {len(captions2)} из 10")
    ready = [i for i in plan2 if i.get("date") and i.get("caption")
             and (i.get("shooting_task_id") or str(i.get("id")) in
                  {str(t.get("content_plan_link") or "") for t in tasks2})]
    print(f"     готовых постов (дата+подпись+ТЗ): {len(ready)} из 10")

# --- 9. Журнал ---
journal = core.journal.list(limit=50)
print(f"OK  11. записей в журнале: {len(journal)}")

print(f"\nВремя прогона: {time.time() - t0:.1f} с")
print("РАЗРЫВЫ:" if breaks else "РАЗРЫВОВ НЕТ")
for line in breaks:
    print(" -", line)
sys.exit(1 if breaks else 0)
