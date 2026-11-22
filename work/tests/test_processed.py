import sys, tempfile
from pathlib import Path
APP = Path(__file__).resolve().parents[2] / "AI_SMM_Work_Architecture_A75"
PROJECT = APP.parent
WORK = Path(tempfile.mkdtemp(prefix="smm_test_"))
import sys, tempfile
from pathlib import Path
ROOT = APP
sys.path.insert(0, str(APP))
from data_manager import DataManager
from ai_core import AICore, MEDIA_IMAGES

from _cleanup import cleanup_media
cleanup_media("proc_clip*")   # не оставлять файлы в media приложения

def ok(name, cond, extra=""):
    print(("PROC_OK " if cond else "PROC_FAIL ") + name + ("" if cond else f" :: {extra}"))
    if not cond:
        raise SystemExit(1)

class Fake:
    ffmpeg_available = True
    def __init__(self):
        self.audio = Path(tempfile.mkdtemp()) / "a.wav"
    def export_for_platform(self, src, platform, dest):
        Path(dest).write_bytes(b"OUT"); return True
    def get_video_info(self, path):
        return {"width": 1080, "height": 1920, "duration": 12.0, "fps": 30.0}
    def extract_audio(self, video):
        self.audio.write_bytes(b"WAV"); return str(self.audio)
    def transcribe(self, audio, language="ru"):
        return {"segments": [{"start": 0.0, "end": 1.0, "text": "привет"}]}
    def generate_srt(self, segments, path):
        Path(path).write_text("1\n00:00:00,000 --> 00:00:01,000\nпривет\n\n", encoding="utf-8-sig")
        return True
    def burn_subtitles(self, video, srt, out):
        Path(out).write_bytes(b"SUB"); return True

tmp = tempfile.mkdtemp(prefix="proc_")
MEDIA_IMAGES.mkdir(parents=True, exist_ok=True)
src = MEDIA_IMAGES / "proc_clip.mp4"; src.write_bytes(b"VIDEO")
dm = DataManager("proc", tmp)
core = AICore(dm, {"monthly_budget_usd": 0})
core.tools.video = Fake()
dm._data["media_ready"].append({"id": "mv1", "name": "proc_clip.mp4", "type": "video",
                                "path": str(src), "status": "pending"})
dm.save()

def marks():
    return list(dm.get_media_ready()[0].get("processed") or [])

core.run_tool("process_video", media_ids=["mv1"], platform="instagram_reels")
ok("первая обработка записана", marks() == ["instagram_reels"], marks())
core.run_tool("process_video", media_ids=["mv1"], platform="youtube_shorts")
ok("вторая площадка добавилась", marks() == ["instagram_reels", "youtube_shorts"], marks())
core.run_tool("process_video", media_ids=["mv1"], platform="instagram_reels")
ok("повтор той же площадки без дубля", marks() == ["instagram_reels", "youtube_shorts"], marks())
core.run_tool("make_subtitles", media_ids=["mv1"], burn=True)
ok("субтитры не стерли площадки",
   marks() == ["instagram_reels", "youtube_shorts", "subtitles"], marks())
core.run_tool("make_subtitles", media_ids=["mv1"], burn=True)
ok("повтор субтитров без дубля", marks().count("subtitles") == 1 and len(marks()) == 3, marks())

dm2 = DataManager("proc", tmp)
ok("накопленное пережило перезапуск",
   dm2.get_media_ready()[0]["processed"] == ["instagram_reels", "youtube_shorts", "subtitles"],
   dm2.get_media_ready()[0])

entry = [e for e in core.journal.list(10) if e["tool"] == "make_subtitles"][0]
core.undo(entry["id"])
ok("откат субтитров не стер видео-статусы",
   marks() == ["instagram_reels", "youtube_shorts", "subtitles"], marks())
print("PROCESSED_OK")
