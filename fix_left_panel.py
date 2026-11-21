#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix: Rebuild left panel with global menu + project block + project sections.
Create placeholder sections for all 7 project sections.
Run: python fix_left_panel.py
"""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

def write(rel, content):
    p = BASE / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding='utf-8', newline='\n')
    print(f"  [OK] {rel}")

print("\n=== Rebuilding Left Panel + Section Placeholders ===\n")

# 1. gui_main.py — new left panel structure
print("[1/8] Writing gui_main.py...")

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

# Global navigation (not project-specific)
GLOBAL_NAV = [
    ("dashboard", "📊", "Дашборд"),
    ("projects", "📁", "Проекты"),
    ("settings", "⚙️", "Настройки"),
]

# Project sections
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


class MainWindow(QMainWindow):
    """New framework: global menu | project block | project sections | workspace | AI panel."""

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
        left.setFixedWidth(240)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        # Logo
        logo = QLabel("AI SMM MANAGER")
        logo.setObjectName("logo")
        left_layout.addWidget(logo)

        # Global nav
        self.global_buttons = {}
        for item_id, icon, label in GLOBAL_NAV:
            btn = QPushButton(f"{icon}  {label}")
            btn.setObjectName("navBtn")
            btn.clicked.connect(lambda checked, sid=item_id: self._on_nav(sid))
            self.global_buttons[item_id] = btn
            left_layout.addWidget(btn)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background-color: #30363d; max-height: 1px; margin: 8px 12px;")
        left_layout.addWidget(sep)

        # Project selector
        proj_selector_label = QLabel("ПРОЕКТ")
        proj_selector_label.setObjectName("projectBlock")
        left_layout.addWidget(proj_selector_label)

        self.project_combo = QComboBox()
        self.project_combo.setObjectName("projectCombo")
        self.project_combo.currentIndexChanged.connect(self._on_project_changed)
        left_layout.addWidget(self.project_combo)

        # Project preview block
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

        # Separator
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet("background-color: #30363d; max-height: 1px; margin: 8px 12px;")
        left_layout.addWidget(sep2)

        # Project sections
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
        
        # Update global buttons
        for sid, btn in self.global_buttons.items():
            btn.setProperty("active", sid == section_id)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        
        # Update section buttons
        for sid, btn in self.section_buttons.items():
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
        elif section_id in SECTION_TITLES:
            self._load_placeholder(title)
        else:
            self._load_placeholder(section_id)

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

# 2-8. Create placeholder sections
print("[2/8] Creating section placeholders...")

sections = [
    ("strategy", "Маркетинговая стратегия", "Целевая аудитория, позиционирование, анализ конкурентов"),
    ("content_plan", "Контент-план", "Планирование публикаций и рубрик"),
    ("calendar", "Календарь", "Визуальное планирование по дням"),
    ("shooting_tasks", "Задания на съемку", "ТЗ для фотографа/оператора"),
    ("media_content", "Медиа-контент", "Исходники, эталоны, готовые материалы"),
    ("other", "Прочие материалы", "Архив, буфер, документы, референсы"),
]

for sec_id, sec_name, sec_desc in sections:
    content = f'''"""Section: {sec_name}."""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt


class {sec_id.capitalize().replace("_", "")}Section(QWidget):
    """Placeholder for {sec_name} section."""

    def __init__(self, app_state=None, parent=None):
        super().__init__(parent)
        self.state = app_state
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        
        title = QLabel("{sec_name}")
        title.setStyleSheet("color: #e6edf3; font-size: 24px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        subtitle = QLabel("{sec_desc}")
        subtitle.setStyleSheet("color: #8b949e; font-size: 14px;")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)
        
        status = QLabel("Раздел в разработке")
        status.setStyleSheet("color: #8b949e; font-size: 12px; margin-top: 20px;")
        status.setAlignment(Qt.AlignCenter)
        layout.addWidget(status)
'''
    
    write(f"gui_sections/{sec_id}_section.py", content)

print("\n=== Rebuild Complete ===")
print("\nNew left panel structure:")
print("  [OK] Global nav: Дашборд, Проекты, Настройки")
print("  [OK] Project selector dropdown")
print("  [OK] Project preview block with stats")
print("  [OK] Project sections: 7 sections")
print("  [OK] Storage bar")
print("\nSection placeholders created:")
for sec_id, sec_name, _ in sections:
    print(f"  - {sec_name}")
print("\nRun START.bat to see the new structure.")