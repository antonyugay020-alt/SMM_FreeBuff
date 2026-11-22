"""Analytics: manual metrics for published posts and a summary from the AI core."""
from typing import Any, Dict

from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMessageBox)
from PySide6.QtCore import Qt, QTimer

from gui_sections.section_base import DataSection
from gui_theme import TEXT, MUTED, TEAL

METRIC_KEYS = ("reach", "likes", "comments", "saves")
PLAN_KEYS = ("date", "topic", "rubric", "format")
COLUMNS = ["Дата", "Тема", "Рубрика", "Формат", "Охват", "Лайки",
           "Комментарии", "Сохранения", "ER"]
PERIOD_DAYS = 30


class AnalyticsSection(DataSection):
    """Метрики публикаций: цифры вводятся руками, сводку считает ядро."""

    def __init__(self, data_manager, settings=None, parent=None):
        super().__init__(data_manager, settings, parent)
        self._loading = False
        self._pending: Dict[str, Dict[str, Any]] = {}
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(400)
        self._save_timer.timeout.connect(self._flush_pending)
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
        title = QLabel("📊 Аналитика")
        title.setStyleSheet(f"color: {TEXT}; font-size: 16px; font-weight: 700;")
        head.addWidget(title)
        self.count_label = QLabel("")
        self.count_label.setStyleSheet(f"color: {MUTED}; font-size: 11px; padding-left: 10px;")
        head.addWidget(self.count_label)
        head.addStretch()
        analyze = QPushButton("🤖 Анализ")
        analyze.setObjectName("topBtn")
        analyze.setProperty("class", "primary")
        analyze.clicked.connect(self._on_analyze)
        head.addWidget(analyze)
        layout.addWidget(header)

        hint = QLabel(
            "Опубликованные посты и посты с метриками. Охват, лайки, комментарии и "
            "сохранения вводятся руками — до подключения Instagram API.")
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {MUTED}; font-size: 11px; padding: 10px 16px 4px 16px;")
        layout.addWidget(hint)

        self.status = QLabel("")
        self.status.setStyleSheet(f"color: {TEAL}; font-size: 11px; padding: 0 16px 6px 16px;")
        layout.addWidget(self.status)

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setObjectName("calendar")
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.itemChanged.connect(self._on_item_changed)
        self.table.setStyleSheet(
            "QTableWidget::item:selected { background-color: rgba(45,212,191,0.18);"
            " color: #e6edf3; }")
        layout.addWidget(self.table, stretch=1)

        bottom = QHBoxLayout()
        bottom.setContentsMargins(16, 8, 16, 12)
        self.table_hint = QLabel("")
        self.table_hint.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
        bottom.addWidget(self.table_hint)
        bottom.addStretch()
        layout.addLayout(bottom)

    # --- data ---
    def _metrics(self) -> Dict[str, Dict[str, Any]]:
        """plan_id -> metrics record."""
        if self.dm is None:
            return {}
        return {str(m.get("plan_id")): m for m in self.dm.get_post_metrics()}

    @staticmethod
    def _engagement(item: Dict[str, Any]) -> float:
        reach = int(item.get("reach") or 0)
        reactions = sum(int(item.get(key) or 0) for key in ("likes", "comments", "saves"))
        return (reactions / reach * 100) if reach else 0.0

    def refresh(self):
        plan = self.dm.get_content_plan() if self.dm else []
        metrics = self._metrics()
        rows = [item for item in plan
                if item.get("status") == "Опубликовано"
                or str(item.get("id")) in metrics]

        self._loading = True
        self.table.setRowCount(len(rows))
        for row, item in enumerate(rows):
            plan_id = str(item.get("id") or "")
            entry = metrics.get(plan_id)
            values = [str(item.get(key) or "") for key in PLAN_KEYS]
            values += ["" if entry is None else str(entry.get(key) or "")
                       for key in METRIC_KEYS]
            values.append(f"{self._engagement(entry):.1f}%" if entry else "—")
            for col, value in enumerate(values):
                cell = QTableWidgetItem(value)
                if col == 0:
                    cell.setData(Qt.UserRole, plan_id)
                if col not in range(4, 8):
                    cell.setFlags(cell.flags() & ~Qt.ItemIsEditable)
                if col == 0 and str(item.get("date") or ""):
                    cell.setToolTip("Дата публикации из контент-плана")
                self.table.setItem(row, col, cell)
        self._loading = False

        measured = [entry for entry in metrics.values()
                    if str(entry.get("plan_id")) in {str(i.get("id")) for i in rows}]
        total_reach = sum(int(entry.get("reach") or 0) for entry in measured)
        avg_er = (sum(self._engagement(entry) for entry in measured) / len(measured)
                  if measured else 0.0)
        self.count_label.setText(f"{len(rows)} постов · {len(measured)} с метриками")
        self.status.setText(
            f"Охват {total_reach:,}".replace(",", " ") + f" · средняя вовлечённость {avg_er:.1f}%"
            if measured else "")
        self.table_hint.setText(
            "" if rows else
            "Пока нечего измерять: отметьте пост как «Опубликовано» в контент-плане.")

    def _on_item_changed(self, _cell):
        if self._loading:
            return
        row = _cell.row()
        id_cell = self.table.item(row, 0)
        plan_id = str(id_cell.data(Qt.UserRole) or "") if id_cell else ""
        if not plan_id:
            return
        fields = {}
        for offset, key in enumerate(METRIC_KEYS, start=4):
            cell = self.table.item(row, offset)
            # пустая ячейка — это ноль, иначе очистка цифры ничего бы не меняла
            fields[key] = cell.text().strip() if cell else ""
        self._pending[plan_id] = fields
        self._save_timer.start()

    def _flush_pending(self):
        metrics = self._metrics()
        for plan_id, fields in list(self._pending.items()):
            entry = metrics.get(plan_id)
            if entry:
                self.update("post_metrics", str(entry.get("id")), fields)
            else:
                self.add("post_metrics", {"plan_id": plan_id, **fields})
        self._pending.clear()
        self.refresh()

    def _on_analyze(self):
        text = self.run_full("analyze_performance", period_days=PERIOD_DAYS) or ""
        first, _, rest = text.partition("\n")
        self.status.setText(first)
        QMessageBox.information(self, "Аналитика", rest or first)
