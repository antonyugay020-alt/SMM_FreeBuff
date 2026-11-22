"""Ручная правка поста: диалог, лимит подписи, сохранение, создание позиции."""
import os, sys, tempfile
from pathlib import Path

APP = Path(__file__).resolve().parents[2] / "AI_SMM_Work_Architecture_A75"
sys.path.insert(0, str(APP))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QDialog, QInputDialog, QMessageBox

app = QApplication([])

from ai_core import AICore, CAPTION_LIMIT
from data_manager import DataManager
from gui_sections.content_plan_section import ContentPlanSection


def ok(name, cond, extra=""):
    print(("EDIT_OK " if cond else "EDIT_FAIL ") + name + ("" if cond else f" :: {extra}"))
    if not cond:
        raise SystemExit(1)


tmp = Path(tempfile.mkdtemp(prefix="post_editor_"))
dm = DataManager("post_editor", str(tmp / "proj"))
core = AICore(dm, None, app_db_path=str(tmp / "app.db"))
core.run_tool("add_record", section="content_plan",
              fields={"id": "cp_1", "date": "01.12.2026", "topic": "Пост про кофе",
                      "rubric": "Польза", "format": "Пост", "status": "Черновик",
                      "responsible": "SMM", "caption": "старая подпись"})
core.run_tool("create_strategy", brief="кофейня",
              sections=[{"id": "s1", "title": "Аудитория", "content": "Город 25–40."}])

sec = ContentPlanSection(dm, None)
sec._core = AICore(dm, None, app_db_path=str(tmp / "app.db"))

# --- диалог заполняется данными позиции ---
dialog = sec._make_dialog("cp_1")
ok("диалог открывается по позиции", dialog is not None)
ok("тема подставлена", dialog.topic.text() == "Пост про кофе", dialog.topic.text())
ok("подпись подставлена", dialog.caption.toPlainText() == "старая подпись",
   dialog.caption.toPlainText())
ok("статус и рубрика подставлены",
   dialog.status.currentText() == "Черновик" and dialog.rubric.currentText() == "Польза",
   (dialog.status.currentText(), dialog.rubric.currentText()))
ok("стратегия в списке", dialog.strategy.count() == 2, dialog.strategy.count())
ok("счётчик символов", dialog.counter.text() == f"{len('старая подпись')}/{CAPTION_LIMIT}",
   dialog.counter.text())

# --- ручная правка и сохранение ---
dialog.caption.setPlainText("Новая подпись\n#кофе #раф")
dialog.topic.setText("Пост про раф")
dialog.rubric.setCurrentText("Продажа")
values = dialog.values()
ok("values отдаёт правку",
   values["caption"].startswith("Новая подпись") and values["topic"] == "Пост про раф"
   and values["rubric"] == "Продажа", values)

sec._save_dialog("cp_1", dialog)
item = dm.get_content_plan_item("cp_1")
ok("правка сохранена",
   item["caption"].startswith("Новая подпись") and item["topic"] == "Пост про раф", item)
ok("журнал edit_record",
   any(entry["tool"] == "edit_record" for entry in sec._core.journal.list(5)),
   sec._core.journal.list(5))
ok("таблица показала новую тему", any(
    sec.table.item(row, 2) and sec.table.item(row, 2).text() == "Пост про раф"
    for row in range(sec.table.rowCount())))

# --- лимит подписи ---
warned = {}
QMessageBox.warning = staticmethod(lambda parent, title, text: warned.update(t=text))
long_dialog = sec._make_dialog("cp_1")
long_dialog.caption.setPlainText("x" * (CAPTION_LIMIT + 1))
ok("счётчик краснеет за лимитом",
   long_dialog.counter.text() == f"{CAPTION_LIMIT + 1}/{CAPTION_LIMIT}"
   and "f87171" in long_dialog.counter.styleSheet(), long_dialog.counter.styleSheet())
long_dialog._on_save()
ok("за лимитом не сохраняет",
   long_dialog.result() != QDialog.Accepted and str(CAPTION_LIMIT) in warned.get("t", ""),
   warned)

# --- генерация подписи из диалога ---
gen_dialog = sec._make_dialog("cp_1")
original_run = sec.run
sec.run = lambda tool, **kwargs: (
    dm._data["content_plan"][0].update({"caption": "Подпись от ИИ"}), "Подпись готова")[1]
gen_dialog._on_generate()
ok("кнопка ИИ заполняет подпись", gen_dialog.caption.toPlainText() == "Подпись от ИИ",
   gen_dialog.caption.toPlainText())
sec.run = original_run

# --- создание позиции сразу открывает редактор ---
opened = []
QInputDialog.getText = staticmethod(lambda *args, **kwargs: ("05.12.2026", True))
sec._open_dialog = lambda item_id: opened.append(item_id) or True
sec._on_add()
ok("новая позиция открывается в редакторе",
   len(opened) == 1 and dm.get_content_plan_item(opened[0]) is not None, opened)

print("POST_EDITOR_OK")
