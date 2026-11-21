#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix: Create Media Content section with 3 zones (Sources, References, Ready).
Run: python fix_media_content.py
"""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

def write(rel, content):
    p = BASE / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding='utf-8', newline='\n')
    print(f"  [OK] {rel}")

print("\n=== Creating Media Content Section ===\n")

# 1. media_content_section.py
print("[1/2] Writing media_content_section.py...")

media_content = r'''"""Media Content section: Sources, References, Ready materials."""
import logging
from pathlib import Path
from typing import Dict, Any, List

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QGridLayout, QScrollArea, QComboBox, QCheckBox,
    QTextEdit, QSplitter, QAbstractItemView)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

logger = logging.getLogger(__name__)

# Demo data
DEMO_SOURCES = [
    {"name": "raw_001.jpg", "type": "image", "size": "4032x3024", "date": "15.10.2026"},
    {"name": "raw_002.jpg", "type": "image", "size": "4032x3024", "date": "15.10.2026"},
    {"name": "raw_003.mp4", "type": "video", "size": "1920x1080", "date": "14.10.2026"},
    {"name": "raw_004.jpg", "type": "image", "size": "3024x4032", "date": "14.10.2026"},
    {"name": "raw_005.jpg", "type": "image", "size": "4032x3024", "date": "13.10.2026"},
    {"name": "raw_006.mp4", "type": "video", "size": "1080x1920", "date": "13.10.2026"},
]

DEMO_REFERENCES = [
    {"name": "ref_cafe_style.jpg", "type": "image", "category": "Лента", "size": "1080x1080"},
    {"name": "ref_reels_example.mp4", "type": "video", "category": "Reels", "size": "1080x1920"},
    {"name": "ref_stories_mood.jpg", "type": "image", "category": "Stories", "size": "1080x1920"},
    {"name": "ref_color_palette.jpg", "type": "image", "category": "Общий", "size": "1920x1080"},
]

DEMO_READY = [
    {"name": "tennis_001.jpg", "status": "approved", "type": "image", "size": "1920x2560"},
    {"name": "tennis_002.jpg", "status": "approved", "type": "image", "size": "1920x2560"},
    {"name": "reels_001.mp4", "status": "approved", "type": "video", "size": "1080x1920"},
    {"name": "coffee_story.jpg", "status": "pending", "type": "image", "size": "1080x1920"},
]


class MediaCard(QFrame):
    """Single media card with checkbox."""
    def __init__(self, file_data: Dict[str, Any], zone: str, parent=None):
        super().__init__(parent)
        self.file_data = file_data
        self.zone = zone
        self.selected = False
        
        self.setObjectName("thumb")
        self.setFrameShape(QFrame.NoFrame)
        self.setStyleSheet("""
            QFrame#thumb {
                background-color: #0d1117;
                border: 2px solid #30363d;
                border-radius: 4px;
            }
            QFrame#thumb:hover { border-color: #58a6ff; }
            QFrame#thumb.selected { border-color: #1f6feb; background-color: #161b22; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Checkbox + preview row
        top_row = QHBoxLayout()
        top_row.setContentsMargins(4, 4, 4, 0)
        
        self.checkbox = QCheckBox()
        self.checkbox.setStyleSheet("""
            QCheckBox { background-color: rgba(0,0,0,0.7); border-radius: 2px; spacing: 0; padding: 2px; margin: 0; }
            QCheckBox::indicator { width: 14px; height: 14px; border: 1px solid #4e4e52; border-radius: 2px; background-color: #1e1e1e; }
            QCheckBox::indicator:checked { background-color: #1f6feb; border-color: #1f6feb; }
        """)
        self.checkbox.stateChanged.connect(self._on_checked)
        top_row.addWidget(self.checkbox)
        top_row.addStretch()
        
        # Type icon
        type_icon = "🎬" if file_data["type"] == "video" else "🖼️"
        type_label = QLabel(type_icon)
        type_label.setStyleSheet("font-size: 16px;")
        top_row.addWidget(type_label)
        
        layout.addLayout(top_row)
        
        # Preview area
        preview = QLabel()
        preview.setAlignment(Qt.AlignCenter)
        preview.setMinimumHeight(80)
        preview.setStyleSheet("background-color: #21262d; border-radius: 4px 4px 0 0; font-size: 28px; color: #8b949e;")
        
        # Try to load real image
        media_dir = Path(__file__).resolve().parent.parent.parent / "media" / "images"
        img_path = media_dir / file_data["name"]
        if img_path.exists():
            try:
                pm = QPixmap(str(img_path))
                if not pm.isNull():
                    scaled = pm.scaled(140, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    preview.setPixmap(scaled)
                    preview.setStyleSheet("background-color: #21262d; border-radius: 4px 4px 0 0;")
            except Exception:
                preview.setText(type_icon)
        else:
            preview.setText(type_icon)
        
        layout.addWidget(preview)
        
        # Name
        name_label = QLabel(file_data["name"][:18] + ("..." if len(file_data["name"]) > 18 else ""))
        name_label.setStyleSheet("color: #c9d1d9; font-size: 10px; padding: 4px 6px 0 6px;")
        layout.addWidget(name_label)
        
        # Size
        size_label = QLabel(file_data["size"])
        size_label.setStyleSheet("color: #8b949e; font-size: 9px; padding: 0 6px 4px 6px;")
        layout.addWidget(size_label)
        
        # Category (for references)
        if "category" in file_data:
            cat_label = QLabel(file_data["category"])
            cat_label.setStyleSheet("color: #58a6ff; font-size: 9px; padding: 0 6px 4px 6px; font-weight: bold;")
            layout.addWidget(cat_label)
        
        # Status (for ready)
        if "status" in file_data:
            status_map = {"approved": ("✅ Одобрено", "#238636"), "pending": ("⏳ На проверке", "#9e6a03"), "rejected": ("❌ Отклонено", "#da3633")}
            status_text, status_color = status_map.get(file_data["status"], ("?", "#8b949e"))
            status_label = QLabel(status_text)
            status_label.setStyleSheet(f"color: {status_color}; font-size: 9px; padding: 0 6px 4px 6px; font-weight: bold;")
            layout.addWidget(status_label)
        
        self.setMinimumWidth(130)
        self.setMaximumWidth(150)
    
    def _on_checked(self, state):
        self.selected = state == Qt.Checked
        if self.selected:
            self.setStyleSheet("""
                QFrame#thumb { background-color: #161b22; border: 2px solid #1f6feb; border-radius: 4px; }
            """)
        else:
            self.setStyleSheet("""
                QFrame#thumb { background-color: #0d1117; border: 2px solid #30363d; border-radius: 4px; }
                QFrame#thumb:hover { border-color: #58a6ff; }
            """)


class MediaColumn(QFrame):
    """One of three columns: Sources, References, Ready."""
    def __init__(self, title: str, icon: str, color: str, files: List[Dict[str, Any]], zone: str, parent=None):
        super().__init__(parent)
        self.zone = zone
        self.files = files
        self.cards: List[MediaCard] = []
        
        self.setObjectName("zone")
        self.setStyleSheet(f"""
            QFrame#zone {{
                background-color: #161b22;
                border: 1px solid #30363d;
                border-top: 3px solid {color};
                border-radius: 6px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header
        header = QFrame()
        header.setObjectName("zoneHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 8, 12, 8)
        
        title_label = QLabel(f"{icon} {title}")
        title_label.setStyleSheet("color: #e6edf3; font-size: 14px; font-weight: bold;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        count_label = QLabel(f"{len(files)}")
        count_label.setStyleSheet(f"background-color: {color}; color: white; border-radius: 10px; padding: 2px 8px; font-weight: bold;")
        header_layout.addWidget(count_label)
        
        layout.addWidget(header)
        
        # Action buttons
        actions = QHBoxLayout()
        actions.setContentsMargins(12, 8, 12, 4)
        
        if zone == "sources":
            upload_btn = QPushButton("📥 Загрузить")
            upload_btn.setObjectName("topBtn")
            upload_btn.setStyleSheet("font-size: 11px;")
            actions.addWidget(upload_btn)
        elif zone == "references":
            add_btn = QPushButton("➕ Добавить")
            add_btn.setObjectName("topBtn")
            add_btn.setStyleSheet("font-size: 11px;")
            actions.addWidget(add_btn)
        elif zone == "ready":
            approve_btn = QPushButton("✅ Одобрить")
            approve_btn.setObjectName("topBtn")
            approve_btn.setStyleSheet("font-size: 11px; background-color: #238636; color: white; border: none;")
            actions.addWidget(approve_btn)
            
            reject_btn = QPushButton("❌ Отклонить")
            reject_btn.setObjectName("topBtn")
            reject_btn.setStyleSheet("font-size: 11px; background-color: #da3633; color: white; border: none;")
            actions.addWidget(reject_btn)
        
        actions.addStretch()
        layout.addLayout(actions)
        
        # Cards grid
        grid_scroll = QScrollArea()
        grid_scroll.setWidgetResizable(True)
        grid_scroll.setStyleSheet("border: none; background-color: #0d1117;")
        
        grid_widget = QWidget()
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setSpacing(8)
        grid_layout.setContentsMargins(12, 8, 12, 12)
        
        row, col = 0, 0
        for file_data in files:
            card = MediaCard(file_data, zone)
            self.cards.append(card)
            grid_layout.addWidget(card, row, col)
            col += 1
            if col >= 3:
                col = 0
                row += 1
        
        grid_scroll.setWidget(grid_widget)
        layout.addWidget(grid_scroll, stretch=1)


class ProcessingPanel(QWidget):
    """Processing panel: appears when source is clicked."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #161b22; border-left: 1px solid #30363d;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        
        # Title
        title = QLabel("🎨 Обработка")
        title.setStyleSheet("color: #e6edf3; font-size: 14px; font-weight: bold;")
        layout.addWidget(title)
        
        # Source preview
        self.source_preview = QLabel("Выберите исходник")
        self.source_preview.setAlignment(Qt.AlignCenter)
        self.source_preview.setMinimumHeight(150)
        self.source_preview.setStyleSheet("background-color: #0d1117; border-radius: 4px; font-size: 14px; color: #8b949e;")
        layout.addWidget(self.source_preview)
        
        # Reference selector
        ref_label = QLabel("Эталон (опционально):")
        ref_label.setStyleSheet("color: #8b949e; font-size: 11px;")
        layout.addWidget(ref_label)
        
        self.ref_combo = QComboBox()
        self.ref_combo.setObjectName("filterCombo")
        self.ref_combo.addItem("— без эталона —")
        self.ref_combo.addItem("ref_cafe_style.jpg")
        self.ref_combo.addItem("ref_reels_example.mp4")
        layout.addWidget(self.ref_combo)
        
        # Text request
        req_label = QLabel("Запрос на обработку:")
        req_label.setStyleSheet("color: #8b949e; font-size: 11px;")
        layout.addWidget(req_label)
        
        self.request_input = QTextEdit()
        self.request_input.setObjectName("chatInput")
        self.request_input.setPlaceholderText("Например: убери фон, сделай теплее, добавь объект справа...")
        self.request_input.setMaximumHeight(100)
        layout.addWidget(self.request_input)
        
        # Process button
        process_btn = QPushButton("⚡ Обработать")
        process_btn.setObjectName("topBtn")
        process_btn.setProperty("class", "primary")
        process_btn.setStyleSheet("font-size: 13px; font-weight: bold; padding: 10px;")
        layout.addWidget(process_btn)
        
        # Result preview
        result_label = QLabel("Результат:")
        result_label.setStyleSheet("color: #8b949e; font-size: 11px; margin-top: 8px;")
        layout.addWidget(result_label)
        
        self.result_preview = QLabel("Здесь появится результат обработки")
        self.result_preview.setAlignment(Qt.AlignCenter)
        self.result_preview.setMinimumHeight(120)
        self.result_preview.setStyleSheet("background-color: #0d1117; border: 2px dashed #30363d; border-radius: 4px; font-size: 12px; color: #8b949e;")
        layout.addWidget(self.result_preview)
        
        layout.addStretch()


class MediaContentSection(QWidget):
    """Media Content section with 3 zones + processing panel."""
    
    def __init__(self, app_state: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.state = app_state
        self._build_ui()
    
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Main splitter: 3 columns | processing panel
        splitter = QSplitter(Qt.Horizontal)
        
        # Left: 3 columns
        columns_container = QWidget()
        columns_layout = QHBoxLayout(columns_container)
        columns_layout.setContentsMargins(16, 16, 16, 16)
        columns_layout.setSpacing(16)
        
        self.sources_col = MediaColumn("Исходники", "📥", "#58a6ff", DEMO_SOURCES, "sources")
        self.references_col = MediaColumn("Эталоны", "🎯", "#bc8cff", DEMO_REFERENCES, "references")
        self.ready_col = MediaColumn("Готовые материалы", "✅", "#3fb950", DEMO_READY, "ready")
        
        columns_layout.addWidget(self.sources_col, stretch=1)
        columns_layout.addWidget(self.references_col, stretch=1)
        columns_layout.addWidget(self.ready_col, stretch=1)
        
        splitter.addWidget(columns_container)
        
        # Right: processing panel
        self.processing_panel = ProcessingPanel()
        self.processing_panel.setFixedWidth(320)
        splitter.addWidget(self.processing_panel)
        
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        
        layout.addWidget(splitter, stretch=1)
'''

write("gui_sections/media_content_section.py", media_content)

# 2. Update gui_main.py to use new section
print("[2/2] Updating gui_main.py...")

gui_main = r'''"""Main window: global menu | project block | project sections."""
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

GLOBAL_NAV = [
    ("dashboard", "📊", "Дашборд"),
    ("projects", "📁", "Проекты"),
    ("settings", "⚙️", "Настройки"),
]

PROJECT_SECTIONS = [
    ("strategy", "🎯", "Маркетинговая стратегия"),
    ("content_plan", "📝", "Контент-план"),
    ("calendar", "📅", "Календарь"),
    ("shooting_tasks", "🎬", "Задания на съемку"),
    ("media_content", "🖼️", "Медиа-контент"),
    ("publications", "📢", "Публикации"),
    ("other", "📦", "Прочие материалы"),
]

SECTION_TITLES = {
    "dashboard": ("Дашборд", "Общая картина по всем проектам"),
    "projects": ("Проекты", "Управление проектами"),
    "settings": ("Настройки", "Настройки приложения"),
    "strategy": ("Маркетинговая стратегия", "Целевая аудитория, позиционирование, анализ конкурентов"),
    "content_plan": ("Контент-план", "Планирование публикаций и рубрик"),
    "calendar": ("Календарь", "Визуальное планирование по дням"),
    "shooting_tasks": ("Задания на съемку", "ТЗ для фотографа/оператора"),
    "media_content": ("Медиа-контент", "Исходники, эталоны, готовые материалы"),
    "publications": ("Публикации", "Управление готовым контентом и планирование публикаций в Instagram"),
    "other": ("Прочие материалы", "Архив, буфер, документы, референсы"),
}

SECTIONS_WITH_IMPL = {"publications", "media_content"}


class MainWindow(QMainWindow):
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

        # LEFT PANEL
        left = QWidget()
        left.setObjectName("leftPanel")
        left.setFixedWidth(240)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        logo = QLabel("AI SMM MANAGER")
        logo.setObjectName("logo")
        left_layout.addWidget(logo)

        self.global_buttons = {}
        for item_id, icon, label in GLOBAL_NAV:
            btn = QPushButton(f"{icon}  {label}")
            btn.setObjectName("navBtn")
            btn.clicked.connect(lambda checked, sid=item_id: self._on_nav(sid))
            self.global_buttons[item_id] = btn
            left_layout.addWidget(btn)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background-color: #30363d; max-height: 1px; margin: 8px 12px;")
        left_layout.addWidget(sep)

        proj_selector_label = QLabel("ПРОЕКТ")
        proj_selector_label.setObjectName("projectBlock")
        left_layout.addWidget(proj_selector_label)

        self.project_combo = QComboBox()
        self.project_combo.setObjectName("projectCombo")
        self.project_combo.currentIndexChanged.connect(self._on_project_changed)
        left_layout.addWidget(self.project_combo)

        self.proj_preview = QLabel("📷")
        self.proj_preview.setAlignment(Qt.AlignCenter)
        self.proj_preview.setMinimumHeight(80)
        self.proj_preview.setStyleSheet("background-color: #0d1117; border-radius: 4px; margin: 8px; font-size: 32px;")
        left_layout.addWidget(self.proj_preview)

        self.proj_name = QLabel("Не выбран")
        self.proj_name.setObjectName("projectName")
        left_layout.addWidget(self.proj_name)

        self.proj_stats = QLabel("0 исходников\n0 готовых\n0 на проверке")
        self.proj_stats.setObjectName("projectStats")
        left_layout.addWidget(self.proj_stats)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet("background-color: #30363d; max-height: 1px; margin: 8px 12px;")
        left_layout.addWidget(sep2)

        sections_label = QLabel("РАЗДЕЛЫ ПРОЕКТА")
        sections_label.setObjectName("projectBlock")
        left_layout.addWidget(sections_label)

        self.section_buttons = {}
        sections_scroll = QScrollArea()
        sections_scroll.setWidgetResizable(True)
        sections_scroll.setStyleSheet("border: none; background: transparent;")
        sections_widget = QWidget()
        sections_layout = QVBoxLayout(sections_widget)
        sections_layout.setContentsMargins(8, 4, 8, 4)
        sections_layout.setSpacing(4)

        for item_id, icon, label in PROJECT_SECTIONS:
            btn = QPushButton(f"{icon}  {label}")
            btn.setObjectName("navBtn")
            btn.clicked.connect(lambda checked, sid=item_id: self._on_nav(sid))
            self.section_buttons[item_id] = btn
            sections_layout.addWidget(btn)

        sections_layout.addStretch()
        sections_scroll.setWidget(sections_widget)
        left_layout.addWidget(sections_scroll, stretch=1)

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

        # CENTER
        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)

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

        search = QLineEdit()
        search.setObjectName("searchBox")
        search.setPlaceholderText("🔍 Поиск по файлам, тегам, описанию...")
        search.setFixedWidth(280)
        top_layout.addWidget(search)

        refresh_btn = QPushButton("🔄 Обновить")
        refresh_btn.setObjectName("topBtn")
        top_layout.addWidget(refresh_btn)

        import_btn = QPushButton("📥 Импорт медиа")
        import_btn.setObjectName("topBtn")
        import_btn.setProperty("class", "primary")
        top_layout.addWidget(import_btn)

        center_layout.addWidget(top_bar)

        self.workspace_scroll = QScrollArea()
        self.workspace_scroll.setWidgetResizable(True)
        self.workspace_scroll.setStyleSheet("border: none; background-color: #0f1419;")

        self.workspace_content = QWidget()
        self.workspace_layout = QVBoxLayout(self.workspace_content)
        self.workspace_layout.setContentsMargins(0, 0, 0, 0)
        self.workspace_layout.setSpacing(0)

        self.workspace_scroll.setWidget(self.workspace_content)
        center_layout.addWidget(self.workspace_scroll, stretch=1)

        main_layout.addWidget(center, stretch=1)

        # RIGHT: AI Panel
        logs_dir = self.state.get("logs_dir", str(ROOT_DIR / "data" / "logs"))
        history_path = str(Path(logs_dir) / "ai_chat_history.json")
        self.ai_panel = AIPanel(history_path)
        self.ai_panel.setFixedWidth(360)
        main_layout.addWidget(self.ai_panel)

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
        
        for sid, btn in self.global_buttons.items():
            btn.setProperty("active", sid == section_id)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        
        for sid, btn in self.section_buttons.items():
            btn.setProperty("active", sid == section_id)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        title, subtitle = SECTION_TITLES.get(section_id, (section_id, ""))
        self.section_title.setText(title)
        self.section_subtitle.setText(subtitle)

        while self.workspace_layout.count():
            item = self.workspace_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if section_id == "publications":
            from gui_sections.publications_section import PublicationsSection
            self.workspace_layout.addWidget(PublicationsSection(self.state))
        elif section_id == "media_content":
            from gui_sections.media_content_section import MediaContentSection
            self.workspace_layout.addWidget(MediaContentSection(self.state))
        else:
            placeholder = QLabel(f'Раздел "{title}" — в разработке')
            placeholder.setAlignment(Qt.AlignCenter)
            placeholder.setStyleSheet("color: #8b949e; font-size: 16px; padding: 60px;")
            self.workspace_layout.addWidget(placeholder)

        self.statusBar().showMessage(f"Раздел: {title}")

    def _on_project_changed(self, index: int):
        if index < 0 or index >= len(self.projects):
            return
        proj = self.projects[index]
        self.current_project_id = proj["id"]
        self.proj_name.setText(proj["name"])
        self.statusBar().showMessage(f"Проект: {proj['name']}")
'''

write("gui_main.py", gui_main)

print("\n=== Media Content Section Created ===")
print("\nFeatures:")
print("  [OK] 3 columns: Sources, References, Ready")
print("  [OK] Checkboxes on each card for mass operations")
print("  [OK] Processing panel on the right (source + reference + request + result)")
print("  [OK] Color-coded column borders (blue/purple/green)")
print("  [OK] Real image previews from media/images/ when available")
print("  [OK] Category tags for references (Stories/Reels/Feed/General)")
print("  [OK] Status badges for ready materials")
print("\nRun START.bat and click 'Медиа-контент' in the left panel.")