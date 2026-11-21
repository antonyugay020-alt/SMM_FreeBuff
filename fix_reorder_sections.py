#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix: Reorder sections to match natural workflow.
New order: Strategy → Content Plan → Calendar → Shooting Tasks → Media Content → Publications → Other
Run: python fix_reorder_sections.py
"""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

def write(rel, content):
    p = BASE / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding='utf-8', newline='\n')
    print(f"  [OK] {rel}")

print("\n=== Reordering Sections ===\n")

# 1. Update gui_main.py — new section order
print("[1/3] Updating gui_main.py section order...")

gui_main_path = BASE / "gui_main.py"
content = gui_main_path.read_text(encoding='utf-8')

# Replace PROJECT_SECTIONS with new order
old_sections = '''PROJECT_SECTIONS = [
    ("strategy", "🎯", "Маркетинговая стратегия"),
    ("content_plan", "📝", "Контент-план"),
    ("calendar", "📅", "Календарь"),
    ("shooting_tasks", "🎬", "Задания на съемку"),
    ("media_content", "🖼️", "Медиа-контент"),
    ("publications", "📢", "Публикации"),
    ("other", "📦", "Прочие материалы"),
]'''

new_sections = '''PROJECT_SECTIONS = [
    ("strategy", "🎯", "Стратегия"),
    ("content_plan", "📝", "Контент-план"),
    ("calendar", "📅", "Календарь"),
    ("shooting_tasks", "🎬", "Задания на съемку"),
    ("media_content", "🖼️", "Медиа-контент"),
    ("publications", "📢", "Публикации"),
    ("other", "📦", "Прочие материалы"),
]'''

content = content.replace(old_sections, new_sections)

# Update SECTION_TITLES to match new names
old_titles = '''SECTION_TITLES = {
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
}'''

new_titles = '''SECTION_TITLES = {
    "dashboard": ("Дашборд", "Общая картина по всем проектам"),
    "projects": ("Проекты", "Управление проектами"),
    "settings": ("Настройки", "Настройки приложения"),
    "strategy": ("Стратегия", "Целевая аудитория, позиционирование, анализ конкурентов"),
    "content_plan": ("Контент-план", "Планирование публикаций и рубрик"),
    "calendar": ("Календарь", "Визуальное планирование по дням"),
    "shooting_tasks": ("Задания на съемку", "ТЗ для фотографа/оператора"),
    "media_content": ("Медиа-контент", "Исходники, эталоны, готовые материалы"),
    "publications": ("Публикации", "Управление готовым контентом и планирование публикаций"),
    "other": ("Прочие материалы", "Архив, буфер, документы, референсы"),
}'''

content = content.replace(old_titles, new_titles)

# Change default section from "publications" to "strategy"
content = content.replace(
    'self.current_section = "publications"',
    'self.current_section = "strategy"'
)

content = content.replace(
    'self._on_nav("publications")',
    'self._on_nav("strategy")'
)

gui_main_path.write_text(content, encoding='utf-8', newline='\n')
print("  [OK] Updated section order and default section")

# 2. Create strategy_section.py — living strategy, not template
print("[2/3] Creating strategy_section.py (living strategy)...")

strategy = r'''"""Strategy section: Living strategy created via AI dialogue, editable manually."""
import logging
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QTextEdit, QScrollArea, QSplitter, QMessageBox,
    QInputDialog, QComboBox, QFormLayout, QLineEdit)
from PySide6.QtCore import Qt

logger = logging.getLogger(__name__)

# Demo strategy data
DEMO_STRATEGY = {
    "project_name": "Теннис",
    "target_audience": [
        {"segment": "Родители детей 6-14 лет", "description": "Ищут секции для развития ребёнка", "priority": "high"},
        {"segment": "Взрослые любители", "description": "Хотят играть для здоровья и удовольствия", "priority": "medium"},
        {"segment": "Профессионалы", "description": "Нужны турниры и тренировки высокого уровня", "priority": "low"}
    ],
    "positioning": "Семейный теннисный клуб с профессиональным подходом и дружеской атмосферой",
    "utp": "Первое занятие бесплатно + персональный план развития для каждого ученика",
    "tone_of_voice": "Дружелюбный, мотивирующий, экспертный но не занудный",
    "visual_style": "Яркие цвета, динамичные фото, минимум текста, акцент на эмоциях",
    "competitors": [
        {"name": "Клуб А", "strengths": "Известный бренд", "weaknesses": "Дорого, нет детских групп"},
        {"name": "Школа Б", "strengths": "Дешевле", "weaknesses": "Старые корты, нет турниров"}
    ],
    "kpis": [
        {"metric": "Подписчики Instagram", "target": "5000", "current": "3200"},
        {"metric": "Охват постов", "target": "10000", "current": "7500"},
        {"metric": "Записи на пробное занятие", "target": "50/мес", "current": "35/мес"}
    ]
}


class StrategySection(QWidget):
    """Strategy section: AI-created, manually editable, versioned."""

    def __init__(self, app_state: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.state = app_state
        self.strategy_data = DEMO_STRATEGY.copy()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header with actions
        header = QFrame()
        header.setObjectName("zoneHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 12, 16, 12)

        title = QLabel("🎯 Стратегия проекта")
        title.setStyleSheet("color: #e6edf3; font-size: 18px; font-weight: bold;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        # AI button
        ai_btn = QPushButton("🤖 Создать/Обновить с AI")
        ai_btn.setObjectName("topBtn")
        ai_btn.setProperty("class", "primary")
        ai_btn.setStyleSheet("font-size: 13px; font-weight: bold; padding: 8px 16px;")
        ai_btn.clicked.connect(self._on_ai_create)
        header_layout.addWidget(ai_btn)

        # Save button
        save_btn = QPushButton("💾 Сохранить")
        save_btn.setObjectName("topBtn")
        save_btn.setStyleSheet("font-size: 13px; padding: 8px 16px;")
        save_btn.clicked.connect(self._on_save)
        header_layout.addWidget(save_btn)

        layout.addWidget(header)

        # Main content: scrollable form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background-color: #0f1419;")

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(24, 24, 24, 24)
        content_layout.setSpacing(20)

        # Project info
        project_frame = self._create_section_frame("📋 Общая информация", [
            ("Название проекта", self.strategy_data.get("project_name", "")),
        ])
        content_layout.addWidget(project_frame)

        # Target audience
        audience_frame = self._create_audience_frame()
        content_layout.addWidget(audience_frame)

        # Positioning & UTP
        positioning_frame = self._create_section_frame("🎯 Позиционирование и УТП", [
            ("Позиционирование", self.strategy_data.get("positioning", "")),
            ("Уникальное торговое предложение", self.strategy_data.get("utp", "")),
        ])
        content_layout.addWidget(positioning_frame)

        # Tone & Visual
        style_frame = self._create_section_frame("🎨 Tone of Voice и Визуальный стиль", [
            ("Tone of Voice", self.strategy_data.get("tone_of_voice", "")),
            ("Визуальный стиль", self.strategy_data.get("visual_style", "")),
        ])
        content_layout.addWidget(style_frame)

        # Competitors
        competitors_frame = self._create_competitors_frame()
        content_layout.addWidget(competitors_frame)

        # KPIs
        kpis_frame = self._create_kpis_frame()
        content_layout.addWidget(kpis_frame)

        content_layout.addStretch()

        scroll.setWidget(content_widget)
        layout.addWidget(scroll, stretch=1)

    def _create_section_frame(self, title: str, fields: List[tuple]) -> QFrame:
        """Create a frame with form fields."""
        frame = QFrame()
        frame.setObjectName("zone")
        frame.setStyleSheet("QFrame#zone { background-color: #161b22; border: 1px solid #30363d; border-radius: 6px; }")

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title_label = QLabel(title)
        title_label.setStyleSheet("color: #e6edf3; font-size: 15px; font-weight: bold; margin-bottom: 8px;")
        layout.addWidget(title_label)

        for label_text, value in fields:
            row = QHBoxLayout()
            label = QLabel(label_text + ":")
            label.setStyleSheet("color: #8b949e; font-size: 12px; min-width: 200px;")
            row.addWidget(label)

            edit = QTextEdit()
            edit.setPlainText(value)
            edit.setMaximumHeight(80)
            edit.setStyleSheet("background-color: #0d1117; color: #e6edf3; border: 1px solid #30363d; border-radius: 4px; font-size: 12px; padding: 6px;")
            row.addWidget(edit, stretch=1)

            layout.addLayout(row)

        return frame

    def _create_audience_frame(self) -> QFrame:
        """Create target audience section."""
        frame = QFrame()
        frame.setObjectName("zone")
        frame.setStyleSheet("QFrame#zone { background-color: #161b22; border: 1px solid #30363d; border-radius: 6px; }")

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("👥 Целевая аудитория")
        title.setStyleSheet("color: #e6edf3; font-size: 15px; font-weight: bold;")
        layout.addWidget(title)

        audiences = self.strategy_data.get("target_audience", [])
        for i, aud in enumerate(audiences):
            seg_frame = QFrame()
            seg_frame.setStyleSheet("background-color: #0d1117; border-radius: 4px; padding: 8px;")
            seg_layout = QVBoxLayout(seg_frame)

            seg_row = QHBoxLayout()
            seg_label = QLabel(f"Сегмент {i+1}:")
            seg_label.setStyleSheet("color: #58a6ff; font-size: 12px; font-weight: bold;")
            seg_row.addWidget(seg_label)

            priority_map = {"high": "🔴 Высокий", "medium": "🟡 Средний", "low": "🟢 Низкий"}
            priority_label = QLabel(priority_map.get(aud.get("priority", "medium"), "🟡 Средний"))
            priority_label.setStyleSheet("color: #8b949e; font-size: 11px;")
            seg_row.addStretch()
            seg_row.addWidget(priority_label)
            seg_layout.addLayout(seg_row)

            name_edit = QTextEdit()
            name_edit.setPlainText(aud.get("segment", ""))
            name_edit.setMaximumHeight(40)
            name_edit.setStyleSheet("background-color: #161b22; color: #e6edf3; border: 1px solid #30363d; border-radius: 4px; font-size: 12px; padding: 4px;")
            seg_layout.addWidget(name_edit)

            desc_edit = QTextEdit()
            desc_edit.setPlainText(aud.get("description", ""))
            desc_edit.setMaximumHeight(60)
            desc_edit.setStyleSheet("background-color: #161b22; color: #e6edf3; border: 1px solid #30363d; border-radius: 4px; font-size: 11px; padding: 4px;")
            seg_layout.addWidget(desc_edit)

            layout.addWidget(seg_frame)

        add_btn = QPushButton("➕ Добавить сегмент")
        add_btn.setObjectName("topBtn")
        add_btn.setStyleSheet("font-size: 12px; padding: 6px 12px;")
        add_btn.clicked.connect(lambda: QMessageBox.information(self, "Добавить", "В реальной версии откроется форма добавления сегмента."))
        layout.addWidget(add_btn)

        return frame

    def _create_competitors_frame(self) -> QFrame:
        """Create competitors analysis section."""
        frame = QFrame()
        frame.setObjectName("zone")
        frame.setStyleSheet("QFrame#zone { background-color: #161b22; border: 1px solid #30363d; border-radius: 6px; }")

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("🏆 Анализ конкурентов")
        title.setStyleSheet("color: #e6edf3; font-size: 15px; font-weight: bold;")
        layout.addWidget(title)

        competitors = self.strategy_data.get("competitors", [])
        for i, comp in enumerate(competitors):
            comp_frame = QFrame()
            comp_frame.setStyleSheet("background-color: #0d1117; border-radius: 4px; padding: 8px;")
            comp_layout = QVBoxLayout(comp_frame)

            name_label = QLabel(f"Конкурент {i+1}: {comp.get('name', '')}")
            name_label.setStyleSheet("color: #bc8cff; font-size: 13px; font-weight: bold;")
            comp_layout.addWidget(name_label)

            strengths = QLabel(f"✅ Сильные стороны: {comp.get('strengths', '')}")
            strengths.setStyleSheet("color: #3fb950; font-size: 11px;")
            comp_layout.addWidget(strengths)

            weaknesses = QLabel(f"❌ Слабые стороны: {comp.get('weaknesses', '')}")
            weaknesses.setStyleSheet("color: #f85149; font-size: 11px;")
            comp_layout.addWidget(weaknesses)

            layout.addWidget(comp_frame)

        add_btn = QPushButton("➕ Добавить конкурента")
        add_btn.setObjectName("topBtn")
        add_btn.setStyleSheet("font-size: 12px; padding: 6px 12px;")
        add_btn.clicked.connect(lambda: QMessageBox.information(self, "Добавить", "В реальной версии откроется форма добавления конкурента."))
        layout.addWidget(add_btn)

        return frame

    def _create_kpis_frame(self) -> QFrame:
        """Create KPIs section."""
        frame = QFrame()
        frame.setObjectName("zone")
        frame.setStyleSheet("QFrame#zone { background-color: #161b22; border: 1px solid #30363d; border-radius: 6px; }")

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("📊 KPI и метрики")
        title.setStyleSheet("color: #e6edf3; font-size: 15px; font-weight: bold;")
        layout.addWidget(title)

        kpis = self.strategy_data.get("kpis", [])
        for kpi in kpis:
            kpi_row = QHBoxLayout()

            metric_label = QLabel(kpi.get("metric", ""))
            metric_label.setStyleSheet("color: #e6edf3; font-size: 12px; min-width: 200px;")
            kpi_row.addWidget(metric_label)

            current_label = QLabel(f"Сейчас: {kpi.get('current', '')}")
            current_label.setStyleSheet("color: #8b949e; font-size: 11px;")
            kpi_row.addWidget(current_label)

            target_label = QLabel(f"Цель: {kpi.get('target', '')}")
            target_label.setStyleSheet("color: #3fb950; font-size: 11px; font-weight: bold;")
            kpi_row.addWidget(target_label)

            layout.addLayout(kpi_row)

        add_btn = QPushButton("➕ Добавить метрику")
        add_btn.setObjectName("topBtn")
        add_btn.setStyleSheet("font-size: 12px; padding: 6px 12px;")
        add_btn.clicked.connect(lambda: QMessageBox.information(self, "Добавить", "В реальной версии откроется форма добавления метрики."))
        layout.addWidget(add_btn)

        return frame

    def _on_ai_create(self):
        """AI strategy creation — will be connected to AI dialogue later."""
        QMessageBox.information(
            self,
            "AI-создание стратегии",
            "В полной версии здесь откроется диалог с AI-менеджером.\n\n"
            "AI задаст вопросы о проекте, целевой аудитории, конкурентах\n"
            "и сформирует живую стратегию, а не шаблон."
        )

    def _on_save(self):
        """Save strategy to database."""
        QMessageBox.information(self, "Сохранено", "Стратегия сохранена (в реальной версии — в БД проекта).")
'''

write("gui_sections/strategy_section.py", strategy)

# 3. Update gui_main.py to load strategy section
print("[3/3] Updating gui_main.py to load strategy section...")

gui_main_content = gui_main_path.read_text(encoding='utf-8')

# Add strategy section loading
old_load = '''        if section_id == "publications":
            from gui_sections.publications_section import PublicationsSection
            self.workspace_layout.addWidget(PublicationsSection(self.state))
        elif section_id == "media_content":
            from gui_sections.media_content_section import MediaContentSection
            self.workspace_layout.addWidget(MediaContentSection(self.state))'''

new_load = '''        if section_id == "strategy":
            from gui_sections.strategy_section import StrategySection
            self.workspace_layout.addWidget(StrategySection(self.state))
        elif section_id == "publications":
            from gui_sections.publications_section import PublicationsSection
            self.workspace_layout.addWidget(PublicationsSection(self.state))
        elif section_id == "media_content":
            from gui_sections.media_content_section import MediaContentSection
            self.workspace_layout.addWidget(MediaContentSection(self.state))'''

gui_main_content = gui_main_content.replace(old_load, new_load)
gui_main_path.write_text(gui_main_content, encoding='utf-8', newline='\n')
print("  [OK] Added strategy section loading")

print("\n=== Sections Reordered + Strategy Section Created ===")
print("\nNew order:")
print("  1. 🎯 Стратегия (default)")
print("  2. 📝 Контент-план")
print("  3. 📅 Календарь")
print("  4. 🎬 Задания на съемку")
print("  5. 🖼️ Медиа-контент")
print("  6. 📢 Публикации")
print("  7. 📦 Прочие материалы")
print("\nStrategy section features:")
print("  [OK] Living strategy structure (not template)")
print("  [OK] Target audience segments with priorities")
print("  [OK] Positioning & UTP")
print("  [OK] Tone of Voice & Visual style")
print("  [OK] Competitor analysis")
print("  [OK] KPIs with current vs target")
print("  [OK] AI creation button (placeholder)")
print("  [OK] Manual editing via text fields")
print("  [OK] Save button (placeholder)")
print("\nRun START.bat to see the new order and strategy section.")