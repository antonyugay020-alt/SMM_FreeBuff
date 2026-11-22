"""Plans and schemes: PDF export of the content plan and of the strategy."""
from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QFileDialog, QMessageBox)
from PySide6.QtCore import Qt

from gui_sections.section_base import DataSection
from gui_theme import TEXT, MUTED, BORDER, PANEL

DOCS = (
    ("plan", "📅 План публикаций",
     "Таблица: дата, тема, рубрика, формат, статус.", "⬇ PDF плана"),
    ("strategy", "🎯 Стратегия",
     "Блоки стратегии текстом, таблица KPI и версия.", "⬇ PDF стратегии"),
)


class PlansSection(DataSection):
    """Выгрузка плана и стратегии в PDF — файл ложится в выбранную папку."""

    def __init__(self, data_manager, settings=None, parent=None):
        super().__init__(data_manager, settings, parent)
        self._details = {}
        self._build_ui()
        self.refresh()

    # --- ui ---
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame()
        header.setObjectName("zoneHeader")
        head = QHBoxLayout(header)
        head.setContentsMargins(16, 12, 16, 12)
        title = QLabel("📐 Планы и схемы")
        title.setStyleSheet(f"color: {TEXT}; font-size: 16px; font-weight: 700;")
        head.addWidget(title)
        self.status = QLabel("")
        self.status.setStyleSheet(f"color: {MUTED}; font-size: 11px; padding-left: 10px;")
        head.addWidget(self.status)
        head.addStretch()
        layout.addWidget(header)

        hint = QLabel("Документ на A4 с датой и именем проекта. Файл сохраняется "
                      "в выбранную папку, действие видно в журнале и отменяется.")
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {MUTED}; font-size: 11px; padding: 10px 16px 4px 16px;")
        layout.addWidget(hint)

        for kind, title_text, description, button_text in DOCS:
            layout.addWidget(self._card(kind, title_text, description, button_text))
        layout.addStretch()

    def _card(self, kind: str, title_text: str, description: str, button_text: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet(f"QFrame {{ background: {PANEL}; border: 1px solid {BORDER};"
                           " border-radius: 8px; }")
        box = QVBoxLayout(card)
        box.setContentsMargins(16, 12, 16, 12)
        box.setSpacing(4)
        box.addWidget(self._label(title_text, TEXT, 13, bold=True))
        box.addWidget(self._label(description, MUTED, 11, wrap=True))
        details = self._label("", TEXT, 11)
        self._details[kind] = details
        box.addWidget(details)
        row = QHBoxLayout()
        button = QPushButton(button_text)
        button.setObjectName("topBtn")
        button.clicked.connect(lambda: self._export(kind))
        row.addWidget(button)
        row.addStretch()
        box.addLayout(row)
        wrap = QFrame()
        wrap.setStyleSheet("QFrame { border: none; background: transparent; }")
        outer = QVBoxLayout(wrap)
        outer.setContentsMargins(16, 6, 16, 6)
        outer.addWidget(card)
        return wrap

    @staticmethod
    def _label(text: str, color: str, size: int, bold: bool = False,
               wrap: bool = False) -> QLabel:
        label = QLabel(text)
        weight = " font-weight: 700;" if bold else ""
        label.setStyleSheet(f"color: {color}; font-size: {size}px;{weight}"
                            " background: transparent; border: none;")
        if wrap:
            label.setWordWrap(True)
        return label

    # --- data ---
    def refresh(self):
        plan = self.dm.get_content_plan() if self.dm else []
        strategy = (self.dm.get_strategy() or {}) if self.dm else {}
        blocks = strategy.get("sections") or []
        scheduled = sum(1 for item in plan if item.get("status") == "Запланировано")
        self._details["plan"].setText(
            f"{len(plan)} позиций · {scheduled} запланировано" if plan
            else "План пуст — сначала добавьте позиции в «Контент-плане».")
        self._details["strategy"].setText(
            f"{len(blocks)} блоков · {len(strategy.get('kpis') or [])} KPI · "
            f"версия {strategy.get('version') or '—'}" if blocks
            else "Стратегии пока нет — создайте её в разделе «Стратегия».")

    def _export(self, kind: str):
        folder = QFileDialog.getExistingDirectory(self, "Куда сохранить PDF")
        if not folder:
            return
        text = self.run_full("export_pdf", kind=kind, dest=folder) or ""
        first, _, _ = text.partition("\n")
        self.status.setText(first)
        QMessageBox.information(self, "PDF", text or "Готово")
        self.refresh()
