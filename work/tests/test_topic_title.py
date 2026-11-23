import sys, tempfile
from pathlib import Path
APP = Path(__file__).resolve().parents[2] / "AI_SMM_Work_Architecture_A75"
PROJECT = APP.parent
WORK = Path(tempfile.mkdtemp(prefix="smm_test_"))
import sys, tempfile, json
from pathlib import Path
ROOT = APP
sys.path.insert(0, str(APP))
from ai_core import (AICore, StubProvider, TOPIC_LIMIT, _short_topic, _clean_section)
from data_manager import DataManager

fails = []
def build(replies):
    tmp = Path(tempfile.mkdtemp(prefix="tt2_"))
    dm = DataManager("p", str(tmp / "p"))
    dm.save_brand_profile({"client_name": "Пар", "niche": "кофейня", "tone_of_voice": "тёплый"})
    stub = StubProvider(list(replies))
    return dm, AICore(dm, {"monthly_budget_usd": 0}, providers=(stub, None)), stub

LONG_TOPIC = "Попробуйте свежеобжаренный кофе, который сохраняет аромат и вкус, как только вы его открываете."
TOPICS = {"topics": [
    {"topic": LONG_TOPIC, "rubric": "Польза", "format": "Пост"},
    {"topic": "Свежая обжарка каждое утро.", "rubric": "Закулисье", "format": "Reels"},
    {"topic": "что взять, если не пьёте кофе", "rubric": "Польза", "format": "Карусель"},
]}
STRATEGY = {"sections": [
    {"id": "about", "title": "О проекте", "content": "О проекте: Кофейня «Пар» — две точки в Алматы."},
    {"id": "positioning", "title": "Позиционирование", "content": "Позиционирование: Позиционирование: «Пар» — свежая обжарка рядом с домом."},
    {"id": "usp", "title": "Уникальные преимущества", "content": "Уникальные преимущества: Уникальные преимущества: обжарка на месте."},
    {"id": "tone", "title": "Тон", "content": "Тональность: тёплый, без снобизма."},
    {"id": "audience", "title": "Аудитория", "content": "Жители района 25–40 лет."},
]}

# 1. темы: длина, без точки, с заглавной
dm, core, stub = build([json.dumps(TOPICS, ensure_ascii=False)])
core.handle("создай контент-план на 3 поста")
plan = dm.get_content_plan()
topics = [i["topic"] for i in plan]
print("1 темы:", topics)
for t in topics:
    if len(t) > TOPIC_LIMIT: fails.append(f"тема длиннее {TOPIC_LIMIT}: {t!r} ({len(t)})")
    if t.endswith((".", "!", "…")): fails.append(f"тема с точкой в конце: {t!r}")
    if t[0].islower(): fails.append(f"тема со строчной: {t!r}")
if "Попробуйте" in topics[0] or topics[0].split()[-1].lower() == "и": fails.append("императив/висячий союз остались в теме")

# 2. в промпте тем есть требования
sysprompt = next((system for system, _ in stub.calls if '"topics"' in system), "")
print("2 промпт тем ok:", "до 60" in sysprompt, "без императива" in sysprompt, "без точки" in sysprompt)
for needle in ("до 60", "без императива", "без точки"):
    if needle not in sysprompt: fails.append(f"в промпте тем нет «{needle}»")

# 3. дубль заголовка в блоках стратегии
dm_s, core_s, stub_s = build([json.dumps(STRATEGY, ensure_ascii=False)])
sections = core_s.router.generate_strategy_sections("кофейня")
print("3 блоки:", [(s["id"], s["content"]) for s in sections])
by_id = {s["id"]: s["content"] for s in sections}
if by_id["about"] != "Кофейня «Пар» — две точки в Алматы.": fails.append(f"about: {by_id['about']!r}")
if by_id["positioning"] != "«Пар» — свежая обжарка рядом с домом.": fails.append(f"positioning: {by_id['positioning']!r}")
if by_id["usp"] != "Обжарка на месте.": fails.append(f"usp: {by_id['usp']!r}")
if by_id["tone"] != "Тёплый, без снобизма.": fails.append(f"tone: {by_id['tone']!r}")
if by_id["audience"] != "Жители района 25–40 лет.": fails.append(f"audience затёрт: {by_id['audience']!r}")
for s in sections:
    if "Позиционирование: " in s["content"] or "Уникальные преимущества: " in s["content"]:
        fails.append(f"дубль заголовка остался: {s['content']!r}")

# 4. промпт стратегии просит не повторять заголовок
sysprompt_strat = stub_s.calls[0][0]
if "не повторяй название блока" not in sysprompt_strat: fails.append("в промпте стратегии нет запрета дубля")

# 5. прямой _short_topic / _clean_section
print("5:", repr(_short_topic("  Попробуйте   наш кофе!!!  ")), "|", repr(_short_topic("слово" * 30)))
if _short_topic("  Попробуйте   наш кофе!!!  ") != "Наш кофе": fails.append("_short_topic: императив/пунктуация")
if len(_short_topic("слово" * 30)) > TOPIC_LIMIT: fails.append("_short_topic не обрезал длинное слово")
COMMA_TOPIC = "Кофе с собой, если не хочется сидеть в зале"
print("5 comma:", repr(_short_topic(COMMA_TOPIC)))
if _short_topic(COMMA_TOPIC) != COMMA_TOPIC:
    fails.append(f"_short_topic потерял часть темы после запятой: {_short_topic(COMMA_TOPIC)!r}")
if _short_topic("Кофе с собой" + ", очень" * 20) == "Кофе с собой":
    fails.append("_short_topic снова режет по запятой")
if _clean_section({"id": "usp", "title": "УТП", "content": "УТП: УТП: свежо."})["content"] != "Свежо.":
    fails.append("_clean_section не снял двойной дубль")

# 6. подпись получает короткую тему, а не длинную фразу
dm6, core6, stub6 = build(["Подпись. #кофе"])
core6.router.write_caption(f"тема: {topics[0]}")
brief = stub6.calls[0][1]
print("6 бриф подписи:", brief[:80])
if LONG_TOPIC in brief: fails.append("в бриф подписи ушла длинная тема")

print("FAILS:", fails or "нет")
sys.exit(1 if fails else 0)
