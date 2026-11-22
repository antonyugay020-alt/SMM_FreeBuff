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
from ai_core import AICore

def ok(name, cond, extra=""):
    print(("C5_OK " if cond else "C5_FAIL ") + name + ("" if cond else f" :: {extra}"))
    if not cond:
        raise SystemExit(1)

tmp = Path(tempfile.mkdtemp(prefix="c5_"))
photo = tmp / "post_story.jpg"; photo.write_bytes(b"JPEG" * 500)
gone = tmp / "потерянный.jpg"

dm = DataManager("c5", str(tmp / "proj"))
core = AICore(dm, {"monthly_budget_usd": 0})
dm._data["media_ready"] += [
    {"id": "m1", "name": "post_story.jpg", "type": "image", "size": "1080x1350",
     "path": str(photo), "status": "approved", "date": "25.11.2026",
     "processed": ["crop", "color"]},
    {"id": "m2", "name": "потерянный.jpg", "type": "image", "path": str(gone),
     "status": "approved", "date": "30.11.2026"}]
dm._data["content_plan"] += [
    {"id": "p1", "date": "25.11.2026", "topic": "Запуск курса", "caption": "Стартуем!",
     "hashtags": ["#курс", "#алматы"], "status": "Запланировано"},
    {"id": "p2", "date": "30.11.2026", "topic": "Без текста", "status": "Запланировано"},
    {"id": "p3", "date": "28.11.2026", "topic": "Нет файла", "caption": "Отдельная подпись",
     "hashtags": ["#тг"], "status": "Запланировано"}]
dm.save()

dest = tmp / "пользовательская"; dest.mkdir()
r = core.run_tool("instagram_pack", dest=str(dest))
folder = next(p for p in dest.iterdir() if p.is_dir())
media = [p for p in (folder / "media").iterdir()]
ok("скопирован один файл", len(media) == 1, media)
name = media[0].name
stem = Path(name).stem

captions = (folder / "captions.txt").read_text(encoding="utf-8")
header = f"=== {name} ==="
ok("подпись стоит под своим файлом",
   header in captions and captions.index(header) < captions.index("Стартуем!"), captions)
ok("чужая подпись не приклеилась",
   "Отдельная подпись" not in captions.split(header)[-1].split("===")[0], captions)

one = folder / "captions" / f"{stem}.txt"
ok("отдельный txt на файл", one.is_file() and "Стартуем!" in one.read_text(encoding="utf-8"),
   list((folder / "captions").iterdir()) if (folder / "captions").is_dir() else "нет папки")
ok("хэштеги в том же файле", "#алматы" in one.read_text(encoding="utf-8"))

manifest = (folder / "manifest.csv").read_text(encoding="utf-8").splitlines()
ok("манифест со связкой", manifest[0].startswith("файл;дата;тема;подпись")
   and manifest[1].split(";")[0] == name and manifest[1].split(";")[3] == "да", manifest)

problems = (folder / "problems.txt").read_text(encoding="utf-8")
ok("потерянный файл в замечаниях", "файл не найден" in problems, problems)
ok("подпись без файла в замечаниях",
   "Нет файла: нет файла под подпись" in problems, problems)
ok("отчёт короткий", f"файлов 1" in r.text.splitlines()[0], r.text)

entry = [e for e in core.journal.list(5) if e["tool"] == "instagram_pack"][0]
core.undo(entry["id"])
ok("откат удалил подпапку", not folder.exists() and dest.is_dir())

empty = AICore(DataManager("empty", str(tmp / "empty")), {"monthly_budget_usd": 0})
ok("пустой проект — отказ", "Пакет не собран" in empty.run_tool("instagram_pack", dest=str(dest)).text)

router = core.router
ok("чат: пакет в инстаграм", router.route("собери пакет для инстаграма").tool == "instagram_pack")
ok("чат: обычный пакет", router.route("собери пакет публикаций").tool == "export_package")

from PySide6.QtWidgets import QApplication, QLabel
app = QApplication([])
import gui_sections.publications_section as pubs
card = pubs.MediaCard({"id": "x", "name": "photo.jpg", "type": "image",
                       "status": "pending", "processed": ["crop", "color", "compress", "weird"]})
texts = [w.text() for w in card.findChildren(QLabel)]
marks = " ".join(texts)
ok("карточка без сырых ключей", "crop" not in marks and "weird" not in marks, texts)
ok("карточка с русскими подписями",
   "Кадр" in marks and "Цвет" in marks and "Сжатие" in marks, texts)

sec = pubs.PublicationsSection(dm, {})
sec._core = core
pubs.QFileDialog.getExistingDirectory = staticmethod(lambda *a, **k: str(dest))
seen = {}
pubs.QMessageBox.information = staticmethod(lambda parent, title, text: seen.update(t=text))
sec._instagram_pack()
ok("кнопка собрала пакет", "Пакет в Instagram" in seen.get("t", ""), seen)
print("C5_OK")
