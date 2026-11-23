import sys, tempfile
from pathlib import Path
APP = Path(__file__).resolve().parents[2] / "AI_SMM_Work_Architecture_A75"
PROJECT = APP.parent
WORK = Path(tempfile.mkdtemp(prefix="smm_test_"))
import os, sys, shutil
sys.path.insert(0, str(APP))
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QImage, QColor

app = QApplication([])

# --- real file ---
src = str(WORK / "sample_pub.png")
img = QImage(400, 300, QImage.Format_RGB32)
img.fill(QColor("#2dd4bf")); img.save(src)

from data_manager import DataManager
from ai_core import AICore

from _cleanup import cleanup_media
cleanup_media("sample_pub*")   # не оставлять файлы в media приложения

shutil.rmtree(str(WORK / "prev_test_data"), ignore_errors=True)
dm = DataManager("prev_test", data_dir=str(WORK / "prev_test_data"))
core = AICore(dm, None, app_db_path=str(WORK / "prev_test_app.db"))
reply = core.run_tool("import_media", paths=[src], zone="ready")
print("IMPORT:", reply.text.splitlines()[0])

dm2 = DataManager("prev_test", data_dir=str(WORK / "prev_test_data"))
ready = dm2.get_media_ready()
print("READY:", [(i.get("name"), i.get("path"), i.get("status")) for i in ready])
assert ready, "медиа не сохранилось"
item = ready[0]
assert item.get("path"), "path не пережил сохранение"

from gui_sections.publications_section import MediaCard, PreviewPanel, _media_file, _pixmap_for
assert _media_file(item) is not None
assert _pixmap_for(item) is not None and not _pixmap_for(item).isNull()
card = MediaCard(item)
thumb = card.layout().itemAt(0).widget()
print("CARD thumb:", thumb.pixmap().isNull(), thumb.pixmap().size())
assert not thumb.pixmap().isNull(), "превью карточки пустое"

panel = PreviewPanel(dm2); panel.resize(420, 420)
panel.show_item(item)
print("PREVIEW:", panel.image.pixmap().isNull(), panel.image.pixmap().size(), "|", panel.meta.text())
assert not panel.image.pixmap().isNull()
assert str(panel.meta.text()).strip(), "мета пустая"
panel.show_item({"name": "нет_такого.jpg"})
print("MISSING:", panel.image.text())
assert "не найден" in panel.image.text()

# --- sync gate ---
from gui_sections.content_plan_section import ContentPlanSection
shutil.rmtree(str(WORK / "sync_gate_data"), ignore_errors=True)
dm3 = DataManager("sync_gate", data_dir=str(WORK / "sync_gate_data"))
dm3._data["content_plan"] = [
    {"id": "cp_1", "date": "05.12.2026", "topic": "С датой", "status": "Черновик"},
    {"id": "cp_2", "date": "", "topic": "Без даты", "status": "Черновик"},
]
dm3._data["calendar_events"] = []
dm3.save()

seen = {}
def fake_question(parent, title, text, *a, **kw):
    seen["title"], seen["text"] = title, text
    return seen["answer"]

QMessageBox.question = staticmethod(fake_question)
section = ContentPlanSection(dm3)

seen["answer"] = QMessageBox.No
section._on_sync()
print("NO ->", section.status.text(), "| events:", len(dm3.get_calendar_events()))
assert "отменена" in section.status.text()
assert dm3.get_calendar_events() == []
assert "Без даты" in seen["text"] and "1 из 2" in seen["text"], seen["text"]

seen["answer"] = QMessageBox.Yes
section._on_sync()
events = dm3.get_calendar_events()
print("YES ->", section.status.text(), "| events:", [(e["title"], e["date"]) for e in events])
assert len(events) == 1 and events[0]["title"] == "С датой"

# plan without undated items -> no dialog
seen.pop("title", None)
dm3._data["content_plan"] = [{"id": "cp_3", "date": "06.12.2026", "topic": "Ок", "status": "Черновик"}]
dm3.save()
before = len(dm3.get_calendar_events())
seen["answer"] = QMessageBox.No
section._on_sync()
assert "title" in seen and "новых событий" in seen["text"], seen
assert len(dm3.get_calendar_events()) == before, "«Нет» в кнопке не пишет в календарь"
seen["answer"] = QMessageBox.Yes
section._on_sync()
assert len(dm3.get_calendar_events()) == before + 1, dm3.get_calendar_events()
print("SYNC_GATE_OK")
print("PREVIEW_OK")
