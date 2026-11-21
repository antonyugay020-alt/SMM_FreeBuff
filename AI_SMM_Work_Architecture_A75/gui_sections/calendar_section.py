"""Calendar section: Integrated with DataManager."""
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
