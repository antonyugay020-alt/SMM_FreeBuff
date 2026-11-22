"""Shooting tasks: ТЗ из позиции плана, статусы и связи."""
import logging
from typing import Any, Dict, List

from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QComboBox, QMessageBox)
from PySide6.QtCore import Qt, QTimer

from gui_sections.section_base import DataSection
from gui_theme import TEXT, MUTED, TEAL

logger = logging.getLogger(__name__)

STATUSES = ["Черновик", "Согласовано", "Снято", "Монтаж", "Готово", "Отменено"]
PRIORITIES = ["Низкий", "Средний", "Высокий"]
COLUMNS = ["Дата", "Время", "Локация", "Тип", "Статус", "Приоритет", "Кадров", "Позиция плана"]


class ShootingTasksSection(DataSection):
    """Список ТЗ: правка, смена статуса, создание из позиции плана."""

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

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame()
        header.setObjectName("zoneHeader")
        head = QHBoxLayout(header)
        head.setContentsMargins(16, 12, 16, 12)
        title = QLabel("🎬 Задания на съёмку")
        title.setStyleSheet(f"color: {TEXT}; font-size: 16px; font-weight: 700;")
        head.addWidget(title)
        head.addStretch()

        self.plan_combo = QComboBox()
        self.plan_combo.setObjectName("formInput")
        head.addWidget(self.plan_combo)

        make_btn = QPushButton("＋ ТЗ из позиции")
        make_btn.setObjectName("topBtn")
        make_btn.setProperty("class", "primary")
        make_btn.clicked.connect(self._on_create)
        head.addWidget(make_btn)

        delete_btn = QPushButton("Удалить")
        delete_btn.setObjectName("topBtn")
        delete_btn.clicked.connect(self._on_delete)
        head.addWidget(delete_btn)
        layout.addWidget(header)

        info = QHBoxLayout()
        info.setContentsMargins(16, 8, 16, 6)
        self.count_label = QLabel("")
        self.count_label.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
        info.addWidget(self.count_label)
        info.addStretch()
        self.status = QLabel("")
        self.status.setStyleSheet(f"color: {TEAL}; font-size: 11px;")
        info.addWidget(self.status)
        layout.addLayout(info)

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setObjectName("calendar")
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.itemChanged.connect(self._on_item_changed)
        self.table.setStyleSheet(
            "QTableWidget::item:selected { background-color: rgba(45,212,191,0.18);"
            " color: #e6edf3; }")
        layout.addWidget(self.table, stretch=1)

    # --- data ---
    def refresh(self):
        tasks = self.dm.get_shooting_tasks() if self.dm else []
        plan = self.dm.get_content_plan() if self.dm else []
        plan_titles = {item.get("id"): (item.get("topic") or item.get("id")) for item in plan}

        self._loading = True
        self.table.setRowCount(len(tasks))
        for row, task in enumerate(tasks):
            values = [str(task.get(key) or "") for key in
                      ("date", "time", "location", "type", "status", "priority")]
            values.append(str(len(task.get("shots") or [])))
            values.append(str(plan_titles.get(task.get("content_plan_link"),
                                             task.get("content_plan_link") or "")))
            for col, value in enumerate(values):
                cell = QTableWidgetItem(value)
                if col == 0:
                    cell.setData(Qt.UserRole, task.get("id"))
                if col in (6, 7):
                    cell.setFlags(cell.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row, col, cell)
        self._loading = False

        self.plan_combo.clear()
        free_items = [item for item in plan if not item.get("shooting_task_id")]
        for item in free_items:
            self.plan_combo.addItem(f"{item.get('date') or '—'} · {item.get('topic') or 'без темы'}",
                                    item.get("id"))
        if not free_items:
            self.plan_combo.addItem("Все позиции уже с ТЗ", None)
        self.count_label.setText(f"{len(tasks)} ТЗ · {len(plan)} позиций плана · "
                                 f"{len(free_items)} без ТЗ")

    def _current_task_id(self) -> str:
        row = self.table.currentRow()
        if row < 0:
            return ""
        cell = self.table.item(row, 0)
        return str(cell.data(Qt.UserRole) or "") if cell else ""

    # --- editing ---
    def _on_item_changed(self, cell):
        if self._loading:
            return
        row = cell.row()
        id_cell = self.table.item(row, 0)
        task_id = str(id_cell.data(Qt.UserRole) or "") if id_cell else ""
        if not task_id:
            return
        keys = ("date", "time", "location", "type", "status", "priority")
        fields = {key: (self.table.item(row, col).text().strip()
                        if self.table.item(row, col) else "")
                  for col, key in enumerate(keys)}
        self._pending[task_id] = fields
        self._save_timer.start()

    def _flush_pending(self):
        for task_id, fields in list(self._pending.items()):
            self.update("shooting_tasks", task_id, fields)
        self._pending.clear()
        self.refresh()

    def _on_create(self):
        plan_id = self.plan_combo.currentData()
        if not plan_id:
            QMessageBox.information(self, "ТЗ", "Сначала добавьте позицию в контент-план.")
            return
        self.status.setText(self.run("create_shooting_task", plan_id=plan_id))
        self.refresh()

    def _on_delete(self):
        task_id = self._current_task_id()
        if not task_id:
            return
        if QMessageBox.question(self, "Удалить ТЗ", "Удалить выбранное задание на съёмку?",
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return
        self.status.setText(self.delete("shooting_tasks", task_id))
        self.refresh()
