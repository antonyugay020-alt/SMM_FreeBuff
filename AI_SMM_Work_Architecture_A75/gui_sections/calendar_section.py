"""Calendar: month grid with events from the plan, manual events and filters."""
import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGridLayout, QScrollArea, QComboBox, QDialog, QLineEdit,
    QTextEdit, QDialogButtonBox, QMessageBox)
from PySide6.QtCore import Qt

from gui_sections.section_base import DataSection
from gui_theme import TEXT, MUTED, TEAL

logger = logging.getLogger(__name__)

EVENT_TYPES = {
    "publication": ("📢", "Публикация", "#5aa9ff"),
    "shooting": ("🎬", "Съёмка", "#c08cff"),
    "meeting": ("📅", "Встреча", "#f87171"),
    "brand_event": ("🎉", "Событие бренда", "#3fb950"),
}
MONTHS = ["январь", "февраль", "март", "апрель", "май", "июнь", "июль",
          "август", "сентябрь", "октябрь", "ноябрь", "декабрь"]
WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


def _parse_date(value: str) -> Optional[date]:
    try:
        return datetime.strptime(str(value or "").strip(), "%d.%m.%Y").date()
    except ValueError:
        return None


class EventDialog(QDialog):
    """Create/edit one calendar event."""

    def __init__(self, event: Optional[Dict[str, Any]] = None, default_date: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Событие" if event else "Новое событие")
        self.setMinimumWidth(380)
        self.deleted = False
        event = event or {}

        layout = QVBoxLayout(self)
        self.date_edit = QLineEdit(event.get("date") or default_date)
        self.date_edit.setObjectName("formInput")
        self.time_edit = QLineEdit(event.get("time") or "12:00")
        self.time_edit.setObjectName("formInput")
        self.title_edit = QLineEdit(event.get("title") or "")
        self.title_edit.setObjectName("formInput")
        self.type_combo = QComboBox()
        self.type_combo.setObjectName("formInput")
        for key, (_, label, _) in EVENT_TYPES.items():
            self.type_combo.addItem(label, key)
        index = self.type_combo.findData(event.get("type") or "publication")
        self.type_combo.setCurrentIndex(max(index, 0))
        self.desc_edit = QTextEdit(event.get("description") or "")
        self.desc_edit.setMaximumHeight(80)
        self.desc_edit.setObjectName("formInput")

        for label, widget in (("Дата (ДД.ММ.ГГГГ)", self.date_edit), ("Время", self.time_edit),
                              ("Заголовок", self.title_edit), ("Тип", self.type_combo),
                              ("Описание", self.desc_edit)):
            layout.addWidget(QLabel(label))
            layout.addWidget(widget)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        if event:
            delete_btn = buttons.addButton("Удалить", QDialogButtonBox.DestructiveRole)
            delete_btn.clicked.connect(self._on_delete)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_delete(self):
        if QMessageBox.question(self, "Удалить событие", "Удалить это событие?",
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes:
            self.deleted = True
            self.accept()

    def _on_accept(self):
        if not self.title_edit.text().strip() or not _parse_date(self.date_edit.text()):
            QMessageBox.warning(self, "Событие", "Нужны заголовок и дата в формате ДД.ММ.ГГГГ.")
            return
        self.accept()

    def values(self) -> Dict[str, Any]:
        return {"date": self.date_edit.text().strip(), "time": self.time_edit.text().strip(),
                "title": self.title_edit.text().strip(),
                "type": self.type_combo.currentData(),
                "description": self.desc_edit.toPlainText().strip()}


class CalendarSection(DataSection):
    """Месячная сетка: события из плана, ручные события, фильтр по типу."""

    def __init__(self, data_manager, settings=None, parent=None):
        super().__init__(data_manager, settings, parent)
        self._offset = 0
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
        title = QLabel("📅 Календарь")
        title.setStyleSheet(f"color: {TEXT}; font-size: 16px; font-weight: 700;")
        head.addWidget(title)
        head.addStretch()

        prev_btn = QPushButton("‹")
        prev_btn.setObjectName("topBtn")
        prev_btn.clicked.connect(lambda: self._shift(-1))
        head.addWidget(prev_btn)

        self.month_label = QLabel("")
        self.month_label.setStyleSheet(f"color: {TEXT}; font-size: 13px; font-weight: 700;"
                                       " padding: 0 8px;")
        head.addWidget(self.month_label)

        next_btn = QPushButton("›")
        next_btn.setObjectName("topBtn")
        next_btn.clicked.connect(lambda: self._shift(1))
        head.addWidget(next_btn)

        today_btn = QPushButton("Сегодня")
        today_btn.setObjectName("topBtn")
        today_btn.clicked.connect(self._today)
        head.addWidget(today_btn)

        add_btn = QPushButton("＋ Событие")
        add_btn.setObjectName("topBtn")
        add_btn.setProperty("class", "primary")
        add_btn.clicked.connect(self._on_add)
        head.addWidget(add_btn)

        sync_btn = QPushButton("События из плана")
        sync_btn.setObjectName("topBtn")
        sync_btn.clicked.connect(self._on_sync)
        head.addWidget(sync_btn)
        layout.addWidget(header)

        filters = QHBoxLayout()
        filters.setContentsMargins(16, 8, 16, 6)
        self.type_filter = QComboBox()
        self.type_filter.setObjectName("formInput")
        self.type_filter.addItem("Все типы", "")
        for key, (_, label, _) in EVENT_TYPES.items():
            self.type_filter.addItem(label, key)
        self.type_filter.currentIndexChanged.connect(self.refresh)
        filters.addWidget(self.type_filter)
        filters.addStretch()
        self.status = QLabel("")
        self.status.setStyleSheet(f"color: {TEAL}; font-size: 11px;")
        filters.addWidget(self.status)
        layout.addLayout(filters)

        scroll = QScrollArea()
        scroll.setObjectName("plainScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        self.grid_host = QFrame()
        self.grid = QGridLayout(self.grid_host)
        self.grid.setContentsMargins(16, 4, 16, 16)
        self.grid.setSpacing(6)
        scroll.setWidget(self.grid_host)
        layout.addWidget(scroll, stretch=1)

    # --- data ---
    def _month(self) -> date:
        today = date.today()
        year = today.year + (today.month - 1 + self._offset) // 12
        month = (today.month - 1 + self._offset) % 12 + 1
        return date(year, month, 1)

    def _events(self) -> List[Dict[str, Any]]:
        events = self.dm.get_calendar_events() if self.dm else []
        chosen = self.type_filter.currentData()
        return [e for e in events if not chosen or e.get("type") == chosen]

    def refresh(self):
        month = self._month()
        self.month_label.setText(f"{MONTHS[month.month - 1].capitalize()} {month.year}")
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()

        for col, name in enumerate(WEEKDAYS):
            label = QLabel(name)
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet(f"color: {MUTED}; font-size: 10px;")
            self.grid.addWidget(label, 0, col)

        events = self._events()
        by_day: Dict[int, List[Dict[str, Any]]] = {}
        for event in events:
            parsed = _parse_date(event.get("date"))
            if parsed and parsed.year == month.year and parsed.month == month.month:
                by_day.setdefault(parsed.day, []).append(event)

        start_col = month.weekday()
        days_in_month = (date(month.year + (month.month == 12), month.month % 12 + 1, 1)
                         - date(month.year, month.month, 1)).days
        row, col = 1, start_col
        for day in range(1, days_in_month + 1):
            self.grid.addWidget(self._day_cell(month, day, by_day.get(day, [])), row, col)
            col += 1
            if col == 7:
                row, col = row + 1, 0
        self.grid.setRowStretch(row + 1, 1)

    def _day_cell(self, month: date, day: int, events: List[Dict[str, Any]]) -> QFrame:
        cell = QFrame()
        cell.setObjectName("zone")
        cell.setMinimumHeight(84)
        layout = QVBoxLayout(cell)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(3)

        is_today = date.today() == date(month.year, month.month, day)
        day_label = QLabel(str(day))
        day_label.setStyleSheet(
            f"color: {TEAL if is_today else MUTED}; font-size: 10px;"
            f" font-weight: {'700' if is_today else '400'};")
        layout.addWidget(day_label)

        for event in events[:3]:
            icon, label, color = EVENT_TYPES.get(event.get("type"),
                                                ("•", "Событие", MUTED))
            chip = QPushButton(f"{icon} {str(event.get('title') or label)[:16]}")
            chip.setToolTip(f"{event.get('time', '')} · {event.get('title', '')}")
            chip.setStyleSheet(
                f"QPushButton {{ background-color: transparent; color: {color}; border: none;"
                " text-align: left; font-size: 9px; padding: 0; }"
                "QPushButton:hover { text-decoration: underline; }")
            chip.clicked.connect(lambda checked=False, e=event: self._edit_event(e))
            layout.addWidget(chip)
        if len(events) > 3:
            more = QLabel(f"+{len(events) - 3}")
            more.setStyleSheet(f"color: {MUTED}; font-size: 9px;")
            layout.addWidget(more)
        layout.addStretch()
        return cell

    # --- actions ---
    def _shift(self, delta: int):
        self._offset += delta
        self.refresh()

    def _today(self):
        self._offset = 0
        self.refresh()

    def _on_add(self):
        default = date.today().strftime("%d.%m.%Y")
        dialog = EventDialog(default_date=default, parent=self)
        if dialog.exec() != QDialog.Accepted:
            return
        self.status.setText(self.add("calendar_events", dialog.values()))
        self.refresh()

    def _edit_event(self, event: Dict[str, Any]):
        dialog = EventDialog(event=event, parent=self)
        if dialog.exec() != QDialog.Accepted:
            return
        if dialog.deleted:
            self.status.setText(self.delete("calendar_events", str(event.get("id"))))
        else:
            self.status.setText(self.update("calendar_events", str(event.get("id")), dialog.values()))
        self.refresh()

    def _on_sync(self):
        self.status.setText(self.run("sync_plan_events"))
        self.refresh()
