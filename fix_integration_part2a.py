#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration Part 2a: Update Content Plan + Calendar to use DataManager.
- Content Plan: "Create shooting task" button per row + strategy link clickable
- Calendar: click shooting event → open shooting task
Run: python fix_integration_part2a.py
"""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

def write(rel, content):
    p = BASE / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding='utf-8', newline='\n')
    print(f"  [OK] {rel}")

print("\n=== Integration Part 2a: Content Plan + Calendar ===\n")

# 1. content_plan_section.py — with DataManager integration
print("[1/2] Updating content_plan_section.py...")

content_plan = r'''"""Content Plan section: Integrated with DataManager."""
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
'''

write("gui_sections/content_plan_section.py", content_plan)

# 2. calendar_section.py — with DataManager integration
print("[2/2] Updating calendar_section.py...")

calendar = r'''"""Calendar section: Integrated with DataManager."""
import logging
from pathlib import Path
from typing import Dict, Any, List

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QGridLayout, QScrollArea, QMessageBox, QComboBox)
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtGui import QColor

logger = logging.getLogger(__name__)

EVENT_TYPES = {
    "publication": {"icon": "📢", "color": "#58a6ff", "label": "Публикация"},
    "shooting": {"icon": "🎬", "color": "#bc8cff", "label": "Съёмка"},
    "meeting": {"icon": "📅", "color": "#f85149", "label": "Встреча"},
    "brand_event": {"icon": "🎉", "color": "#3fb950", "label": "Событие бренда"},
}


class EventCard(QFrame):
    def __init__(self, event: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.event = event
        et = EVENT_TYPES.get(event["type"], {"icon": "❓", "color": "#8b949e", "label": "?"})

        self.setStyleSheet(f"""
            QFrame {{ background-color: #161b22; border-left: 4px solid {et['color']}; border-radius: 4px; padding: 8px; }}
            QFrame:hover {{ background-color: #1c2333; }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        header = QHBoxLayout()
        icon = QLabel(et["icon"])
        icon.setStyleSheet("font-size: 16px;")
        header.addWidget(icon)

        title = QLabel(event["title"])
        title.setStyleSheet("color: #e6edf3; font-size: 13px; font-weight: bold;")
        header.addWidget(title, stretch=1)

        time = QLabel(event["time"])
        time.setStyleSheet("color: #8b949e; font-size: 12px;")
        header.addWidget(time)
        layout.addLayout(header)

        if event.get("description"):
            desc = QLabel(event["description"])
            desc.setStyleSheet("color: #8b949e; font-size: 11px;")
            desc.setWordWrap(True)
            layout.addWidget(desc)

        type_label = QLabel(et["label"])
        type_label.setStyleSheet(f"color: {et['color']}; font-size: 10px; font-weight: bold;")
        layout.addWidget(type_label)


class MonthView(QWidget):
    event_clicked = Signal(dict)

    def __init__(self, data_manager, year=2026, month=11, parent=None):
        super().__init__(parent)
        self.dm = data_manager
        self.year = year
        self.month = month
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header = QHBoxLayout()
        prev_btn = QPushButton("◀")
        prev_btn.setObjectName("topBtn")
        prev_btn.setStyleSheet("font-size: 16px; padding: 4px 12px;")
        header.addWidget(prev_btn)

        month_names = ["", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
                       "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
        lbl = QLabel(f"{month_names[self.month]} {self.year}")
        lbl.setStyleSheet("color: #e6edf3; font-size: 20px; font-weight: bold;")
        header.addWidget(lbl, stretch=1)

        next_btn = QPushButton("▶")
        next_btn.setObjectName("topBtn")
        next_btn.setStyleSheet("font-size: 16px; padding: 4px 12px;")
        header.addWidget(next_btn)
        header.addStretch()
        layout.addLayout(header)

        grid = QGridLayout()
        grid.setSpacing(4)

        for col, day_name in enumerate(["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]):
            lbl = QLabel(day_name)
            lbl.setStyleSheet("color: #8b949e; font-size: 12px; font-weight: bold; padding: 8px;")
            lbl.setAlignment(Qt.AlignCenter)
            grid.addWidget(lbl, 0, col)

        first_day = QDate(self.year, self.month, 1)
        days_in_month = first_day.daysInMonth()
        start_weekday = first_day.dayOfWeek() - 1

        row, col = 1, start_weekday
        for day in range(1, days_in_month + 1):
            cell = self._create_day_cell(day)
            grid.addWidget(cell, row, col)
            col += 1
            if col >= 7:
                col = 0
                row += 1

        layout.addLayout(grid, stretch=1)

    def _create_day_cell(self, day: int) -> QFrame:
        cell = QFrame()
        cell.setStyleSheet("""
            QFrame { background-color: #0d1117; border: 1px solid #30363d; border-radius: 4px; min-height: 80px; }
            QFrame:hover { background-color: #161b22; border-color: #58a6ff; }
        """)

        cl = QVBoxLayout(cell)
        cl.setContentsMargins(4, 4, 4, 4)
        cl.setSpacing(2)

        day_label = QLabel(str(day))
        day_label.setStyleSheet("color: #e6edf3; font-size: 12px; font-weight: bold;")
        cl.addWidget(day_label)

        date_str = f"{day:02d}.{self.month:02d}.{self.year}"
        events = [e for e in self.dm.get_calendar_events() if e["date"] == date_str]

        for event in events[:3]:
            et = EVENT_TYPES.get(event["type"], {"icon": "❓", "color": "#8b949e"})
            el = QLabel(f"{et['icon']} {event['time'][:5]}")
            el.setStyleSheet(f"color: {et['color']}; font-size: 10px; background-color: #21262d; border-radius: 2px; padding: 2px;")
            el.setCursor(Qt.PointingHandCursor)
            el.mousePressEvent = lambda ev, e=event: self._on_event_click(e)
            cl.addWidget(el)

        if len(events) > 3:
            more = QLabel(f"+{len(events) - 3} ещё")
            more.setStyleSheet("color: #8b949e; font-size: 9px;")
            cl.addWidget(more)

        cl.addStretch()
        return cell

    def _on_event_click(self, event):
        self.event_clicked.emit(event)


class WeekView(QWidget):
    event_clicked = Signal(dict)

    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.dm = data_manager
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("📅 Неделя 16-22 ноября 2026")
        title.setStyleSheet("color: #e6edf3; font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        days = ["Пн 16", "Вт 17", "Ср 18", "Чт 19", "Пт 20", "Сб 21", "Вс 22"]
        grid = QGridLayout()
        grid.setSpacing(8)

        for col, day_name in enumerate(days):
            lbl = QLabel(day_name)
            lbl.setStyleSheet("color: #e6edf3; font-size: 14px; font-weight: bold; padding: 8px; background-color: #161b22; border-radius: 4px;")
            lbl.setAlignment(Qt.AlignCenter)
            grid.addWidget(lbl, 0, col)

        for col, day_name in enumerate(days):
            day_num = 16 + col
            date_str = f"{day_num:02d}.11.2026"
            day_events = [e for e in self.dm.get_calendar_events() if e["date"] == date_str]

            day_column = QVBoxLayout()
            for event in day_events:
                card = EventCard(event)
                day_column.addWidget(card)

            day_widget = QWidget()
            day_widget.setLayout(day_column)
            grid.addWidget(day_widget, 1, col)

        layout.addLayout(grid, stretch=1)


class DayView(QWidget):
    def __init__(self, data_manager, date="15.11.2026", parent=None):
        super().__init__(parent)
        self.dm = data_manager
        self.date = date
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel(f"📅 {self.date}")
        title.setStyleSheet("color: #e6edf3; font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background-color: #0f1419;")

        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setSpacing(8)

        for hour in range(8, 21):
            slot = QFrame()
            slot.setStyleSheet("background-color: #161b22; border-radius: 4px; padding: 8px; min-height: 60px;")
            sl = QHBoxLayout(slot)

            time_label = QLabel(f"{hour:02d}:00")
            time_label.setStyleSheet("color: #8b949e; font-size: 12px; min-width: 60px;")
            sl.addWidget(time_label)

            hour_str = f"{hour:02d}:"
            hour_events = [e for e in self.dm.get_calendar_events()
                          if e["date"] == self.date and e["time"].startswith(hour_str)]

            if hour_events:
                for event in hour_events:
                    card = EventCard(event)
                    sl.addWidget(card, stretch=1)
            else:
                empty = QLabel("—")
                empty.setStyleSheet("color: #30363d; font-size: 12px;")
                sl.addWidget(empty)

            cl.addWidget(slot)

        cl.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll, stretch=1)


class ListView(QWidget):
    event_clicked = Signal(dict)

    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.dm = data_manager
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("📋 Список событий")
        title.setStyleSheet("color: #e6edf3; font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        filters = QHBoxLayout()
        type_filter = QComboBox()
        type_filter.addItem("Все типы")
        for tid, tinfo in EVENT_TYPES.items():
            type_filter.addItem(f"{tinfo['icon']} {tinfo['label']}")
        type_filter.setObjectName("filterCombo")
        type_filter.setFixedWidth(200)
        filters.addWidget(type_filter)
        filters.addStretch()
        layout.addLayout(filters)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background-color: #0f1419;")

        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setSpacing(12)

        events_by_date = {}
        for event in self.dm.get_calendar_events():
            d = event["date"]
            if d not in events_by_date:
                events_by_date[d] = []
            events_by_date[d].append(event)

        for date in sorted(events_by_date.keys()):
            dl = QLabel(f"📅 {date}")
            dl.setStyleSheet("color: #58a6ff; font-size: 14px; font-weight: bold; margin-top: 8px;")
            cl.addWidget(dl)

            for event in events_by_date[date]:
                card = EventCard(event)
                cl.addWidget(card)

        cl.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll, stretch=1)


class CalendarSection(QWidget):
    """Calendar section with DataManager integration."""

    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.dm = data_manager
        self.current_mode = "month"
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame()
        header.setObjectName("zoneHeader")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(16, 12, 16, 12)

        title = QLabel("📅 Календарь")
        title.setStyleSheet("color: #e6edf3; font-size: 18px; font-weight: bold;")
        hl.addWidget(title)
        hl.addStretch()

        self.mode_buttons = {}
        for text, mid in [("📆 Месяц", "month"), ("📅 Неделя", "week"), ("📋 День", "day"), ("📄 Список", "list")]:
            btn = QPushButton(text)
            btn.setObjectName("topBtn")
            if mid == self.current_mode:
                btn.setProperty("class", "primary")
            btn.setStyleSheet("font-size: 12px; padding: 6px 12px;")
            btn.clicked.connect(lambda checked, m=mid: self._switch_mode(m))
            self.mode_buttons[mid] = btn
            hl.addWidget(btn)

        add_btn = QPushButton("➕ Добавить событие")
        add_btn.setObjectName("topBtn")
        add_btn.setProperty("class", "primary")
        add_btn.setStyleSheet("font-size: 13px; font-weight: bold; padding: 8px 16px; margin-left: 16px;")
        add_btn.clicked.connect(lambda: QMessageBox.information(self, "Добавить", "В полной версии откроется форма создания события."))
        hl.addWidget(add_btn)

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

        if self.current_mode == "month":
            widget = MonthView(self.dm, 2026, 11)
            widget.event_clicked.connect(self._on_event_clicked)
        elif self.current_mode == "week":
            widget = WeekView(self.dm)
        elif self.current_mode == "day":
            widget = DayView(self.dm, "15.11.2026")
        elif self.current_mode == "list":
            widget = ListView(self.dm)

        self.content_layout.addWidget(widget, stretch=1)

    def _switch_mode(self, mode):
        self.current_mode = mode
        for m, btn in self.mode_buttons.items():
            btn.setProperty("class", "primary" if m == mode else "")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self._load_content()

    def _on_event_clicked(self, event):
        """Handle event click — open related task if shooting."""
        logger.info(f"Calendar: event clicked: {event}")
        if event.get("type") == "shooting" and event.get("link"):
            task = self.dm.get_shooting_task(event["link"])
            if task:
                QMessageBox.information(
                    self, "Связанное задание",
                    f"Событие связано с заданием {task['id']}:\n"
                    f"📅 {task['date']} в {task['time']}\n"
                    f"📍 {task['location']}\n"
                    f"👥 {task['team']}\n"
                    f"📊 Статус: {task['status']}\n\n"
                    f"Перейдите в раздел 'Задания на съемку' для полного ТЗ."
                )
            else:
                QMessageBox.information(self, "Событие", f"Съёмка: {event['title']}\nЗадание не найдено.")
        elif event.get("type") == "publication":
            QMessageBox.information(self, "Публикация", f"📢 {event['title']}\n🕐 {event['time']}")
        else:
            QMessageBox.information(self, "Событие", f"{event.get('icon', '')} {event['title']}\n{event.get('description', '')}")
'''

write("gui_sections/calendar_section.py", calendar)

print("\n=== Integration Part 2a Complete ===")
print("\nContent Plan changes:")
print("  [OK] Now uses DataManager for all data")
print("  [OK] Column 'Стратегия' shows linked strategy section (clickable)")
print("  [OK] Column 'Действия': '➕ Создать ТЗ' or '✅ ТЗ: st_XXX'")
print("  [OK] Click 'Создать ТЗ' → creates shooting task + calendar event")
print("  [OK] Click strategy link → emits signal to open strategy section")
print("\nCalendar changes:")
print("  [OK] Now uses DataManager for all data")
print("  [OK] Click shooting event → shows linked task info")
print("  [OK] Click publication event → shows publication info")
print("  [OK] All 4 views (month/week/day/list) use DataManager")
print("\nRun START.bat to test.")