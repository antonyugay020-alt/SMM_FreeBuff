import sys, tempfile
from pathlib import Path
APP = Path(__file__).resolve().parents[2] / "AI_SMM_Work_Architecture_A75"
PROJECT = APP.parent
WORK = Path(tempfile.mkdtemp(prefix="smm_test_"))
import sys, tempfile, json
from pathlib import Path
ROOT = APP
sys.path.insert(0, str(APP))
from ai_core import _extract_json, AICore, StubProvider
from data_manager import DataManager

fails = []
SEC = {"sections": [{"id": "about", "title": "О проекте", "content": "Кофейня у дома, 2 точки"}]}
ANS = json.dumps(SEC, ensure_ascii=False)
EXAMPLE = '{"sections": ["пример", "не тот"]}'

variants = {
    "<thinking> с примером + ```json": "<thinking>\nФормат: " + EXAMPLE + "\nЕщё {'a': 1}\n</thinking>\n```json\n" + ANS + "\n```",
    "<thinking> + голый JSON": "<thinking>\nДумаю про {скобки} и " + EXAMPLE + "\n</thinking>\n" + ANS,
    "рассуждения без тегов": "Сначала подумаю. Пример: " + EXAMPLE + "\nОтвет:\n" + ANS,
    "незакрытый <thinking>": "<thinking>\nДумаю, JSON будет: " + EXAMPLE + "\n",
    "текст вокруг": "Вот стратегия:\n" + ANS + "\nГотово.",
    "скобки внутри строк": json.dumps({"sections": [{"id": "a", "title": "О", "content": "цели {и} задачи"}]}, ensure_ascii=False),
    "```json": "```json\n" + ANS + "\n```",
    "голый JSON": ANS,
}
for name, text in variants.items():
    tmp = Path(tempfile.mkdtemp(prefix="th_"))
    dm = DataManager("p", str(tmp / "p"))
    dm.save_brand_profile({"client_name": "Пар", "niche": "кофейня"})
    core = AICore(dm, {"monthly_budget_usd": 0}, providers=(StubProvider([text]), None))
    core.handle("сделай стратегию")
    sections = dm.get_strategy().get("sections") or []
    expect_none = name.startswith("незакрытый")
    ok = (not sections) if expect_none else (len(sections) == 1)
    print(f"{'OK  ' if ok else 'FAIL'} {name}: блоков {len(sections)} {[s.get('title') for s in sections]}")
    if not ok:
        fails.append(name)

# роутер на том же принципе: пример инструмента в рассуждениях не должен перебить настоящий ответ
tmp = Path(tempfile.mkdtemp(prefix="th2_"))
dm = DataManager("p", str(tmp / "p"))
raw = ('<thinking>Может, {"tool": "delete_record", "args": {"section": "content_plan"}}</thinking>\n'
       '{"tool": "create_content_plan", "args": {"count": 10}, "confidence": 0.9}')
core = AICore(dm, {"monthly_budget_usd": 0}, providers=(StubProvider([raw, raw]), None))
d = core.router.route("сделай что-нибудь по плану")
print("router ->", d.tool, d.args, d.confidence)
if d.tool != "create_content_plan":
    fails.append(f"router выбрал {d.tool} вместо create_content_plan")

print("\nFAILS:", fails or "нет")
sys.exit(1 if fails else 0)
