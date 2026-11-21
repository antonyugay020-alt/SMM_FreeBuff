#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix Phase 1.2 v2: Write gui_main.py and publications_section.py directly.
Run: python fix_phase1_2_v2.py
"""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

def write(rel, content):
    p = BASE / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding='utf-8', newline='\n')
    print(f"  [OK] {rel}")

print("\n=== Phase 1.2 v2 Fix ===\n")

# 1. gui_theme.py
print("[1/3] Writing gui_theme.py...")

theme = r'''"""Dark theme for AI SMM Manager."""

DARK_THEME_QSS = """
QMainWindow { background-color: #0f1419; color: #e6edf3; }
QWidget { background-color: transparent; }

QWidget#leftPanel { background-color: #161b22; border-right: 1px solid #30363d; }
QLabel#logo { color: #58a6ff; font-size: 13px; font-weight: bold; padding: 12px; border-bottom: 1px solid #30363d; }
QPushButton#navBtn {
    background-color: transparent; color: #c9d1d9; border: none;
    padding: 10px 12px; text-align: left; font-size: 13px; border-radius: 4px;
}
QPushButton#navBtn:hover { background-color: #21262d; color: #ffffff; }
QPushButton#navBtn.active { background-color: #1f6feb; color: #ffffff; }
QLabel#projectBlock { color: #8b949e; font-size: 10px; padding: 8px 12px 4px 12px; }
QLabel#projectName { color: #e6edf3; font-size: 13px; font-weight: bold; padding: 4px 12px; }
QLabel#projectStats { color: #8b949e; font-size: 11px; padding: 2px 12px; }
QProgressBar#storageBar {
    background-color: #21262d; border-radius: 3px; text-align: center;
    color: #e6edf3; font-size: 10px; height: 16px;
}
QProgressBar#storageBar::chunk { background-color: #1f6feb; border-radius: 3px; }

QWidget#topBar { background-color: #161b22; border-bottom: 1px solid #30363d; padding: 8px 16px; }
QLabel#sectionTitle { color: #e6edf3; font-size: 18px; font-weight: bold; }
QLabel#sectionSubtitle { color: #8b949e; font-size: 12px; }
QLineEdit#searchBox {
    background-color: #0d1117; color: #e6edf3; border: 1px solid #30363d;
    border-radius: 4px; padding: 6px 10px; font-size: 12px;
}
QLineEdit#searchBox:focus { border-color: #1f6feb; }
QComboBox#projectCombo, QComboBox#filterCombo {
    background-color: #21262d; color: #e6edf3; border: 1px solid #30363d;
    border-radius: 4px; padding: 6px 10px; font-size: 12px;
}
QPushButton#topBtn {
    background-color: #21262d; color: #e6edf3; border: 1px solid #30363d;
    padding: 6px 12px; border-radius: 4px; font-size: 12px;
}
QPushButton#topBtn:hover { background-color: #30363d; }
QPushButton#topBtn.primary { background-color: #1f6feb; border-color: #1f6feb; color: #ffffff; }
QPushButton#topBtn.primary:hover { background-color: #388bfd; }

QLabel#zoneTitle { color: #e6edf3; font-size: 14px; font-weight: bold; padding: 8px 12px; }
QLabel#zoneTitle.blue { color: #58a6ff; }
QLabel#zoneTitle.purple { color: #bc8cff; }
QLabel#zoneTitle.green { color: #3fb950; }
QLabel#zoneTitle.red { color: #f85149; }
QLabel#zoneTitle.yellow { color: #d29922; }

QFrame#zone { background-color: #161b22; border: 1px solid #30363d; border-radius: 6px; }
QFrame#zoneHeader { background-color: #1c2128; border-radius: 6px 6px 0 0; padding: 8px 12px; }

QPushButton#statusBtn {
    background-color: #21262d; color: #c9d1d9; border: 1px solid #30363d;
    padding: 4px 10px; border-radius: 12px; font-size: 11px;
}
QPushButton#statusBtn:hover { background-color: #30363d; }
QPushButton#statusBtn.active { background-color: #1f6feb; color: #ffffff; border-color: #1f6feb; }
QPushButton#statusBtn.approved { background-color: #238636; color: #ffffff; border-color: #238636; }
QPushButton#statusBtn.rejected { background-color: #da3633; color: #ffffff; border-color: #da3633; }
QPushButton#statusBtn.pending { background-color: #9e6a03; color: #ffffff; border-color: #9e6a03; }

QWidget#thumb { background-color: #0d1117; border: 2px solid #30363d; border-radius: 4px; }
QWidget#thumb:hover { border-color: #58a6ff; }
QWidget#thumb.selected { border-color: #1f6feb; background-color: #161b22; }
QLabel#thumbName { color: #c9d1d9; font-size: 10px; padding: 4px; }

QFrame#folderCard { background-color: #161b22; border: 1px solid #30363d; border-radius: 6px; }
QFrame#folderCard.stories { border-color: #9e6a03; }
QFrame#folderCard.reels { border-color: #1f6feb; }
QFrame#folderCard.feed { border-color: #238636; }

QTableWidget#calendar {
    background-color: #0d1117; color: #e6edf3; border: 1px solid #30363d;
    gridline-color: #30363d; font-size: 11px;
}
QTableWidget#calendar::item { padding: 4px; }
QTableWidget#calendar::item:selected { background-color: #1f6feb; }
QHeaderView::section {
    background-color: #161b22; color: #8b949e; border: 1px solid #30363d;
    padding: 6px; font-size: 11px;
}

QScrollBar:vertical { background-color: #0d1117; width: 10px; border: none; }
QScrollBar::handle:vertical { background-color: #30363d; border-radius: 5px; min-height: 20px; }
QScrollBar::handle:vertical:hover { background-color: #484f58; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

QWidget#aiPanel { background-color: #161b22; border-left: 1px solid #30363d; }
QTextEdit#chatHistory { background-color: #0d1117; color: #e6edf3; border: none; font-family: Consolas, monospace; font-size: 12px; }
QTextEdit#chatInput { background-color: #0d1117; color: #e6edf3; border: 1px solid #30363d; border-radius: 4px; font-family: Consolas, monospace; font-size: 12px; }
QPushButton#sendBtn { background-color: #1f6feb; color: #ffffff; border: none; padding: 8px 16px; border-radius: 4px; font-size: 12px; font-weight: bold; }
QPushButton#sendBtn:hover { background-color: #388bfd; }
"""
'''

write("gui_theme.py", theme)

# 2. gui_main.py
print("[2/3] Writing gui_main.py...")

gui_main = r'''"""Main window: new framework with icon menu + project dropdown."""
import logging
from pathlib import Path
from typing import Dict, Any, List

from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QScrollArea, QFrame, QComboBox, QLineEdit, QProgressBar)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from gui_theme import DARK_THEME_QSS
from gui_ai_panel import AIPanel

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parent.parent

NAV_ITEMS = [
    ("dashboard", "📊", "Дашборд"),
    ("projects", "📁", "Проекты"),
    ("sources", "📥", "Исходники"),
    ("reference", "🎯", "Эталон"),
    ("processing", "🎨", "Обработка"),
    ("publications", "📢", "Публикации"),
    ("content_plan", "📝", "Контент-план"),
    ("ai_manager", "🤖", "AI-менеджер"),
    ("settings", "⚙️", "Настройки"),
]

SECTION_TITLES = {
    "dashboard": ("Дашборд", "Общая картина по всем проектам"),
    "projects": ("Проекты", "Управление проектами"),
    "sources": ("Исходники", "Загрузка исходных материалов"),
    "reference": ("Эталон", "Референсы для обработки"),
    "processing": ("Обработка", "Обработка фото и видео"),
    "publications": ("Публикации", "Управление готовым контентом и планирование публикаций в Instagram"),
    "content_plan": ("Контент-план", "Планирование контента"),
    "ai_manager": ("AI-менеджер", "Диалог с AI-ассистентом"),
    "settings": ("Настройки", "Настройки приложения"),
}


class MainWindow(QMainWindow):
    """New framework: icon menu | workspace | AI panel."""

    def __init__(self, app_state: Dict[str, Any]):
        super().__init__()
        self.state = app_state
        self.current_section = "publications"
        self.projects: List[Dict[str, Any]] = []
        self.current_project_id = "default"
        self.setWindowTitle("AI SMM Manager")
        self.resize(1600, 950)
        self.setStyleSheet(DARK_THEME_QSS)
        self._build_ui()
        self._load_projects()
        self._on_nav("publications")

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # === LEFT PANEL ===
        left = QWidget()
        left.setObjectName("leftPanel")
        left.setFixedWidth(220)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        logo = QLabel("AI SMM MANAGER")
        logo.setObjectName("logo")
        left_layout.addWidget(logo)

        self.nav_buttons = {}
        nav_scroll = QScrollArea()
        nav_scroll.setWidgetResizable(True)
        nav_scroll.setStyleSheet("border: none; background: transparent;")
        nav_widget = QWidget()
        nav_widget_layout = QVBoxLayout(nav_widget)
        nav_widget_layout.setContentsMargins(8, 8, 8, 8)
        nav_widget_layout.setSpacing(4)

        for item_id, icon, label in NAV_ITEMS:
            btn = QPushButton(f"{icon}  {label}")
            btn.setObjectName("navBtn")
            btn.clicked.connect(lambda checked, sid=item_id: self._on_nav(sid))
            self.nav_buttons[item_id] = btn
            nav_widget_layout.addWidget(btn)

        nav_widget_layout.addStretch()
        nav_scroll.setWidget(nav_widget)
        left_layout.addWidget(nav_scroll, stretch=1)

        # Current project block
        proj_label = QLabel("Текущий проект")
        proj_label.setObjectName("projectBlock")
        left_layout.addWidget(proj_label)

        self.proj_preview = QLabel("📷")
        self.proj_preview.setAlignment(Qt.AlignCenter)
        self.proj_preview.setMinimumHeight(100)
        self.proj_preview.setStyleSheet("background-color: #0d1117; border-radius: 4px; margin: 0 8px; font-size: 40px;")
        left_layout.addWidget(self.proj_preview)

        self.proj_name = QLabel("Не выбран")
        self.proj_name.setObjectName("projectName")
        left_layout.addWidget(self.proj_name)

        self.proj_stats = QLabel("0 исходников\n0 готовых\n0 на проверке")
        self.proj_stats.setObjectName("projectStats")
        left_layout.addWidget(self.proj_stats)

        # Storage bar
        storage_label = QLabel("Хранилище проекта")
        storage_label.setObjectName("projectBlock")
        left_layout.addWidget(storage_label)

        self.storage_bar = QProgressBar()
        self.storage_bar.setObjectName("storageBar")
        self.storage_bar.setValue(21)
        self.storage_bar.setFormat("42.6 ГБ из 200 ГБ")
        self.storage_bar.setStyleSheet("margin: 0 8px 8px 8px;")
        left_layout.addWidget(self.storage_bar)

        main_layout.addWidget(left)

        # === CENTER: Workspace ===
        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)

        # Top bar
        top_bar = QWidget()
        top_bar.setObjectName("topBar")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(16, 10, 16, 10)

        self.section_title = QLabel("Публикации")
        self.section_title.setObjectName("sectionTitle")
        top_layout.addWidget(self.section_title)

        self.section_subtitle = QLabel("")
        self.section_subtitle.setObjectName("sectionSubtitle")
        top_layout.addWidget(self.section_subtitle)

        top_layout.addStretch()

        # Search
        search = QLineEdit()
        search.setObjectName("searchBox")
        search.setPlaceholderText("🔍 Поиск по файлам, тегам, описанию...")
        search.setFixedWidth(280)
        top_layout.addWidget(search)

        # Project dropdown
        self.project_combo = QComboBox()
        self.project_combo.setObjectName("projectCombo")
        self.project_combo.setFixedWidth(180)
        self.project_combo.currentIndexChanged.connect(self._on_project_changed)
        top_layout.addWidget(self.project_combo)

        # Buttons
        refresh_btn = QPushButton("🔄 Обновить")
        refresh_btn.setObjectName("topBtn")
        top_layout.addWidget(refresh_btn)

        import_btn = QPushButton("📥 Импорт медиа")
        import_btn.setObjectName("topBtn")
        import_btn.setProperty("class", "primary")
        top_layout.addWidget(import_btn)

        center_layout.addWidget(top_bar)

        # Workspace content
        self.workspace_scroll = QScrollArea()
        self.workspace_scroll.setWidgetResizable(True)
        self.workspace_scroll.setStyleSheet("border: none; background-color: #0f1419;")

        self.workspace_content = QWidget()
        self.workspace_layout = QVBoxLayout(self.workspace_content)
        self.workspace_layout.setContentsMargins(16, 16, 16, 16)
        self.workspace_layout.setSpacing(16)

        self.workspace_scroll.setWidget(self.workspace_content)
        center_layout.addWidget(self.workspace_scroll, stretch=1)

        main_layout.addWidget(center, stretch=1)

        # === RIGHT: AI Panel ===
        logs_dir = self.state.get("logs_dir", str(ROOT_DIR / "data" / "logs"))
        history_path = str(Path(logs_dir) / "ai_chat_history.json")
        self.ai_panel = AIPanel(history_path)
        self.ai_panel.setFixedWidth(360)
        main_layout.addWidget(self.ai_panel)

        # Status bar
        self.statusBar().showMessage("Готов к работе")

    def _load_projects(self):
        pm = self.state.get("project_manager")
        if pm:
            self.projects = pm.list_projects()
            if not self.projects:
                pm.create_project("default", "Теннис", "")
                self.projects = pm.list_projects()

        self.project_combo.clear()
        for proj in self.projects:
            self.project_combo.addItem(proj["name"], proj["id"])

        if self.projects:
            first = self.projects[0]
            self.current_project_id = first["id"]
            self.proj_name.setText(first["name"])
            self.proj_stats.setText("18 исходников\n24 готовых\n12 на проверке\n5 запланировано")

    def _on_nav(self, section_id: str):
        self.current_section = section_id
        for sid, btn in self.nav_buttons.items():
            btn.setProperty("active", sid == section_id)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        title, subtitle = SECTION_TITLES.get(section_id, (section_id, ""))
        self.section_title.setText(title)
        self.section_subtitle.setText(subtitle)

        # Clear workspace
        while self.workspace_layout.count():
            item = self.workspace_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Load section content
        if section_id == "publications":
            self._load_publications_section()
        else:
            self._load_placeholder(title)

        self.statusBar().showMessage(f"Раздел: {title}")

    def _load_placeholder(self, title: str):
        placeholder = QLabel(f'Раздел "{title}" — в разработке')
        placeholder.setAlignment(Qt.AlignCenter)
        placeholder.setStyleSheet("color: #8b949e; font-size: 16px; padding: 60px;")
        self.workspace_layout.addWidget(placeholder)

    def _load_publications_section(self):
        from gui_sections.publications_section import PublicationsSection
        section = PublicationsSection(self.state)
        self.workspace_layout.addWidget(section)

    def _on_project_changed(self, index: int):
        if index < 0 or index >= len(self.projects):
            return
        proj = self.projects[index]
        self.current_project_id = proj["id"]
        self.proj_name.setText(proj["name"])
        self.statusBar().showMessage(f"Проект: {proj['name']}")
'''

write("gui_main.py", gui_main)

# 3. publications_section.py
print("[3/3] Writing publications_section.py...")

publications = r'''"""Publications section: media library, folders, calendar, schedule."""
import logging
from pathlib import Path
from typing import Dict, Any, List

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QGridLayout, QScrollArea, QComboBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QFormLayout, QTimeEdit, QCheckBox,
    QAbstractItemView)
from PySide6.QtCore import Qt, QTime
from PySide6.QtGui import QPixmap

logger = logging.getLogger(__name__)

DEMO_FILES = [
    {"name": "tennis_001.jpg", "status": "pending", "type": "image", "size": "1920x2560", "date": "15.10.2026 14:30"},
    {"name": "tennis_002.jpg", "status": "approved", "type": "image", "size": "1920x2560", "date": "15.10.2026 14:32"},
    {"name": "tennis_003.jpg", "status": "pending", "type": "image", "size": "1920x2560", "date": "15.10.2026 14:35"},
    {"name": "reels_001.mp4", "status": "approved", "type": "video", "size": "1080x1920", "date": "15.10.2026 15:00"},
    {"name": "coffee_story.jpg", "status": "pending", "type": "image", "size": "1080x1920", "date": "15.10.2026 15:20"},
    {"name": "room_001.jpg", "status": "rejected", "type": "image", "size": "1920x2560", "date": "15.10.2026 15:45"},
    {"name": "sunset.jpg", "status": "approved", "type": "image", "size": "1920x1080", "date": "14.10.2026 10:00"},
    {"name": "shoes.jpg", "status": "pending", "type": "image", "size": "1920x1080", "date": "14.10.2026 11:30"},
]

STATUS_LABELS = {"pending": "На проверке", "approved": "Одобрено", "rejected": "Отклонено"}
STATUS_CLASSES = {"pending": "pending", "approved": "approved", "rejected": "rejected"}


class MediaThumbnail(QWidget):
    """Single media thumbnail with status."""
    def __init__(self, file_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.file_data = file_data
        self.setObjectName("thumb")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Preview area
        preview = QLabel()
        preview.setAlignment(Qt.AlignCenter)
        preview.setMinimumHeight(110)

        media_dir = Path(__file__).resolve().parent.parent.parent / "media" / "images"
        img_path = media_dir / file_data["name"]
        if img_path.exists():
            try:
                pm = QPixmap(str(img_path))
                if not pm.isNull():
                    scaled = pm.scaled(160, 110, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    preview.setPixmap(scaled)
                    preview.setStyleSheet("background-color: #21262d; border-radius: 4px 4px 0 0;")
                else:
                    preview.setText("🖼️")
                    preview.setStyleSheet("background-color: #21262d; border-radius: 4px 4px 0 0; font-size: 32px; color: #8b949e;")
            except Exception:
                preview.setText("🖼️")
                preview.setStyleSheet("background-color: #21262d; border-radius: 4px 4px 0 0; font-size: 32px; color: #8b949e;")
        else:
            icon = "🎬" if file_data["type"] == "video" else "🖼️"
            preview.setText(icon)
            preview.setStyleSheet("background-color: #21262d; border-radius: 4px 4px 0 0; font-size: 32px; color: #8b949e;")
        layout.addWidget(preview)

        # Name
        name_label = QLabel(file_data["name"])
        name_label.setObjectName("thumbName")
        layout.addWidget(name_label)

        # Size
        size_label = QLabel(file_data["size"])
        size_label.setStyleSheet("color: #8b949e; font-size: 9px; padding: 0 4px;")
        layout.addWidget(size_label)

        # Status button
        status = file_data["status"]
        status_btn = QPushButton(STATUS_LABELS.get(status, status))
        status_btn.setObjectName("statusBtn")
        status_btn.setProperty("class", STATUS_CLASSES.get(status, ""))
        status_btn.setStyleSheet("margin: 4px; font-size: 10px;")
        layout.addWidget(status_btn)

        self.setMinimumSize(140, 180)
        self.setMaximumSize(160, 200)


class PublicationsSection(QWidget):
    """Publications section with zones."""

    def __init__(self, app_state: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.state = app_state
        self.selected_file = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # Zone 1: Media Library
        self.zone1 = self._build_media_library()
        layout.addWidget(self.zone1)

        # Zone 3: Publication Folders
        self.zone3 = self._build_folders()
        layout.addWidget(self.zone3)

        # Zone 4 + 5 side by side
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(16)
        self.zone4 = self._build_calendar()
        self.zone5 = self._build_schedule_settings()
        bottom_row.addWidget(self.zone4, stretch=2)
        bottom_row.addWidget(self.zone5, stretch=1)
        layout.addLayout(bottom_row)

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
        title.setObjectName("zoneTitle")
        title.setProperty("class", "blue")
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Status filters
        filters = [("Все (24)", "active"), ("На проверке (12)", ""), ("Одобрено (8)", "approved"), ("Отклонено (4)", "rejected")]
        for text, cls in filters:
            btn = QPushButton(text)
            btn.setObjectName("statusBtn")
            if cls:
                btn.setProperty("class", cls)
            btn.setStyleSheet("font-size: 11px;")
            header_layout.addWidget(btn)

        header_layout.addSpacing(16)

        # Type/Format/Sort combos
        for label in ["Тип: Все", "Формат: Все", "Сортировка: По дате"]:
            combo = QComboBox()
            combo.setObjectName("filterCombo")
            combo.addItem(label)
            combo.setFixedWidth(130)
            header_layout.addWidget(combo)

        layout.addWidget(header)

        # Grid of thumbnails
        grid_scroll = QScrollArea()
        grid_scroll.setWidgetResizable(True)
        grid_scroll.setMaximumHeight(320)
        grid_scroll.setStyleSheet("border: none; background-color: #0d1117;")

        grid_widget = QWidget()
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setSpacing(8)
        grid_layout.setContentsMargins(12, 12, 12, 12)

        row, col = 0, 0
        for file_data in DEMO_FILES:
            thumb = MediaThumbnail(file_data)
            grid_layout.addWidget(thumb, row, col)
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

        title = QLabel("Папки публикаций (виртуальные) — перетаскивай файлы или добавляй через меню")
        title.setObjectName("zoneTitle")
        title.setProperty("class", "purple")
        header_layout.addWidget(title)

        header_layout.addStretch()

        compare_btn = QPushButton("🔍 Сравнить с исходником")
        compare_btn.setObjectName("topBtn")
        header_layout.addWidget(compare_btn)

        layout.addWidget(header)

        # Three folder cards
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)
        cards_layout.setContentsMargins(12, 12, 12, 12)

        folders = [
            ("Stories", "📷", "Фото и короткие видео (до 60 сек)", "stories", "4 файла", "Сегодня 18:00", 4),
            ("Reels", "🎬", "Вертикальные видео (до 90 сек)", "reels", "3 файла", "Пт, 17 окт 2026, 15:45", 3),
            ("Лента", "📰", "Фото и видео (1:1, 4:5, 16:9)", "feed", "4 файла", "Завтра 12:00", 4),
        ]

        for name, icon, desc, css_class, count, next_pub, thumb_count in folders:
            card = QFrame()
            card.setObjectName("folderCard")
            card.setProperty("class", css_class)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(12, 12, 12, 12)
            card_layout.setSpacing(8)

            # Card header
            card_header = QHBoxLayout()
            card_title = QLabel(f"{icon} {name}")
            card_title.setStyleSheet("color: #e6edf3; font-size: 14px; font-weight: bold;")
            card_header.addWidget(card_title)
            card_header.addStretch()
            schedule_btn = QPushButton("📅 Расписание")
            schedule_btn.setObjectName("topBtn")
            schedule_btn.setStyleSheet("font-size: 11px;")
            card_header.addWidget(schedule_btn)
            card_layout.addLayout(card_header)

            # Description
            desc_label = QLabel(desc)
            desc_label.setStyleSheet("color: #8b949e; font-size: 11px;")
            card_layout.addWidget(desc_label)

            # Thumbnails row
            thumbs_row = QHBoxLayout()
            thumbs_row.setSpacing(6)
            for i in range(min(thumb_count, 4)):
                thumb_box = QLabel("🖼️")
                thumb_box.setAlignment(Qt.AlignCenter)
                thumb_box.setStyleSheet("background-color: #21262d; border-radius: 4px; min-width: 60px; min-height: 60px; font-size: 24px; color: #8b949e;")
                thumbs_row.addWidget(thumb_box)

            # Add button
            add_btn = QLabel("+\nДобавить")
            add_btn.setAlignment(Qt.AlignCenter)
            add_btn.setStyleSheet("background-color: #21262d; border: 2px dashed #30363d; border-radius: 4px; min-width: 60px; min-height: 60px; color: #8b949e; font-size: 11px;")
            thumbs_row.addWidget(add_btn)
            card_layout.addLayout(thumbs_row)

            # Footer
            footer = QLabel(f"{count} · Следующая публикация: {next_pub}")
            footer.setStyleSheet("color: #8b949e; font-size: 11px;")
            card_layout.addWidget(footer)

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
        title.setObjectName("zoneTitle")
        title.setProperty("class", "red")
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Month nav
        prev_btn = QPushButton("◀")
        prev_btn.setObjectName("topBtn")
        header_layout.addWidget(prev_btn)
        month_label = QLabel("Октябрь 2026")
        month_label.setStyleSheet("color: #e6edf3; font-size: 13px; font-weight: bold;")
        header_layout.addWidget(month_label)
        next_btn = QPushButton("▶")
        next_btn.setObjectName("topBtn")
        header_layout.addWidget(next_btn)

        header_layout.addSpacing(16)

        # View mode
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
        table.setSelectionMode(QAbstractItemView.SingleSelection)

        # Sample events
        events = {
            (0, 2): [("10:00 Reels", "#1f6feb"), ("18:00 Stories", "#9e6a03")],
            (0, 4): [("12:00 Лента", "#238636"), ("15:45 Reels", "#1f6feb")],
            (0, 6): [("18:00 Stories", "#9e6a03")],
            (1, 0): [("12:00 Лента", "#238636")],
            (1, 2): [("15:00 Reels", "#1f6feb")],
            (1, 4): [("18:00 Stories", "#9e6a03")],
            (1, 6): [("15:45 Reels", "#1f6feb")],
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
        table.setMinimumHeight(180)
        layout.addWidget(table)

        return zone

    def _build_schedule_settings(self) -> QFrame:
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
        title.setObjectName("zoneTitle")
        title.setProperty("class", "yellow")
        header_layout.addWidget(title)

        layout.addWidget(header)

        # Tabs
        tabs_row = QHBoxLayout()
        tabs_row.setContentsMargins(12, 8, 12, 4)
        for tab_name, active in [("Общие настройки", True), ("Индивидуальное время", False)]:
            btn = QPushButton(tab_name)
            btn.setObjectName("topBtn")
            if active:
                btn.setProperty("class", "primary")
            btn.setStyleSheet("font-size: 11px;")
            tabs_row.addWidget(btn)
        tabs_row.addStretch()
        layout.addLayout(tabs_row)

        # Form
        form_widget = QWidget()
        form_layout = QFormLayout(form_widget)
        form_layout.setContentsMargins(12, 8, 12, 12)
        form_layout.setSpacing(8)

        tz_combo = QComboBox()
        tz_combo.addItem("(UTC+6:00) Алматы")
        form_layout.addRow("Часовой пояс", tz_combo)

        period_combo = QComboBox()
        period_combo.addItem("Ежедневно")
        period_combo.addItem("По будням")
        period_combo.addItem("Несколько раз в неделю")
        form_layout.addRow("Периодичность", period_combo)

        time_row = QHBoxLayout()
        time1 = QTimeEdit()
        time1.setTime(QTime(12, 0))
        time_row.addWidget(time1)
        time2 = QTimeEdit()
        time2.setTime(QTime(18, 0))
        time_row.addWidget(time2)
        add_time_btn = QPushButton("+ Добавить время")
        add_time_btn.setObjectName("topBtn")
        add_time_btn.setStyleSheet("font-size: 11px;")
        time_row.addWidget(add_time_btn)
        form_layout.addRow("Время публикации", time_row)

        count_combo = QComboBox()
        count_combo.addItem("1 публикация")
        count_combo.addItem("2 публикации")
        count_combo.addItem("3 публикации")
        form_layout.addRow("Количество за ввод", count_combo)

        repeat_row = QHBoxLayout()
        repeat_row.addWidget(QLabel("Повторять после завершения"))
        repeat_row.addStretch()
        repeat_check = QCheckBox("Да")
        repeat_check.setChecked(True)
        repeat_row.addWidget(repeat_check)
        form_layout.addRow(repeat_row)

        layout.addWidget(form_widget)

        # Save button
        save_btn = QPushButton("💾 Сохранить")
        save_btn.setObjectName("topBtn")
        save_btn.setProperty("class", "primary")
        save_btn.setStyleSheet("margin: 0 12px 12px 12px; font-size: 12px; font-weight: bold;")
        layout.addWidget(save_btn)

        return zone
'''

write("gui_sections/publications_section.py", publications)

print("\n=== Phase 1.2 v2 Complete ===")
print("Run START.bat to see the new interface.")