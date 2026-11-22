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
tmp = Path(tempfile.mkdtemp(prefix="ro_"))
dm = DataManager("p", str(tmp / "p"))
core = AICore(dm, {"monthly_budget_usd": 0}, providers=(StubProvider([]), None))
core.handle("создай контент-план на 3 поста")
base = len(core.journal.list(limit=500))

cases = [
    ("instagram_status", {}),
    ("analyze_performance", {"period_days": 30}),
    ("search_knowledge", {"query": "бриф", "limit": 5}),
    ("get_project_context", {"scope": "calendar"}),
    ("validate_plan", {}),
]
for tool, args in cases:
    spec = core.registry.get(tool)
    reply = core._execute(tool, args, "rules")
    grew = len(core.journal.list(limit=500))
    print(f"{tool}: read_only={spec.read_only} журнал {base}->{grew} actions={len(reply.actions)}")
    print("   ", reply.text.replace("\n", " | ")[:110])
    if not spec.read_only:
        fails.append(f"{tool}: флаг read_only не выставлен")
    if grew != base:
        fails.append(f"{tool}: пишется в журнал")
    if reply.actions:
        fails.append(f"{tool}: вернул действия")

# записывающие инструменты не задеты
core._execute("create_shooting_task", {"plan_id": dm.get_content_plan()[0]["id"]}, "rules")
grew = len(core.journal.list(limit=500))
print(f"create_shooting_task: журнал {base}->{grew}")
if grew <= base:
    fails.append("create_shooting_task больше не пишет журнал")
spec = core.registry.get("validate_plan")
print(f"validate_plan: read_only={core.registry.get('validate_plan').read_only}")

print("\nFAILS:", fails or "нет")
sys.exit(1 if fails else 0)
