"""Проверка: batch_photo (реальная обработка) + кнопка в «Публикациях» + гейт синхронизации."""
import sys, tempfile
from pathlib import Path
APP = Path(__file__).resolve().parents[2] / "AI_SMM_Work_Architecture_A75"
PROJECT = APP.parent
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(APP))

from PIL import Image
from PySide6.QtWidgets import QApplication, QMessageBox

from data_manager import DataManager
from ai_core import AICore

from _cleanup import cleanup_media
cleanup_media("wide*")   # не оставлять файлы в media приложения

app = QApplication.instance() or QApplication(sys.argv)

WORK = Path(tempfile.mkdtemp(prefix="step6_"))
SRC = WORK / "wide.png"
Image.new("RGB", (1200, 600), (40, 90, 160)).save(SRC)

dm = DataManager("step6", data_dir=str(WORK / "proj"))
core = AICore(dm, None, app_db_path=str(WORK / "app.db"))

reply = core.run_tool("import_media", paths=[str(SRC)], zone="ready")
assert reply.actions, reply.text
record = dm.get_media_ready()[0]
media_id = record["id"]
original_path = Path(record["path"])
assert original_path.is_file()

out = core.run_tool("batch_photo", media_ids=[media_id],
                    operations=["crop", "color", "compress"])
assert "Обработал фото: 1" in out.text, out.text
assert out.actions, out.text

record = dm.get_media_ready()[0]
processed = Path(record["path"])
assert processed.name.endswith("_web.jpg"), processed.name
assert processed.is_file()
assert record["source_path"] == str(SRC)
assert record["processed"] == ["crop", "color", "compress"]
assert original_path.is_file(), "исходник должен остаться на диске"
with Image.open(processed) as im:
    assert im.size == (480, 600), im.size
    assert im.format == "JPEG", im.format
print("BATCH_PHOTO_OK", processed.name)

undo_reply = core.undo(out.actions[0]["id"])
assert "Откатил" in undo_reply.text, undo_reply.text
record = dm.get_media_ready()[0]
assert Path(record["path"]) == original_path, record["path"]
assert not processed.exists(), "готовый файл должен исчезнуть после отката"
print("BATCH_UNDO_OK")

empty = core.run_tool("batch_photo", media_ids=["nope"])
assert not empty.actions and "не найдены" in empty.text, empty.text
bad_ops = core.run_tool("batch_photo", media_ids=[media_id], operations=["blur"])
assert not bad_ops.actions and "Неизвестные операции" in bad_ops.text, bad_ops.text
print("BATCH_GUARD_OK")

from gui_sections import publications_section as pubs

answers = {"question": QMessageBox.Yes, "info": []}
pubs.QMessageBox.information = staticmethod(lambda *a, **k: answers["info"].append(a[2]))
pubs.QInputDialog.getItem = staticmethod(
    lambda *a, **k: ("Кадрировать 4:5 + цвет + сжатие", True))

section = pubs.PublicationsSection(dm)
section._select(dm.get_media_ready()[0])
assert section.preview.image.pixmap() is not None, "превью должно показать файл"
before_pixmap = section.preview.image.pixmap().cacheKey()

section._process_media()
record = dm.get_media_ready()[0]
assert Path(record["path"]).is_file(), "кнопка должна записать готовый файл"
assert any("Обработал фото: 1" in text for text in answers["info"]), answers["info"]
assert section.current["id"] == record["id"]
assert section.preview.image.pixmap() is not None
assert section.preview.image.pixmap().cacheKey() != before_pixmap, "превью должно обновиться"
print("PUBLICATIONS_BATCH_OK", Path(record["path"]).name)

from gui_sections import content_plan_section as cps
ContentPlanSection = cps.ContentPlanSection

dm._data["content_plan"] = [
    {"id": "cp_1", "date": "01.12.2026", "rubric": "Польза", "topic": "С датой",
     "format": "Пост", "status": "Черновик"},
    {"id": "cp_2", "date": "", "rubric": "Польза", "topic": "Без даты",
     "format": "Пост", "status": "Черновик"},
]
dm.save()
plan_section = ContentPlanSection(dm)
calls = []


def fake_question(*args, **kwargs):
    calls.append(args[2])
    return answers["question"]


cps.QMessageBox.question = staticmethod(fake_question)

events_before = len(dm.get_calendar_events())
answers["question"] = QMessageBox.No
plan_section._on_sync()
assert "отменена" in plan_section.status.text(), plan_section.status.text()
assert len(dm.get_calendar_events()) == events_before, "«Нет» не должен синхронизировать"
assert "Без даты 1 из 2" in calls[-1], calls[-1]

answers["question"] = QMessageBox.Yes
plan_section._on_sync()
assert len(dm.get_calendar_events()) > events_before, "«Да» должен синхронизировать"
assert dm.get_content_plan()[0]["status"] == "Запланировано"
print("SYNC_GATE_OK")
print("STEP6_OK")
