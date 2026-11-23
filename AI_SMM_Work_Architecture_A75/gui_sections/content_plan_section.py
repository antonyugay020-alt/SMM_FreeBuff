"""Content plan: editable table, filters, links to strategy and shooting tasks."""
from typing import Any, Dict, List

from typing import Callable, Optional

from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QComboBox, QInputDialog, QMessageBox, QDialog, QDialogButtonBox, QFormLayout,
    QLineEdit, QTextEdit, QApplication, QListWidget, QListWidgetItem, QToolButton)
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QIcon

from ai_core import CAPTION_LIMIT, NO_DATE, collect_plan_issues, review_badge
from gui_sections.section_base import DataSection
from gui_theme import TEXT, MUTED, TEAL

RUBRICS = ["Польза", "Развлечение", "Продажа", "Личное"]
FORMATS = ["Пост", "Reels", "Stories", "Карусель", "Видео"]
STATUSES = ["Черновик", "Запланировано", "В работе", "Одобрено", "Опубликовано"]
COLUMNS = ["Дата", "Рубрика", "Тема", "Формат", "Статус", "Ответственный", "Стратегия",
           "ТЗ", "Подпись"]


def media_icon(record: Dict[str, Any], size: int = 72) -> QIcon:
    """Миниатюра материала: фото или кадр видео; нет кадра — пустая иконка."""
    try:
        from gui_sections.publications_section import _pixmap_for
        pixmap = _pixmap_for(record)
    except Exception:
        pixmap = None
    if pixmap is None or pixmap.isNull():
        return QIcon()
    return QIcon(pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation))


class MediaPickerDialog(QDialog):
    """Выбор готовых фото и видео для поста."""

    def __init__(self, media: List[Dict[str, Any]], selected: List[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Медиа поста")
        self.setMinimumSize(560, 420)
        layout = QVBoxLayout(self)
        hint = QLabel("Отметьте материалы, которые идут с постом:")
        hint.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
        layout.addWidget(hint)
        self.list = QListWidget()
        self.list.setViewMode(QListWidget.IconMode)
        self.list.setIconSize(QSize(96, 96))
        self.list.setResizeMode(QListWidget.Adjust)
        self.list.setMovement(QListWidget.Static)
        for record in media:
            name = str(record.get("name") or record.get("id") or "материал")
            entry = QListWidgetItem(media_icon(record, 96),
                                    f"{name}\n{record.get('type') or ''}".strip())
            entry.setData(Qt.UserRole, str(record.get("id") or ""))
            entry.setFlags(entry.flags() | Qt.ItemIsUserCheckable)
            entry.setCheckState(Qt.Checked if str(record.get("id")) in selected
                                else Qt.Unchecked)
            self.list.addItem(entry)
        layout.addWidget(self.list, stretch=1)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Применить")
        buttons.button(QDialogButtonBox.Cancel).setText("Отмена")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def chosen(self) -> List[str]:
        result = []
        for row in range(self.list.count()):
            entry = self.list.item(row)
            if entry.checkState() == Qt.Checked:
                result.append(str(entry.data(Qt.UserRole) or ""))
        return [item_id for item_id in result if item_id]


class PostDialog(QDialog):
    """Ручная правка одного поста: поля плана, текст подписи и медиа."""

    def __init__(self, item: Dict[str, Any], strategies: List[Dict[str, Any]],
                 generate: Optional[Callable[[], str]] = None,
                 media: Optional[List[Dict[str, Any]]] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Пост")
        self.setMinimumWidth(600)
        self._generate = generate
        self._media_all = list(media or [])
        self._media_ids = [str(one) for one in (item.get("media_ids") or [])]
        self.dangling_strategy = False
        self._build_ui(item, strategies)

    @staticmethod
    def _select(combo: QComboBox, value: Any) -> None:
        index = combo.findText(str(value or ""))
        combo.setCurrentIndex(index if index >= 0 else 0)

    def _build_ui(self, item: Dict[str, Any], strategies: List[Dict[str, Any]]) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.date = QLineEdit(str(item.get("date") or ""))
        self.date.setObjectName("formInput")
        self.date.setPlaceholderText("ДД.ММ.ГГГГ")
        form.addRow("Дата", self.date)

        self.rubric = QComboBox()
        self.rubric.setObjectName("formInput")
        self.rubric.addItems(RUBRICS)
        self._select(self.rubric, item.get("rubric"))
        form.addRow("Рубрика", self.rubric)

        self.topic = QLineEdit(str(item.get("topic") or ""))
        self.topic.setObjectName("formInput")
        self.topic.setPlaceholderText("О чём пост")
        form.addRow("Тема", self.topic)

        self.format = QComboBox()
        self.format.setObjectName("formInput")
        self.format.addItems(FORMATS)
        self._select(self.format, item.get("format"))
        form.addRow("Формат", self.format)

        self.status = QComboBox()
        self.status.setObjectName("formInput")
        self.status.addItems(STATUSES)
        self._select(self.status, item.get("status"))
        form.addRow("Статус", self.status)

        self.responsible = QLineEdit(str(item.get("responsible") or ""))
        self.responsible.setObjectName("formInput")
        form.addRow("Ответственный", self.responsible)

        self.strategy = QComboBox()
        self.strategy.setObjectName("formInput")
        self.strategy.addItem("—", "")
        for section in strategies:
            self.strategy.addItem(str(section.get("title") or section.get("id")),
                                  str(section.get("id") or ""))
        current = str(item.get("strategy_link") or "")
        index = self.strategy.findData(current)
        if current and index < 0:
            # раздел удалён — связь не теряем, показываем её отдельным пунктом
            self.strategy.addItem(f"{current} — раздел удалён", current)
            index = self.strategy.count() - 1
            self.dangling_strategy = True
        self.strategy.setCurrentIndex(max(index, 0))
        form.addRow("Стратегия", self.strategy)
        layout.addLayout(form)
        if self.dangling_strategy:
            warning = QLabel(f"Раздел стратегии «{current}» удалён: связь сохранена. "
                             "Выберите другой раздел или пункт «—», чтобы отвязать пост.")
            warning.setWordWrap(True)
            warning.setStyleSheet("color: #f87171; font-size: 11px;")
            layout.addWidget(warning)

        media_head = QHBoxLayout()
        media_title = QLabel("Медиа")
        media_title.setStyleSheet(f"color: {TEXT}; font-weight: 700;")
        media_head.addWidget(media_title)
        self.media_count = QLabel("")
        self.media_count.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
        media_head.addWidget(self.media_count)
        media_head.addStretch()
        pick_btn = QPushButton("Прикрепить…")
        pick_btn.setObjectName("topBtn")
        pick_btn.clicked.connect(self._on_pick_media)
        media_head.addWidget(pick_btn)
        layout.addLayout(media_head)
        self.media_hint = QLabel("Нажмите на миниатюру, чтобы убрать материал")
        self.media_hint.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
        layout.addWidget(self.media_hint)
        self.media_row = QHBoxLayout()
        layout.addLayout(self.media_row)
        self._render_media()

        head = QHBoxLayout()
        title = QLabel("Подпись")
        title.setStyleSheet(f"color: {TEXT}; font-weight: 700;")
        head.addWidget(title)
        self.counter = QLabel("")
        self.counter.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
        head.addWidget(self.counter)
        head.addStretch()
        self.generate_btn = QPushButton("🤖 Сгенерировать")
        self.generate_btn.setObjectName("topBtn")
        self.generate_btn.setEnabled(self._generate is not None)
        self.generate_btn.clicked.connect(self._on_generate)
        head.addWidget(self.generate_btn)
        copy_btn = QPushButton("Копировать")
        copy_btn.setObjectName("topBtn")
        copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(
            self.caption.toPlainText()))
        head.addWidget(copy_btn)
        layout.addLayout(head)

        self.caption = QTextEdit()
        self.caption.setObjectName("formInput")
        self.caption.setAcceptRichText(False)
        self.caption.setFixedHeight(190)
        self.caption.setPlainText(str(item.get("caption") or ""))
        self.caption.textChanged.connect(self._update_counter)
        layout.addWidget(self.caption)
        self._caption_saved = str(item.get("caption") or "")
        verdict = item.get("caption_review")
        self._review_verdict = verdict if isinstance(verdict, dict) else {}
        self.review = QLabel("")
        self.review.setWordWrap(True)
        layout.addWidget(self.review)
        self.caption.textChanged.connect(self._update_review)
        self._update_counter()
        self._update_review()

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText("Сохранить")
        buttons.button(QDialogButtonBox.Cancel).setText("Отмена")
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # --- медиа поста ---
    def _media_record(self, media_id: str) -> Optional[Dict[str, Any]]:
        return next((record for record in self._media_all
                     if str(record.get("id")) == media_id), None)

    def _apply_media(self, media_ids: List[str]) -> None:
        self._media_ids = [str(one) for one in media_ids if str(one)]
        self._render_media()

    def _remove_media(self, media_id: str) -> None:
        self._apply_media([one for one in self._media_ids if one != media_id])

    def _on_pick_media(self) -> None:
        dialog = MediaPickerDialog(self._media_all, self._media_ids, self)
        if dialog.exec() == QDialog.Accepted:
            self._apply_media(dialog.chosen())

    def _render_media(self) -> None:
        while self.media_row.count():
            entry = self.media_row.takeAt(0)
            widget = entry.widget()
            if widget is not None:
                widget.deleteLater()
        for media_id in self._media_ids:
            record = self._media_record(media_id) or {}
            name = str(record.get("name") or media_id)
            button = QToolButton()
            button.setIcon(media_icon(record, 72))
            button.setIconSize(QSize(72, 72))
            button.setText(name if len(name) <= 14 else name[:12] + "…")
            button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            button.setToolTip(f"{name} — нажмите, чтобы убрать")
            button.clicked.connect(lambda _=False, mid=media_id: self._remove_media(mid))
            self.media_row.addWidget(button)
        self.media_row.addStretch()
        count = len(self._media_ids)
        self.media_count.setText(f"{count} шт." if count else "нет материалов")
        self.media_hint.setVisible(bool(count))

    def _update_counter(self) -> None:
        length = len(self.caption.toPlainText())
        color = "#f87171" if length > CAPTION_LIMIT else MUTED
        self.counter.setText(f"{length}/{CAPTION_LIMIT}")
        self.counter.setStyleSheet(f"color: {color}; font-size: 11px;")

    def _update_review(self) -> None:
        """Вердикт редактора в карточке: одобрил/переписал, а после правки — что он устарел."""
        if not self._review_verdict:
            self.review.setText("")
            self.review.setVisible(False)
            return
        if self.caption.toPlainText().strip() != self._caption_saved.strip():
            self.review.setText("Редактор: подпись изменена после проверки — вердикт устарел")
            self.review.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
        else:
            self.review.setText(review_badge({"caption_review": self._review_verdict}))
            self.review.setStyleSheet(f"color: {TEAL}; font-size: 11px;")
        self.review.setVisible(True)

    def _on_generate(self) -> None:
        if self._generate is None:
            return
        text = self._generate()
        if text:
            self.caption.setPlainText(text)

    def _on_save(self) -> None:
        length = len(self.caption.toPlainText().strip())
        if length > CAPTION_LIMIT:
            QMessageBox.warning(self, "Подпись",
                                f"Подпись длиннее {CAPTION_LIMIT} символов: {length}. "
                                "Сократите текст.")
            return
        self.accept()

    def values(self) -> Dict[str, Any]:
        """Поля для `edit_record`: только изменяемые ключи плана."""
        return {"date": self.date.text().strip(),
                "rubric": self.rubric.currentText().strip(),
                "topic": self.topic.text().strip(),
                "format": self.format.currentText().strip(),
                "status": self.status.currentText().strip(),
                "responsible": self.responsible.text().strip(),
                "strategy_link": str(self.strategy.currentData() or "").strip(),
                "media_ids": list(self._media_ids),
                "caption": self.caption.toPlainText().strip()}


class ContentPlanSection(DataSection):
    """Рабочий контент-план: правка, добавление, связь со стратегией и ТЗ."""

    def __init__(self, data_manager, settings=None, parent=None):
        super().__init__(data_manager, settings, parent)
        self._loading = False
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(400)
        self._save_timer.timeout.connect(self._flush_pending)
        self._pending: Dict[str, Dict[str, Any]] = {}
        self._build_ui()
        self.refresh()

    # --- ui ---
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame()
        header.setObjectName("zoneHeader")
        head = QHBoxLayout(header)
        head.setContentsMargins(16, 12, 16, 12)
        title = QLabel("📝 Контент-план")
        title.setStyleSheet(f"color: {TEXT}; font-size: 16px; font-weight: 700;")
        head.addWidget(title)
        self.count_label = QLabel("")
        self.count_label.setStyleSheet(f"color: {MUTED}; font-size: 11px; padding-left: 10px;")
        head.addWidget(self.count_label)
        head.addStretch()
        for text, handler in (("＋ Позиция", self._on_add),
                              ("🤖 План на неделю", self._on_ai_plan),
                              ("📅 В календарь", self._on_sync)):
            btn = QPushButton(text)
            btn.setObjectName("topBtn")
            if "AI" in text or "🤖" in text:
                btn.setProperty("class", "primary")
            btn.clicked.connect(handler)
            head.addWidget(btn)
        layout.addWidget(header)

        filters = QHBoxLayout()
        filters.setContentsMargins(16, 10, 16, 6)
        self.rubric_filter = QComboBox()
        self.rubric_filter.setObjectName("formInput")
        self.rubric_filter.addItem("Все рубрики")
        self.rubric_filter.addItems(RUBRICS)
        self.rubric_filter.currentIndexChanged.connect(self.refresh)
        filters.addWidget(self.rubric_filter)

        self.status_filter = QComboBox()
        self.status_filter.setObjectName("formInput")
        self.status_filter.addItem("Все статусы")
        self.status_filter.addItems(STATUSES)
        self.status_filter.currentIndexChanged.connect(self.refresh)
        filters.addWidget(self.status_filter)
        filters.addStretch()
        self.status = QLabel("")
        self.status.setStyleSheet(f"color: {TEAL}; font-size: 11px;")
        filters.addWidget(self.status)
        layout.addLayout(filters)

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setObjectName("calendar")
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.itemChanged.connect(self._on_item_changed)
        self.table.setStyleSheet(
            "QTableWidget::item:selected { background-color: rgba(45,212,191,0.18);"
            " color: #e6edf3; }")
        layout.addWidget(self.table, stretch=1)

        bottom = QHBoxLayout()
        bottom.setContentsMargins(16, 8, 16, 12)
        for text, handler in (("✎ Править", self._on_edit),
                              ("✓ Проверить", self._on_validate),
                              ("Создать ТЗ", self._on_create_task),
                              ("Подпись", self._on_caption),
                              ("Удалить", self._on_delete)):
            btn = QPushButton(text)
            btn.setObjectName("topBtn")
            btn.clicked.connect(handler)
            bottom.addWidget(btn)
        bottom.addStretch()
        layout.addLayout(bottom)

    # --- data ---
    def refresh(self):
        plan = self.dm.get_content_plan() if self.dm else []
        rubric = self.rubric_filter.currentText()
        status = self.status_filter.currentText()
        rows = [item for item in plan
                if (rubric in ("Все рубрики", "") or item.get("rubric") == rubric)
                and (status in ("Все статусы", "") or item.get("status") == status)]

        self._loading = True
        self.table.setRowCount(len(rows))
        strategy_map = {s.get("id"): s.get("title") for s in
                        (self.dm.get_strategy().get("sections", []) if self.dm else [])}
        for row, item in enumerate(rows):
            values = [str(item.get(key) or "") for key in
                      ("date", "rubric", "topic", "format", "status", "responsible")]
            values.append(strategy_map.get(item.get("strategy_link"), item.get("strategy_link") or ""))
            values.append(str(item.get("shooting_task_id") or ""))
            caption = str(item.get("caption") or "")
            values.append(caption if len(caption) <= 48 else caption[:46] + "…")
            for col, value in enumerate(values):
                cell = QTableWidgetItem(value)
                if col == 0:
                    cell.setData(Qt.UserRole, item.get("id"))
                if col in (7, 8):
                    cell.setFlags(cell.flags() & ~Qt.ItemIsEditable)
                if col == 8 and item.get("caption"):
                    cell.setToolTip(str(item.get("caption")))
                self.table.setItem(row, col, cell)
        self._loading = False

        total = len(plan)
        scheduled = sum(1 for i in plan if i.get("status") == "Запланировано")
        self.count_label.setText(f"{total} позиций · {scheduled} запланировано")
        self.count_label.setStyleSheet(f"color: {MUTED}; font-size: 11px; padding-left: 10px;")

    def _current_item_id(self) -> str:
        row = self.table.currentRow()
        if row < 0:
            return ""
        cell = self.table.item(row, 0)
        return str(cell.data(Qt.UserRole) or "") if cell else ""

    # --- editing ---
    def _on_item_changed(self, _cell):
        if self._loading:
            return
        row = _cell.row()
        id_cell = self.table.item(row, 0)
        item_id = str(id_cell.data(Qt.UserRole) or "") if id_cell else ""
        if not item_id:
            return
        keys = ("date", "rubric", "topic", "format", "status", "responsible")
        fields = {key: (self.table.item(row, col).text().strip()
                        if self.table.item(row, col) else "")
                  for col, key in enumerate(keys)}
        # «Стратегия» — заголовок блока; храним id, если блок найден
        title = self.table.item(row, 6).text().strip() if self.table.item(row, 6) else ""
        sections = (self.dm.get_strategy().get("sections", []) if self.dm else [])
        fields["strategy_link"] = next(
            (str(s.get("id")) for s in sections if s.get("title") == title), title)
        self._pending[item_id] = fields
        self._save_timer.start()

    def _flush_pending(self):
        for item_id, fields in list(self._pending.items()):
            self.update("content_plan", item_id, fields)
        self._pending.clear()
        self.refresh()

    def _on_add(self):
        date, ok = QInputDialog.getText(self, "Новая позиция", "Дата (ДД.ММ.ГГГГ):")
        if not ok or not date.strip():
            return
        before = {str(item.get("id")) for item in self._plan()}
        self.add("content_plan", {"date": date.strip(), "rubric": RUBRICS[0], "topic": "Новая тема",
                                  "format": "Пост", "status": "Черновик", "responsible": "SMM"})
        self.refresh()
        new_id = next((str(item.get("id")) for item in self._plan()
                       if str(item.get("id")) not in before), "")
        if new_id:
            self._open_dialog(new_id)

    # --- ручная правка поста ---
    def _plan(self) -> List[Dict[str, Any]]:
        return list(self.dm.get_content_plan()) if self.dm else []

    def _strategy_sections(self) -> List[Dict[str, Any]]:
        if not self.dm:
            return []
        return list((self.dm.get_strategy() or {}).get("sections") or [])

    def _generate_caption(self, item_id: str) -> Callable[[], str]:
        """Подпись от ИИ для диалога: пишем через журнал и возвращаем готовый текст."""
        def run() -> str:
            self.status.setText(self.run("write_captions", plan_id=item_id))
            item = self.dm.get_content_plan_item(item_id) if self.dm else None
            return str((item or {}).get("caption") or "")
        return run

    def _make_dialog(self, item_id: str) -> Optional[PostDialog]:
        item = self.dm.get_content_plan_item(item_id) if self.dm else None
        if not item:
            return None
        media = list(self.dm.get_media_ready()) if self.dm else []
        return PostDialog(item, self._strategy_sections(),
                          self._generate_caption(item_id), media, self)

    def _save_dialog(self, item_id: str, dialog: PostDialog) -> bool:
        """Сохранить поля из диалога и обновить таблицу."""
        values = dialog.values()
        text = self.update("content_plan", item_id, values)
        link = str(values.get("strategy_link") or "")
        if dialog.dangling_strategy and link:
            text = f"{text} · связь со стратегией {link} сохранена (раздел удалён)"
        self.status.setText(text)
        self.refresh()
        return True

    def _open_dialog(self, item_id: str) -> bool:
        dialog = self._make_dialog(item_id)
        if dialog is None:
            QMessageBox.information(self, "Пост", "Позиция не найдена — обновите план.")
            return False
        if dialog.exec() != QDialog.Accepted:
            return False
        return self._save_dialog(item_id, dialog)

    def _on_edit(self):
        item_id = self._current_item_id()
        if not item_id:
            QMessageBox.information(self, "Пост", "Выберите позицию плана.")
            return
        self._open_dialog(item_id)

    def _on_ai_plan(self):
        count, ok = QInputDialog.getInt(self, "План на неделю", "Сколько постов:", 7, 1, 30)
        if not ok:
            return
        text = self.run("create_content_plan", count=count, period_days=7,
                        rubrics=RUBRICS)
        self.status.setText(text)
        self.refresh()

    def _confirm_undated(self) -> bool:
        """Warn that positions without a date never reach the calendar; False = cancel."""
        if self.dm is None:
            return True
        undated = [issue for issue in collect_plan_issues(self.dm)[0]
                   if NO_DATE in issue["problems"]]
        if not undated:
            return True
        names = "\n".join(f"· {issue['topic']} ({issue['id']})" for issue in undated[:10])
        if len(undated) > 10:
            names += f"\n… и ещё {len(undated) - 10}"
        answer = QMessageBox.question(
            self, "Перед синхронизацией",
            f"Без даты {len(undated)} из {len(self.dm.get_content_plan())} позиций — "
            f"в календарь они не попадут:\n\n{names}\n\nПоставить в календарь остальные?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        if answer == QMessageBox.Yes:
            return True
        self.status.setText(f"Синхронизация отменена: позиций без даты — {len(undated)}")
        return False

    def _on_sync(self):
        if not self._confirm_undated():
            return
        self.status.setText(self.run("sync_plan_events"))
        self.refresh()

    def _on_validate(self):
        lines = [line for line in self.run_full("validate_plan").splitlines()
                 if not line.startswith("Журнал:")]
        if not lines:
            return
        self.status.setText(lines[0])
        if lines[0].startswith("Ошибка:") or lines[0] == "Нет проекта":
            return
        QMessageBox.information(self, "Проверка плана",
                                "\n".join(lines[1:]) or "Замечаний нет.")

    def _on_create_task(self):
        item_id = self._current_item_id()
        if not item_id:
            QMessageBox.information(self, "ТЗ", "Выберите позицию плана.")
            return
        self.status.setText(self.run("create_shooting_task", plan_id=item_id))
        self.refresh()

    def _on_caption(self):
        item_id = self._current_item_id()
        if not item_id:
            QMessageBox.information(self, "Подпись", "Выберите позицию плана.")
            return
        self.status.setText(self.run("write_captions", plan_id=item_id))
        self.refresh()

    def _on_delete(self):
        item_id = self._current_item_id()
        if not item_id:
            return
        if QMessageBox.question(self, "Удалить позицию", "Удалить выбранную позицию плана?",
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        self.status.setText(self.delete("content_plan", item_id))
        self.refresh()
