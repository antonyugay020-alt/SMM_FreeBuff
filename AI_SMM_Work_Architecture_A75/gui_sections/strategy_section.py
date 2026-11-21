"""Strategy section: Living document created via AI dialogue."""
import logging
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QTextEdit, QScrollArea, QSplitter, QMessageBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QListWidget, QListWidgetItem, QComboBox)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QTextDocument

logger = logging.getLogger(__name__)

# Demo strategy as document sections
DEMO_STRATEGY_SECTIONS = [
    {
        "id": "about",
        "title": "О проекте",
        "icon": "📋",
        "content": "Семейный теннисный клуб «Чемпион» работает с 2018 года. Основная специализация — обучение детей и взрослых теннису с нуля до соревновательного уровня. В клубе 4 корта (2 закрытых, 2 открытых), профессиональные тренеры с опытом работы в детских спортивных школах."
    },
    {
        "id": "audience",
        "title": "Целевая аудитория",
        "icon": "👥",
        "content": "Основной сегмент — родители детей 6-14 лет, которые ищут секцию для развития ребёнка. Они ценят профессиональный подход, безопасность и возможность отслеживать прогресс. Вторичный сегмент — взрослые любители 30-45 лет, играющие для здоровья и удовольствия. Третичный — профессионалы, готовящиеся к турнирам."
    },
    {
        "id": "positioning",
        "title": "Позиционирование",
        "icon": "🎯",
        "content": "«Первый шаг к большому теннису» — клуб, где каждый ученик получает персональный план развития. Мы не просто учим бить по мячу, мы воспитываем характер через спорт. Дружеская атмосфера сочетается с профессиональным подходом к тренировкам."
    },
    {
        "id": "utp",
        "title": "Уникальное торговое предложение",
        "icon": "💎",
        "content": "Первое занятие бесплатно + персональный план развития для каждого ученика. Родители получают ежемесячный отчёт о прогрессе ребёнка с видеоанализом техники. Взрослые участники могут гибко планировать тренировки через мобильное приложение."
    },
    {
        "id": "tone",
        "title": "Tone of Voice",
        "icon": "🗣️",
        "content": "Дружелюбный, мотивирующий, экспертный но не занудный. Мы говорим на языке родителей и детей, избегаем спортивного жаргона. Используем истории успеха учеников, показываем реальные эмоции с тренировок. Юмор уместен, но не в ущерб профессионализму."
    },
    {
        "id": "visual",
        "title": "Визуальный стиль",
        "icon": "🎨",
        "content": "Яркие цвета (оранжевый, синий, белый), динамичные фото с тренировок, минимум текста на изображениях. Акцент на эмоциях — радость победы, концентрация во время игры, командный дух. Шрифты современные, без засечек. Логотип — стилизованный мяч с крыльями."
    },
    {
        "id": "competitors",
        "title": "Анализ конкурентов",
        "icon": "🏆",
        "content": "Клуб «А» — известный бренд, но дорого и нет детских групп. Школа «Б» — дешевле, но старые корты и нет турниров. Наше преимущество — баланс цены и качества, фокус на детях, современная инфраструктура."
    },
    {
        "id": "channels",
        "title": "Каналы коммуникации",
        "icon": "📱",
        "content": "Instagram — основной канал (визуальный контент, stories с тренировок). VK — дополнительная аудитория (родители 35+). Telegram — быстрые новости и анонсы турниров. YouTube — длинные видео с советами тренеров и разборами техники."
    }
]

DEMO_KPIS = [
    {"metric": "Подписчики Instagram", "current": "3200", "target": "5000", "deadline": "31.12.2026"},
    {"metric": "Охват постов (средний)", "current": "7500", "target": "10000", "deadline": "31.12.2026"},
    {"metric": "Записи на пробное занятие", "current": "35/мес", "target": "50/мес", "deadline": "31.12.2026"},
    {"metric": "Вовлечённость (ER)", "current": "4.2%", "target": "6.0%", "deadline": "31.12.2026"},
    {"metric": "Публикаций в неделю", "current": "3", "target": "5", "deadline": "01.12.2026"},
]

DEMO_VERSIONS = []


class StrategyDocument(QWidget):
    """Strategy displayed as readable document."""
    action_requested = Signal(str, str)  # section_id, action

    def __init__(self, sections: List[Dict[str, Any]], parent=None):
        super().__init__(parent)
        self.sections = sections
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background-color: #0f1419;")

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(32, 32, 32, 32)
        content_layout.setSpacing(24)

        # Title
        title = QLabel("Стратегия проекта «Теннис»")
        title.setStyleSheet("color: #e6edf3; font-size: 28px; font-weight: bold; margin-bottom: 8px;")
        content_layout.addWidget(title)

        # subtitle = QLabel("Версия 1.1 · Обновлено 12.11.2026")  # REMOVED
#         subtitle.setStyleSheet("color: #8b949e; font-size: 13px; margin-bottom: 32px;")  # REMOVED (subtitle ref)
#         content_layout.addWidget(subtitle)  # REMOVED (subtitle ref)

        # Sections
        for section in self.sections:
            section_widget = self._create_section_widget(section)
            content_layout.addWidget(section_widget)

        content_layout.addStretch()

        scroll.setWidget(content)
        layout.addWidget(scroll, stretch=1)

    def _create_section_widget(self, section: Dict[str, Any]) -> QFrame:
        """Create a section with content and action buttons."""
        frame = QFrame()
        frame.setObjectName("zone")
        frame.setStyleSheet("""
            QFrame#zone {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 8px;
                padding: 0;
            }
        """)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        # Header with icon and title
        header = QHBoxLayout()
        icon_label = QLabel(section["icon"])
        icon_label.setStyleSheet("font-size: 20px;")
        header.addWidget(icon_label)

        title_label = QLabel(section["title"])
        title_label.setStyleSheet("color: #e6edf3; font-size: 18px; font-weight: bold;")
        header.addWidget(title_label)

        header.addStretch()
        layout.addLayout(header)

        # Content text
        content_label = QLabel(section["content"])
        content_label.setWordWrap(True)
        content_label.setStyleSheet("""
            color: #c9d1d9;
            font-size: 14px;
            line-height: 1.6;
            padding: 12px 0;
        """)
        layout.addWidget(content_label)

        # Action buttons
        actions = QHBoxLayout()
        actions.setSpacing(8)

        actions_data = [
            ("✏️ Редактировать", "edit"),
            ("🤖 Переформулировать", "rewrite"),
            ("💡 Альтернатива", "alternative"),
            ("🔍 Углубить", "deepen"),
        ]

        for text, action_id in actions_data:
            btn = QPushButton(text)
            btn.setObjectName("topBtn")
            btn.setStyleSheet("font-size: 11px; padding: 6px 12px;")
            btn.clicked.connect(lambda checked, sid=section["id"], aid=action_id: self.action_requested.emit(sid, aid))
            actions.addWidget(btn)

        actions.addStretch()
        layout.addLayout(actions)

        return frame


class StrategyTable(QWidget):
    """Strategy displayed as KPI table."""
    def __init__(self, kpis: List[Dict[str, Any]], parent=None):
        super().__init__(parent)
        self.kpis = kpis
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("📊 KPI и метрики стратегии")
        title.setStyleSheet("color: #e6edf3; font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        table = QTableWidget()
        table.setObjectName("calendar")
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["Метрика", "Сейчас", "Цель", "Дедлайн"])
        table.setRowCount(len(self.kpis))
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.verticalHeader().setVisible(False)

        for row, kpi in enumerate(self.kpis):
            for col, key in enumerate(["metric", "current", "target", "deadline"]):
                item = QTableWidgetItem(kpi.get(key, ""))
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                table.setItem(row, col, item)

        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        table.setMinimumHeight(300)
        layout.addWidget(table)

        # Progress summary
        summary = QFrame()
        summary.setStyleSheet("background-color: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 16px;")
        summary_layout = QVBoxLayout(summary)

        summary_title = QLabel("Прогресс выполнения")
        summary_title.setStyleSheet("color: #e6edf3; font-size: 14px; font-weight: bold;")
        summary_layout.addWidget(summary_title)

        for kpi in self.kpis:
            try:
                current = float(kpi["current"].replace("/мес", "").replace("%", ""))
                target = float(kpi["target"].replace("/мес", "").replace("%", ""))
                progress = min(100, int((current / target) * 100))
            except:
                progress = 0

            row = QHBoxLayout()
            label = QLabel(kpi["metric"])
            label.setStyleSheet("color: #c9d1d9; font-size: 12px; min-width: 200px;")
            row.addWidget(label)

            bar = QFrame()
            bar.setFixedHeight(8)
            bar.setStyleSheet(f"background-color: #21262d; border-radius: 4px;")
            bar_layout = QHBoxLayout(bar)
            bar_layout.setContentsMargins(0, 0, 0, 0)
            fill = QFrame()
            fill.setFixedHeight(8)
            color = "#238636" if progress >= 70 else "#9e6a03" if progress >= 40 else "#da3633"
            fill.setStyleSheet(f"background-color: {color}; border-radius: 4px; min-width: {progress}px; max-width: {progress}px;")
            bar_layout.addWidget(fill)
            bar_layout.addStretch()
            row.addWidget(bar, stretch=1)

            percent = QLabel(f"{progress}%")
            percent.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold; min-width: 40px;")
            row.addWidget(percent)

            summary_layout.addLayout(row)

        layout.addWidget(summary)
        layout.addStretch()


class StrategyMap(QWidget):
    """Strategy displayed as visual map (placeholder)."""
    def __init__(self, sections: List[Dict[str, Any]], parent=None):
        super().__init__(parent)
        self.sections = sections
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("🗺️ Карта стратегии")
        title.setStyleSheet("color: #e6edf3; font-size: 20px; font-weight: bold;")
        layout.addWidget(title)
# subtitle removed
#         subtitle.setStyleSheet("color: #8b949e; font-size: 13px;")  # REMOVED (subtitle ref)
#         layout.addWidget(subtitle)  # REMOVED (subtitle ref)

        # Placeholder map
        map_frame = QFrame()
        map_frame.setStyleSheet("background-color: #161b22; border: 2px dashed #30363d; border-radius: 8px; min-height: 400px;")
        map_layout = QVBoxLayout(map_frame)
        map_layout.setAlignment(Qt.AlignCenter)

        placeholder = QLabel("🗺️")
        placeholder.setStyleSheet("font-size: 80px; color: #8b949e;")
        placeholder.setAlignment(Qt.AlignCenter)
        map_layout.addWidget(placeholder)

        text = QLabel("Визуальная карта связей\n(в разработке)")
        text.setStyleSheet("color: #8b949e; font-size: 14px;")
        text.setAlignment(Qt.AlignCenter)
        map_layout.addWidget(text)

        layout.addWidget(map_frame, stretch=1)
        layout.addStretch()


# class VersionHistory(QWidget):
    pass  # Removed

class StrategySection(QWidget):
    """Strategy section: living document with multiple views."""

    def __init__(self, app_state: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.state = app_state
        self.current_mode = "document"
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

        title = QLabel("🎯 Стратегия проекта")
        title.setStyleSheet("color: #e6edf3; font-size: 18px; font-weight: bold;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Mode buttons
        self.mode_buttons = {}
        modes = [("📄 Документ", "document"), ("📊 Таблица", "table"), ("🗺️ Карта", "map")]
        for text, mode_id in modes:
            btn = QPushButton(text)
            btn.setObjectName("topBtn")
            if mode_id == self.current_mode:
                btn.setProperty("class", "primary")
            btn.setStyleSheet("font-size: 12px; padding: 6px 12px;")
            btn.clicked.connect(lambda checked, m=mode_id: self._switch_mode(m))
            self.mode_buttons[mode_id] = btn
            header_layout.addWidget(btn)

        # AI button
        ai_btn = QPushButton("🤖 Создать с AI")
        ai_btn.setObjectName("topBtn")
        ai_btn.setProperty("class", "primary")
        ai_btn.setStyleSheet("font-size: 13px; font-weight: bold; padding: 8px 16px; margin-left: 16px;")
        ai_btn.clicked.connect(self._on_ai_create)
        header_layout.addWidget(ai_btn)

        layout.addWidget(header)

        # Main splitter: content | version history
        splitter = QSplitter(Qt.Horizontal)

        # Content area
        self.content_area = QWidget()
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)

        self._load_content()

        splitter.addWidget(self.content_area)

        # Version history
        pass  # Version panel removed

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        splitter.setHandleWidth(6)
        splitter.setSizes([1000, 280])
        splitter.setStyleSheet("""
            QSplitter::handle { background-color: #30363d; border-radius: 2px; }
            QSplitter::handle:hover { background-color: #58a6ff; }
        """)

        layout.addWidget(splitter, stretch=1)

    def _load_content(self):
        """Load content based on current mode."""
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if self.current_mode == "document":
            widget = StrategyDocument(DEMO_STRATEGY_SECTIONS)
            widget.action_requested.connect(self._on_action_requested)
        elif self.current_mode == "table":
            widget = StrategyTable(DEMO_KPIS)
        elif self.current_mode == "map":
            widget = StrategyMap(DEMO_STRATEGY_SECTIONS)

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

    def _on_action_requested(self, section_id: str, action: str):
        """Handle action button click in document mode."""
        action_messages = {
            "edit": f"Открыть редактор раздела '{section_id}'",
            "rewrite": f"AI переформулирует раздел '{section_id}'",
            "alternative": f"AI предложит альтернативу для раздела '{section_id}'",
            "deepen": f"AI углубит раздел '{section_id}'",
        }
        msg = action_messages.get(action, f"Действие: {action}")
        QMessageBox.information(self, "Действие", f"{msg}\n\nВ полной версии это действие выполнит AI-менеджер.")

    def _on_ai_create(self):
        """AI strategy creation."""
        QMessageBox.information(
            self,
            "AI-создание стратегии",
            "В полной версии здесь начнётся диалог с AI-менеджером.\n\n"
            "AI задаст вопросы о проекте и сформирует живую стратегию."
        )

    def _on_version_selected(self, version: str):
        """Handle version selection."""
        QMessageBox.information(self, "Версия", f"Выбрана версия {version}\n\nВ реальной версии стратегия загрузится из этой версии.")
