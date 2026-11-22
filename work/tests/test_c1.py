import sys, tempfile
from pathlib import Path
APP = Path(__file__).resolve().parents[2] / "AI_SMM_Work_Architecture_A75"
PROJECT = APP.parent
WORK = Path(tempfile.mkdtemp(prefix="smm_test_"))
import os, sys, json, tempfile, subprocess
from pathlib import Path
ROOT = APP
sys.path.insert(0, str(APP))
from data_manager import DataManager
from ai_core import AICore, MEDIA_IMAGES

from _cleanup import cleanup_media
cleanup_media("c1_clip*")   # не оставлять файлы в media приложения
import video_processor

def ok(name, cond, extra=""):
    print(("C1_OK " if cond else "C1_FAIL ") + name + ("" if cond else f" :: {extra}"))
    if not cond:
        raise SystemExit(1)

# --- подмена ffmpeg/ffprobe в модуле: работает и на Linux, и на Windows ---
from _ffmpeg_fake import patch_ffmpeg  # noqa: E402

patch_ffmpeg(video_processor)

proc = video_processor.VideoProcessor()
ok("ffmpeg отвечает на -version", proc.ffmpeg_available)

tmp = tempfile.mkdtemp(prefix="c1_")
dm = DataManager("c1", tmp)
core = AICore(dm, {"monthly_budget_usd": 0})
src = MEDIA_IMAGES / "c1_clip.mov"
MEDIA_IMAGES.mkdir(parents=True, exist_ok=True)
src.write_bytes(b"NOT-REAL-VIDEO")
core.run_tool("add_record", section="content_plan", fields={"id": "cp_c1", "date": "01.12.2026",
              "topic": "Ролик", "status": "Запланировано"})
dm._data["media_ready"].append({"id": "mv1", "name": "c1_clip.mov", "type": "video",
                                "size": "1920x1080", "path": str(src), "status": "pending",
                                "date": "01.12.2026"})
dm.save()

r = core.run_tool("process_video", media_ids=["mv1"], platform="instagram_reels")
rec = dm.get_media_ready()[0]
dest = MEDIA_IMAGES / "c1_clip_reels.mp4"
ok("готовый файл создан", dest.is_file(), r.text)
ok("имя с площадкой", rec["name"] == "c1_clip_reels.mp4" and rec["path"] == str(dest), rec)
ok("исходник сохранён в source_path", Path(rec["source_path"]) == src, rec)
ok("размер = 1080x1920 из ffprobe", rec["size"] == "1080x1920", rec["size"])
ok("площадка в processed", rec.get("processed") == ["instagram_reels"], rec)
ok("журнал process_video", any(e["tool"] == "process_video" and e["status"] == "done"
                               for e in core.journal.list(5)))
ok("fps разобран без eval", proc.get_video_info(str(dest))["fps"] == 29.97, proc.get_video_info(str(dest)))

core.run_tool("process_video", media_ids=["mv1"], platform="instagram_reels")
names = [p.name for p in MEDIA_IMAGES.glob("c1_clip*")]
ok("повтор не плодит _reels_reels", names.count("c1_clip_reels.mp4") == 1 and not any("_reels_reels" in n for n in names), names)

dm._data["media_ready"].append({"id": "mv2", "name": "c1_clip_reels.mp4", "type": "video",
                                "path": str(dest), "status": "pending"})
dm.save()
core.run_tool("process_video", media_ids=["mv2"], platform="instagram_reels")
names2 = [p.name for p in MEDIA_IMAGES.glob("c1_clip*")]
ok("повтор без source_path не даёт _reels_reels",
   "c1_clip_reels_reels.mp4" not in names2 and "c1_clip_reels.mp4" in names2, names2)

entries = [e for e in core.journal.list(8) if e["tool"] == "process_video"]
msg = core.undo(entries[0]["id"]).text
ok("откат удалил готовый файл", "Откатил" in msg and not dest.exists(), msg)
for entry in entries[1:]:
    core.undo(entry["id"])
ok("откат вернул исходную запись", dm.get_media_ready()[0].get("name") == "c1_clip.mov",
   dm.get_media_ready()[0])
ok("исходник цел", src.is_file())

bad = core.run_tool("process_video", media_ids=["mv1"], platform="vhs")
ok("чужая площадка отклонена", "Неизвестная площадка" in bad.text, bad.text)

core.tools.video = type("Fake", (), {"ffmpeg_available": False})()
before = len(core.journal.list(6))
r = core.run_tool("process_video", media_ids=["mv1"], platform="instagram_reels")
ok("без ffmpeg — сообщение и нет записи", "Нужен ffmpeg" in r.text and len(core.journal.list(6)) == before, r.text)
core.tools.video = proc

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication
app = QApplication([])
import gui_sections.publications_section as pubs

patch_ffmpeg(pubs)
sec = pubs.PublicationsSection(dm, {})
sec.current = dm.get_media_ready()[0]
pubs.QInputDialog.getItem = staticmethod(lambda *a, **k: ("Reels 9:16, до 90 сек", True))
seen = {}
pubs.QMessageBox.information = staticmethod(lambda parent, title, text: seen.update(t=text))
sec._process_video()
ok("кнопка подготовила видео", dest.is_file() and seen.get("t", "").startswith("Обработал видео"), seen)
ok("просмотр показывает новую запись", sec.current and sec.current.get("name") == "c1_clip_reels.mp4", sec.current)
print("C1_OK")
