"""Brand profile: пустое состояние до шага 3, потом заполняется AI-диалогом."""
import logging
from typing import Any, Dict

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QFrame,
    QScrollArea, QFormLayout)
from PySide6.QtCore import Qt

from gui_theme import TEXT, MUTED, TEAL

logger = logging.getLogger(__name__)

FIELDS = [
    ("client_name", "Клиент / бренд"),
    ("niche", "Ниша"),
    ("city", "География"),
    ("audience", "Целевая аудитория"),
    ("positioning", "Позиционирование"),
    ("tone_of_voice", "Tone of voice"),
    ("languages", "Языки контента"),
    ("stop_words", "Стоп-слова"),
    ("banned_topics", "Запрещённые темы"),
    ("visual_rules", "Визуальные правила"),
]


class BrandProfileSection(QWidget):
    """Read-only view; заполнение появится вместе с ядром AI (шаг 3)."""

    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.dm = data_manager
        self._build_ui()

    def _profile(self) -> Dict[str, Any]:
        if self.dm is None or not hasattr(self.dm, "get_brand_profile"):
            return {}
        try:
            return self.dm.get_brand_profile() or {}
        except Exception as exc:
            logger.warning(f"brand profile load failed: {exc}")
            return {}

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setObjectName("plainScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        box = QVBoxLayout(content)
        box.setContentsMargins(24, 20, 24, 24)
        box.setSpacing(14)

        title = QLabel("Бренд-профиль")
        title.setStyleSheet(f"color: {TEXT}; font-size: 22px; font-weight: 700;")
        box.addWidget(title)

        subtitle = QLabel("Вход для стратегии и ТЗ: ниша, аудитория, tone of voice, язык контента")
        subtitle.setStyleSheet(f"color: {MUTED}; font-size: 12px;")
        box.addWidget(subtitle)

        profile = self._profile()
        filled = any(str(profile.get(key) or "").strip() for key, _ in FIELDS)

        if not filled:
            card = QFrame()
            card.setObjectName("zone")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(24, 22, 24, 22)
            card_layout.setSpacing(8)

            headline = QLabel("Профиль ещё не заполнен")
            headline.setStyleSheet(f"color: {TEXT}; font-size: 15px; font-weight: 700;")
            card_layout.addWidget(headline)

            hint = QLabel(
                "Заполним диалогом с AI на шаге 3: он задаст 5–7 вопросов о клиенте, "
                "толе общения и языках (RU или RU+KZ), а затем будет подставлять профиль "
                "в каждый запрос — стратегию, контент-план и ТЗ.")
            hint.setWordWrap(True)
            hint.setStyleSheet(f"color: {MUTED}; font-size: 12px;")
            card_layout.addWidget(hint)

            note = QLabel("Ручной формы здесь не будет — только правка через AI.")
            note.setWordWrap(True)
            note.setStyleSheet(f"color: {TEAL}; font-size: 11px;")
            card_layout.addWidget(note)

            box.addWidget(card)
        else:
            card = QFrame()
            card.setObjectName("zone")
            form = QFormLayout(card)
            form.setContentsMargins(24, 20, 24, 20)
            form.setSpacing(10)
            for key, label in FIELDS:
                value = str(profile.get(key) or "").strip() or "—"
                field = QLabel(value)
                field.setWordWrap(True)
                field.setStyleSheet(f"color: {TEXT}; font-size: 12px;")
                form.addRow(QLabel(label), field)
            box.addWidget(card)

            updated = str(profile.get("updated_at") or "").strip()
            if updated:
                stamp = QLabel(f"Обновлено: {updated}")
                stamp.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
                box.addWidget(stamp)

        box.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
