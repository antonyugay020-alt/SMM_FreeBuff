"""Проверка: «Экспорт пакета» из GUI «Публикаций» — папка, отчёт, журнал, откат."""
import sys, tempfile
from pathlib import Path
APP = Path(__file__).resolve().parents[2] / "AI_SMM_Work_Architecture_A75"
PROJECT = APP.parent
import sys
import tempfile
from pathlib import Path

ROOT = PROJECT
sys.path.insert(0, str(APP))

from PySide6.QtWidgets import QApplication, QPushButton

from data_manager import DataManager
from gui_sections import publications_section as pubs

app = QApplication.instance() or QApplication(sys.argv)
WORK = Path(tempfile.mkdtemp(prefix="step10_"))
OUT = WORK / "export_here"
OUT.mkdir()

dm = DataManager("step10", data_dir=str(WORK / "proj"))
dm._data["content_plan"] = [
    {"id": "cp_1", "date": "2026-11-23", "topic": "Пост про уход", "status": "Запланировано"},
    {"id": "cp_2", "date": "2026-11-25", "topic": "Рилс про кожу", "status": "Запланировано"},
    {"id": "cp_3", "date": "2026-11-27", "topic": "Черновик", "status": "Идея"},
]
dm.save()

section = pubs.PublicationsSection(dm)
section.resize(1200, 800)
section.show()
app.processEvents()

messages = []
pubs.QMessageBox.information = lambda *a, **k: messages.append(a[2])
real_dialog = pubs.QFileDialog.getExistingDirectory

# --- 1. кнопка есть в шапке медиатеки и открывает выбор папки ---
buttons = [b for b in section.findChildren(QPushButton) if "Экспорт" in b.text()]
assert buttons, [b.text() for b in section.findChildren(QPushButton)]
button = buttons[0]

pubs.QFileDialog.getExistingDirectory = lambda *a, **k: str(OUT)
button.click()
app.processEvents()

folders = [p for p in OUT.iterdir() if p.is_dir()]
assert len(folders) == 1, folders
package = folders[0] / "package.txt"
assert package.is_file(), list(folders[0].iterdir())
text = package.read_text(encoding="utf-8")
assert "2026-11-23 — Пост про уход" in text and "Рилс про кожу" in text, text
assert "Черновик" not in text, "в пакет идут только «Запланировано»"
assert messages and "Собрал пакет в" in messages[-1] and "(позиций: 2)" in messages[-1], messages
assert str(folders[0]) in messages[-1], messages

entries = section.core().journal.list(3)
assert entries and entries[0]["tool"] == "export_package", entries[:1]
assert entries[0]["status"] == "done", entries[:1]
action_id = entries[0]["id"]
print("GUI_EXPORT_OK", folders[0].name, "|", messages[-1])

# --- 2. отмена выбора папки ничего не делает ---
pubs.QFileDialog.getExistingDirectory = lambda *a, **k: ""
before = len(messages)
count_before = len(list(OUT.iterdir()))
button.click()
app.processEvents()
assert len(messages) == before and len(list(OUT.iterdir())) == count_before
assert section.core().journal.list(1)[0]["id"] == action_id
print("EXPORT_CANCEL_OK")

# --- 3. откат удаляет собранную папку ---
undo = section.core().undo(action_id)
assert "Удалил пакет" in undo.text, undo.text
assert not folders[0].exists() and OUT.is_dir()
print("EXPORT_UNDO_OK")

# --- 4. без папки (из чата) пакет остаётся в проекте ---
pubs.QFileDialog.getExistingDirectory = real_dialog
reply = section.core().run_tool("export_package")
assert "Собрал пакет в" in reply.text and "(позиций: 2)" in reply.text, reply.text
assert (Path(dm.data_dir) / "exports").is_dir()
print("EXPORT_DEFAULT_DIR_OK")

print("STEP10_OK")
