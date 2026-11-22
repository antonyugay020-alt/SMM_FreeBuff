"""Strategy section: живой документ с блоками, правкой и AI-действиями."""
import logging
from typing import Any, Dict, List, Optional

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QTextEdit, QScrollArea, QMessageBox, QInputDialog,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView)
from PySide6.QtCore import Qt, Signal, QThread

from gui_theme import TEXT, MUTED, TEAL, PURPLE

logger = logging.getLogger(__name__)

PROFILE_HINTS = [("client_name", "клиент"), ("niche", "ниша"),
                 ("audience", "аудитория"), ("tone_of_voice", "tone"),
                 ("languages", "языки")]

AI_ACTIONS = [("Переписать", "rewrite"), ("Углубить", "deepen"),
              ("Альтернатива", "alternative")]


class _CoreWorker(QThread):
    """Runs a blocking AI call off the GUI thread."""

    done = Signal(str, bool)

    def __init__(self, fn, parent=None):
        super().__init__(parent)
        self.fn = fn

    def run(self):
        try:
            text = self.fn()
            self.done.emit(text or "Готово", True)
        except Exception as exc:
            logger.exception("strategy ai action failed")
            self.done.emit(f"Ошибка: {exc}", False)


class SectionCard(QFrame):
    """One strategy block: reads, edits inline, asks AI."""

    save_requested = Signal(str, str)   # section_id, text
    ai_requested = Signal(str, str)     # section_id, mode

    def __init__(self, section: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.setObjectName("zone")
        self.section = section
        self.section_id = str(section.get("id") or "")
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        header = QHBoxLayout()
        icon = QLabel(str(self.section.get("icon") or "•"))
        icon.setStyleSheet("font-size: 14px;")
        header.addWidget(icon)
        title = QLabel(str(self.section.get("title") or self.section_id))
        title.setStyleSheet(f"color: {TEXT}; font-size: 14px; font-weight: 700;")
        header.addWidget(title)
        header.addStretch()
        for text, mode in AI_ACTIONS:
            btn = QPushButton(f"🤖 {text}")
            btn.setObjectName("topBtn")
            btn.setStyleSheet("font-size: 10px; padding: 3px 8px;")
            btn.clicked.connect(lambda checked=False, m=mode: self.ai_requested.emit(self.section_id, m))
            header.addWidget(btn)
        layout.addLayout(header)

        self.content_label = QLabel(str(self.section.get("content") or "Блок пуст — нажмите «Редактировать»."))
        self.content_label.setWordWrap(True)
        self.content_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.content_label.setStyleSheet(f"color: #c9d1d9; font-size: 12px;")
        layout.addWidget(self.content_label)

        self.editor = QTextEdit()
        self.editor.setPlainText(str(self.section.get("content") or ""))
        self.editor.setMinimumHeight(110)
        self.editor.setStyleSheet(
            f"background-color: #0a0e13; color: {TEXT}; border: 1px solid {TEAL};"
            " border-radius: 6px; padding: 8px; font-size: 12px;")
        self.editor.hide()
        layout.addWidget(self.editor)

        buttons = QHBoxLayout()
        self.edit_btn = QPushButton("✏️ Редактировать")
        self.edit_btn.setObjectName("topBtn")
        self.edit_btn.setStyleSheet("font-size: 10px; padding: 3px 8px;")
        self.edit_btn.clicked.connect(self._toggle_editor)
        buttons.addWidget(self.edit_btn)

        self.save_btn = QPushButton("Сохранить")
        self.save_btn.setObjectName("topBtn")
        self.save_btn.setStyleSheet("font-size: 10px; padding: 3px 8px;")
        self.save_btn.clicked.connect(self._save)
        self.save_btn.hide()
        buttons.addWidget(self.save_btn)

        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.setObjectName("topBtn")
        self.cancel_btn.setStyleSheet("font-size: 10px; padding: 3px 8px;")
        self.cancel_btn.clicked.connect(self._toggle_editor)
        self.cancel_btn.hide()
        buttons.addWidget(self.cancel_btn)
        buttons.addStretch()
        layout.addLayout(buttons)

    def _toggle_editor(self):
        editing = self.editor.isHidden()
        self.editor.setVisible(editing)
        self.content_label.setVisible(not editing)
        self.save_btn.setVisible(editing)
        self.cancel_btn.setVisible(editing)
        self.edit_btn.setText("✏️ Редактировать" if not editing else "✏️ Скрыть")
        if not editing:
            self.editor.setPlainText(str(self.section.get("content") or ""))

    def _save(self):
        text = self.editor.toPlainText().strip()
        self.save_requested.emit(self.section_id, text)


class StrategyDocument(QWidget):
    """List of editable blocks + empty state."""

    save_requested = Signal(str, str)
    ai_requested = Signal(str, str)

    def __init__(self, sections: List[Dict[str, Any]], project_name: str = "", parent=None):
        super().__init__(parent)
        self.sections = sections
        self.project_name = project_name
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(14)

        title = QLabel(f"Стратегия проекта «{self.project_name}»" if self.project_name
                       else "Стратегия проекта")
        title.setStyleSheet(f"color: {TEXT}; font-size: 22px; font-weight: 700;")
        layout.addWidget(title)

        if not self.sections:
            placeholder = QLabel(
                "Стратегии пока нет.\n\nСоберите её кнопкой «Создать с AI» или опишите проект "
                "AI-менеджеру справа — блоки появятся здесь и будут редактируемыми.")
            placeholder.setWordWrap(True)
            placeholder.setStyleSheet(
                f"color: {MUTED}; font-size: 13px; padding: 22px; background-color: #121820;"
                " border: 1px dashed #2b3540; border-radius: 10px;")
            layout.addWidget(placeholder)
            layout.addStretch()
            return

        for section in self.sections:
            card = SectionCard(section)
            card.save_requested.connect(self.save_requested.emit)
            card.ai_requested.connect(self.ai_requested.emit)
            layout.addWidget(card)
        layout.addStretch()


class KpiEditor(QWidget):
    """Editable KPI table; saves into strategy.kpis."""

    save_requested = Signal(list)

    def __init__(self, kpis: List[Dict[str, Any]], parent=None):
        super().__init__(parent)
        self.rows = [dict(k) for k in kpis]
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(12)

        title = QLabel("KPI и метрики")
        title.setStyleSheet(f"color: {TEXT}; font-size: 22px; font-weight: 700;")
        layout.addWidget(title)

        self.table = QTableWidget(len(self.rows), 4)
        self.table.setObjectName("calendar")
        self.table.setHorizontalHeaderLabels(["Метрика", "Сейчас", "Цель", "Дедлайн"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        for index, kpi in enumerate(self.rows):
            for col, key in enumerate(("metric", "current", "target", "deadline")):
                self.table.setItem(index, col, QTableWidgetItem(str(kpi.get(key) or "")))
        layout.addWidget(self.table, stretch=1)

        buttons = QHBoxLayout()
        add_btn = QPushButton("＋ Строка")
        add_btn.setObjectName("topBtn")
        add_btn.clicked.connect(self._add_row)
        buttons.addWidget(add_btn)

        save_btn = QPushButton("Сохранить KPI")
        save_btn.setObjectName("topBtn")
        save_btn.setProperty("class", "primary")
        save_btn.clicked.connect(self._collect_and_save)
        buttons.addWidget(save_btn)
        buttons.addStretch()
        layout.addLayout(buttons)

    def _add_row(self):
        self.table.insertRow(self.table.rowCount())

    def _collect_and_save(self):
        kpis = []
        for row in range(self.table.rowCount()):
            values = [self.table.item(row, col).text().strip() if self.table.item(row, col) else ""
                      for col in range(4)]
            if not any(values):
                continue
            kpis.append({"metric": values[0], "current": values[1],
                         "target": values[2], "deadline": values[3]})
        self.save_requested.emit(kpis)


class StrategySection(QWidget):
    """Стратегия как рабочий раздел: правка блоков, AI, связь с профилем."""

    navigate = Signal(str)
    data_changed = Signal()

    def __init__(self, data_manager, settings=None, parent=None):
        super().__init__(parent)
        self.dm = data_manager
        self.settings = settings
        self.mode = "document"
        self._core = None
        self._worker = None
        self._build_ui()
        self._reload()

    # --- data / core ---
    def _get_core(self):
        if self._core is None and self.dm is not None:
            from ai_core import AICore
            self._core = AICore(self.dm, self.settings)
        return self._core

    def _strategy(self) -> Dict[str, Any]:
        return (self.dm.get_strategy() if self.dm else {}) or {}

    # --- ui ---
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame()
        header.setObjectName("zoneHeader")
        head = QHBoxLayout(header)
        head.setContentsMargins(16, 12, 16, 12)

        title = QLabel("🎯 Стратегия")
        title.setStyleSheet(f"color: {TEXT}; font-size: 16px; font-weight: 700;")
        head.addWidget(title)

        self.version_label = QLabel("")
        self.version_label.setStyleSheet(f"color: {MUTED}; font-size: 11px; padding-left: 10px;")
        head.addWidget(self.version_label)
        head.addStretch()

        for text, mode in (("📄 Документ", "document"), ("📊 KPI", "kpi")):
            btn = QPushButton(text)
            btn.setObjectName("topBtn")
            btn.setStyleSheet("font-size: 11px; padding: 5px 10px;")
            btn.clicked.connect(lambda checked=False, m=mode: self._switch_mode(m))
            head.addWidget(btn)

        self.ai_btn = QPushButton("🤖 Создать с AI")
        self.ai_btn.setObjectName("topBtn")
        self.ai_btn.setProperty("class", "primary")
        self.ai_btn.setStyleSheet("font-size: 11px; padding: 6px 12px; margin-left: 10px;")
        self.ai_btn.clicked.connect(self._on_create_ai)
        head.addWidget(self.ai_btn)
        layout.addWidget(header)

        self.profile_strip = QFrame()
        strip_layout = QHBoxLayout(self.profile_strip)
        strip_layout.setContentsMargins(24, 8, 24, 8)
        self.profile_label = QLabel("")
        self.profile_label.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
        strip_layout.addWidget(self.profile_label, stretch=1)
        profile_btn = QPushButton("Открыть профиль")
        profile_btn.setObjectName("topBtn")
        profile_btn.setStyleSheet("font-size: 10px; padding: 3px 8px;")
        profile_btn.clicked.connect(lambda: self.navigate.emit("brand_profile"))
        strip_layout.addWidget(profile_btn)
        layout.addWidget(self.profile_strip)

        self.status = QLabel("")
        self.status.setStyleSheet(f"color: {TEAL}; font-size: 11px; padding: 0 24px;")
        layout.addWidget(self.status)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll.setWidget(self.content)
        layout.addWidget(self.scroll, stretch=1)

    def _clear_content(self):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()

    def _reload(self):
        strategy = self._strategy()
        version = strategy.get("version") or "—"
        updated = strategy.get("updated") or "—"
        self.version_label.setText(f"версия {version} · обновлено {updated}")
        self._update_profile_strip()
        self._clear_content()

        if self.mode == "kpi":
            editor = KpiEditor(strategy.get("kpis") or [])
            editor.save_requested.connect(self._save_kpis)
            self.content_layout.addWidget(editor)
            return

        document = StrategyDocument(strategy.get("sections") or [],
                                    strategy.get("project_name") or "")
        document.save_requested.connect(self._save_section)
        document.ai_requested.connect(self._run_ai_action)
        self.content_layout.addWidget(document)

    def _update_profile_strip(self):
        profile = (self.dm.get_brand_profile() if self.dm else {}) or {}
        parts = [f"{label}: {profile.get(key)}" for key, label in PROFILE_HINTS
                 if str(profile.get(key) or "").strip()]
        if parts:
            self.profile_label.setText("Бренд-профиль · " + " · ".join(parts))
            self.profile_label.setStyleSheet(f"color: {TEAL}; font-size: 11px;")
        else:
            self.profile_label.setText(
                "Бренд-профиль не заполнен — AI будет спрашивать контекст в каждом запросе")
            self.profile_label.setStyleSheet(f"color: {MUTED}; font-size: 11px;")

    def _switch_mode(self, mode: str):
        self.mode = mode
        self._reload()

    # --- actions ---
    def _save_section(self, section_id: str, text: str):
        core = self._get_core()
        if core is not None:
            reply = core.run_tool("update_strategy_section",
                                  section_id=section_id, content=text)
        else:
            self.dm.update_strategy_section(section_id, text)
            reply = None
        self.status.setText(reply.text.splitlines()[0] if reply else "Блок сохранён")
        self._reload()
        self.data_changed.emit()

    def _save_kpis(self, kpis: List[Dict[str, Any]]):
        core = self._get_core()
        if core is not None:
            reply = core.run_tool("update_kpis", kpis=kpis)
        else:
            strategy = self.dm.get_strategy() if self.dm else None
            if strategy is None:
                return
            strategy["kpis"] = kpis
            self.dm.save()
            reply = None
        self.status.setText(reply.text.splitlines()[0] if reply else "KPI сохранены")
        self.status.setStyleSheet(f"color: {TEAL}; font-size: 11px; padding: 0 24px;")
        self._reload()
        self.data_changed.emit()

    def _run_ai_action(self, section_id: str, mode: str):
        core = self._get_core()
        if core is None:
            self.status.setText("AI недоступен: нет проекта")
            return
        self.status.setText("Модель думает…")
        self._set_busy(True)
        self._worker = _CoreWorker(lambda: core.rewrite_section(section_id, mode).text, self)
        self._worker.done.connect(self._on_ai_done)
        self._worker.start()

    def _on_create_ai(self):
        strategy = self._strategy()
        if strategy.get("sections"):
            answer = QMessageBox.question(
                self, "Перезаписать стратегию?",
                "Стратегия уже заполнена. Новый вариант заменит все блоки "
                "(откат доступен в журнале AI). Продолжить?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if answer != QMessageBox.Yes:
                return
        brief, ok = QInputDialog.getMultiLineText(
            self, "Создать стратегию", "Кратко о клиенте, продукте и цели:")
        if not ok or not brief.strip():
            return
        core = self._get_core()
        if core is None:
            return
        self.status.setText("Собираю стратегию…")
        self._set_busy(True)
        self._worker = _CoreWorker(lambda: self._create_strategy_blocking(core, brief), self)
        self._worker.done.connect(self._on_ai_done)
        self._worker.start()

    @staticmethod
    def _create_strategy_blocking(core, brief: str) -> str:
        reply = core.handle(f"сделай стратегию: {brief}")
        if reply.needs_confirmation:
            reply = core.handle("да")
        return reply.text

    def _on_ai_done(self, text: str, ok: bool):
        self._set_busy(False)
        self.status.setText(text.splitlines()[0] if text else "")
        self.status.setStyleSheet(
            f"color: {TEAL if ok else '#f87171'}; font-size: 11px; padding: 0 24px;")
        self._reload()
        self.data_changed.emit()

    def _set_busy(self, busy: bool):
        self.ai_btn.setEnabled(not busy)
        self.ai_btn.setText("⏳ Работаю…" if busy else "🤖 Создать с AI")
