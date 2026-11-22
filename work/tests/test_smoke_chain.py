import sys, tempfile
from pathlib import Path
APP = Path(__file__).resolve().parents[2] / "AI_SMM_Work_Architecture_A75"
PROJECT = APP.parent
WORK = Path(tempfile.mkdtemp(prefix="smm_test_"))
import os, sys, shutil
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(APP))
from PySide6.QtWidgets import QApplication
from data_manager import DataManager
from gui_sections.strategy_section import StrategySection
from gui_sections.content_plan_section import ContentPlanSection
from gui_sections.calendar_section import CalendarSection
from gui_sections.shooting_tasks_section import ShootingTasksSection
app = QApplication.instance() or QApplication([])
TMP = str(WORK / "smoke_chain_proj"); shutil.rmtree(TMP, ignore_errors=True)
dm = DataManager("tmp_smoke_chain", data_dir=TMP)
settings = {"monthly_budget_usd": 0}
for cls in (StrategySection, ContentPlanSection, CalendarSection, ShootingTasksSection):
    w = cls(dm, settings)
    assert w is not None
    print("OK", cls.__name__)
print("SMOKE_CHAIN_OK")
