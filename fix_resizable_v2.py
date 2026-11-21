#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix v2: Rewrite gui_main.py with QSplitter for resizable panels.
Run: python fix_resizable_v2.py
"""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

def write(rel, content):
    p = BASE / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding='utf-8', newline='\n')
    print(f"  [OK] {rel}")

print("\n=== Resizable Panels v2 ===\n")

gui_main = r'''"""Main window: global menu | project block | project sections. Resizable via QSplitter."""
import logging
from pathlib import Path
from typing import Dict, Any, List

from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QScrollArea, QFrame, QComboBox, QLineEdit, QProgressBar, QSplitter)
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

SPLITTER_STYLE = """
QSplitter::handle {
    background-color: #30363d;
}
QSplitter::handle:hover {
    background-color: #58a6ff;
}
"""


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

        # === LEFT PANEL ===
        left = QWidget()
        left.setObjectName("leftPanel")
        left.setMinimumWidth(180)
        left.setMaximumWidth(500)
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

        # === CENTER ===
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

        # === RIGHT: AI Panel ===
        logs_dir = self.state.get("logs_dir", str(ROOT_DIR / "data" / "logs"))
        history_path = str(Path(logs_dir) / "ai_chat_history.json")
        self.ai_panel = AIPanel(history_path)
        self.ai_panel.setMinimumWidth(280)
        self.ai_panel.setMaximumWidth(600)

        # === MAIN SPLITTER ===
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.addWidget(left)
        self.main_splitter.addWidget(center)
        self.main_splitter.addWidget(self.ai_panel)
        self.main_splitter.setStretchFactor(0, 0)
        self.main_splitter.setStretchFactor(1, 1)
        self.main_splitter.setStretchFactor(2, 0)
        self.main_splitter.setSizes([240, 1000, 360])
        self.main_splitter.setHandleWidth(4)
        self.main_splitter.setStyleSheet(SPLITTER_STYLE)

        main_layout.addWidget(self.main_splitter)

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

print("\n=== Resizable Panels v2 Complete ===")
print("\nChanges:")
print("  [OK] Main window uses QSplitter for 3 panels")
print("  [OK] Left panel: 180-500px (default 240px)")
print("  [OK] Center: flexible (takes remaining space)")
print("  [OK] Right (AI): 280-600px (default 360px)")
print("  [OK] Splitter handles: 4px wide, blue on hover")
print("\nDrag panel borders to resize them.")
print("\nRun START.bat to test.")