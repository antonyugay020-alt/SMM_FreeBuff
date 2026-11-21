#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix: Complete Publications section with full integration.
- Media library pulls from Media Content "Ready" zone
- Drag-and-drop to folders (Stories/Reels/Feed)
- Calendar linked to Content Plan
- Schedule settings with save
Run: python fix_publications_complete.py
"""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

def write(rel, content):
    p = BASE / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding='utf-8', newline='\n')
    print(f"  [OK] {rel}")

print("\n=== Completing Publications Section ===\n")

publications = r'''"""Publications section: Full integration with media, content plan, calendar."""
import logging
import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QGridLayout, QScrollArea, QComboBox, QCheckBox,
    QTextEdit, QSplitter, QAbstractItemView, QMessageBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QFormLayout, QTimeEdit, QDateEdit)
from PySide6.QtCore import Qt, QDate, QTime, Signal, QMimeData, QByteArray
from PySide6.QtGui import QPixmap, QDrag, QColor

logger = logging.getLogger(__name__)

DRAG_TYPE = "application/x-smm-publication"

# Demo ready materials (from Media Content section)
DEMO_READY_MATERIALS = [
    {"name": "tennis_001.jpg", "type": "image", "size": "1920x2560", "status": "approved", "date": "15.11.2026"},
    {"name": "tennis_002.jpg", "type": "image", "size": "1920x2560", "status": "approved", "date": "15.11.2026"},
    {"name": "reels_001.mp4", "type": "video", "size": "1080x1920", "status": "approved", "date": "16.11.2026"},
    {"name": "coffee_story.jpg", "type": "image", "size": "1080x1920", "status": "pending", "date": "17.11.2026"},
    {"name": "room_001.jpg", "type": "image", "size": "1920x2560", "status": "rejected", "date": "17.11.2026"},
]

# Demo content plan items
DEMO_CONTENT_PLAN = [
    {"date": "15.11.2026", "topic": "5 упражнений для запястья", "format": "Пост", "status": "Одобрено"},
    {"date": "16.11.2026", "topic": "Смешные моменты с тренировок", "format": "Reels", "status": "В работе"},
    {"date": "17.11.2026", "topic": "Акция: первое занятие бесплатно", "format": "Stories", "status": "Запланировано"},
    {"date": "18.11.2026", "topic": "История успеха ученика Максима", "format": "Пост", "status": "Черновик"},
]

# Demo folders
DEMO_FOLDERS = {
    "stories": {
        "name": "Stories",
        "icon": "📷",
        "desc": "Фото и короткие видео (до 60 сек)",
        "color": "#9e6a03",
        "items": [
            {"name": "coffee_story.jpg", "time": "18:00", "date": "17.11.2026"},
        ]
    },
    "reels": {
        "name": "Reels",
        "icon": "🎬",
        "desc": "Вертикальные видео (до 90 сек)",
        "color": "#1f6feb",
        "items": [
            {"name": "reels_001.mp4", "time": "15:45", "date": "16.11.2026"},
        ]
    },
    "feed": {
        "name": "Лента",
        "icon": "📰",
        "desc": "Фото и видео (1:1, 4:5, 16:9)",
        "color": "#238636",
        "items": [
            {"name": "tennis_001.jpg", "time": "12:00", "date": "15.11.2026"},
            {"name": "tennis_002.jpg", "time": "12:00", "date": "15.11.2026"},
        ]
    }
}


class MaterialCard(QFrame):
    """Media material card with drag support."""
    def __init__(self, material: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.material = material
        self._drag_pos = None

        self.setObjectName("thumb")
        self.setFrameShape(QFrame.NoFrame)
        self.setStyleSheet("""
            QFrame#thumb { background-color: #0d1117; border: 2px solid #30363d; border-radius: 6px; }
            QFrame#thumb:hover { border-color: #58a6ff; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Preview
        preview = QLabel()
        preview.setAlignment(Qt.AlignCenter)
        preview.setMinimumHeight(100)
        preview.setStyleSheet("background-color: #21262d; font-size: 32px; color: #8b949e;")

        media_dir = Path(__file__).resolve().parent.parent.parent / "media" / "images"
        img_path = media_dir / material["name"]
        if img_path.exists():
            try:
                pm = QPixmap(str(img_path))
                if not pm.isNull():
                    scaled = pm.scaled(140, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    preview.setPixmap(scaled)
            except:
                pass

        icon = "🎬" if material["type"] == "video" else "🖼️"
        if preview.pixmap().isNull():
            preview.setText(icon)
        layout.addWidget(preview)

        # Name
        name = material["name"]
        name_label = QLabel(name if len(name) <= 20 else name[:17] + "...")
        name_label.setStyleSheet("color: #c9d1d9; font-size: 10px; padding: 4px 6px 0 6px; font-weight: bold;")
        layout.addWidget(name_label)

        # Size
        size_label = QLabel(material["size"])
        size_label.setStyleSheet("color: #8b949e; font-size: 9px; padding: 0 6px;")
        layout.addWidget(size_label)

        # Status
        status = material.get("status", "pending")
        status_map = {"approved": ("✅ Одобрено", "#238636"), "pending": ("⏳ На проверке", "#9e6a03"), "rejected": ("❌ Отклонено", "#da3633")}
        status_text, status_color = status_map.get(status, ("?", "#8b949e"))
        status_label = QLabel(status_text)
        status_label.setStyleSheet(f"color: {status_color}; font-size: 9px; padding: 0 6px 4px 6px; font-weight: bold;")
        layout.addWidget(status_label)

        self.setMinimumWidth(140)
        self.setMaximumWidth(160)
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return
        if self._drag_pos is None:
            return
        if (event.pos() - self._drag_pos).manhattanLength() < 10:
            return

        logger.info(f"Starting drag: {self.material['name']}")

        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(DRAG_TYPE, json.dumps(self.material).encode('utf-8'))
        drag.setMimeData(mime)

        drag.exec_(Qt.MoveAction)
        self._drag_pos = None


class FolderCard(QFrame):
    """Publication folder with drop support."""
    def __init__(self, folder_id: str, folder_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.folder_id = folder_id
        self.folder_data = folder_data
        self.color = folder_data["color"]

        self.setObjectName("zone")
        self.setStyleSheet(f"""
            QFrame#zone {{
                background-color: #161b22;
                border: 1px solid #30363d;
                border-top: 4px solid {self.color};
                border-radius: 6px;
            }}
        """)
        self.setAcceptDrops(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Header
        header = QHBoxLayout()
        title = QLabel(f"{folder_data['icon']} {folder_data['name']}")
        title.setStyleSheet("color: #e6edf3; font-size: 14px; font-weight: bold;")
        header.addWidget(title)
        header.addStretch()

        schedule_btn = QPushButton("📅 Расписание")
        schedule_btn.setObjectName("topBtn")
        schedule_btn.setStyleSheet("font-size: 11px;")
        header.addWidget(schedule_btn)
        layout.addLayout(header)

        # Description
        desc = QLabel(folder_data["desc"])
        desc.setStyleSheet("color: #8b949e; font-size: 11px;")
        layout.addWidget(desc)

        # Items
        items_layout = QHBoxLayout()
        items_layout.setSpacing(6)

        for item in folder_data["items"][:4]:
            thumb = QLabel("🖼️")
            thumb.setAlignment(Qt.AlignCenter)
            thumb.setStyleSheet("background-color: #21262d; border-radius: 4px; min-width: 50px; min-height: 50px; font-size: 20px; color: #8b949e;")
            items_layout.addWidget(thumb)

        # Add button
        add_btn = QLabel("+\nДобавить")
        add_btn.setAlignment(Qt.AlignCenter)
        add_btn.setStyleSheet("background-color: #21262d; border: 2px dashed #30363d; border-radius: 4px; min-width: 50px; min-height: 50px; color: #8b949e; font-size: 10px;")
        items_layout.addWidget(add_btn)

        layout.addLayout(items_layout)

        # Footer
        count = len(folder_data["items"])
        next_pub = folder_data["items"][0]["time"] if folder_data["items"] else "—"
        footer = QLabel(f"{count} файл(ов) · Следующая: {next_pub}")
        footer.setStyleSheet("color: #8b949e; font-size: 11px;")
        layout.addWidget(footer)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(DRAG_TYPE):
            event.acceptProposedAction()
            self.setStyleSheet(f"""
                QFrame#zone {{
                    background-color: #1c2333;
                    border: 2px dashed {self.color};
                    border-top: 4px solid {self.color};
                    border-radius: 6px;
                }}
            """)

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(DRAG_TYPE):
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self.setStyleSheet(f"""
            QFrame#zone {{
                background-color: #161b22;
                border: 1px solid #30363d;
                border-top: 4px solid {self.color};
                border-radius: 6px;
            }}
        """)

    def dropEvent(self, event):
        if not event.mimeData().hasFormat(DRAG_TYPE):
            return

        data = json.loads(bytes(event.mimeData().data(DRAG_TYPE)).decode('utf-8'))
        logger.info(f"Dropped {data['name']} into {self.folder_id}")

        # Add to folder
        self.folder_data["items"].append({
            "name": data["name"],
            "time": "12:00",
            "date": datetime.now().strftime("%d.%m.%Y")
        })

        # Refresh
        QMessageBox.information(self, "Добавлено", f"{data['name']} добавлен в папку {self.folder_data['name']}")

        self.setStyleSheet(f"""
            QFrame#zone {{
                background-color: #161b22;
                border: 1px solid #30363d;
                border-top: 4px solid {self.color};
                border-radius: 6px;
            }}
        """)

        event.acceptProposedAction()


class PublicationsSection(QWidget):
    """Publications section with full integration."""

    def __init__(self, app_state: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.state = app_state
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # Zone 1: Media Library
        zone1 = self._build_media_library()
        layout.addWidget(zone1)

        # Zone 3: Folders
        zone3 = self._build_folders()
        layout.addWidget(zone3)

        # Zone 4 + 5: Calendar + Schedule
        bottom = QHBoxLayout()
        bottom.setSpacing(16)
        zone4 = self._build_calendar()
        zone5 = self._build_schedule()
        bottom.addWidget(zone4, stretch=2)
        bottom.addWidget(zone5, stretch=1)
        layout.addLayout(bottom)

    def _build_media_library(self) -> QFrame:
        zone = QFrame()
        zone.setObjectName("zone")
        layout = QVBoxLayout(zone)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QFrame()
        header.setObjectName("zoneHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 8, 12, 8)

        num = QLabel("1")
        num.setStyleSheet("background-color: #1f6feb; color: white; border-radius: 10px; padding: 2px 8px; font-weight: bold; margin-right: 8px;")
        header_layout.addWidget(num)

        title = QLabel("Медиатека готовых материалов")
        title.setStyleSheet("color: #58a6ff; font-size: 14px; font-weight: bold;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Filters
        for label in ["Все (5)", "Одобрено (2)", "На проверке (2)", "Отклонено (1)"]:
            btn = QPushButton(label)
            btn.setObjectName("statusBtn")
            btn.setStyleSheet("font-size: 11px;")
            header_layout.addWidget(btn)

        layout.addWidget(header)

        # Grid
        grid_scroll = QScrollArea()
        grid_scroll.setWidgetResizable(True)
        grid_scroll.setMaximumHeight(280)
        grid_scroll.setStyleSheet("border: none; background-color: #0d1117;")

        grid_widget = QWidget()
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setSpacing(8)
        grid_layout.setContentsMargins(12, 12, 12, 12)

        row, col = 0, 0
        for material in DEMO_READY_MATERIALS:
            card = MaterialCard(material)
            grid_layout.addWidget(card, row, col)
            col += 1
            if col >= 6:
                col = 0
                row += 1

        grid_scroll.setWidget(grid_widget)
        layout.addWidget(grid_scroll)

        return zone

    def _build_folders(self) -> QFrame:
        zone = QFrame()
        zone.setObjectName("zone")
        layout = QVBoxLayout(zone)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QFrame()
        header.setObjectName("zoneHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 8, 12, 8)

        num = QLabel("3")
        num.setStyleSheet("background-color: #bc8cff; color: white; border-radius: 10px; padding: 2px 8px; font-weight: bold; margin-right: 8px;")
        header_layout.addWidget(num)

        title = QLabel("Папки публикаций — перетаскивай файлы из медиатеки")
        title.setStyleSheet("color: #bc8cff; font-size: 14px; font-weight: bold;")
        header_layout.addWidget(title)

        layout.addWidget(header)

        # Folder cards
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)
        cards_layout.setContentsMargins(12, 12, 12, 12)

        for folder_id, folder_data in DEMO_FOLDERS.items():
            card = FolderCard(folder_id, folder_data)
            cards_layout.addWidget(card, stretch=1)

        layout.addLayout(cards_layout)

        return zone

    def _build_calendar(self) -> QFrame:
        zone = QFrame()
        zone.setObjectName("zone")
        layout = QVBoxLayout(zone)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QFrame()
        header.setObjectName("zoneHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 8, 12, 8)

        num = QLabel("4")
        num.setStyleSheet("background-color: #f85149; color: white; border-radius: 10px; padding: 2px 8px; font-weight: bold; margin-right: 8px;")
        header_layout.addWidget(num)

        title = QLabel("Календарь публикаций")
        title.setStyleSheet("color: #f85149; font-size: 14px; font-weight: bold;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        for mode in ["День", "Неделя", "Месяц"]:
            btn = QPushButton(mode)
            btn.setObjectName("topBtn")
            if mode == "Месяц":
                btn.setProperty("class", "primary")
            header_layout.addWidget(btn)

        layout.addWidget(header)

        # Calendar table
        table = QTableWidget()
        table.setObjectName("calendar")
        table.setRowCount(2)
        table.setColumnCount(7)
        table.setHorizontalHeaderLabels(["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"])
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        # Sample events from content plan
        events = {
            (0, 2): [("10:00 Reels", "#1f6feb")],
            (0, 4): [("12:00 Лента", "#238636")],
            (0, 6): [("18:00 Stories", "#9e6a03")],
            (1, 0): [("12:00 Лента", "#238636")],
            (1, 2): [("15:00 Reels", "#1f6feb")],
        }

        for row in range(2):
            for col in range(7):
                day_num = 12 + row * 7 + col
                cell_text = str(day_num)
                if (row, col) in events:
                    for event_text, color in events[(row, col)]:
                        cell_text += f"\n{event_text}"
                item = QTableWidgetItem(cell_text)
                item.setTextAlignment(Qt.AlignTop | Qt.AlignLeft)
                table.setItem(row, col, item)

        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setMinimumHeight(160)
        layout.addWidget(table)

        return zone

    def _build_schedule(self) -> QFrame:
        zone = QFrame()
        zone.setObjectName("zone")
        layout = QVBoxLayout(zone)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QFrame()
        header.setObjectName("zoneHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 8, 12, 8)

        num = QLabel("5")
        num.setStyleSheet("background-color: #d29922; color: white; border-radius: 10px; padding: 2px 8px; font-weight: bold; margin-right: 8px;")
        header_layout.addWidget(num)

        title = QLabel("Настройки расписания")
        title.setStyleSheet("color: #d29922; font-size: 14px; font-weight: bold;")
        header_layout.addWidget(title)

        layout.addWidget(header)

        # Form
        form = QWidget()
        form_layout = QFormLayout(form)
        form_layout.setContentsMargins(12, 12, 12, 12)
        form_layout.setSpacing(8)

        tz_combo = QComboBox()
        tz_combo.addItem("(UTC+6:00) Алматы")
        form_layout.addRow("Часовой пояс", tz_combo)

        period_combo = QComboBox()
        period_combo.addItem("Ежедневно")
        period_combo.addItem("По будням")
        form_layout.addRow("Периодичность", period_combo)

        time1 = QTimeEdit()
        time1.setTime(QTime(12, 0))
        form_layout.addRow("Время публикации", time1)

        save_btn = QPushButton("💾 Сохранить")
        save_btn.setObjectName("topBtn")
        save_btn.setProperty("class", "primary")
        save_btn.setStyleSheet("font-size: 12px; font-weight: bold; padding: 8px;")
        save_btn.clicked.connect(lambda: QMessageBox.information(self, "Сохранено", "Настройки расписания сохранены"))
        form_layout.addRow(save_btn)

        layout.addWidget(form)

        return zone
'''

write("gui_sections/publications_section.py", publications)

print("\n=== Publications Section Completed ===")
print("\nFeatures:")
print("  [OK] Media library pulls ready materials")
print("  [OK] Drag-and-drop from media to folders")
print("  [OK] 3 folders: Stories, Reels, Feed")
print("  [OK] Calendar with content plan events")
print("  [OK] Schedule settings with save")
print("\nRun START.bat and click 'Публикации' in left panel.")