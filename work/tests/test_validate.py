"""Headless test for the pre-publish plan validator (core tool + GUI button)."""
import sys, tempfile
from pathlib import Path
APP = Path(__file__).resolve().parents[2] / "AI_SMM_Work_Architecture_A75"
PROJECT = APP.parent
WORK = Path(tempfile.mkdtemp(prefix="smm_test_"))
import json, os, shutil, sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(APP))

from data_manager import DataManager
from ai_core import AICore

TMP = str(WORK / "valid_proj")
shutil.rmtree(TMP, ignore_errors=True)
SETTINGS = {"monthly_budget_usd": 0}

dm = DataManager("tmp_valid", data_dir=TMP)
dm._data["content_plan"] = []
dm._data["shooting_tasks"] = []
dm.save()

dm._data["content_plan"] = [
    {"id": "cp_ok", "date": "01.12.2026", "topic": "Готовый пост", "rubric": "Польза",
     "format": "Пост", "status": "Запланировано", "caption": "Текст", "shooting_task_id": "st_001"},
    {"id": "cp_nocap", "date": "02.12.2026", "topic": "Без подписи", "rubric": "Польза",
     "format": "Пост", "status": "Черновик", "caption": "", "shooting_task_id": "st_003"},
    {"id": "cp_nodate", "date": "", "topic": "Без даты", "rubric": "Польза",
     "format": "Пост", "status": "Черновик", "caption": "Текст", "shooting_task_id": "st_002"},
    {"id": "cp_linked", "date": "04.12.2026", "topic": "ТЗ через связь", "rubric": "Польза",
     "format": "Пост", "status": "Черновик", "caption": "Текст", "shooting_task_id": ""},
    {"id": "cp_bare", "date": "  ", "topic": "Пустая позиция", "rubric": "Польза",
     "format": "Reels", "status": "Черновик", "caption": "   "},
]
dm._data["shooting_tasks"] = [
    {"id": "st_001", "content_plan_link": "cp_ok"},
    {"id": "st_002", "content_plan_link": "cp_nocap"},
    {"id": "st_003", "content_plan_link": "cp_nodate"},
    {"id": "st_linked", "content_plan_link": "cp_linked"},
]
dm.save()

core = AICore(dm, SETTINGS, app_db_path=str(WORK / "valid_app.db"))
reply = core.run_tool("validate_plan")
print("--- reply ---")
print(reply.text)

first = reply.text.splitlines()[0]
assert "3 из 5" in first, first
assert "· — · Без даты" in reply.text, reply.text
assert "без даты: 2" in first and "без подписи: 2" in first and "без ТЗ: 1" in first, first
assert "Готовый пост" not in reply.text, reply.text
assert "ТЗ через связь" not in reply.text, reply.text
snapshot = json.dumps(dm.get_content_plan(), ensure_ascii=False, sort_keys=True)
assert not reply.actions, "read-only validation must not report actions"
assert not [e for e in core.journal.list(20) if e["tool"] == "validate_plan"], \
    "validation must not be journaled"
again = core.run_tool("validate_plan")
assert again.text.splitlines()[0] == first, again.text
assert json.dumps(dm.get_content_plan(), ensure_ascii=False, sort_keys=True) == snapshot, \
    "validation changed the plan"

for item in dm.get_content_plan():
    item["date"] = item["date"].strip() or "05.12.2026"
    item["caption"] = item["caption"].strip() or "Текст"
    item["shooting_task_id"] = item.get("shooting_task_id") or "st_linked"
dm.save()
clean = core.run_tool("validate_plan")
print("--- clean ---", clean.text.splitlines()[0])
assert "в порядке" in clean.text, clean.text

dm._data["content_plan"] = []
dm.save()
empty = core.run_tool("validate_plan")
print("--- empty ---", empty.text.splitlines()[0])
assert "пуст" in empty.text.splitlines()[0]

from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton
from gui_sections.content_plan_section import ContentPlanSection

app = QApplication.instance() or QApplication([])
dm._data["content_plan"] = [
    {"id": "cp_gui", "date": "07.12.2026", "topic": "GUI позиция", "rubric": "Польза",
     "format": "Пост", "status": "Черновик", "caption": "", "shooting_task_id": ""},
]
dm.save()
section = ContentPlanSection(dm, SETTINGS)
buttons = [b.text() for b in section.findChildren(QPushButton)]
print("--- buttons ---", buttons)
assert any("Проверить" in b for b in buttons), buttons

shown = {}
QMessageBox.information = staticmethod(lambda parent, title, text: shown.update(title=title, text=text))
section.refresh()
section._on_validate()
print("--- dialog ---", shown)
assert shown["title"] == "Проверка плана", shown
assert "без подписи" in shown["text"] and "без ТЗ" in shown["text"], shown
assert "Проверка:" in section.status.text(), section.status.text()
assert len(dm.get_content_plan()) == 1, "validator must not change data"

print("VALIDATE_OK")
