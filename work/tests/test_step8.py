"""Проверка: просмотр перерисовывается при изменении размера панели."""
import sys, tempfile
from pathlib import Path
APP = Path(__file__).resolve().parents[2] / "AI_SMM_Work_Architecture_A75"
PROJECT = APP.parent
WORK = Path(tempfile.mkdtemp(prefix="smm_test_"))
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = PROJECT
sys.path.insert(0, str(APP))

from PIL import Image
from PySide6.QtWidgets import QApplication

from data_manager import DataManager
from gui_sections import publications_section as pubs

app = QApplication.instance() or QApplication(sys.argv)
WORK = Path(tempfile.mkdtemp(prefix="step8_"))
MEDIA = PROJECT / "media" / "images"   # та же папка, что у приложения (ai_core.MEDIA_IMAGES)
MEDIA.mkdir(parents=True, exist_ok=True)

wide = MEDIA / "t8_wide.png"
portrait = MEDIA / "t8_tall.png"
Image.new("RGB", (1200, 400), (60, 120, 200)).save(wide)
Image.new("RGB", (400, 1200), (200, 120, 60)).save(portrait)

dm = DataManager("step8", data_dir=str(WORK / "proj"))
panel = pubs.PreviewPanel(dm)
panel.resize(400, 400)
panel.show()
app.processEvents()

item = {"id": "w", "name": "t8_wide.png", "type": "image", "path": str(wide)}
panel.show_item(item)
app.processEvents()
first = panel.image.pixmap()
assert first is not None and not first.isNull()
assert first.width() <= panel.image.width() and first.height() <= panel.image.height(), \
    (first.width(), first.height(), panel.image.width(), panel.image.height())

panel.resize(300, 700)
app.processEvents()
second = panel.image.pixmap()
assert second is not None and not second.isNull()
assert (second.width(), second.height()) != (first.width(), first.height()), "кадр не пересчитан под новый размер"
assert second.height() >= first.height() or second.width() <= first.width(), \
    (first.size(), second.size())
assert abs(second.width() / second.height() - 3.0) < 0.05, (second.width(), second.height())
print("RESIZE_OK", (400, 400), (first.width(), first.height()),
      (300, 700), (second.width(), second.height()))

tall = {"id": "t", "name": "t8_tall.png", "type": "image", "path": str(portrait)}
panel.resize(500, 300)
app.processEvents()
panel.show_item(tall)
app.processEvents()
pixmap = panel.image.pixmap()
assert pixmap is not None
assert abs(pixmap.width() / pixmap.height() - 1 / 3) < 0.05, (pixmap.width(), pixmap.height())
panel.resize(500, 620)
app.processEvents()
taller = panel.image.pixmap()
assert taller.height() > pixmap.height(), (pixmap.size(), taller.size())
print("RESIZE_VERTICAL_OK", (pixmap.width(), pixmap.height()), (taller.width(), taller.height()))

missing = {"id": "m", "name": "t8_missing.png", "type": "image"}
panel.show_item(missing)
app.processEvents()
assert "не найден" in panel.image.text(), panel.image.text()
panel.resize(340, 340)
app.processEvents()
assert "не найден" in panel.image.text(), panel.image.text()
print("RESIZE_TEXT_OK")

wide.unlink()
portrait.unlink()
shutil.rmtree(WORK, ignore_errors=True)
print("STEP8_OK")
