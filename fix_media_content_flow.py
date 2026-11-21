#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix: Make Media Content section interactive with clear flow.
- Click card → load into processing panel
- Process button → simulate result → add to Ready column
- Better visual flow between columns
Run: python fix_media_content_flow.py
"""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

def write(rel, content):
    p = BASE / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding='utf-8', newline='\n')
    print(f"  [OK] {rel}")

print("\n=== Making Media Content Interactive ===\n")

# 1. media_content_section.py — interactive version
print("[1/1] Writing interactive media_content_section.py...")

media_content = r'''"""Media Content section: Interactive with clear flow."""
import logging
from pathlib import Path
from typing import Dict, Any, List

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QGridLayout, QScrollArea, QComboBox, QCheckBox,
    QTextEdit, QSplitter, QAbstractItemView, QMessageBox)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap

logger = logging.getLogger(__name__)

# Demo data
DEMO_SOURCES = [
    {"name": "raw_001.jpg", "type": "image", "size": "4032x3024", "date": "15.10.2026"},
    {"name": "raw_002.jpg", "type": "image", "size": "4032x3024", "date": "15.10.2026"},
    {"name": "raw_003.mp4", "type": "video", "size": "1920x1080", "date": "14.10.2026"},
    {"name": "raw_004.jpg", "type": "image", "size": "3024x4032", "date": "14.10.2026"},
    {"name": "raw_005.jpg", "type": "image", "size": "4032x3024", "date": "13.10.2026"},
    {"name": "raw_006.mp4", "type": "video", "size": "1080x1920", "date": "13.10.2026"},
]

DEMO_REFERENCES = [
    {"name": "ref_cafe_style.jpg", "type": "image", "category": "Лента", "size": "1080x1080"},
    {"name": "ref_reels_example.mp4", "type": "video", "category": "Reels", "size": "1080x1920"},
    {"name": "ref_stories_mood.jpg", "type": "image", "category": "Stories", "size": "1080x1920"},
    {"name": "ref_color_palette.jpg", "type": "image", "category": "Общий", "size": "1920x1080"},
]

DEMO_READY = [
    {"name": "tennis_001.jpg", "status": "approved", "type": "image", "size": "1920x2560"},
    {"name": "tennis_002.jpg", "status": "approved", "type": "image", "size": "1920x2560"},
    {"name": "reels_001.mp4", "status": "approved", "type": "video", "size": "1080x1920"},
    {"name": "coffee_story.jpg", "status": "pending", "type": "image", "size": "1080x1920"},
]


class MediaCard(QFrame):
    """Single media card with checkbox and click handler."""
    card_clicked = Signal(dict, str)  # file_data, zone
    
    def __init__(self, file_data: Dict[str, Any], zone: str, parent=None):
        super().__init__(parent)
        self.file_data = file_data
        self.zone = zone
        self.selected = False
        
        self.setObjectName("thumb")
        self.setFrameShape(QFrame.NoFrame)
        self.setStyleSheet("""
            QFrame#thumb {
                background-color: #0d1117;
                border: 2px solid #30363d;
                border-radius: 6px;
            }
            QFrame#thumb:hover { border-color: #58a6ff; }
            QFrame#thumb.selected { border-color: #1f6feb; background-color: #161b22; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Checkbox + preview row
        top_row = QHBoxLayout()
        top_row.setContentsMargins(6, 6, 6, 0)
        
        self.checkbox = QCheckBox()
        self.checkbox.setStyleSheet("""
            QCheckBox { background-color: rgba(0,0,0,0.7); border-radius: 2px; spacing: 0; padding: 2px; margin: 0; }
            QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #4e4e52; border-radius: 3px; background-color: #1e1e1e; }
            QCheckBox::indicator:checked { background-color: #1f6feb; border-color: #1f6feb; }
        """)
        self.checkbox.stateChanged.connect(self._on_checked)
        top_row.addWidget(self.checkbox)
        top_row.addStretch()
        
        # Type icon
        type_icon = "🎬" if file_data["type"] == "video" else "🖼️"
        type_label = QLabel(type_icon)
        type_label.setStyleSheet("font-size: 18px;")
        top_row.addWidget(type_label)
        
        layout.addLayout(top_row)
        
        # Preview area (larger)
        preview = QLabel()
        preview.setAlignment(Qt.AlignCenter)
        preview.setMinimumHeight(120)
        preview.setStyleSheet("background-color: #21262d; border-radius: 4px 4px 0 0; font-size: 32px; color: #8b949e;")
        
        # Try to load real image
        media_dir = Path(__file__).resolve().parent.parent.parent / "media" / "images"
        img_path = media_dir / file_data["name"]
        if img_path.exists():
            try:
                pm = QPixmap(str(img_path))
                if not pm.isNull():
                    scaled = pm.scaled(200, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    preview.setPixmap(scaled)
                    preview.setStyleSheet("background-color: #21262d; border-radius: 4px 4px 0 0;")
            except Exception:
                preview.setText(type_icon)
        else:
            preview.setText(type_icon)
        
        layout.addWidget(preview)
        
        # Name
        name_label = QLabel(file_data["name"][:20] + ("..." if len(file_data["name"]) > 20 else ""))
        name_label.setStyleSheet("color: #c9d1d9; font-size: 11px; padding: 6px 8px 0 8px; font-weight: bold;")
        layout.addWidget(name_label)
        
        # Size
        size_label = QLabel(file_data["size"])
        size_label.setStyleSheet("color: #8b949e; font-size: 10px; padding: 2px 8px 4px 8px;")
        layout.addWidget(size_label)
        
        # Category (for references)
        if "category" in file_data:
            cat_label = QLabel(file_data["category"])
            cat_label.setStyleSheet("color: #58a6ff; font-size: 10px; padding: 0 8px 4px 8px; font-weight: bold;")
            layout.addWidget(cat_label)
        
        # Status (for ready)
        if "status" in file_data:
            status_map = {"approved": ("✅ Одобрено", "#238636"), "pending": ("⏳ На проверке", "#9e6a03"), "rejected": ("❌ Отклонено", "#da3633")}
            status_text, status_color = status_map.get(file_data["status"], ("?", "#8b949e"))
            status_label = QLabel(status_text)
            status_label.setStyleSheet(f"color: {status_color}; font-size: 10px; padding: 0 8px 6px 8px; font-weight: bold;")
            layout.addWidget(status_label)
        
        self.setMinimumWidth(180)
        self.setMaximumWidth(200)
        
        # Make clickable
        self.setCursor(Qt.PointingHandCursor)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.card_clicked.emit(self.file_data, self.zone)
        super().mousePressEvent(event)
    
    def _on_checked(self, state):
        self.selected = state == Qt.Checked
        if self.selected:
            self.setStyleSheet("""
                QFrame#thumb { background-color: #161b22; border: 2px solid #1f6feb; border-radius: 6px; }
            """)
        else:
            self.setStyleSheet("""
                QFrame#thumb { background-color: #0d1117; border: 2px solid #30363d; border-radius: 6px; }
                QFrame#thumb:hover { border-color: #58a6ff; }
            """)


class MediaColumn(QFrame):
    """One of three columns: Sources, References, Ready."""
    def __init__(self, title: str, icon: str, color: str, files: List[Dict[str, Any]], zone: str, parent=None):
        super().__init__(parent)
        self.zone = zone
        self.files = files
        self.cards: List[MediaCard] = []
        
        self.setObjectName("zone")
        self.setStyleSheet(f"""
            QFrame#zone {{
                background-color: #161b22;
                border: 1px solid #30363d;
                border-top: 4px solid {color};
                border-radius: 6px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header
        header = QFrame()
        header.setObjectName("zoneHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 10, 12, 10)
        
        title_label = QLabel(f"{icon} {title}")
        title_label.setStyleSheet("color: #e6edf3; font-size: 15px; font-weight: bold;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        count_label = QLabel(f"{len(files)}")
        count_label.setStyleSheet(f"background-color: {color}; color: white; border-radius: 12px; padding: 3px 10px; font-weight: bold; font-size: 12px;")
        header_layout.addWidget(count_label)
        
        layout.addWidget(header)
        
        # Action buttons
        actions = QHBoxLayout()
        actions.setContentsMargins(12, 8, 12, 6)
        
        if zone == "sources":
            upload_btn = QPushButton("📥 Загрузить")
            upload_btn.setObjectName("topBtn")
            upload_btn.setStyleSheet("font-size: 12px; padding: 6px 12px;")
            actions.addWidget(upload_btn)
        elif zone == "references":
            add_btn = QPushButton("➕ Добавить")
            add_btn.setObjectName("topBtn")
            add_btn.setStyleSheet("font-size: 12px; padding: 6px 12px;")
            actions.addWidget(add_btn)
        elif zone == "ready":
            approve_btn = QPushButton("✅ Одобрить выбранные")
            approve_btn.setObjectName("topBtn")
            approve_btn.setStyleSheet("font-size: 11px; background-color: #238636; color: white; border: none; padding: 6px 12px;")
            actions.addWidget(approve_btn)
            
            reject_btn = QPushButton("❌ Отклонить")
            reject_btn.setObjectName("topBtn")
            reject_btn.setStyleSheet("font-size: 11px; background-color: #da3633; color: white; border: none; padding: 6px 12px;")
            actions.addWidget(reject_btn)
        
        actions.addStretch()
        layout.addLayout(actions)
        
        # Cards grid
        grid_scroll = QScrollArea()
        grid_scroll.setWidgetResizable(True)
        grid_scroll.setStyleSheet("border: none; background-color: #0d1117;")
        
        grid_widget = QWidget()
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setSpacing(10)
        grid_layout.setContentsMargins(12, 8, 12, 12)
        
        row, col = 0, 0
        for file_data in files:
            card = MediaCard(file_data, zone)
            card.card_clicked.connect(self._on_card_clicked)
            self.cards.append(card)
            grid_layout.addWidget(card, row, col)
            col += 1
            if col >= 2:
                col = 0
                row += 1
        
        grid_scroll.setWidget(grid_widget)
        layout.addWidget(grid_scroll, stretch=1)
    
    def _on_card_clicked(self, file_data: dict, zone: str):
        """Emit signal when card is clicked."""
        # Find parent section and call its method
        parent = self.parent()
        while parent and not hasattr(parent, 'on_source_selected'):
            parent = parent.parent()
        if parent and hasattr(parent, 'on_source_selected'):
            parent.on_source_selected(file_data, zone)


class ProcessingPanel(QWidget):
    """Processing panel: appears when source is clicked."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #161b22; border-left: 1px solid #30363d;")
        self.current_source = None
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)
        
        # Title
        title = QLabel("🎨 Обработка")
        title.setStyleSheet("color: #e6edf3; font-size: 16px; font-weight: bold; border-bottom: 1px solid #30363d; padding-bottom: 8px;")
        layout.addWidget(title)
        
        # Step 1: Source
        step1_label = QLabel("1️⃣ Исходник:")
        step1_label.setStyleSheet("color: #58a6ff; font-size: 12px; font-weight: bold;")
        layout.addWidget(step1_label)
        
        self.source_preview = QLabel("👈 Кликни на карточку в колонке 'Исходники'")
        self.source_preview.setAlignment(Qt.AlignCenter)
        self.source_preview.setMinimumHeight(140)
        self.source_preview.setStyleSheet("background-color: #0d1117; border: 2px dashed #30363d; border-radius: 6px; font-size: 13px; color: #8b949e; padding: 20px;")
        layout.addWidget(self.source_preview)
        
        # Step 2: Reference
        step2_label = QLabel("2️⃣ Эталон (опционально):")
        step2_label.setStyleSheet("color: #bc8cff; font-size: 12px; font-weight: bold; margin-top: 8px;")
        layout.addWidget(step2_label)
        
        self.ref_combo = QComboBox()
        self.ref_combo.setObjectName("filterCombo")
        self.ref_combo.addItem("— без эталона —")
        self.ref_combo.addItem("ref_cafe_style.jpg (Лента)")
        self.ref_combo.addItem("ref_reels_example.mp4 (Reels)")
        self.ref_combo.addItem("ref_stories_mood.jpg (Stories)")
        self.ref_combo.setStyleSheet("font-size: 12px; padding: 6px;")
        layout.addWidget(self.ref_combo)
        
        # Step 3: Request
        step3_label = QLabel("3️⃣ Запрос на обработку:")
        step3_label.setStyleSheet("color: #3fb950; font-size: 12px; font-weight: bold; margin-top: 8px;")
        layout.addWidget(step3_label)
        
        self.request_input = QTextEdit()
        self.request_input.setObjectName("chatInput")
        self.request_input.setPlaceholderText("Например:\n• убери фон\n• сделай теплее\n• добавь объект справа\n• поменяй цветовую гамму")
        self.request_input.setMaximumHeight(100)
        self.request_input.setStyleSheet("font-size: 12px; padding: 8px;")
        layout.addWidget(self.request_input)
        
        # Process button
        process_btn = QPushButton("⚡ Обработать")
        process_btn.setObjectName("topBtn")
        process_btn.setProperty("class", "primary")
        process_btn.setStyleSheet("font-size: 14px; font-weight: bold; padding: 12px; margin-top: 8px;")
        process_btn.clicked.connect(self._on_process)
        layout.addWidget(process_btn)
        
        # Result preview
        step4_label = QLabel("4️⃣ Результат:")
        step4_label.setStyleSheet("color: #3fb950; font-size: 12px; font-weight: bold; margin-top: 8px;")
        layout.addWidget(step4_label)
        
        self.result_preview = QLabel("Здесь появится результат обработки")
        self.result_preview.setAlignment(Qt.AlignCenter)
        self.result_preview.setMinimumHeight(120)
        self.result_preview.setStyleSheet("background-color: #0d1117; border: 2px dashed #30363d; border-radius: 6px; font-size: 12px; color: #8b949e; padding: 20px;")
        layout.addWidget(self.result_preview)
        
        layout.addStretch()
    
    def set_source(self, file_data: dict):
        """Set source file and update preview."""
        self.current_source = file_data
        self.source_preview.setText(f"✅ {file_data['name']}\n{file_data['size']}")
        self.source_preview.setStyleSheet("background-color: #0d1117; border: 2px solid #238636; border-radius: 6px; font-size: 13px; color: #e6edf3; padding: 20px;")
    
    def _on_process(self):
        """Simulate processing."""
        if not self.current_source:
            QMessageBox.warning(self, "Внимание", "Сначала выбери исходник!")
            return
        
        request = self.request_input.toPlainText().strip()
        if not request:
            QMessageBox.warning(self, "Внимание", "Введи запрос на обработку!")
            return
        
        # Simulate processing
        self.result_preview.setText("⏳ Обработка...")
        self.result_preview.setStyleSheet("background-color: #0d1117; border: 2px solid #9e6a03; border-radius: 6px; font-size: 13px; color: #e6edf3; padding: 20px;")
        
        # In real implementation, this would call the processing pipeline
        # For now, simulate success
        import time
        time.sleep(1)  # Simulate processing time
        
        result_name = f"processed_{self.current_source['name']}"
        self.result_preview.setText(f"✅ Готово!\n{result_name}\n\nЗапрос: {request[:50]}...")
        self.result_preview.setStyleSheet("background-color: #0d1117; border: 2px solid #238636; border-radius: 6px; font-size: 13px; color: #e6edf3; padding: 20px;")
        
        QMessageBox.information(self, "Успех", f"Файл обработан!\n{result_name}\n\nВ реальной версии он появится в колонке 'Готовые материалы'.")


class MediaContentSection(QWidget):
    """Media Content section with 3 zones + processing panel."""
    
    def __init__(self, app_state: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.state = app_state
        self._build_ui()
    
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Main splitter: 3 columns | processing panel
        splitter = QSplitter(Qt.Horizontal)
        
        # Left: 3 columns
        columns_container = QWidget()
        columns_layout = QHBoxLayout(columns_container)
        columns_layout.setContentsMargins(16, 16, 16, 16)
        columns_layout.setSpacing(16)
        
        self.sources_col = MediaColumn("Исходники", "📥", "#58a6ff", DEMO_SOURCES, "sources")
        self.references_col = MediaColumn("Эталоны", "🎯", "#bc8cff", DEMO_REFERENCES, "references")
        self.ready_col = MediaColumn("Готовые материалы", "✅", "#3fb950", DEMO_READY, "ready")
        
        columns_layout.addWidget(self.sources_col, stretch=1)
        columns_layout.addWidget(self.references_col, stretch=1)
        columns_layout.addWidget(self.ready_col, stretch=1)
        
        splitter.addWidget(columns_container)
        
        # Right: processing panel
        self.processing_panel = ProcessingPanel()
        self.processing_panel.setFixedWidth(340)
        splitter.addWidget(self.processing_panel)
        
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        
        layout.addWidget(splitter, stretch=1)
    
    def on_source_selected(self, file_data: dict, zone: str):
        """Handle source selection."""
        if zone == "sources":
            self.processing_panel.set_source(file_data)
'''

write("gui_sections/media_content_section.py", media_content)

print("\n=== Media Content Section Made Interactive ===")
print("\nImprovements:")
print("  [OK] Click on source card → loads into processing panel")
print("  [OK] Processing panel shows 4 clear steps")
print("  [OK] Process button simulates processing (will connect to real pipeline later)")
print("  [OK] Larger card previews (120px height)")
print("  [OK] Better visual hierarchy with numbered steps")
print("  [OK] Status messages and warnings")
print("\nRun START.bat and click 'Медиа-контент' to test the flow.")