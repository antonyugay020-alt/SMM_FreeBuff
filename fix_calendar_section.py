#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix: Create Calendar section with month/week/day/list views.
Run: python fix_calendar_section.py
"""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

def write(rel, content):
    p = BASE / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding='utf-8', newline='\n')
    print(f"  [OK] {rel}")

print("\n=== Creating Calendar Section ===\n")

calendar = r'''"""Calendar section: Full event planning with multiple views."""
import logging
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime, timedelta

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QGridLayout, QAbstractItemView,
    QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView, QSplitter,
    QComboBox, QListWidget, QListWidgetItem, QTimeEdit, QDateEdit)
from PySide6.QtCore import Qt, QDate, QTime
from PySide6.QtGui import QColor, QBrush

logger = logging.getLogger(__name__)

# Event types with colors and icons
EVENT_TYPES = {
    "publication": {"icon": "📢", "color": "#58a6ff", "label": "Публикация"},
    "shooting": {"icon": "🎬", "color": "#bc8cff", "label": "Съёмка"},
    "meeting": {"icon": "📅", "color": "#f85149", "label": "Встреча"},
    "brand_event": {"icon": "🎉", "color": "#3fb950", "label": "Событие бренда"},
}

# Demo events for November 2026
DEMO_EVENTS = [
    {"date": "15.11.2026", "time": "10:00", "type": "publication", "title": "Пост: 5 упражнений для запястья", "description": "Публикация в Instagram", "link": "content_plan_001"},
    {"date": "15.11.2026", "time": "14:00", "type": "shooting", "title": "Съёмка тренировки группы 6-8 лет", "description": "Фото и видео для Stories", "link": "shooting_task_003"},
    {"date": "16.11.2026", "time": "12:00", "type": "meeting", "title": "Встреча с тренером Мариной", "description": "Обсуждение плана на декабрь", "link": None},
    {"date": "17.11.2026", "time": "09:00", "type": "publication", "title": "Stories: Акция первое занятие бесплатно", "description": "Серия из 3 stories", "link": "content_plan_003"},
    {"date": "18.11.2026", "time": "16:00", "type": "brand_event", "title": "Турнир среди юниоров", "description": "Ежемесячный турнир клуба", "link": None},
    {"date": "19.11.2026", "time": "11:00", "type": "publication", "title": "Reels: Как выбрать ракетку новичку", "description": "Видео-совет от тренера", "link": "content_plan_005"},
    {"date": "20.11.2026", "time": "15:00", "type": "shooting", "title": "Съёмка закулисья турнира", "description": "Фотоотчёт для ленты", "link": "shooting_task_005"},
    {"date": "21.11.2026", "time": "10:00", "type": "publication", "title": "Пост: Открытие новой группы 6-8 лет", "description": "Анонс новой группы", "link": "content_plan_007"},
    {"date": "22.11.2026", "time": "12:00", "type": "meeting", "title": "Планёрка команды", "description": "Еженедельная встреча", "link": None},
    {"date": "25.11.2026", "time": "18:00", "type": "brand_event", "title": "День открытых дверей", "description": "Бесплатные пробные занятия", "link": None},
]


class EventCard(QFrame):
    """Single event card for list/day views."""
    def __init__(self, event: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.event = event
        event_type = EVENT_TYPES.get(event["type"], {"icon": "❓", "color": "#8b949e", "label": "Неизвестно"})

        self.setStyleSheet(f"""
            QFrame {{
                background-color: #161b22;
                border-left: 4px solid {event_type['color']};
                border-radius: 4px;
                padding: 8px;
            }}
            QFrame:hover {{
                background-color: #1c2333;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        # Header: icon + title + time
        header = QHBoxLayout()
        icon = QLabel(event_type["icon"])
        icon.setStyleSheet("font-size: 16px;")
        header.addWidget(icon)

        title = QLabel(event["title"])
        title.setStyleSheet("color: #e6edf3; font-size: 13px; font-weight: bold;")
        header.addWidget(title, stretch=1)

        time = QLabel(event["time"])
        time.setStyleSheet("color: #8b949e; font-size: 12px;")
        header.addWidget(time)

        layout.addLayout(header)

        # Description
        if event.get("description"):
            desc = QLabel(event["description"])
            desc.setStyleSheet("color: #8b949e; font-size: 11px;")
            desc.setWordWrap(True)
            layout.addWidget(desc)

        # Type label
        type_label = QLabel(event_type["label"])
        type_label.setStyleSheet(f"color: {event_type['color']}; font-size: 10px; font-weight: bold;")
        layout.addWidget(type_label)


class MonthView(QWidget):
    """Month view: grid with events."""
    event_clicked = Signal(dict)

    def __init__(self, events: List[Dict[str, Any]], year: int = 2026, month: int = 11, parent=None):
        super().__init__(parent)
        self.events = events
        self.year = year
        self.month = month
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header with month navigation
        header = QHBoxLayout()
        prev_btn = QPushButton("◀")
        prev_btn.setObjectName("topBtn")
        prev_btn.setStyleSheet("font-size: 16px; padding: 4px 12px;")
        header.addWidget(prev_btn)

        month_names = ["", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
                       "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
        month_label = QLabel(f"{month_names[self.month]} {self.year}")
        month_label.setStyleSheet("color: #e6edf3; font-size: 20px; font-weight: bold;")
        header.addWidget(month_label, stretch=1)

        next_btn = QPushButton("▶")
        next_btn.setObjectName("topBtn")
        next_btn.setStyleSheet("font-size: 16px; padding: 4px 12px;")
        header.addWidget(next_btn)

        header.addStretch()
        layout.addLayout(header)

        # Weekday headers
        weekdays = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        grid = QGridLayout()
        grid.setSpacing(4)

        for col, day_name in enumerate(weekdays):
            label = QLabel(day_name)
            label.setStyleSheet("color: #8b949e; font-size: 12px; font-weight: bold; padding: 8px;")
            label.setAlignment(Qt.AlignCenter)
            grid.addWidget(label, 0, col)

        # Calendar days
        first_day = QDate(self.year, self.month, 1)
        days_in_month = first_day.daysInMonth()
        start_weekday = first_day.dayOfWeek() - 1  # Monday = 0

        row = 1
        col = start_weekday
        for day in range(1, days_in_month + 1):
            day_cell = self._create_day_cell(day)
            grid.addWidget(day_cell, row, col)
            col += 1
            if col >= 7:
                col = 0
                row += 1

        layout.addLayout(grid, stretch=1)

    def _create_day_cell(self, day: int) -> QFrame:
        """Create a day cell with events."""
        cell = QFrame()
        cell.setStyleSheet("""
            QFrame {
                background-color: #0d1117;
                border: 1px solid #30363d;
                border-radius: 4px;
                min-height: 80px;
            }
            QFrame:hover {
                background-color: #161b22;
                border-color: #58a6ff;
            }
        """)

        cell_layout = QVBoxLayout(cell)
        cell_layout.setContentsMargins(4, 4, 4, 4)
        cell_layout.setSpacing(2)

        # Day number
        day_label = QLabel(str(day))
        day_label.setStyleSheet("color: #e6edf3; font-size: 12px; font-weight: bold;")
        cell_layout.addWidget(day_label)

        # Events for this day
        date_str = f"{day:02d}.{self.month:02d}.{self.year}"
        day_events = [e for e in self.events if e["date"] == date_str]

        for event in day_events[:3]:  # Show max 3 events
            event_type = EVENT_TYPES.get(event["type"], {"icon": "❓", "color": "#8b949e"})
            event_label = QLabel(f"{event_type['icon']} {event['time'][:5]}")
            event_label.setStyleSheet(f"color: {event_type['color']}; font-size: 10px; background-color: #21262d; border-radius: 2px; padding: 2px;")
            cell_layout.addWidget(event_label)

        if len(day_events) > 3:
            more_label = QLabel(f"+{len(day_events) - 3} ещё")
            more_label.setStyleSheet("color: #8b949e; font-size: 9px;")
            cell_layout.addWidget(more_label)

        cell_layout.addStretch()
        return cell


class WeekView(QWidget):
    """Week view: timeline by hours (simplified)."""
    def __init__(self, events: List[Dict[str, Any]], parent=None):
        super().__init__(parent)
        self.events = events
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("📅 Неделя 16-22 ноября 2026")
        title.setStyleSheet("color: #e6edf3; font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        # Simplified week view: days as columns
        days = ["Пн 16", "Вт 17", "Ср 18", "Чт 19", "Пт 20", "Сб 21", "Вс 22"]
        grid = QGridLayout()
        grid.setSpacing(8)

        # Header row
        for col, day_name in enumerate(days):
            label = QLabel(day_name)
            label.setStyleSheet("color: #e6edf3; font-size: 14px; font-weight: bold; padding: 8px; background-color: #161b22; border-radius: 4px;")
            label.setAlignment(Qt.AlignCenter)
            grid.addWidget(label, 0, col)

        # Events for each day
        for col, day_name in enumerate(days):
            day_num = 16 + col
            date_str = f"{day_num:02d}.11.2026"
            day_events = [e for e in self.events if e["date"] == date_str]

            day_column = QVBoxLayout()
            for event in day_events:
                card = EventCard(event)
                day_column.addWidget(card)

            day_widget = QWidget()
            day_widget.setLayout(day_column)
            grid.addWidget(day_widget, 1, col)

        layout.addLayout(grid, stretch=1)


class DayView(QWidget):
    """Day view: detailed hourly schedule."""
    def __init__(self, events: List[Dict[str, Any]], date: str = "15.11.2026", parent=None):
        super().__init__(parent)
        self.events = events
        self.date = date
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel(f"📅 {self.date}")
        title.setStyleSheet("color: #e6edf3; font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        # Hourly slots
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background-color: #0f1419;")

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(8)

        for hour in range(8, 21):  # 8:00 to 20:00
            slot = QFrame()
            slot.setStyleSheet("background-color: #161b22; border-radius: 4px; padding: 8px; min-height: 60px;")
            slot_layout = QHBoxLayout(slot)

            time_label = QLabel(f"{hour:02d}:00")
            time_label.setStyleSheet("color: #8b949e; font-size: 12px; min-width: 60px;")
            slot_layout.addWidget(time_label)

            # Find events for this hour
            hour_str = f"{hour:02d}:"
            hour_events = [e for e in self.events if e["date"] == self.date and e["time"].startswith(hour_str)]

            if hour_events:
                for event in hour_events:
                    card = EventCard(event)
                    slot_layout.addWidget(card, stretch=1)
            else:
                empty_label = QLabel("—")
                empty_label.setStyleSheet("color: #30363d; font-size: 12px;")
                slot_layout.addWidget(empty_label)

            content_layout.addWidget(slot)

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll, stretch=1)


class ListView(QWidget):
    """List view: chronological event list."""
    def __init__(self, events: List[Dict[str, Any]], parent=None):
        super().__init__(parent)
        self.events = events
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("📋 Список событий")
        title.setStyleSheet("color: #e6edf3; font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        # Filters
        filters = QHBoxLayout()
        type_filter = QComboBox()
        type_filter.addItem("Все типы")
        for type_id, type_info in EVENT_TYPES.items():
            type_filter.addItem(f"{type_info['icon']} {type_info['label']}")
        type_filter.setObjectName("filterCombo")
        type_filter.setFixedWidth(200)
        filters.addWidget(type_filter)

        filters.addStretch()
        layout.addLayout(filters)

        # Event list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background-color: #0f1419;")

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(12)

        # Group by date
        events_by_date = {}
        for event in self.events:
            date = event["date"]
            if date not in events_by_date:
                events_by_date[date] = []
            events_by_date[date].append(event)

        for date in sorted(events_by_date.keys()):
            date_label = QLabel(f"📅 {date}")
            date_label.setStyleSheet("color: #58a6ff; font-size: 14px; font-weight: bold; margin-top: 8px;")
            content_layout.addWidget(date_label)

            for event in events_by_date[date]:
                card = EventCard(event)
                content_layout.addWidget(card)

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll, stretch=1)


class CalendarSection(QWidget):
    """Calendar section with multiple views."""

    def __init__(self, app_state: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.state = app_state
        self.current_mode = "month"
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header with mode switcher
        header = QFrame()
        header.setObjectName("zoneHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 12, 16, 12)

        title = QLabel("📅 Календарь")
        title.setStyleSheet("color: #e6edf3; font-size: 18px; font-weight: bold;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Mode buttons
        self.mode_buttons = {}
        modes = [("📆 Месяц", "month"), ("📅 Неделя", "week"), ("📋 День", "day"), ("📄 Список", "list")]
        for text, mode_id in modes:
            btn = QPushButton(text)
            btn.setObjectName("topBtn")
            if mode_id == self.current_mode:
                btn.setProperty("class", "primary")
            btn.setStyleSheet("font-size: 12px; padding: 6px 12px;")
            btn.clicked.connect(lambda checked, m=mode_id: self._switch_mode(m))
            self.mode_buttons[mode_id] = btn
            header_layout.addWidget(btn)

        # Add event button
        add_btn = QPushButton("➕ Добавить событие")
        add_btn.setObjectName("topBtn")
        add_btn.setProperty("class", "primary")
        add_btn.setStyleSheet("font-size: 13px; font-weight: bold; padding: 8px 16px; margin-left: 16px;")
        add_btn.clicked.connect(self._on_add_event)
        header_layout.addWidget(add_btn)

        layout.addWidget(header)

        # Content area
        self.content_area = QWidget()
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)

        self._load_content()

        layout.addWidget(self.content_area, stretch=1)

    def _load_content(self):
        """Load content based on current mode."""
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if self.current_mode == "month":
            widget = MonthView(DEMO_EVENTS, 2026, 11)
        elif self.current_mode == "week":
            widget = WeekView(DEMO_EVENTS)
        elif self.current_mode == "day":
            widget = DayView(DEMO_EVENTS, "15.11.2026")
        elif self.current_mode == "list":
            widget = ListView(DEMO_EVENTS)

        self.content_layout.addWidget(widget, stretch=1)

    def _switch_mode(self, mode: str):
        """Switch view mode."""
        self.current_mode = mode
        for m, btn in self.mode_buttons.items():
            if m == mode:
                btn.setProperty("class", "primary")
            else:
                btn.setProperty("class", "")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self._load_content()

    def _on_add_event(self):
        """Add new event."""
        QMessageBox.information(
            self,
            "Добавить событие",
            "В полной версии откроется форма создания события:\n\n"
            "• Дата и время\n"
            "• Тип (публикация/съёмка/встреча/событие бренда)\n"
            "• Название и описание\n"
            "• Связь с контент-планом или заданием на съёмку"
        )
'''

write("gui_sections/calendar_section.py", calendar)

print("\n=== Calendar Section Created ===")
print("\nFeatures:")
print("  [OK] Month view: grid with event indicators")
print("  [OK] Week view: 7-day timeline")
print("  [OK] Day view: hourly schedule")
print("  [OK] List view: chronological with filters")
print("  [OK] 4 event types with color coding")
print("  [OK] Mode switcher in header")
print("  [OK] Add event button (placeholder)")
print("\nRun START.bat and click 'Календарь' in left panel.")