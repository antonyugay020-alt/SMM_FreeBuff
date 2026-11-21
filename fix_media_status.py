#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Step 1 (real functions): Live status change in Media Content.
Approve/Reject writes to DataManager, saves to disk, refreshes left-panel stats.
Rewrites media_content_section.py fully + adds refresh_stats() to gui_main.py.
Run: python fix_media_status.py
"""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

def write(rel, content):
    p = BASE / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding='utf-8', newline='\n')
    print(f"  [OK] {rel}")

print("\n=== Step 1: Live Status Change ===\n")

# ----------------------------------------------------------------------------
# 1. media_content_section.py — full rewrite with mass-action -> DataManager
# ----------------------------------------------------------------------------
print("[1/2] Rewriting media_content_section.py ...")

media_content = r'''"""Media Content: 3 view modes + live status change via DataManager."""
import logging
import json
from pathlib import Path
from typing import Dict, Any, List

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QGridLayout, QScrollArea, QComboBox, QCheckBox,
    QTextEdit, QSplitter, QAbstractItemView, QMessageBox, QTableWidget,
    QTableWidgetItem, QHeaderView)
from PySide6.QtCore import Qt, Signal, QMimeData, QByteArray
from PySide6.QtGui import QPixmap, QDrag, QColor

logger = logging.getLogger(__name__)

DRAG_TYPE = "application/x-smm-media-card"

STATUS_MAP = {
    "approved": ("✅ Одобрено", "#238636"),
    "pending": ("⏳ На проверке", "#9e6a03"),
    "rejected": ("❌ Отклонено", "#da3633"),
}
FILE_ICONS = {"image": "🖼️", "video": "🎬"}


# ===================== CARD (cards mode) =====================
class MediaCard(QFrame):
    card_clicked = Signal(dict, str)

    def __init__(self, file_data, zone, parent=None):
        super().__init__(parent)
        self.file_data = file_data
        self.zone = zone
        self.selected = False
        self._drag_pos = None

        self.setObjectName("thumb")
        self.setFrameShape(QFrame.NoFrame)
        self.setStyleSheet("""
            QFrame#thumb { background-color:#0d1117; border:2px solid #30363d; border-radius:6px; }
            QFrame#thumb:hover { border-color:#58a6ff; }
            QFrame#thumb.selected { border-color:#1f6feb; background-color:#161b22; }
        """)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        top = QHBoxLayout(); top.setContentsMargins(6, 6, 6, 0)
        self.checkbox = QCheckBox()
        self.checkbox.setStyleSheet("""
            QCheckBox { spacing:0; padding:2px; margin:0; }
            QCheckBox::indicator { width:16px; height:16px; border:1px solid #4e4e52; border-radius:3px; background-color:#1e1e1e; }
            QCheckBox::indicator:checked { background-color:#1f6feb; border-color:#1f6feb; }
        """)
        self.checkbox.stateChanged.connect(self._on_checked)
        top.addWidget(self.checkbox); top.addStretch()
        tl = QLabel(FILE_ICONS.get(file_data.get("type"), "🖼️")); tl.setStyleSheet("font-size:18px;")
        top.addWidget(tl)
        lay.addLayout(top)

        preview = QLabel(); preview.setAlignment(Qt.AlignCenter)
        preview.setMinimumHeight(180)
        preview.setStyleSheet("background-color:#21262d; font-size:40px; color:#8b949e;")
        media_dir = Path(__file__).resolve().parent.parent.parent / "media" / "images"
        img = media_dir / file_data["name"]
        shown = False
        if img.exists():
            try:
                pm = QPixmap(str(img))
                if not pm.isNull():
                    preview.setPixmap(pm.scaled(320, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                    preview.setStyleSheet("background-color:#21262d;")
                    shown = True
            except Exception:
                pass
        if not shown:
            preview.setText(FILE_ICONS.get(file_data.get("type"), "🖼️"))
        lay.addWidget(preview)

        nm = file_data["name"]
        nl = QLabel(nm if len(nm) <= 26 else nm[:23] + "...")
        nl.setStyleSheet("color:#c9d1d9; font-size:11px; padding:6px 8px 0 8px; font-weight:bold;")
        lay.addWidget(nl)
        sl = QLabel(file_data.get("size", "")); sl.setStyleSheet("color:#8b949e; font-size:10px; padding:2px 8px;")
        lay.addWidget(sl)
        if "category" in file_data:
            cl = QLabel(file_data["category"]); cl.setStyleSheet("color:#58a6ff; font-size:10px; padding:0 8px 4px 8px; font-weight:bold;")
            lay.addWidget(cl)
        if "status" in file_data:
            st, sc = STATUS_MAP.get(file_data["status"], ("?", "#8b949e"))
            stl = QLabel(st); stl.setStyleSheet(f"color:{sc}; font-size:10px; padding:0 8px 6px 8px; font-weight:bold;")
            lay.addWidget(stl)

        self.setMinimumWidth(280); self.setMaximumWidth(320)
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_pos = e.pos()
            self.card_clicked.emit(self.file_data, self.zone)
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if not (e.buttons() & Qt.LeftButton) or self._drag_pos is None:
            return
        if (e.pos() - self._drag_pos).manhattanLength() < 10:
            return
        drag = QDrag(self); mime = QMimeData()
        mime.setData(DRAG_TYPE, json.dumps(self.file_data).encode('utf-8'))
        mime.setData(b"zone", QByteArray(self.zone.encode('utf-8')))
        drag.setMimeData(mime); drag.exec_(Qt.MoveAction); self._drag_pos = None

    def _on_checked(self, state):
        self.selected = state == Qt.Checked
        self.setStyleSheet(
            "QFrame#thumb{background-color:#161b22;border:2px solid #1f6feb;border-radius:6px;}"
            if self.selected else
            "QFrame#thumb{background-color:#0d1117;border:2px solid #30363d;border-radius:6px;}QFrame#thumb:hover{border-color:#58a6ff;}"
        )


# ===================== LIST ROW (list mode) =====================
class MediaListRow(QFrame):
    row_clicked = Signal(dict, str)

    def __init__(self, file_data, zone, parent=None):
        super().__init__(parent)
        self.file_data = file_data
        self.zone = zone
        self.selected = False
        self._drag_pos = None
        self.setStyleSheet("""
            QFrame{background-color:#0d1117;border:1px solid #30363d;border-radius:4px;padding:6px;}
            QFrame:hover{background-color:#161b22;border-color:#58a6ff;}
        """)
        lay = QHBoxLayout(self); lay.setContentsMargins(8, 6, 8, 6); lay.setSpacing(12)
        self.checkbox = QCheckBox()
        self.checkbox.setStyleSheet("""
            QCheckBox{spacing:0;}
            QCheckBox::indicator{width:14px;height:14px;border:1px solid #4e4e52;border-radius:2px;background-color:#1e1e1e;}
            QCheckBox::indicator:checked{background-color:#1f6feb;border-color:#1f6feb;}
        """)
        self.checkbox.stateChanged.connect(self._on_checked)
        lay.addWidget(self.checkbox)
        il = QLabel(FILE_ICONS.get(file_data.get("type"), "🖼️")); il.setStyleSheet("font-size:18px;min-width:24px;")
        lay.addWidget(il)
        nl = QLabel(file_data["name"]); nl.setStyleSheet("color:#e6edf3;font-size:12px;font-weight:bold;")
        lay.addWidget(nl, 1)
        sz = QLabel(file_data.get("size", "")); sz.setStyleSheet("color:#8b949e;font-size:11px;min-width:80px;")
        lay.addWidget(sz)
        if "category" in file_data:
            cg = QLabel(file_data["category"]); cg.setStyleSheet("color:#58a6ff;font-size:11px;min-width:70px;")
            lay.addWidget(cg)
        if "status" in file_data:
            st, sc = STATUS_MAP.get(file_data["status"], ("?", "#8b949e"))
            stl = QLabel(st); stl.setStyleSheet(f"color:{sc};font-size:11px;font-weight:bold;min-width:110px;")
            lay.addWidget(stl)
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_pos = e.pos()
            self.row_clicked.emit(self.file_data, self.zone)
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if not (e.buttons() & Qt.LeftButton) or self._drag_pos is None:
            return
        if (e.pos() - self._drag_pos).manhattanLength() < 10:
            return
        drag = QDrag(self); mime = QMimeData()
        mime.setData(DRAG_TYPE, json.dumps(self.file_data).encode('utf-8'))
        mime.setData(b"zone", QByteArray(self.zone.encode('utf-8')))
        drag.setMimeData(mime); drag.exec_(Qt.MoveAction); self._drag_pos = None

    def _on_checked(self, state):
        self.selected = state == Qt.Checked


# ===================== COLUMN =====================
class MediaColumn(QFrame):
    card_clicked_signal = Signal(dict, str)
    mass_action_requested = Signal(str, list)  # action, [file_data...]

    def __init__(self, title, icon, color, files, zone, view_mode="cards", parent=None):
        super().__init__(parent)
        self.zone = zone
        self.files = list(files)
        self.view_mode = view_mode
        self.color = color
        self.cards = []

        self.setObjectName("zone")
        self.setStyleSheet(f"QFrame#zone{{background-color:#161b22;border:1px solid #30363d;border-top:4px solid {color};border-radius:6px;}}")
        self.setAcceptDrops(True)

        lay = QVBoxLayout(self); lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(0)

        hdr = QFrame(); hdr.setObjectName("zoneHeader")
        hl = QHBoxLayout(hdr); hl.setContentsMargins(12, 10, 12, 10)
        ttl = QLabel(f"{icon} {title}"); ttl.setStyleSheet("color:#e6edf3;font-size:15px;font-weight:bold;")
        hl.addWidget(ttl); hl.addStretch()
        self.count_label = QLabel(str(len(self.files)))
        self.count_label.setStyleSheet(f"background-color:{color};color:white;border-radius:12px;padding:3px 10px;font-weight:bold;font-size:12px;")
        hl.addWidget(self.count_label)
        lay.addWidget(hdr)

        act = QHBoxLayout(); act.setContentsMargins(12, 8, 12, 6)
        if zone == "sources":
            ub = QPushButton("📥 Загрузить"); ub.setObjectName("topBtn"); ub.setStyleSheet("font-size:12px;padding:6px 12px;")
            ub.clicked.connect(lambda: QMessageBox.information(self, "Загрузка", "Используй кнопку 'Импорт медиа' в верхней панели."))
            act.addWidget(ub)
        elif zone == "references":
            ab = QPushButton("➕ Добавить"); ab.setObjectName("topBtn"); ab.setStyleSheet("font-size:12px;padding:6px 12px;")
            ab.clicked.connect(lambda: QMessageBox.information(self, "Добавить", "В реальной версии откроется диалог выбора эталона."))
            act.addWidget(ab)
        elif zone == "ready":
            ap = QPushButton("✅ Одобрить выбранные"); ap.setObjectName("topBtn")
            ap.setStyleSheet("font-size:11px;background-color:#238636;color:white;border:none;padding:6px 12px;")
            ap.clicked.connect(lambda: self._emit_mass("approve")); act.addWidget(ap)
            rj = QPushButton("❌ Отклонить выбранные"); rj.setObjectName("topBtn")
            rj.setStyleSheet("font-size:11px;background-color:#da3633;color:white;border:none;padding:6px 12px;")
            rj.clicked.connect(lambda: self._emit_mass("reject")); act.addWidget(rj)
        act.addStretch(); lay.addLayout(act)

        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("border:none;background-color:#0d1117;")
        self.inner = QWidget()
        self.inner_lay = QVBoxLayout(self.inner)
        self.inner_lay.setContentsMargins(12, 8, 12, 12); self.inner_lay.setSpacing(8)
        self._rebuild_content()
        self.scroll.setWidget(self.inner)
        lay.addWidget(self.scroll, 1)

    def _emit_mass(self, action):
        sel = [c.file_data for c in self.cards if getattr(c, "selected", False)]
        if not sel:
            QMessageBox.warning(self, "Внимание", "Отметь галочками нужные карточки (режимы Карточки/Список).")
            return
        self.mass_action_requested.emit(action, sel)

    def _rebuild_content(self):
        while self.inner_lay.count():
            it = self.inner_lay.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        self.cards = []

        if self.view_mode == "cards":
            grid = QGridLayout(); grid.setSpacing(12)
            r, c = 0, 0
            for fd in self.files:
                card = MediaCard(fd, self.zone)
                card.card_clicked.connect(self.card_clicked_signal.emit)
                self.cards.append(card)
                grid.addWidget(card, r, c); c += 1
                if c >= 2:
                    c = 0; r += 1
            self.inner_lay.addLayout(grid)
        elif self.view_mode == "list":
            for fd in self.files:
                row = MediaListRow(fd, self.zone)
                row.row_clicked.connect(self.card_clicked_signal.emit)
                self.cards.append(row)
                self.inner_lay.addWidget(row)
        elif self.view_mode == "table":
            t = QTableWidget(); t.setObjectName("calendar")
            t.setColumnCount(5); t.setHorizontalHeaderLabels(["Имя", "Тип", "Размер", "Категория", "Статус"])
            t.setRowCount(len(self.files)); t.setEditTriggers(QAbstractItemView.NoEditTriggers)
            t.setSelectionMode(QAbstractItemView.SingleSelection); t.verticalHeader().setVisible(False)
            for r, fd in enumerate(self.files):
                t.setItem(r, 0, QTableWidgetItem(f"{FILE_ICONS.get(fd.get('type'),'🖼️')} {fd['name']}"))
                ti = QTableWidgetItem(str(fd.get("type","")).capitalize()); ti.setTextAlignment(Qt.AlignCenter); t.setItem(r, 1, ti)
                t.setItem(r, 2, QTableWidgetItem(fd.get("size","")))
                ci = QTableWidgetItem(fd.get("category","—")); ci.setTextAlignment(Qt.AlignCenter); t.setItem(r, 3, ci)
                st = fd.get("status","")
                if st:
                    txt, col = STATUS_MAP.get(st, ("?", "#8b949e"))
                    si = QTableWidgetItem(txt); si.setForeground(QColor(col))
                else:
                    si = QTableWidgetItem("—")
                t.setItem(r, 4, si)
            t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            t.setMinimumHeight(max(120, len(self.files) * 30 + 40))
            self.inner_lay.addWidget(t)

    # ---- drag & drop ----
    def dragEnterEvent(self, e):
        if e.mimeData().hasFormat(DRAG_TYPE):
            e.acceptProposedAction()
            self.setStyleSheet(f"QFrame#zone{{background-color:#1c2333;border:2px dashed {self.color};border-top:4px solid {self.color};border-radius:6px;}}")
    def dragMoveEvent(self, e):
        if e.mimeData().hasFormat(DRAG_TYPE):
            e.acceptProposedAction()
    def dragLeaveEvent(self, e):
        self.setStyleSheet(f"QFrame#zone{{background-color:#161b22;border:1px solid #30363d;border-top:4px solid {self.color};border-radius:6px;}}")
    def dropEvent(self, e):
        if not e.mimeData().hasFormat(DRAG_TYPE):
            return
        try:
            data = json.loads(bytes(e.mimeData().data(DRAG_TYPE)).decode('utf-8'))
            src = bytes(e.mimeData().data(b"zone")).decode('utf-8')
        except Exception as ex:
            logger.error(f"drop parse: {ex}"); return
        self.setStyleSheet(f"QFrame#zone{{background-color:#161b22;border:1px solid #30363d;border-top:4px solid {self.color};border-radius:6px;}}")
        par = self.parent()
        while par and not isinstance(par, MediaContentSection):
            par = par.parent()
        if par:
            par.move_card(data, src, self.zone)
        e.acceptProposedAction()


# ===================== PROCESSING PANEL =====================
class ProcessingPanel(QWidget):
    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.dm = data_manager
        self.current_source = None
        self.setStyleSheet("background-color:#161b22;border-left:1px solid #30363d;")
        lay = QVBoxLayout(self); lay.setContentsMargins(16, 16, 16, 16); lay.setSpacing(14)

        t = QLabel("🎨 Обработка"); t.setStyleSheet("color:#e6edf3;font-size:16px;font-weight:bold;border-bottom:1px solid #30363d;padding-bottom:8px;")
        lay.addWidget(t)

        s1 = QLabel("1️⃣ Исходник:"); s1.setStyleSheet("color:#58a6ff;font-size:12px;font-weight:bold;"); lay.addWidget(s1)
        self.source_preview = QLabel("👈 Кликни на карточку в 'Исходники'")
        self.source_preview.setAlignment(Qt.AlignCenter); self.source_preview.setMinimumHeight(120)
        self.source_preview.setStyleSheet("background-color:#0d1117;border:2px dashed #30363d;border-radius:6px;font-size:13px;color:#8b949e;padding:20px;")
        lay.addWidget(self.source_preview)

        s2 = QLabel("2️⃣ Эталон (опционально):"); s2.setStyleSheet("color:#bc8cff;font-size:12px;font-weight:bold;margin-top:8px;"); lay.addWidget(s2)
        self.ref_combo = QComboBox(); self.ref_combo.setObjectName("filterCombo")
        self.ref_combo.addItem("— без эталона —")
        for ref in self.dm.get_media_references():
            self.ref_combo.addItem(f"{ref['name']} ({ref.get('category','')})")
        self.ref_combo.setStyleSheet("font-size:12px;padding:6px;"); lay.addWidget(self.ref_combo)

        s3 = QLabel("3️⃣ Запрос на обработку:"); s3.setStyleSheet("color:#3fb950;font-size:12px;font-weight:bold;margin-top:8px;"); lay.addWidget(s3)
        self.request_input = QTextEdit(); self.request_input.setObjectName("chatInput")
        self.request_input.setPlaceholderText("Например:\n• убери фон\n• сделай теплее\n• добавь объект справа")
        self.request_input.setMaximumHeight(100); self.request_input.setStyleSheet("font-size:12px;padding:8px;")
        lay.addWidget(self.request_input)

        el = QLabel("Движок обработки:"); el.setStyleSheet("color:#8b949e;font-size:11px;margin-top:8px;"); lay.addWidget(el)
        self.engine_combo = QComboBox()
        self.engine_combo.addItem("🖥️ Stable Diffusion (локально)")
        self.engine_combo.addItem("☁️ OpenAI GPT-Image")
        self.engine_combo.setStyleSheet("font-size:12px;padding:6px;"); lay.addWidget(self.engine_combo)

        self.process_btn = QPushButton("⚡ Обработать"); self.process_btn.setObjectName("topBtn")
        self.process_btn.setProperty("class", "primary")
        self.process_btn.setStyleSheet("font-size:14px;font-weight:bold;padding:12px;margin-top:8px;")
        self.process_btn.clicked.connect(self._on_process); lay.addWidget(self.process_btn)

        s4 = QLabel("4️⃣ Результат:"); s4.setStyleSheet("color:#3fb950;font-size:12px;font-weight:bold;margin-top:8px;"); lay.addWidget(s4)
        self.result_preview = QLabel("Здесь появится результат обработки")
        self.result_preview.setAlignment(Qt.AlignCenter); self.result_preview.setMinimumHeight(100)
        self.result_preview.setStyleSheet("background-color:#0d1117;border:2px dashed #30363d;border-radius:6px;font-size:12px;color:#8b949e;padding:20px;")
        lay.addWidget(self.result_preview)
        lay.addStretch()

    def set_source(self, fd):
        self.current_source = fd
        self.source_preview.setText(f"✅ {fd['name']}\n{fd.get('size','')}")
        self.source_preview.setStyleSheet("background-color:#0d1117;border:2px solid #238636;border-radius:6px;font-size:13px;color:#e6edf3;padding:20px;")

    def _on_process(self):
        if not self.current_source:
            QMessageBox.warning(self, "Внимание", "Сначала выбери исходник!"); return
        req = self.request_input.toPlainText().strip()
        if not req:
            QMessageBox.warning(self, "Внимание", "Введи запрос на обработку!"); return
        self.result_preview.setText("⏳ Обработка...")
        self.result_preview.setStyleSheet("background-color:#0d1117;border:2px solid #9e6a03;border-radius:6px;font-size:13px;color:#e6edf3;padding:20px;")
        self.process_btn.setEnabled(False)
        import time; time.sleep(1.5)
        rn = f"processed_{self.current_source['name']}"
        eng = "OpenAI" if self.engine_combo.currentIndex() == 1 else "Stable Diffusion"
        self.result_preview.setText(f"✅ Готово!\n\n📄 {rn}\n🔧 Запрос: {req[:50]}\n🤖 Движок: {eng}")
        self.result_preview.setStyleSheet("background-color:#0d1117;border:2px solid #238636;border-radius:6px;font-size:12px;color:#e6edf3;padding:16px;")
        self.process_btn.setEnabled(True)
        QMessageBox.information(self, "Успех", f"Файл обработан:\n{rn}")


# ===================== SECTION =====================
class MediaContentSection(QWidget):
    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.dm = data_manager
        self.view_mode = "cards"
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self); lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(0)

        bar = QFrame(); bar.setObjectName("zoneHeader")
        bl = QHBoxLayout(bar); bl.setContentsMargins(16, 8, 16, 8)
        ml = QLabel("Режим просмотра:"); ml.setStyleSheet("color:#8b949e;font-size:12px;"); bl.addWidget(ml)
        self.mode_buttons = {}
        for txt, mid, ic in [("Карточки", "cards", "🔲"), ("Список", "list", "📋"), ("Таблица", "table", "📊")]:
            b = QPushButton(f"{ic} {txt}"); b.setObjectName("topBtn")
            if mid == self.view_mode:
                b.setProperty("class", "primary")
            b.setStyleSheet("font-size:12px;padding:6px 12px;")
            b.clicked.connect(lambda checked, m=mid: self._switch_mode(m))
            self.mode_buttons[mid] = b; bl.addWidget(b)
        bl.addStretch(); lay.addWidget(bar)

        splitter = QSplitter(Qt.Horizontal)
        cc = QWidget(); ccl = QHBoxLayout(cc); ccl.setContentsMargins(16, 16, 16, 16); ccl.setSpacing(16)

        self.sources_col = MediaColumn("Исходники", "📥", "#58a6ff", self.dm.get_media_sources(), "sources", self.view_mode)
        self.references_col = MediaColumn("Эталоны", "🎯", "#bc8cff", self.dm.get_media_references(), "references", self.view_mode)
        self.ready_col = MediaColumn("Готовые материалы", "✅", "#3fb950", self.dm.get_media_ready(), "ready", self.view_mode)

        self.sources_col.card_clicked_signal.connect(self.on_source_selected)
        self.references_col.card_clicked_signal.connect(self.on_reference_selected)
        self.ready_col.card_clicked_signal.connect(self.on_ready_selected)
        self.ready_col.mass_action_requested.connect(self._on_mass_action)

        for col in (self.sources_col, self.references_col, self.ready_col):
            col.setMinimumWidth(380); col.setMaximumWidth(700)
            ccl.addWidget(col, 1)
        splitter.addWidget(cc)

        self.processing_panel = ProcessingPanel(self.dm)
        self.processing_panel.setMinimumWidth(320); self.processing_panel.setMaximumWidth(450)
        splitter.addWidget(self.processing_panel)

        splitter.setStretchFactor(0, 3); splitter.setStretchFactor(1, 1)
        splitter.setHandleWidth(6); splitter.setSizes([1100, 400])
        splitter.setStyleSheet("QSplitter::handle{background-color:#30363d;border-radius:2px;}QSplitter::handle:hover{background-color:#58a6ff;}")
        lay.addWidget(splitter, 1)

    def _switch_mode(self, mode):
        self.view_mode = mode
        for m, b in self.mode_buttons.items():
            b.setProperty("class", "primary" if m == mode else "")
            b.style().unpolish(b); b.style().polish(b)
        for col, files in ((self.sources_col, self.dm.get_media_sources()),
                           (self.references_col, self.dm.get_media_references()),
                           (self.ready_col, self.dm.get_media_ready())):
            col.view_mode = mode
            col.files = list(files)
            col._rebuild_content()
            col.count_label.setText(str(len(col.files)))

    def _on_mass_action(self, action, selected_files):
        new_status = "approved" if action == "approve" else "rejected"
        for fd in selected_files:
            fd["status"] = new_status
        self.dm.save()
        # reload ready column from DataManager (same objects, status updated)
        self.ready_col.files = self.dm.get_media_ready()
        self.ready_col._rebuild_content()
        self.ready_col.count_label.setText(str(len(self.ready_col.files)))
        # refresh left-panel stats
        win = self.window()
        if hasattr(win, "refresh_stats"):
            win.refresh_stats()
        word = "одобрено" if action == "approve" else "отклонено"
        logger.info(f"Mass {action}: {len(selected_files)} file(s)")
        QMessageBox.information(self, "Готово", f"{len(selected_files)} файл(ов) {word}.\nСтатистика обновлена.")

    def on_source_selected(self, fd, zone):
        if zone == "sources":
            self.processing_panel.set_source(fd)

    def on_reference_selected(self, fd, zone):
        for i in range(self.processing_panel.ref_combo.count()):
            if fd["name"] in self.processing_panel.ref_combo.itemText(i):
                self.processing_panel.ref_combo.setCurrentIndex(i); break

    def on_ready_selected(self, fd, zone):
        self.processing_panel.result_preview.setText(f"📄 {fd['name']}\n{fd.get('size','')}\nСтатус: {fd.get('status','?')}")
        self.processing_panel.result_preview.setStyleSheet("background-color:#0d1117;border:2px solid #3fb950;border-radius:6px;font-size:13px;color:#e6edf3;padding:20px;")

    def move_card(self, fd, from_zone, to_zone):
        if from_zone == to_zone:
            return
        cols = {"sources": self.sources_col, "references": self.references_col, "ready": self.ready_col}
        s, t = cols.get(from_zone), cols.get(to_zone)
        if not s or not t:
            return
        if fd in s.files:
            s.files.remove(fd); s._rebuild_content(); s.count_label.setText(str(len(s.files)))
        if to_zone == "ready" and "status" not in fd:
            fd["status"] = "pending"
        if to_zone == "references" and "category" not in fd:
            fd["category"] = "Общий"
        if fd not in t.files:
            t.files.append(fd); t._rebuild_content(); t.count_label.setText(str(len(t.files)))
        win = self.window()
        if hasattr(win, "refresh_stats"):
            win.refresh_stats()
        logger.info(f"Moved {fd['name']}: {from_zone} -> {to_zone}")
'''

write("gui_sections/media_content_section.py", media_content)

# ----------------------------------------------------------------------------
# 2. gui_main.py — add refresh_stats() + call it after import
# ----------------------------------------------------------------------------
print("[2/2] Patching gui_main.py (refresh_stats) ...")

gui_path = BASE / "gui_main.py"
g = gui_path.read_text(encoding='utf-8')

# Insert refresh_stats method before _on_project_changed
anchor = "    def _on_project_changed(self, index: int):"
method = '''    def refresh_stats(self):
        """Recompute and show project stats in the left panel from DataManager."""
        try:
            stats = self.data_manager.get_stats()
            self.proj_stats.setText(
                f"{stats['sources']} исходников\\n"
                f"{stats['ready']} готовых\\n"
                f"{stats['pending']} на проверке\\n"
                f"{stats['scheduled']} запланировано"
            )
        except Exception as e:
            logger.warning(f"refresh_stats failed: {e}")

'''
if "def refresh_stats" not in g:
    g = g.replace(anchor, method + anchor)
    print("  [OK] Added refresh_stats()")
else:
    print("  [skip] refresh_stats() already present")

# Call refresh_stats after import loop (before the if imported>0 block)
old_imp = "        if imported > 0:\n            from PySide6.QtWidgets import QMessageBox"
new_imp = "        self.refresh_stats()\n        if imported > 0:\n            from PySide6.QtWidgets import QMessageBox"
if old_imp in g and "        self.refresh_stats()\n        if imported > 0:" not in g:
    g = g.replace(old_imp, new_imp)
    print("  [OK] refresh_stats() called after import")
else:
    print("  [skip] import hook already patched or pattern not found")

gui_path.write_text(g, encoding='utf-8', newline='\n')

print("\n=== Step 1 Complete ===")
print("Now approve/reject in 'Готовые материалы' writes to DataManager,")
print("saves to disk, and updates the left-panel counters live.")
print("\nRun START.bat")