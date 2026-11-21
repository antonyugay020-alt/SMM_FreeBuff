"""
Reusable GUI components: MediaThumbnail, ChatBubble, KanbanCard.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QPushButton,
    QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QPixmap, QIcon, QColor
from pathlib import Path

class MediaThumbnail(QWidget):
    """Thumbnail with status border, checkbox, name, status text."""
    
    clicked = Signal(str)  # file_id
    selection_changed = Signal(str, bool)  # file_id, selected
    
    STATUS_COLORS = {
        "pending": "#3e3e42",
        "processing": "#ff9800",
        "approved": "#4caf50",
        "rejected": "#f44336",
    }
    
    STATUS_TEXTS = {
        "pending": "Ожидает",
        "processing": "В работе",
        "approved": "Одобрено",
        "rejected": "Отклонено",
    }
    
    def __init__(self, file_id: str, file_path: str, status: str = "pending", parent=None):
        super().__init__(parent)
        self.file_id = file_id
        self.file_path = file_path
        self.status = status
        self.selected = False
        
        self.setObjectName("thumbnail")
        self.setProperty("status", status)
        self.setStyleSheet(f"border: 2px solid {self.STATUS_COLORS.get(status, '#3e3e42')}; border-radius: 4px; background-color: #252526;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Image area with checkbox overlay
        image_container = QWidget()
        image_container.setStyleSheet("background-color: #1e1e1e;")
        image_layout = QVBoxLayout(image_container)
        image_layout.setContentsMargins(0, 0, 0, 0)
        
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumHeight(100)
        self.image_label.setStyleSheet("background-color: #1e1e1e;")
        
        # Load image
        if file_path and Path(file_path).exists():
            try:
                pixmap = QPixmap(str(file_path))
                if not pixmap.isNull():
                    scaled = pixmap.scaled(150, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    self.image_label.setPixmap(scaled)
            except Exception:
                self.image_label.setText("Нет превью")
        else:
            self.image_label.setText("Нет файла")
        
        image_layout.addWidget(self.image_label)
        layout.addWidget(image_container)
        
        # Checkbox (top-left overlay, shown on hover)
        self.checkbox = QCheckBox()
        self.checkbox.setObjectName("thumbCheckbox")
        self.checkbox.setStyleSheet("""
            QCheckBox#thumbCheckbox {
                background-color: rgba(0, 0, 0, 0.7);
                border-radius: 2px;
                spacing: 0;
                padding: 2px;
                margin: 4px;
            }
        """)
        self.checkbox.stateChanged.connect(lambda state: self._on_selection_changed(state))
        
        # Name label
        self.name_label = QLabel(file_id[:20] + "..." if len(file_id) > 20 else file_id)
        self.name_label.setObjectName("thumbnailName")
        self.name_label.setStyleSheet("color: #cccccc; font-size: 10px; padding: 4px;")
        layout.addWidget(self.name_label)
        
        # Status label
        self.status_label = QLabel(self.STATUS_TEXTS.get(status, status))
        self.status_label.setObjectName("thumbnailStatus")
        self.status_label.setStyleSheet(f"color: {self.STATUS_COLORS.get(status, '#888888')}; font-size: 9px; padding: 0 4px 4px 4px;")
        layout.addWidget(self.status_label)
        
        self.setMinimumSize(160, 160)
        self.setMaximumSize(180, 180)
    
    def set_status(self, status: str):
        self.status = status
        self.setProperty("status", status)
        color = self.STATUS_COLORS.get(status, "#3e3e42")
        self.setStyleSheet(f"border: 2px solid {color}; border-radius: 4px; background-color: #252526;")
        self.status_label.setText(self.STATUS_TEXTS.get(status, status))
        self.status_label.setStyleSheet(f"color: {color}; font-size: 9px; padding: 0 4px 4px 4px;")
    
    def set_selected(self, selected: bool):
        self.selected = selected
        self.checkbox.blockSignals(True)
        self.checkbox.setChecked(selected)
        self.checkbox.blockSignals(False)
        if selected:
            self.setStyleSheet("border: 2px solid #007acc; border-radius: 4px; background-color: #2a2d2e;")
        else:
            color = self.STATUS_COLORS.get(self.status, "#3e3e42")
            self.setStyleSheet(f"border: 2px solid {color}; border-radius: 4px; background-color: #252526;")
    
    def _on_selection_changed(self, state):
        self.set_selected(state == Qt.Checked)
        self.selection_changed.emit(self.file_id, state == Qt.Checked)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.file_id)
        super().mousePressEvent(event)


class ChatBubble(QWidget):
    """Single message in AI chat history."""
    
    def __init__(self, role: str, text: str, timestamp: str = "", parent=None):
        super().__init__(parent)
        self.role = role
        self.text = text
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(2)
        
        # Header: role + timestamp
        header = QHBoxLayout()
        role_label = QLabel("🤖 AI" if role == "assistant" else "👤 Вы")
        role_label.setStyleSheet(f"color: {'#4fc3f7' if role == 'assistant' else '#81c784'}; font-weight: bold; font-size: 11px;")
        header.addWidget(role_label)
        
        if timestamp:
            time_label = QLabel(timestamp)
            time_label.setStyleSheet("color: #888888; font-size: 10px;")
            header.addStretch()
            header.addWidget(time_label)
        
        layout.addLayout(header)
        
        # Message text
        text_label = QLabel(text)
        text_label.setWordWrap(True)
        text_label.setStyleSheet("""
            color: #e0e0e0;
            font-size: 12px;
            font-family: "Consolas", monospace;
            padding: 6px 10px;
            background-color: #2d2d30;
            border-radius: 4px;
        """)
        layout.addWidget(text_label)
        
        # Separator
        sep = QLabel()
        sep.setStyleSheet("background-color: #3e3e42; min-height: 1px; max-height: 1px;")
        layout.addWidget(sep)


class KanbanCard(QWidget):
    """Card in kanban column."""
    
    def __init__(self, task_id: str, title: str, task_type: str = "text", parent=None):
        super().__init__(parent)
        self.task_id = task_id
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        
        self.setStyleSheet("background-color: #3e3e42; border-radius: 4px; border: 1px solid #4e4e52;")
        
        type_icon = "📝" if task_type == "text" else "🎬" if task_type == "video" else "🖼️"
        title_label = QLabel(f"{type_icon} {title[:40]}")
        title_label.setStyleSheet("color: #ffffff; font-size: 12px; font-weight: bold;")
        layout.addWidget(title_label)
        
        id_label = QLabel(task_id)
        id_label.setStyleSheet("color: #888888; font-size: 10px;")
        layout.addWidget(id_label)
