"""Content plan: editable table, filters, links to strategy and shooting tasks."""
from typing import Any, Dict, List

from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QComboBox, QInputDialog, QMessageBox)
from PySide6.QtCore import Qt, QTimer

from ai_core import NO_DATE, collect_plan_issues
from gui_sections.section_base import DataSection
from gui_theme import TEXT, MUTED, TEAL

RUBRICS = ["Польза", "Развлечение", "Продажа", "Личное"]
FORMATS = ["Пост", "Reels", "Stories", "Карусель", "Видео"]
STATUSES = ["Черновик", "Запланировано", "В работе", "Одобрено", "Опубликовано"]
COLUMNS = ["Дата", "Рубрика", "Тема", "Формат", "Статус", "Ответственный", "Стратегия",
           "ТЗ", "Подпись"]


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
        for text, handler in (("✓ Проверить", self._on_validate),
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
        self.add("content_plan", {"date": date.strip(), "rubric": RUBRICS[0], "topic": "Новая тема",
                                  "format": "Пост", "status": "Черновик", "responsible": "SMM"})
        self.refresh()

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
