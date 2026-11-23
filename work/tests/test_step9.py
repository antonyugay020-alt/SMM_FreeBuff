"""Проверка: кнопки просмотра «Повторить обработку» и «Сравнить с исходником»."""
import sys, tempfile
from pathlib import Path
APP = Path(__file__).resolve().parents[2] / "AI_SMM_Work_Architecture_A75"
PROJECT = APP.parent
import sys
import tempfile
from pathlib import Path

ROOT = PROJECT
sys.path.insert(0, str(APP))

from PIL import Image
from PySide6.QtWidgets import QApplication, QLabel

from data_manager import DataManager
from ai_core import AICore
from gui_sections import publications_section as pubs

app = QApplication.instance() or QApplication(sys.argv)
MEDIA = ROOT / "media" / "images"
WORK = Path(tempfile.mkdtemp(prefix="step9_"))


def cleanup():
    for path in MEDIA.glob("t9_*"):
        path.unlink(missing_ok=True)


cleanup()

dm = DataManager("step9", data_dir=str(WORK / "proj"))
core = AICore(dm, None, app_db_path=str(WORK / "app.db"))
src = WORK / "t9_shot.png"
Image.new("RGB", (1200, 600), (30, 140, 90)).save(src)
core.run_tool("import_media", paths=[str(src)], zone="ready")
record = dm.get_media_ready()[0]
media_id = record["id"]
original = Path(record["path"])

section = pubs.PublicationsSection(dm)
section.resize(1200, 800)
section.show()
app.processEvents()
target = next(m for m in dm.get_media_ready() if m["id"] == media_id)
section._select(target)
assert section.preview.item is target

messages = []
pubs.QMessageBox.information = staticmethod(
    lambda *args, **kwargs: messages.append(args[2] if len(args) > 2 else ""))
pubs.QInputDialog.getItem = staticmethod(
    lambda *args, **kwargs: (pubs.PHOTO_PRESETS[0][0], True))
answers = {"question": pubs.QMessageBox.Yes}
questions = []


def fake_question(parent, title, text, *args, **kwargs):
    questions.append(text)
    return answers["question"]


pubs.QMessageBox.question = staticmethod(fake_question)

# --- 1. «Повторить обработку» в просмотре реально прогоняет batch_photo ---
section.preview.repeat_btn.click()
app.processEvents()
updated = next(m for m in dm.get_media_ready() if m["id"] == media_id)
assert updated.get("processed") == ["crop", "color", "compress"], updated.get("processed")
assert updated["name"] == "t9_shot_web.jpg", updated["name"]
assert Path(updated["source_path"]) == src, updated.get("source_path")
assert Path(updated["path"]).is_file()
assert section.preview.item["id"] == media_id
assert messages and "Обработал фото: 1" in messages[-1], messages
print("PREVIEW_REPEAT_OK", updated["name"], "|", messages[-1])

# --- 2. второй клик тоже реальная обработка, без _web_web ---
messages.clear()
section.preview.repeat_btn.click()
app.processEvents()
assert sorted(p.name for p in MEDIA.glob("t9_shot*")) == ["t9_shot.png", "t9_shot_web.jpg"], \
    sorted(p.name for p in MEDIA.glob("t9_shot*"))
assert messages and "Обработал фото: 1" in messages[-1], messages
print("PREVIEW_REPEAT_TWICE_OK")

# --- 3. «Сравнить с исходником» строит диалог из source_path ---
updated = next(m for m in dm.get_media_ready() if m["id"] == media_id)
section._select(updated)
dialog = pubs.CompareDialog(Path(updated["source_path"]), pubs._media_file(updated),
                            section.preview)
texts = [label.text() for label in dialog.findChildren(QLabel)]
assert any("t9_shot.png" in t and "1200×600 px" in t for t in texts), texts
assert any("t9_shot_web.jpg" in t and "480×600 px" in t for t in texts), texts
assert "Исходник" in texts and "Обработано" in texts, texts
dialog.close()

opened = []
real_exec = pubs.CompareDialog.exec
pubs.CompareDialog.exec = lambda self: opened.append(self) or 0
section.preview._compare()
pubs.CompareDialog.exec = real_exec
assert opened, "«Сравнить с исходником» не открыла диалог"
print("PREVIEW_COMPARE_OK", [t for t in texts if "px" in t])

# --- 4. без source_path — понятное сообщение вместо пустого окна ---
updated.pop("source_path", None)
dm.save()
section._select(updated)
messages.clear()
section.preview._compare()
assert messages and "Исходник не сохранён" in messages[-1], messages
print("COMPARE_NO_SOURCE_OK")

# --- 5. отказ в диалоге ничего не обрабатывает ---
answers["question"] = pubs.QMessageBox.No
updated = next(m for m in dm.get_media_ready() if m["id"] == media_id)
section._select(updated)
before_processed = list(updated.get("processed") or [])
before_name = updated["name"]
questions.clear()
section.preview.repeat_btn.click()
app.processEvents()
now = next(m for m in dm.get_media_ready() if m["id"] == media_id)
assert now["name"] == before_name, now
assert list(now.get("processed") or []) == before_processed, now
assert questions and "Обработать «t9_shot_web.jpg»" in questions[-1], questions
print("PROCESS_CANCEL_OK")
answers["question"] = pubs.QMessageBox.Yes

# --- 6. «Обработать фото» в шапке по-прежнему работает (общая функция) ---
messages.clear()
section._process_media()
app.processEvents()
assert messages and "Обработал фото: 1" in messages[-1], messages
print("HEADER_PROCESS_OK")

cleanup()
print("STEP9_OK")
