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
from ai_core import AICore, MEDIA_IMAGES, AIRouter

def ok(name, cond, extra=""):
    print(("C4_OK " if cond else "C4_FAIL ") + name + ("" if cond else f" :: {extra}"))
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

tmp = tempfile.mkdtemp(prefix="c4_")
MEDIA_IMAGES.mkdir(parents=True, exist_ok=True)
outside = Path(tmp) / "chat_clip.mp4"; outside.write_bytes(b"CHAT" * 10)
dm = DataManager("c4", tmp)
core = AICore(dm, {"monthly_budget_usd": 0})
core.tools.video = Fake()

r = core.run_tool("process_video", paths=[str(outside)], platform="instagram_reels")
ready = dm.get_media_ready()
ok("файл из чата попал в проект", len(ready) == 1, ready)
rec = ready[0]
ok("копия лежит в медиатеке", Path(rec["path"]).parent == MEDIA_IMAGES, rec)
ok("оригинал остался в source_path", Path(rec["source_path"]) == outside, rec)
ok("обработка записана", rec["processed"] == ["instagram_reels"], rec)

core.run_tool("process_video", paths=[str(outside)], platform="instagram_reels")
ok("тот же путь не создал вторую копию", len(dm.get_media_ready()) == 1, dm.get_media_ready())
ok("статус без дубля", dm.get_media_ready()[0]["processed"] == ["instagram_reels"],
   dm.get_media_ready()[0])

core.run_tool("make_subtitles", paths=[str(outside)], burn=True)
ok("субтитры по пути из чата",
   dm.get_media_ready()[0]["processed"] == ["instagram_reels", "subtitles"],
   dm.get_media_ready()[0])

before = len(core.journal.list(10))
r = core.run_tool("process_video", paths=[str(Path(tmp) / "нет.mp4")], platform="instagram_reels")
ok("чужой путь — понятный отказ",
   "файл не найден" in r.text and len(core.journal.list(10)) == before, r.text)

router = getattr(core, "router", None) or AIRouter(core.registry, {}, None, "p")
d = router.route("подготовь видео под рилс /tmp/x.mp4")
ok("чат: видео под рилс", d.tool == "process_video" and d.args.get("platform") == "instagram_reels"
   and d.args.get("paths") == ["/tmp/x.mp4"], d)
d = router.route("сделай видео для тиктока /tmp/x.mp4")
ok("чат: тикток", d.args.get("platform") == "tiktok", d)
d = router.route("сделай субтитры /tmp/x.mp4")
ok("чат: субтитры с выжиганием", d.tool == "make_subtitles" and d.args.get("burn") is True, d)
d = router.route("сделай субтитры только srt /tmp/x.mp4")
ok("чат: только srt", d.args.get("burn") is False, d)
d = router.route("подготовь видео под рилс")
ok("чат: без пути — уточнение", not d.tool and "путь" in (d.clarify or ""), d)

from PySide6.QtWidgets import QApplication
app = QApplication([])
import gui_sections.publications_section as pubs
sec = pubs.PublicationsSection(dm, {})
sec._core = core
second = Path(tmp) / "chat_clip2.mp4"; second.write_bytes(b"CHAT2")
pubs.QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: (str(second), ""))
pubs.QInputDialog.getItem = staticmethod(lambda *a, **k: (list(dict(pubs.PHOTO_PRESETS))[0], True))
seen = {}
pubs.QMessageBox.information = staticmethod(lambda parent, title, text: seen.update(t=text))
from ai_core import VIDEO_TARGETS
pubs.QInputDialog.getItem = staticmethod(
    lambda parent, title, label, items, cur, editable: (items[0], True))
sec._process_video()
recs = [m for m in dm.get_media_ready() if str(m.get("source_path", "")).endswith("chat_clip2.mp4")]
ok("кнопка взяла файл с диска",
   len(recs) == 1 and recs[0]["processed"] == ["instagram_reels"], dm.get_media_ready())
ok("отчёт по файлу", "видео" in seen.get("t", "").lower(), seen)
sec._process_subtitles()
pubs.QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: ("", ""))
sec._process_subtitles()
ok("без файла — подсказка", "или файл на диске" in seen.get("t", ""), seen)
print("C4_OK")
