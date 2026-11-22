import sys, tempfile
from pathlib import Path
APP = Path(__file__).resolve().parents[2] / "AI_SMM_Work_Architecture_A75"
PROJECT = APP.parent
WORK = Path(tempfile.mkdtemp(prefix="smm_test_"))
import os, sys, tempfile
from pathlib import Path
ROOT = APP
sys.path.insert(0, str(APP))
from data_manager import DataManager
from ai_core import AICore, MEDIA_IMAGES

def ok(name, cond, extra=""):
    print(("C2_OK " if cond else "C2_FAIL ") + name + ("" if cond else f" :: {extra}"))
    if not cond:
        raise SystemExit(1)

class Fake:
    ffmpeg_available = True
    def __init__(self):
        self.audio = Path(tempfile.mkdtemp()) / "a.wav"
    def extract_audio(self, video):
        self.audio.write_bytes(b"WAV"); return str(self.audio)
    def transcribe(self, audio, language="ru"):
        return {"text": "привет", "language": language,
                "segments": [{"id": 0, "start": 0.0, "end": 1.0, "text": "привет"}]}
    def generate_srt(self, segments, path):
        Path(path).write_text("1\n00:00:00,000 --> 00:00:01,000\nпривет\n\n", encoding="utf-8-sig")
        return True
    def burn_subtitles(self, video, srt, out):
        Path(out).write_bytes(b"SUBVIDEO"); return True

tmp = tempfile.mkdtemp(prefix="c2_")
MEDIA_IMAGES.mkdir(parents=True, exist_ok=True)
src = MEDIA_IMAGES / "c2_clip.mp4"; src.write_bytes(b"VIDEO")
dm = DataManager("c2", tmp)
core = AICore(dm, {"monthly_budget_usd": 0})
core.tools.video = Fake()
dm._data["media_ready"].append({"id": "mv1", "name": "c2_clip.mp4", "type": "video",
                                "path": str(src), "status": "pending"})
dm.save()

r = core.run_tool("make_subtitles", media_ids=["mv1"], language="ru", burn=True)
srt = Path(tmp) / "subtitles" / "c2_clip.srt"
subs = MEDIA_IMAGES / "c2_clip_subs.mp4"
rec = dm.get_media_ready()[0]
ok("srt и видео созданы", srt.is_file() and subs.is_file(), r.text)
ok("srt с BOM", srt.read_bytes().startswith(b"\xef\xbb\xbf"), srt.read_bytes()[:3])
ok("запись теперь на видео с субтитрами",
   rec["name"] == "c2_clip_subs.mp4" and rec["path"] == str(subs), rec)
ok("исходник в source_path", Path(rec["source_path"]) == src, rec)
ok("журнал make_subtitles", any(e["tool"] == "make_subtitles" and e["status"] == "done"
                                for e in core.journal.list(5)))
ok("отчёт без лишнего", "выжжено в видео: 1" in r.text.splitlines()[0], r.text)

dm2 = DataManager("c2", tmp)
ok("source_path пережил перезапуск",
   Path(dm2.get_media_ready()[0].get("source_path", "")) == src, dm2.get_media_ready()[0])

entry = [e for e in core.journal.list(5) if e["tool"] == "make_subtitles"][0]
core.undo(entry["id"])
ok("откат удалил srt и видео", not srt.exists() and not subs.exists())
ok("откат вернул запись", dm.get_media_ready()[0]["name"] == "c2_clip.mp4", dm.get_media_ready()[0])

src2 = MEDIA_IMAGES / "c2_clip2.mp4"; src2.write_bytes(b"VIDEO2")
dm._data["media_ready"].append({"id": "mv2", "name": "c2_clip2.mp4", "type": "video",
                                "path": str(src2), "status": "pending"})
dm.save()
r = core.run_tool("make_subtitles", media_ids=["mv2"], burn=False)
srt2 = Path(tmp) / "subtitles" / "c2_clip2.srt"
ok("только srt — без видео", srt2.is_file() and not (MEDIA_IMAGES / "c2_clip2_subs.mp4").exists(), r.text)
ok("запись не менялась", dm.get_media_ready()[1]["name"] == "c2_clip2.mp4")
entry2 = [e for e in core.journal.list(5) if e["tool"] == "make_subtitles"][0]
core.undo(entry2["id"])
ok("откат убрал один srt", not srt2.exists())

dm._data["media_ready"].append({"id": "mv3", "name": "c2_clip.mp4", "type": "video",
                                "path": str(src), "status": "pending"})
dm.save()
class Deaf(Fake):
    def transcribe(self, audio, language="ru"):
        return None
core.tools.video = Deaf()
before = len(core.journal.list(6))
r = core.run_tool("make_subtitles", media_ids=["mv3"], burn=True)
ok("без распознавания — сообщение и нет записи",
   "не распознана" in r.text and len(core.journal.list(6)) == before, r.text)

core.tools.video = type("Off", (), {"ffmpeg_available": False})()
r = core.run_tool("make_subtitles", media_ids=["mv3"], burn=True)
ok("без ffmpeg — отказ", "Нужен ffmpeg" in r.text, r.text)
core.tools.video = Fake()

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication
app = QApplication([])
import gui_sections.publications_section as pubs

sec = pubs.PublicationsSection(dm, {})
sec._core = core  # раздел берёт ядро с подставленным распознавателем
sec.current = dm.get_media_ready()[0]
pubs.QInputDialog.getItem = staticmethod(lambda *a, **k: ("Видео с субтитрами", True))
seen = {}
pubs.QMessageBox.information = staticmethod(lambda parent, title, text: seen.update(t=text))
sec._process_subtitles()
ok("кнопка субтитров работает", seen.get("t", "").startswith("Субтитры"), seen)
ok("просмотр на видео с субтитрами",
   sec.current and sec.current.get("name") == "c2_clip_subs.mp4", sec.current)
print("C2_OK")
