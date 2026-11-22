import sys, tempfile
from pathlib import Path
APP = Path(__file__).resolve().parents[2] / "AI_SMM_Work_Architecture_A75"
PROJECT = APP.parent
WORK = Path(tempfile.mkdtemp(prefix="smm_test_"))
import sys, tempfile
from pathlib import Path
ROOT = APP
sys.path.insert(0, str(APP))
from data_manager import DataManager
from ai_core import AICore, StubProvider

fails = []
tmp = Path(tempfile.mkdtemp(prefix="read_"))
dm = DataManager("p", str(tmp / "p"))
core = AICore(dm, {"monthly_budget_usd": 0}, providers=(StubProvider([]), None))
core.handle("создай контент-план на 3 поста")
core.tools.sync_plan_events()
base = len(dm.get_calendar_events())
journal_before = len(core.journal.list(limit=200))
print(f"событий в проекте: {base}")

for phrase in ("покажи события календаря", "открой календарь", "посмотри календарь",
               "что в календаре", "список событий календаря"):
    d = core.router.route(phrase)
    r = core.handle(phrase)
    after = len(dm.get_calendar_events())
    print(f"\nVIEW {phrase!r} -> {d.tool} scope={(d.args or {}).get('scope')} events {base}->{after}")
    print("  " + r.text.replace("\n", "\n  ")[:300])
    if d.tool != "get_project_context":
        fails.append(f"{phrase!r}: {d.tool} вместо get_project_context")
    if after != base:
        fails.append(f"{phrase!r}: создал события {base}->{after}")
    if "События календаря" not in r.text:
        fails.append(f"{phrase!r}: в ответе нет списка событий")

# пустой календарь — понятный ответ без ошибки
dm2 = DataManager("p2", str(tmp / "p2"))
core2 = AICore(dm2, {"monthly_budget_usd": 0}, providers=(StubProvider([]), None))
r = core2.handle("покажи события календаря")
print("\nEMPTY ->", r.text.replace("\n", " | ")[:160])
if "Событий пока нет" not in r.text:
    fails.append("пустой календарь: нет понятного ответа")

# действия и остальные правила не задеты
for phrase, tool in (("добавь план в календарь", "sync_plan_events"),
                     ("перенеси план в календарь", "sync_plan_events"),
                     ("проверь план перед публикацией", "validate_plan"),
                     ("проверь доступ к инстаграму", "instagram_status"),
                     ("создай контент-план на 10 постов", "create_content_plan"),
                     ("сколько событий в календаре", "get_project_context")):
    d = core.router.route(phrase)
    print(f"RULE {phrase!r} -> {d.tool} scope={(d.args or {}).get('scope')}")
    if d.tool != tool:
        fails.append(f"{phrase!r}: {d.tool} вместо {tool}")

print("\nFAILS:", fails or "нет")
sys.exit(1 if fails else 0)
