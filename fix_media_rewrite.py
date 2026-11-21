#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rewrite media_content_section.py completely. No more patching.
Run: python fix_media_rewrite.py
"""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

def write(rel, content):
    p = BASE / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding='utf-8', newline='\n')
    print(f"  [OK] {rel}")

print("\n=== Rewriting media_content_section.py ===\n")

media_content = r'''"""Media Content section: 3 zones + processing panel. Uses DataManager."""
import logging
import json
from pathlib import Path
from typing import Dict, Any, List

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QGridLayout, QScrollArea, QComboBox, QCheckBox,
    QTextEdit, QSplitter, QAbstractItemView, QMessageBox)
from PySide6.QtCore import Qt, Signal, QMimeData, QByteArray
from PySide6.QtGui import QPixmap, QDrag

logger = logging.getLogger(__name__)

DRAG_TYPE = "application/x-smm-media-card"


class MediaCard(QFrame):
    card_clicked = Signal(dict, str)

    def __init__(self, file_data: Dict[str, Any], zone: str, parent=None):
        super().__init__(parent)
        self.file_data = file_data
        self.zone = zone
        self.selected = False
        self._drag_pos = None

        self.setObjectName("thumb")
        self.setFrameShape(QFrame.NoFrame)
        self.setStyleSheet("""
            QFrame#thumb { background-color: #0d1117; border: 2px solid #30363d; border-radius: 6px; }
            QFrame#thumb:hover { border-color: #58a6ff; }
            QFrame#thumb.selected { border-color: #1f6feb; background-color: #161b22; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(6, 6, 6, 0)

        self.checkbox = QCheckBox()
        self.checkbox.setStyleSheet("""
            QCheckBox { spacing: 0; padding: 2px; margin: 0; }
            QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #4e4e52; border-radius: 3px; background-color: #1e1e1e; }
            QCheckBox::indicator:checked { background-color: #1f6feb; border-color: #1f6feb; }
        """)
        self.checkbox.stateChanged.connect(self._on_checked)
        top_row.addWidget(self.checkbox)
        top_row.addStretch()

        type_icon = "🎬" if file_data["type"] == "video" else "🖼️"
        type_label = QLabel(type_icon)
        type_label.setStyleSheet("font-size: 18px;")
        top_row.addWidget(type_label)
        layout.addLayout(top_row)

        preview = QLabel()
        preview.setAlignment(Qt.AlignCenter)
        preview.setMinimumHeight(120)
        preview.setStyleSheet("background-color: #21262d; font-size: 40px; color: #8b949e;")

        media_dir = Path(__file__).resolve().parent.parent.parent / "media" / "images"
        img_path = media_dir / file_data["name"]
        if img_path.exists():
            try:
                pm = QPixmap(str(img_path))
                if not pm.isNull():
                    scaled = pm.scaled(260, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    preview.setPixmap(scaled)
                    preview.setStyleSheet("background-color: #21262d;")
            except Exception:
                preview.setText(type_icon)
        else:
            preview.setText(type_icon)
        layout.addWidget(preview)

        name = file_data["name"]
        name_label = QLabel(name if len(name) <= 24 else name[:21] + "...")
        name_label.setStyleSheet("color: #c9d1d9; font-size: 11px; padding: 6px 8px 0 8px; font-weight: bold;")
        layout.addWidget(name_label)

        size_label = QLabel(file_data["size"])
        size_label.setStyleSheet("color: #8b949e; font-size: 10px; padding: 2px 8px;")
        layout.addWidget(size_label)

        if "category" in file_data:
            cat_label = QLabel(file_data["category"])
            cat_label.setStyleSheet("color: #58a6ff; font-size: 10px; padding: 0 8px 4px 8px; font-weight: bold;")
            layout.addWidget(cat_label)

        if "status" in file_data:
            status_map = {
                "approved": ("✅ Одобрено", "#238636"),
                "pending": ("⏳ На проверке", "#9e6a03"),
                "rejected": ("❌ Отклонено", "#da3633")
            }
            status_text, status_color = status_map.get(file_data["status"], ("?", "#8b949e"))
            status_label = QLabel(status_text)
            status_label.setStyleSheet(f"color: {status_color}; font-size: 10px; padding: 0 8px 6px 8px; font-weight: bold;")
            layout.addWidget(status_label)

        self.setMinimumWidth(200)
        self.setMaximumWidth(260)
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.pos()
            self.card_clicked.emit(self.file_data, self.zone)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return
        if self._drag_pos is None:
            return
        if (event.pos() - self._drag_pos).manhattanLength() < 10:
            return

        logger.info(f"Starting drag: {self.file_data['name']} from {self.zone}")

        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(DRAG_TYPE, json.dumps(self.file_data).encode('utf-8'))
        mime.setData("zone".encode('utf-8'), QByteArray(self.zone.encode('utf-8')))
        drag.setMimeData(mime)

        result = drag.exec_(Qt.MoveAction)
        logger.info(f"Drag finished with result: {result}")
        self._drag_pos = None

    def _on_checked(self, state):
        self.selected = state == Qt.Checked
        if self.selected:
            self.setStyleSheet("QFrame#thumb { background-color: #161b22; border: 2px solid #1f6feb; border-radius: 6px; }")
        else:
            self.setStyleSheet("QFrame#thumb { background-color: #0d1117; border: 2px solid #30363d; border-radius: 6px; } QFrame#thumb:hover { border-color: #58a6ff; }")


class MediaColumn(QFrame):
    card_clicked_signal = Signal(dict, str)

    def __init__(self, title: str, icon: str, color: str, files: List[Dict[str, Any]], zone: str, parent=None):
        super().__init__(parent)
        self.zone = zone
        self.files = list(files)
        self.cards = []
        self.color = color

        self.setObjectName("zone")
        self.setStyleSheet(f"""
            QFrame#zone {{ background-color: #161b22; border: 1px solid #30363d; border-top: 4px solid {color}; border-radius: 6px; }}
        """)
        self.setAcceptDrops(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame()
        header.setObjectName("zoneHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 10, 12, 10)

        title_label = QLabel(f"{icon} {title}")
        title_label.setStyleSheet("color: #e6edf3; font-size: 15px; font-weight: bold;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        self.count_label = QLabel(f"{len(self.files)}")
        self.count_label.setStyleSheet(f"background-color: {color}; color: white; border-radius: 12px; padding: 3px 10px; font-weight: bold; font-size: 12px;")
        header_layout.addWidget(self.count_label)
        layout.addWidget(header)

        actions = QHBoxLayout()
        actions.setContentsMargins(12, 8, 12, 6)

        if zone == "sources":
            upload_btn = QPushButton("📥 Загрузить")
            upload_btn.setObjectName("topBtn")
            upload_btn.setStyleSheet("font-size: 12px; padding: 6px 12px;")
            upload_btn.clicked.connect(lambda: QMessageBox.information(self, "Загрузка", "Используй кнопку 'Импорт медиа' в верхней панели."))
            actions.addWidget(upload_btn)
        elif zone == "references":
            add_btn = QPushButton("➕ Добавить")
            add_btn.setObjectName("topBtn")
            add_btn.setStyleSheet("font-size: 12px; padding: 6px 12px;")
            add_btn.clicked.connect(lambda: QMessageBox.information(self, "Добавить", "В реальной версии откроется диалог выбора эталона."))
            actions.addWidget(add_btn)
        elif zone == "ready":
            self.approve_btn = QPushButton("✅ Одобрить выбранные")
            self.approve_btn.setObjectName("topBtn")
            self.approve_btn.setStyleSheet("font-size: 11px; background-color: #238636; color: white; border: none; padding: 6px 12px;")
            self.approve_btn.clicked.connect(self._on_approve_selected)
            actions.addWidget(self.approve_btn)

            reject_btn = QPushButton("❌ Отклонить выбранные")
            reject_btn.setObjectName("topBtn")
            reject_btn.setStyleSheet("font-size: 11px; background-color: #da3633; color: white; border: none; padding: 6px 12px;")
            reject_btn.clicked.connect(self._on_reject_selected)
            actions.addWidget(reject_btn)

        actions.addStretch()
        layout.addLayout(actions)

        self.grid_scroll = QScrollArea()
        self.grid_scroll.setWidgetResizable(True)
        self.grid_scroll.setStyleSheet("border: none; background-color: #0d1117;")

        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(12)
        self.grid_layout.setContentsMargins(12, 8, 12, 12)

        self._rebuild_cards()

        self.grid_scroll.setWidget(self.grid_widget)
        layout.addWidget(self.grid_scroll, stretch=1)

    def _rebuild_cards(self):
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.cards.clear()
        row = 0
        for file_data in self.files:
            card = MediaCard(file_data, self.zone)
            card.card_clicked.connect(self.card_clicked_signal.emit)
            self.cards.append(card)
            self.grid_layout.addWidget(card, row, 0)
            row += 1
        self.count_label.setText(str(len(self.files)))

    def _on_approve_selected(self):
        selected = [c for c in self.cards if c.selected]
        if not selected:
            QMessageBox.warning(self, "Внимание", "Выбери хотя бы одну карточку!")
            return
        for card in selected:
            card.file_data["status"] = "approved"
        self._rebuild_cards()
        QMessageBox.information(self, "Успех", f"Одобрено: {len(selected)}")

    def _on_reject_selected(self):
        selected = [c for c in self.cards if c.selected]
        if not selected:
            QMessageBox.warning(self, "Внимание", "Выбери хотя бы одну карточку!")
            return
        for card in selected:
            card.file_data["status"] = "rejected"
        self._rebuild_cards()
        QMessageBox.information(self, "Успех", f"Отклонено: {len(selected)}")

    def dragEnterEvent(self, event):
        logger.info(f"[{self.zone}] dragEnterEvent, formats: {event.mimeData().formats()}")
        if event.mimeData().hasFormat(DRAG_TYPE):
            event.acceptProposedAction()
            self.setStyleSheet(f"""
                QFrame#zone {{ background-color: #1c2333; border: 2px dashed {self.color}; border-top: 4px solid {self.color}; border-radius: 6px; }}
            """)

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(DRAG_TYPE):
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        logger.info(f"[{self.zone}] dragLeaveEvent")
        self.setStyleSheet(f"""
            QFrame#zone {{ background-color: #161b22; border: 1px solid #30363d; border-top: 4px solid {self.color}; border-radius: 6px; }}
        """)

    def dropEvent(self, event):
        logger.info(f"[{self.zone}] dropEvent")
        if not event.mimeData().hasFormat(DRAG_TYPE):
            return

        raw = bytes(event.mimeData().data(DRAG_TYPE)).decode('utf-8')
        try:
            data = json.loads(raw)
            source_zone = bytes(event.mimeData().data("zone".encode('utf-8'))).decode('utf-8')
        except Exception as e:
            logger.error(f"[{self.zone}] Failed to parse drop data: {e}")
            return

        logger.info(f"[{self.zone}] Dropped {data.get('name')} from {source_zone}")

        self.setStyleSheet(f"""
            QFrame#zone {{ background-color: #161b22; border: 1px solid #30363d; border-top: 4px solid {self.color}; border-radius: 6px; }}
        """)

        parent = self._find_parent_section()
        if parent:
            parent.move_card(data, source_zone, self.zone)

        event.acceptProposedAction()

    def _find_parent_section(self):
        parent = self.parent()
        while parent and not isinstance(parent, MediaContentSection):
            parent = parent.parent()
        return parent


class ProcessingPanel(QWidget):
    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.dm = data_manager
        self.current_source = None
        self.setStyleSheet("background-color: #161b22; border-left: 1px solid #30363d;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        title = QLabel("🎨 Обработка")
        title.setStyleSheet("color: #e6edf3; font-size: 16px; font-weight: bold; border-bottom: 1px solid #30363d; padding-bottom: 8px;")
        layout.addWidget(title)

        step1 = QLabel("1️⃣ Исходник:")
        step1.setStyleSheet("color: #58a6ff; font-size: 12px; font-weight: bold;")
        layout.addWidget(step1)

        self.source_preview = QLabel("👈 Кликни на карточку в 'Исходники'")
        self.source_preview.setAlignment(Qt.AlignCenter)
        self.source_preview.setMinimumHeight(120)
        self.source_preview.setStyleSheet("background-color: #0d1117; border: 2px dashed #30363d; border-radius: 6px; font-size: 13px; color: #8b949e; padding: 20px;")
        layout.addWidget(self.source_preview)

        step2 = QLabel("2️⃣ Эталон (опционально):")
        step2.setStyleSheet("color: #bc8cff; font-size: 12px; font-weight: bold; margin-top: 8px;")
        layout.addWidget(step2)

        self.ref_combo = QComboBox()
        self.ref_combo.setObjectName("filterCombo")
        self.ref_combo.addItem("— без эталона —")
        for ref in self.dm.get_media_references():
            self.ref_combo.addItem(f"{ref['name']} ({ref.get('category', '')})")
        self.ref_combo.setStyleSheet("font-size: 12px; padding: 6px;")
        layout.addWidget(self.ref_combo)

        step3 = QLabel("3️⃣ Запрос на обработку:")
        step3.setStyleSheet("color: #3fb950; font-size: 12px; font-weight: bold; margin-top: 8px;")
        layout.addWidget(step3)

        self.request_input = QTextEdit()
        self.request_input.setObjectName("chatInput")
        self.request_input.setPlaceholderText("Например:\n• убери фон\n• сделай теплее\n• добавь объект справа")
        self.request_input.setMaximumHeight(100)
        self.request_input.setStyleSheet("font-size: 12px; padding: 8px;")
        layout.addWidget(self.request_input)

        engine_label = QLabel("Движок обработки:")
        engine_label.setStyleSheet("color: #8b949e; font-size: 11px; margin-top: 8px;")
        layout.addWidget(engine_label)

        self.engine_combo = QComboBox()
        self.engine_combo.addItem("🖥️ Stable Diffusion (локально)")
        self.engine_combo.addItem("☁️ OpenAI GPT-Image")
        self.engine_combo.setStyleSheet("font-size: 12px; padding: 6px;")
        layout.addWidget(self.engine_combo)

        self.process_btn = QPushButton("⚡ Обработать")
        self.process_btn.setObjectName("topBtn")
        self.process_btn.setProperty("class", "primary")
        self.process_btn.setStyleSheet("font-size: 14px; font-weight: bold; padding: 12px; margin-top: 8px;")
        self.process_btn.clicked.connect(self._on_process)
        layout.addWidget(self.process_btn)

        step4 = QLabel("4️⃣ Результат:")
        step4.setStyleSheet("color: #3fb950; font-size: 12px; font-weight: bold; margin-top: 8px;")
        layout.addWidget(step4)

        self.result_preview = QLabel("Здесь появится результат обработки")
        self.result_preview.setAlignment(Qt.AlignCenter)
        self.result_preview.setMinimumHeight(100)
        self.result_preview.setStyleSheet("background-color: #0d1117; border: 2px dashed #30363d; border-radius: 6px; font-size: 12px; color: #8b949e; padding: 20px;")
        layout.addWidget(self.result_preview)

        layout.addStretch()

    def set_source(self, file_data):
        self.current_source = file_data
        self.source_preview.setText(f"✅ {file_data['name']}\n{file_data['size']}")
        self.source_preview.setStyleSheet("background-color: #0d1117; border: 2px solid #238636; border-radius: 6px; font-size: 13px; color: #e6edf3; padding: 20px;")

    def _on_process(self):
        if not self.current_source:
            QMessageBox.warning(self, "Внимание", "Сначала выбери исходник!")
            return
        request = self.request_input.toPlainText().strip()
        if not request:
            QMessageBox.warning(self, "Внимание", "Введи запрос на обработку!")
            return

        self.result_preview.setText("⏳ Обработка...")
        self.result_preview.setStyleSheet("background-color: #0d1117; border: 2px solid #9e6a03; border-radius: 6px; font-size: 13px; color: #e6edf3; padding: 20px;")
        self.process_btn.setEnabled(False)

        import time
        time.sleep(1.5)

        result_name = f"processed_{self.current_source['name']}"
        engine = "OpenAI" if self.engine_combo.currentIndex() == 1 else "Stable Diffusion"
        self.result_preview.setText(f"✅ Готово!\n\n📄 {result_name}\n🔧 Запрос: {request[:50]}\n🤖 Движок: {engine}")
        self.result_preview.setStyleSheet("background-color: #0d1117; border: 2px solid #238636; border-radius: 6px; font-size: 12px; color: #e6edf3; padding: 16px;")
        self.process_btn.setEnabled(True)

        QMessageBox.information(self, "Успех", f"Файл обработан:\n{result_name}")


class MediaContentSection(QWidget):
    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.dm = data_manager
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        splitter = QSplitter(Qt.Horizontal)

        columns_container = QWidget()
        columns_layout = QHBoxLayout(columns_container)
        columns_layout.setContentsMargins(16, 16, 16, 16)
        columns_layout.setSpacing(16)

        self.sources_col = MediaColumn("Исходники", "📥", "#58a6ff", self.dm.get_media_sources(), "sources")
        self.references_col = MediaColumn("Эталоны", "🎯", "#bc8cff", self.dm.get_media_references(), "references")
        self.ready_col = MediaColumn("Готовые материалы", "✅", "#3fb950", self.dm.get_media_ready(), "ready")

        self.sources_col.card_clicked_signal.connect(self.on_source_selected)
        self.references_col.card_clicked_signal.connect(self.on_reference_selected)
        self.ready_col.card_clicked_signal.connect(self.on_ready_selected)

        self.sources_col.setMinimumWidth(260)
        self.sources_col.setMaximumWidth(380)
        self.references_col.setMinimumWidth(260)
        self.references_col.setMaximumWidth(380)
        self.ready_col.setMinimumWidth(260)
        self.ready_col.setMaximumWidth(380)

        columns_layout.addWidget(self.sources_col, stretch=1)
        columns_layout.addWidget(self.references_col, stretch=1)
        columns_layout.addWidget(self.ready_col, stretch=1)

        splitter.addWidget(columns_container)

        self.processing_panel = ProcessingPanel(self.dm)
        self.processing_panel.setMinimumWidth(320)
        self.processing_panel.setMaximumWidth(450)
        splitter.addWidget(self.processing_panel)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        splitter.setHandleWidth(6)
        splitter.setSizes([950, 380])
        splitter.setStyleSheet("""
            QSplitter::handle { background-color: #30363d; border-radius: 2px; }
            QSplitter::handle:hover { background-color: #58a6ff; }
        """)

        layout.addWidget(splitter, stretch=1)

    def on_source_selected(self, file_data, zone):
        if zone == "sources":
            self.processing_panel.set_source(file_data)

    def on_reference_selected(self, file_data, zone):
        for i in range(self.processing_panel.ref_combo.count()):
            if file_data["name"] in self.processing_panel.ref_combo.itemText(i):
                self.processing_panel.ref_combo.setCurrentIndex(i)
                break

    def on_ready_selected(self, file_data, zone):
        self.processing_panel.result_preview.setText(f"📄 {file_data['name']}\n{file_data['size']}\nСтатус: {file_data.get('status', '?')}")
        self.processing_panel.result_preview.setStyleSheet("background-color: #0d1117; border: 2px solid #3fb950; border-radius: 6px; font-size: 13px; color: #e6edf3; padding: 20px;")

    def move_card(self, file_data, from_zone, to_zone):
        if from_zone == to_zone:
            return

        cols = {"sources": self.sources_col, "references": self.references_col, "ready": self.ready_col}
        source_col = cols.get(from_zone)
        target_col = cols.get(to_zone)

        if not source_col or not target_col:
            return

        if file_data in source_col.files:
            source_col.files.remove(file_data)
            source_col._rebuild_cards()

        if to_zone == "ready" and "status" not in file_data:
            file_data["status"] = "pending"
        if to_zone == "references" and "category" not in file_data:
            file_data["category"] = "Общий"

        if file_data not in target_col.files:
            target_col.files.append(file_data)
            target_col._rebuild_cards()

        logger.info(f"Moved {file_data['name']}: {from_zone} -> {to_zone}")
'''

write("gui_sections/media_content_section.py", media_content)

print("\n=== Media Content Section Rewritten ===")
print("\nRun START.bat")