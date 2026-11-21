"""Content Plan section: Integrated with DataManager."""
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QMessageBox, QScrollArea, QProgressBar, QComboBox)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

logger = logging.getLogger(__name__)

RUBRICS = {
    "Польза": {"color": "#58a6ff", "target_percent": 40},
    "Развлечение": {"color": "#bc8cff", "target_percent": 30},
    "Продажа": {"color": "#3fb950", "target_percent": 20},
    "Личное": {"color": "#f85149", "target_percent": 10},
}

STATUS_COLORS = {
    "Одобрено": "#238636",
    "В работе": "#9e6a03",
    "Запланировано": "#58a6ff",
    "Черновик": "#8b949e",
}


class ContentPlanTable(QWidget):
    """Content plan table with integration buttons."""
    open_shooting_task = Signal(str)  # task_id
    open_strategy_section = Signal(str)  # section_id

    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.dm = data_manager
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("📝 Контент-план на ноябрь 2026")
        title.setStyleSheet("color: #e6edf3; font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        # Filters
        filters = QHBoxLayout()
        rubric_filter = QComboBox()
        rubric_filter.addItem("Все рубрики")
        for r in RUBRICS:
            rubric_filter.addItem(r)
        rubric_filter.setObjectName("filterCombo")
        rubric_filter.setFixedWidth(180)
        filters.addWidget(rubric_filter)

        status_filter = QComboBox()
        status_filter.addItem("Все статусы")
        for s in STATUS_COLORS:
            status_filter.addItem(s)
        status_filter.setObjectName("filterCombo")
        status_filter.setFixedWidth(180)
        filters.addWidget(status_filter)

        filters.addStretch()
        layout.addLayout(filters)

        # Table
        plan = self.dm.get_content_plan()
        table = QTableWidget()
        table.setObjectName("calendar")
        table.setColumnCount(8)
        table.setHorizontalHeaderLabels(["Дата", "Рубрика", "Тема", "Формат", "Статус", "Ответств.", "Стратегия", "Действия"])
        table.setRowCount(len(plan))
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.verticalHeader().setVisible(False)

        for row, item in enumerate(plan):
            for col, key in enumerate(["date", "rubric", "topic", "format", "status", "responsible"]):
                cell = QTableWidgetItem(item.get(key, ""))
                cell.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                if key == "status":
                    cell.setForeground(QColor(STATUS_COLORS.get(item.get(key, ""), "#8b949e")))
                table.setItem(row, col, cell)

            # Strategy link (clickable)
            strat_id = item.get("strategy_link", "")
            strat_section = self.dm.get_strategy_section_by_id(strat_id) if strat_id else None
            strat_text = strat_section["title"] if strat_section else "—"
            strat_cell = QTableWidgetItem(strat_text)
            strat_cell.setForeground(QColor("#58a6ff"))
            strat_cell.setData(Qt.UserRole, strat_id)
            table.setItem(row, 6, strat_cell)

            # Actions: create shooting task button
            task_id = item.get("shooting_task_id")
            if task_id:
                action_cell = QTableWidgetItem(f"✅ ТЗ: {task_id}")
                action_cell.setForeground(QColor("#238636"))
            else:
                action_cell = QTableWidgetItem("➕ Создать ТЗ")
                action_cell.setForeground(QColor("#bc8cff"))
            action_cell.setData(Qt.UserRole, item.get("id"))
            table.setItem(row, 7, action_cell)

        table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        table.setColumnWidth(0, 100)
        table.setColumnWidth(1, 110)
        table.setColumnWidth(2, 250)
        table.setColumnWidth(3, 90)
        table.setColumnWidth(4, 110)
        table.setColumnWidth(5, 100)
        table.setColumnWidth(6, 130)
        table.setColumnWidth(7, 130)
        table.setMinimumHeight(400)
        table.itemClicked.connect(self._on_item_clicked)

        layout.addWidget(table, stretch=1)

        # Summary
        summary = QHBoxLayout()
        total_label = QLabel(f"Всего публикаций: {len(plan)}")
        total_label.setStyleSheet("color: #e6edf3; font-size: 13px; font-weight: bold;")
        summary.addWidget(total_label)

        for rubric, config in RUBRICS.items():
            count = sum(1 for item in plan if item.get("rubric") == rubric)
            lbl = QLabel(f"{rubric}: {count}")
            lbl.setStyleSheet(f"color: {config['color']}; font-size: 12px;")
            summary.addWidget(lbl)

        summary.addStretch()
        layout.addLayout(summary)

    def _on_item_clicked(self, item):
        col = item.column()
        row = item.row()
        plan = self.dm.get_content_plan()
        cp_item = plan[row] if row < len(plan) else None
        if not cp_item:
            return

        if col == 6:  # Strategy link
            strat_id = item.data(Qt.UserRole)
            if strat_id:
                self.open_strategy_section.emit(strat_id)
        elif col == 7:  # Actions
            task_id = cp_item.get("shooting_task_id")
            if task_id:
                self.open_shooting_task.emit(task_id)
            else:
                # Create new shooting task
                new_task = self.dm.create_shooting_task_from_content_plan(cp_item["id"])
                if new_task:
                    QMessageBox.information(
                        self, "Задание создано",
                        f"Создано задание {new_task['id']} на {new_task['date']}\n"
                        f"Событие добавлено в календарь.\n\n"
                        f"Перейдите в раздел 'Задания на съемку' для редактирования."
                    )
                    self._refresh()

    def _refresh(self):
        """Reload table from DataManager."""
        while self.layout().count() > 3:
            item = self.layout().takeAt(3)
            if item.widget():
                item.widget().deleteLater()
        table = self.layout().itemAt(2).widget() if self.layout().count() > 2 else None
        if table:
            table.deleteLater()
        self._build_ui()


class ContentPlanCalendar(QWidget):
    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.dm = data_manager
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("📅 Календарь публикаций")
        title.setStyleSheet("color: #e6edf3; font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        placeholder = QLabel("📅 Календарный вид (в разработке — используйте режим 'Таблица')")
        placeholder.setAlignment(Qt.AlignCenter)
        placeholder.setStyleSheet("color: #8b949e; font-size: 14px; padding: 60px;")
        layout.addWidget(placeholder)


class RubricatorWidget(QWidget):
    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.dm = data_manager
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        title = QLabel("📊 Рубрикатор контента")
        title.setStyleSheet("color: #e6edf3; font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        plan = self.dm.get_content_plan()
        total = len(plan)

        for rubric, config in RUBRICS.items():
            actual_count = sum(1 for item in plan if item.get("rubric") == rubric)
            actual_percent = (actual_count / total * 100) if total > 0 else 0
            target_percent = config["target_percent"]

            frame = QFrame()
            frame.setStyleSheet("background-color: #161b22; border-radius: 6px; padding: 12px;")
            fl = QVBoxLayout(frame)

            header = QHBoxLayout()
            lbl = QLabel(rubric)
            lbl.setStyleSheet(f"color: {config['color']}; font-size: 14px; font-weight: bold;")
            header.addWidget(lbl)
            header.addStretch()
            pct = QLabel(f"{actual_percent:.0f}% / {target_percent}%")
            pct.setStyleSheet("color: #8b949e; font-size: 12px;")
            header.addWidget(pct)
            fl.addLayout(header)

            bar = QProgressBar()
            bar.setValue(int(actual_percent))
            bar.setStyleSheet(f"""
                QProgressBar {{ background-color: #21262d; border: none; border-radius: 4px; text-align: center; color: transparent; height: 8px; }}
                QProgressBar::chunk {{ background-color: {config['color']}; border-radius: 4px; }}
            """)
            fl.addWidget(bar)
            layout.addWidget(frame)

        layout.addStretch()


class ContentPlanSection(QWidget):
    """Content Plan section with DataManager integration."""

    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.dm = data_manager
        self.current_mode = "table"
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QFrame()
        header.setObjectName("zoneHeader")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(16, 12, 16, 12)

        title = QLabel("📝 Контент-план")
        title.setStyleSheet("color: #e6edf3; font-size: 18px; font-weight: bold;")
        hl.addWidget(title)
        hl.addStretch()

        self.mode_buttons = {}
        for text, mid in [("📊 Таблица", "table"), ("📅 Календарь", "calendar"), ("📈 Рубрикатор", "rubricator")]:
            btn = QPushButton(text)
            btn.setObjectName("topBtn")
            if mid == self.current_mode:
                btn.setProperty("class", "primary")
            btn.setStyleSheet("font-size: 12px; padding: 6px 12px;")
            btn.clicked.connect(lambda checked, m=mid: self._switch_mode(m))
            self.mode_buttons[mid] = btn
            hl.addWidget(btn)

        ai_btn = QPushButton("🤖 Создать план с AI")
        ai_btn.setObjectName("topBtn")
        ai_btn.setProperty("class", "primary")
        ai_btn.setStyleSheet("font-size: 13px; font-weight: bold; padding: 8px 16px; margin-left: 16px;")
        ai_btn.clicked.connect(lambda: QMessageBox.information(self, "AI", "В полной версии AI создаст план на основе стратегии."))
        hl.addWidget(ai_btn)

        layout.addWidget(header)

        self.content_area = QWidget()
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self._load_content()
        layout.addWidget(self.content_area, stretch=1)

    def _load_content(self):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if self.current_mode == "table":
            widget = ContentPlanTable(self.dm)
            widget.open_shooting_task.connect(self._on_open_task)
            widget.open_strategy_section.connect(self._on_open_strategy)
        elif self.current_mode == "calendar":
            widget = ContentPlanCalendar(self.dm)
        elif self.current_mode == "rubricator":
            widget = RubricatorWidget(self.dm)

        self.content_layout.addWidget(widget, stretch=1)

    def _switch_mode(self, mode):
        self.current_mode = mode
        for m, btn in self.mode_buttons.items():
            btn.setProperty("class", "primary" if m == mode else "")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self._load_content()

    def _on_open_task(self, task_id):
        """Signal to parent to open shooting task."""
        logger.info(f"ContentPlan: open shooting task {task_id}")
        # Store for parent to read
        self._pending_task = task_id

    def _on_open_strategy(self, section_id):
        """Signal to parent to open strategy section."""
        logger.info(f"ContentPlan: open strategy section {section_id}")
        self._pending_strategy = section_id
