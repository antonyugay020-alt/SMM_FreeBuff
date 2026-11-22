"""Проверка: повторная обработка фото (один _web), прозрачность PNG, кадр-превью видео."""
import sys, tempfile
from pathlib import Path
APP = Path(__file__).resolve().parents[2] / "AI_SMM_Work_Architecture_A75"
PROJECT = APP.parent
WORK = Path(tempfile.mkdtemp(prefix="smm_test_"))
import os
import shutil
import stat
import sys
import tempfile
from pathlib import Path

ROOT = PROJECT
sys.path.insert(0, str(APP))

from PIL import Image
from PySide6.QtWidgets import QApplication

from data_manager import DataManager
from ai_core import AICore

app = QApplication.instance() or QApplication(sys.argv)
WORK = Path(tempfile.mkdtemp(prefix="step7_"))
MEDIA = PROJECT / "media" / "images"   # та же папка, что у приложения (ai_core.MEDIA_IMAGES)
MEDIA.mkdir(parents=True, exist_ok=True)


def cleanup():
    for path in MEDIA.glob("t7_*"):
        path.unlink(missing_ok=True)
    for path in (MEDIA / ".thumbs").glob("t7_*"):
        path.unlink(missing_ok=True)


cleanup()

dm = DataManager("step7", data_dir=str(WORK / "proj"))
core = AICore(dm, None, app_db_path=str(WORK / "app.db"))

# --- 1. два прогона подряд: один готовый файл, всегда от исходника ---
src = WORK / "t7_wide.png"
Image.new("RGB", (1200, 600), (40, 90, 160)).save(src)
core.run_tool("import_media", paths=[str(src)], zone="ready")
record = dm.get_media_ready()[0]
media_id = record["id"]
original = Path(record["path"])

ops = ["crop", "color", "compress"]
first = core.run_tool("batch_photo", media_ids=[media_id], operations=ops)
assert first.actions, first.text
first_path = Path(dm.get_media_ready()[0]["path"])
first_bytes = first_path.read_bytes()
second = core.run_tool("batch_photo", media_ids=[media_id], operations=ops)
assert second.actions, second.text
record = dm.get_media_ready()[0]
assert Path(record["path"]) == first_path, record["path"]
assert record["name"] == "t7_wide_web.jpg", record["name"]
assert record["source_path"] == str(src), record["source_path"]
assert not (MEDIA / "t7_wide_web_web.jpg").exists()
assert sorted(p.name for p in MEDIA.glob("t7_wide*")) == ["t7_wide.png", "t7_wide_web.jpg"], \
    sorted(p.name for p in MEDIA.glob("t7_wide*"))
assert first_path.read_bytes() == first_bytes, "повторный прогон должен перезаписать тот же файл тем же результатом"
with Image.open(first_path) as im:
    assert im.size == (480, 600), im.size
print("REPEAT_OK", first_path.name)

# --- 1b. старая запись без source_path, путь уже на готовый файл ---
record.pop("source_path")
record["path"] = str(first_path)
dm.save()
third = core.run_tool("batch_photo", media_ids=[media_id], operations=ops)
assert third.actions, third.text
record = dm.get_media_ready()[0]
assert record["source_path"] == str(original), record["source_path"]
assert record["name"] == "t7_wide_web.jpg", record["name"]
assert not (MEDIA / "t7_wide_web_web.jpg").exists()
print("LEGACY_RECORD_OK")

# --- 2. прозрачность PNG не уходит в чёрный фон ---
alpha_src = WORK / "t7_alpha.png"
image = Image.new("RGBA", (400, 400), (200, 30, 30, 255))
image.putpixel((0, 0), (0, 0, 0, 0))
for x in range(20):
    for y in range(20):
        image.putpixel((x, y), (0, 0, 0, 0))
image.save(alpha_src)
core.run_tool("import_media", paths=[str(alpha_src)], zone="ready")
alpha_record = next(r for r in dm.get_media_ready() if r["name"].startswith("t7_alpha"))
out = core.run_tool("batch_photo", media_ids=[alpha_record["id"]], operations=["compress"])
assert out.actions, out.text
alpha_record = next(r for r in dm.get_media_ready() if r["id"] == alpha_record["id"])
rendered = Path(alpha_record["path"])
assert rendered.suffix == ".png", rendered.name
with Image.open(rendered) as im:
    assert im.mode == "RGBA", im.mode
    assert im.getpixel((0, 0))[3] == 0, im.getpixel((0, 0))
    assert im.getpixel((10, 10))[3] == 0
    assert im.getpixel((200, 200))[:3] == (200, 30, 30), im.getpixel((200, 200))
print("ALPHA_OK", rendered.name)

# --- 3. кадр-превью видео ---
clip = MEDIA / "t7_clip.mp4"
clip.write_bytes(b"not a real video, ffmpeg stubbed")
poster_src = WORK / "poster.png"
Image.new("RGB", (320, 180), (10, 200, 160)).save(poster_src)

stub_dir = WORK / "bin"
stub_dir.mkdir()
stub = stub_dir / "ffmpeg"
stub.write_text(f"#!/bin/sh\nfor last; do :; done\ncp '{poster_src}' \"$last\"\n")
stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
old_path = os.environ["PATH"]
os.environ["PATH"] = f"{stub_dir}:{old_path}"

from gui_sections import publications_section as pubs  # noqa: E402

item = {"id": "vid_1", "name": "t7_clip.mp4", "type": "video", "path": str(clip)}
pm = pubs._pixmap_for(item)
assert pm is not None and not pm.isNull(), "кадр видео должен декодироваться"
assert list((MEDIA / ".thumbs").glob("t7_clip*.jpg")), "кадр должен кешироваться в .thumbs"
card = pubs.MediaCard(item)
thumb = card.findChildren(pubs.QLabel)[0]
assert thumb.pixmap() is not None, "карточка показывает кадр, а не надпись VIDEO"

panel = pubs.PreviewPanel(dm)
panel.resize(420, 420)
panel.show_item(item)
assert panel.image.pixmap() is not None and not panel.image.pixmap().isNull()
print("VIDEO_POSTER_OK", pubs._video_poster(clip).name)

# --- 4. без ffmpeg — честная надпись, без падения ---
clip2 = MEDIA / "t7_clip2.mp4"
clip2.write_bytes(b"still not a video")
os.environ["PATH"] = ""
item2 = {"id": "vid_2", "name": "t7_clip2.mp4", "type": "video", "path": str(clip2)}
assert pubs._pixmap_for(item2) is None
card2 = pubs.MediaCard(item2)
assert card2.findChildren(pubs.QLabel)[0].text() == "VIDEO"
panel.show_item(item2)
assert "ffmpeg" in panel.image.text(), panel.image.text()
os.environ["PATH"] = old_path
print("VIDEO_FALLBACK_OK")

cleanup()
shutil.rmtree(WORK, ignore_errors=True)
print("STEP7_OK")
