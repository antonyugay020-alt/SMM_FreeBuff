import sys, tempfile
from pathlib import Path
APP = Path(__file__).resolve().parents[2] / "AI_SMM_Work_Architecture_A75"
PROJECT = APP.parent
WORK = Path(tempfile.mkdtemp(prefix="smm_test_"))
import sys, os
sys.path.insert(0, str(APP))
from data_manager import DataManager
from ai_task_router import AITaskRouter

dm = DataManager("legacy_val", data_dir=str(WORK / "legacy_val_data"))
dm._data["content_plan"] = [
    {"id": "cp_a", "date": "02.12.2026", "topic": "A", "caption": "текст", "format": "Reels", "status": "Черновик"},
    {"id": "cp_b", "date": "03.12.2026", "topic": "B", "caption": "", "format": "Пост", "status": "Черновик"},
]
dm._data["shooting_tasks"] = [{"id": "sh_1", "content_plan_link": "cp_a"}]
dm._data["strategy"] = {"sections": [{"id": "s1", "title": "ЦА", "content": "тест"}, {"id": "s2", "title": "Тон", "content": "  "}]}
dm.save()
r = AITaskRouter()._run_validation(dm)
print("RESULT:", r)
assert r["checked_items"] == 2
assert any("B" in i and "без подписи" in i for i in r["issues"]), r
assert any("ЦА" not in i and "Тон" in i for i in r["issues"]), r
assert not any("A" in i and "без ТЗ" in i for i in r["issues"]), r
empty = DataManager("legacy_empty", data_dir=str(WORK / "legacy_empty_data"))
empty._data["content_plan"] = []; empty._data["strategy"] = {"sections": []}; empty.save()
r2 = AITaskRouter()._run_validation(empty)
print("EMPTY:", r2)
assert r2["issues"] == ["Контент-план пуст"], r2
print("LEGACY_VALIDATE_OK")
