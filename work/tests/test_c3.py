import sys, tempfile
from pathlib import Path
APP = Path(__file__).resolve().parents[2] / "AI_SMM_Work_Architecture_A75"
PROJECT = APP.parent
WORK = Path(tempfile.mkdtemp(prefix="smm_test_"))
import os, sys, tempfile
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path
ROOT = APP
sys.path.insert(0, str(APP))
from data_manager import DataManager
from PySide6.QtWidgets import QApplication, QLabel
app = QApplication([])
import gui_sections.publications_section as pubs

def ok(name, cond, extra=""):
    print(("C3_OK " if cond else "C3_FAIL ") + name + ("" if cond else f" :: {extra}"))
    if not cond:
        raise SystemExit(1)

tmp = tempfile.mkdtemp(prefix="c3_")
src = Path(tmp) / "clip.mov"; src.write_bytes(b"A" * 2048)
dst = Path(tmp) / "clip_reels.mp4"; dst.write_bytes(b"B" * (3 * 1024 * 1024))
dm = DataManager("c3", tmp)
rec = {"id": "mv1", "name": "clip_reels.mp4", "type": "video", "size": "1080x1920",
       "path": str(dst), "source_path": str(src), "processed": ["instagram_reels"],
       "status": "pending"}
dm._data["media_ready"].append(dict(rec))
dm.save()

dm2 = DataManager("c3", tmp)
ok("processed пережил перезапуск", dm2.get_media_ready()[0]["processed"] == ["instagram_reels"],
   dm2.get_media_ready()[0])

card = pubs.MediaCard(dm.get_media_ready()[0])
texts = [w.text() for w in card.findChildren(QLabel)]
ok("карточка показывает операцию", any("Reels" in t for t in texts), texts)

sec = pubs.PublicationsSection(dm, {})
sec.preview.show_item(dm.get_media_ready()[0])
pills = [sec.preview.badge_row.itemAt(i).widget().text()
         for i in range(sec.preview.badge_row.count())
         if sec.preview.badge_row.itemAt(i).widget()]
ok("просмотр показывает и статус, и операцию",
   any("На проверке" in p for p in pills) and any("Reels" in p for p in pills), pills)

ok("размер в диалоге", pubs._file_size(dst) == "3.0 МБ", pubs._file_size(dst))
ok("без ffmpeg длительность честная",
   pubs._video_duration(dst) == "длительность неизвестна", pubs._video_duration(dst))

dlg = pubs.VideoCompareDialog(src, dst, dm.get_media_ready()[0])
texts = [w.text() for w in dlg.findChildren(QLabel)]
ok("диалог до/после собирается",
   any("clip.mov" in t for t in texts) and any("clip_reels.mp4" in t for t in texts), texts)

opened = {}
pubs.VideoCompareDialog = lambda s, c, i, parent=None: opened.update(s=str(s), c=str(c), i=i) or type(
    "D", (), {"exec": lambda self: 0})()
seen = {}
pubs.QMessageBox.information = staticmethod(lambda parent, title, text: seen.update(t=text))

sec.preview.show_item(dm.get_media_ready()[0])
sec.preview._compare_video()
ok("кнопка открыла сравнение исходника и готового",
   opened.get("s") == str(src) and opened.get("c") == str(dst), opened)

photo = {"id": "p1", "name": "a.jpg", "type": "image", "path": str(src)}
sec.preview.show_item(photo)
sec.preview._compare_video()
ok("для фото — подсказка", "для видео" in seen.get("t", ""), seen)

nosrc = {"id": "mv2", "name": "clip_reels.mp4", "type": "video", "path": str(dst)}
sec.preview.show_item(nosrc)
sec.preview._compare_video()
ok("без исходника — сообщение", "Исходник не сохранён" in seen.get("t", ""), seen)
print("C3_OK")
