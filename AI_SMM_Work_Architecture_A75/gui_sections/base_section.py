"""Base class for all workspace sections."""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Signal

class BaseSection(QWidget):
    """Base section with header and mode switcher."""
    mode_changed = Signal(str)  # mode name

    SECTION_NAME = "Раздел"
    AVAILABLE_MODES = ["text"]  # text, table, charts, calendar, etc.

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_mode = "text"
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header with title and mode switcher
        header = QWidget()
        header.setObjectName("sectionHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 8, 12, 8)

        self.title_label = QLabel(self.SECTION_NAME)
        self.title_label.setObjectName("sectionTitle")
        header_layout.addWidget(self.title_label)

        header_layout.addStretch()

        # Mode switcher buttons
        self.mode_buttons = {}
        for mode in self.AVAILABLE_MODES:
            btn = QPushButton(mode.capitalize())
            btn.setObjectName("modeBtn")
            btn.setCheckable(True)
            if mode == self.current_mode:
                btn.setChecked(True)
                btn.setProperty("active", True)
            btn.clicked.connect(lambda checked, m=mode: self.set_mode(m))
            self.mode_buttons[mode] = btn
            header_layout.addWidget(btn)

        layout.addWidget(header)

        # Content area (to be overridden)
        self.content_area = QWidget()
        self.content_area.setObjectName("sectionPlaceholder")
        content_layout = QVBoxLayout(self.content_area)
        content_layout.setAlignment(__import__("PySide6.QtCore", fromlist=["Qt"]).Qt.AlignCenter)

        self.mode_label = QLabel(f"Режим: {self.current_mode}")
        self.mode_label.setObjectName("placeholderTitle")
        content_layout.addWidget(self.mode_label)

        self.desc_label = QLabel(f"Раздел \"{self.SECTION_NAME}\" — в разработке")
        self.desc_label.setObjectName("placeholderText")
        content_layout.addWidget(self.desc_label)

        layout.addWidget(self.content_area, stretch=1)

    def set_mode(self, mode):
        """Switch view mode."""
        if mode not in self.AVAILABLE_MODES:
            return
        self.current_mode = mode
        for m, btn in self.mode_buttons.items():
            btn.setChecked(m == mode)
            btn.setProperty("active", m == mode)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self.mode_label.setText(f"Режим: {mode}")
        self.mode_changed.emit(mode)
        self.on_mode_changed(mode)

    def on_mode_changed(self, mode):
        """Override in subclasses to react to mode changes."""
        pass

    def save_state(self):
        """Override to save section state."""
        return {"mode": self.current_mode}

    def restore_state(self, state):
        """Override to restore section state."""
        if state and "mode" in state:
            self.set_mode(state["mode"])