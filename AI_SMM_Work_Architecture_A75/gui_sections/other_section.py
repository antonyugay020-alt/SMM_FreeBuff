"""Section: Прочие материалы."""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt


class OtherSection(QWidget):
    """Placeholder for Прочие материалы section."""

    def __init__(self, app_state=None, parent=None):
        super().__init__(parent)
        self.state = app_state
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        
        title = QLabel("Прочие материалы")
        title.setStyleSheet("color: #e6edf3; font-size: 24px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        subtitle = QLabel("Архив, буфер, документы, референсы")
        subtitle.setStyleSheet("color: #8b949e; font-size: 14px;")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)
        
        status = QLabel("Раздел в разработке")
        status.setStyleSheet("color: #8b949e; font-size: 12px; margin-top: 20px;")
        status.setAlignment(Qt.AlignCenter)
        layout.addWidget(status)
