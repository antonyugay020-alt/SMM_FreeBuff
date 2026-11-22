import sys, tempfile
from pathlib import Path
APP = Path(__file__).resolve().parents[2] / "AI_SMM_Work_Architecture_A75"
PROJECT = APP.parent
WORK = Path(tempfile.mkdtemp(prefix="smm_test_"))
import os, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(APP))
from data_manager import DataManager
from ai_core import AICore

def ok(name, cond, extra=""):
    print(("STEP13_OK " if cond else "STEP13_FAIL ") + name + ("" if cond else f" :: {extra}"))
    if not cond:
        raise SystemExit(1)

tmp = tempfile.mkdtemp(prefix="step13_")
src = Path(tmp) / "src"; src.mkdir()
txt = src / "brief.txt"; txt.write_text("бриф", encoding="utf-8")
from PIL import Image
png = src / "ref.png"; Image.new("RGB", (40, 30), (20, 120, 90)).save(png)

dm = DataManager("t13", tmp)
core = AICore(dm, {"monthly_budget_usd": 0})
r = core.run_tool("import_materials", paths=[str(txt), str(png)], folder="documents")
records = dm.get_other_files()["documents"]
ok("два материала в папке", len(records) == 2, records)
ok("копии в проекте", all(Path(x["path"]).is_file() for x in records)
   and all("/materials/documents/" in x["path"].replace("\\", "/") for x in records), records)
ok("тип, размер, дата", {x["type"] for x in records} == {"document", "image"}
   and all(x["size"] and x["date"] for x in records), records)
ok("у записей есть id", all(x["id"].startswith("of_") for x in records), records)
ok("журнал import_materials", any(e["tool"] == "import_materials" and e["status"] == "done"
                                  for e in core.journal.list(5)), core.journal.list(3))

core.run_tool("import_materials", paths=[str(txt)], folder="documents")
names = [x["name"] for x in dm.get_other_files()["documents"]]
ok("имя не затирается", "brief_1.txt" in names, names)

bad = core.run_tool("import_materials", paths=[str(txt)], folder="music")
ok("чужая папка отклонена", "Неизвестная папка" in bad.text, bad.text)
none = core.run_tool("import_materials", paths=[str(src / "нет.txt")], folder="buffer")
ok("нет файлов — нечего импортировать", "импортировать нечего" in none.text, none.text)

dm2 = DataManager("t13", tmp)
ok("материалы пережили перезапуск", len(dm2.get_other_files()["documents"]) == 3,
   dm2.get_other_files())

before_files = [x["path"] for x in dm2.get_other_files()["documents"]]
first = [e for e in core.journal.list(9) if e["tool"] == "import_materials"][0]
core.undo(first["id"])
ok("откат импорта вернул список", len(dm2.get_other_files()) >= 0
   and len(core.dm.get_other_files()["documents"]) == 2,
   core.dm.get_other_files()["documents"])
ok("откат удалил копию, исходник цел", txt.is_file() and len(list(Path(tmp).glob("materials/documents/*"))) <= 2,
   list(Path(tmp).glob("materials/documents/*")))

records = core.dm.get_other_files()["documents"]
target = records[0]
core.run_tool("delete_material", item_id=target["id"])
ok("запись убрана", len(core.dm.get_other_files()["documents"]) == 1,
   core.dm.get_other_files()["documents"])
ok("файл остался на диске", Path(target["path"]).is_file(), target["path"])
entry = [e for e in core.journal.list(5) if e["tool"] == "delete_material"][0]
core.undo(entry["id"])
ok("откат удаления вернул запись", len(core.dm.get_other_files()["documents"]) == 2,
   core.dm.get_other_files()["documents"])

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication, QMessageBox
app = QApplication([])
import gui_sections.other_materials_section as om

sec = om.OtherMaterialsSection(core.dm, {})
sec.folder = "documents"; sec.refresh()
ok("таблица раздела", sec.table.rowCount() == 2, sec.table.rowCount())
ok("счётчик в шапке", "файлов" in sec.count_label.text(), sec.count_label.text())

sec.search.setText("brief")
ok("поиск фильтрует", sec.table.rowCount() == 1, sec.table.rowCount())
sec.search.setText("")
sec.type_filter.setCurrentText("Изображение")
ok("фильтр по типу", sec.table.rowCount() == 1, sec.table.rowCount())
sec.type_filter.setCurrentIndex(0)

sec.table.selectRow(0)
sec._show_preview()
ok("предпросмотр текста", sec.preview.text() != "" or sec.preview.pixmap() is not None, sec.preview.text())

om.QFileDialog.getOpenFileNames = staticmethod(lambda *a, **k: ([str(txt)], ""))
sec._on_import()
ok("кнопка загрузки добавила файл", sec.table.rowCount() == 3, sec.table.rowCount())
ok("статус после загрузки", sec.status.text().startswith("Добавил материалов"), sec.status.text())

sec.table.selectRow(0)
om.QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.Yes)
sec._remove_selected()
ok("убрать из раздела", sec.table.rowCount() == 2, sec.table.rowCount())
print("STEP13_OK")
