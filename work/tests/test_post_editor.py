"""Ручная правка поста: диалог, лимит подписи, сохранение, создание позиции."""
import os, sys, tempfile
from pathlib import Path

APP = Path(__file__).resolve().parents[2] / "AI_SMM_Work_Architecture_A75"
sys.path.insert(0, str(APP))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication, QDialog, QInputDialog, QMessageBox

app = QApplication([])

from ai_core import AICore, CAPTION_LIMIT
from data_manager import DataManager
from gui_sections.content_plan_section import (ContentPlanSection, MediaPickerDialog,
                                              media_icon)


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

# --- удалённый раздел стратегии не теряет связь ---
dm._data["content_plan"][0]["strategy_link"] = "s1"
dm.save()
dm._data["strategy"]["sections"] = []
dm.save()

dangling = sec._make_dialog("cp_1")
ok("удалённый раздел виден в списке",
   dangling.dangling_strategy and dangling.strategy.currentData() == "s1",
   (dangling.dangling_strategy, dangling.strategy.currentText()))
ok("values сохраняет связь", dangling.values()["strategy_link"] == "s1",
   dangling.values())
sec._save_dialog("cp_1", dangling)
ok("сохранение не стёрло связь",
   dm.get_content_plan_item("cp_1").get("strategy_link") == "s1",
   dm.get_content_plan_item("cp_1"))
ok("статус предупредил о разделе", "раздел удалён" in sec.status.text(), sec.status.text())

# --- медиа привязывается к позиции плана ---
pic = tmp / "p1.png"
QImage(80, 60, QImage.Format_RGB32).save(str(pic))
missing = tmp / "gone.mp4"
dm._data["media_ready"].extend([
    {"id": "me_1", "name": "p1.png", "type": "image", "path": str(pic),
     "status": "approved"},
    {"id": "me_2", "name": "gone.mp4", "type": "video", "path": str(missing),
     "status": "approved"}])
dm.save()

post = sec._make_dialog("cp_1")
ok("сначала медиа нет", post.values()["media_ids"] == [], post.values())
ok("миниатюра фото рисуется", not media_icon(dm.get_media_ready()[0]).isNull())
ok("нет файла — пустая иконка, без падения", media_icon(dm.get_media_ready()[1]).isNull())

picker = MediaPickerDialog(dm.get_media_ready(), [], None)
ok("в выборе видны все материалы", picker.list.count() == 2, picker.list.count())
picker.list.item(0).setCheckState(Qt.Checked)
ok("выбор отдаёт отмеченное", picker.chosen() == ["me_1"], picker.chosen())

post._apply_media(picker.chosen())
ok("миниатюра появилась в посте",
   post.media_row.count() >= 1 and post.media_count.text().startswith("1"),
   (post.media_row.count(), post.media_count.text()))
ok("values отдаёт медиа", post.values()["media_ids"] == ["me_1"], post.values())
sec._save_dialog("cp_1", post)
ok("медиа сохранено в позиции",
   dm.get_content_plan_item("cp_1").get("media_ids") == ["me_1"],
   dm.get_content_plan_item("cp_1"))

reopened = sec._make_dialog("cp_1")
ok("прикреплённое видно при повторном открытии",
   reopened.values()["media_ids"] == ["me_1"]
   and reopened.media_count.text().startswith("1"), reopened.values())
reopened._remove_media("me_1")
ok("миниатюра убирается", reopened.values()["media_ids"] == [], reopened.values())

print("POST_EDITOR_OK")
