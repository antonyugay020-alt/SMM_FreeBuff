import sys, tempfile
from pathlib import Path
APP = Path(__file__).resolve().parents[2] / "AI_SMM_Work_Architecture_A75"
PROJECT = APP.parent
WORK = Path(tempfile.mkdtemp(prefix="smm_test_"))
import sys, tempfile, json
from pathlib import Path
ROOT = APP
sys.path.insert(0, str(APP))
from data_manager import DataManager
from ai_core import AICore, StubProvider

fails = []
tmp = Path(tempfile.mkdtemp(prefix="fix_"))
dm = DataManager("p", str(tmp / "p"))
core = AICore(dm, {"monthly_budget_usd": 0}, providers=(StubProvider([json.dumps({"sections":[{"id":"a","title":"О","content":"x"}]})]), None))
core.handle("создай контент-план на 3 поста")
plan = dm.get_content_plan()

# 1. маршрутизация фраз
for phrase, tool in (("добавь план в календарь", "sync_plan_events"),
                     ("перенеси план в календарь", "sync_plan_events"),
                     ("проверь план перед публикацией", "validate_plan"),
                     ("проверка плана", "validate_plan"),
                     ("создай стратегию", "create_strategy"),
                     ("создай контент-план на 10 постов", "create_content_plan"),
                     ("создай ТЗ", "create_shooting_task"),
                     ("проверь доступ к инстаграму", "instagram_status"),
                     ("собери пакет под инстаграм", "instagram_pack")):
    d = core.router.route(phrase)
    print(f"1 {phrase!r} -> {d.tool}")
    if d.tool != tool:
        fails.append(f"фраза {phrase!r}: {d.tool or d.clarify!r} вместо {tool}")

# 2. подпись конкретной позиции: смотрим, у какой позиции появилась подпись
for phrase, expect in (("напиши подпись для 2 поста", plan[1]["id"]),
                       ("подпись к 1 посту", plan[0]["id"]),
                       ("подпись на " + plan[2]["date"], plan[2]["id"]),
                       ("напиши подпись", plan[-1]["id"]),
                       ("подпись для 3 позиции", plan[2]["id"])):
    d = core.router.route(phrase)
    arg = (d.args or {}).get("plan_id")
    core.handle(phrase)
    got = (dm.get_content_plan_item(expect) or {}).get("caption", "")
    print(f"2 {phrase!r} -> {arg}, подпись у цели: {bool(got)}")
    if arg != expect:
        fails.append(f"подпись {phrase!r}: адрес {arg} вместо {expect}")
    if not got:
        fails.append(f"подпись {phrase!r}: у цели нет подписи")

r = core.handle("подпись для 99 поста")
print("2 вне диапазона ->", r.text[:80])
if "номера 99 нет" not in r.text:
    fails.append("подпись вне диапазона: нет понятного отказа")

# 3. продолжение дат
before = [i["date"] for i in dm.get_content_plan()]
core.handle("создай контент-план на 2 поста")
after = [i["date"] for i in dm.get_content_plan()]
print("3 dates:", before, "->", after, "dupes:", len(after) - len(set(after)))
if len(after) - len(set(after)):
    fails.append(f"даты дублируются: {after}")
if after[len(before):] and min(after[len(before):]) <= max(before):
    fails.append("новый план начался не после последней даты")

# 4. слияние профиля
dm2 = DataManager("p2", str(tmp / "p2"))
dm2.save_brand_profile({"client_name": "Пар", "niche": "кофейня", "banned_topics": "политика",
                        "visual_rules": "тёплый свет", "languages": "ru"})
core2 = AICore(dm2, {"monthly_budget_usd": 0}, providers=(StubProvider([]), None))
core2.handle("заполни бренд-профиль")
for answer in ("Пар", "кофейня", "Алматы", "жители района", "обжарка", "тёплый", "ru", "нет"):
    core2.handle(answer)
prof = dm2.get_brand_profile()
print("4 banned:", repr(prof.get("banned_topics")), "visual:", repr(prof.get("visual_rules")), "city:", repr(prof.get("city")))
if prof.get("banned_topics") != "политика" or prof.get("visual_rules") != "тёплый свет":
    fails.append("профиль: поля из формы стёрлись")
if prof.get("city") != "Алматы":
    fails.append("профиль: ответ интервью не записался")
dm2.save_brand_profile({f: "" for f in ("client_name","niche","city","audience","positioning",
                                        "tone_of_voice","languages","stop_words","banned_topics","visual_rules")})
if dm2.get_brand_profile().get("city") != "":
    fails.append("профиль: очистка поля через форму не работает")

print("\nFAILS:", fails or "нет")
sys.exit(1 if fails else 0)
