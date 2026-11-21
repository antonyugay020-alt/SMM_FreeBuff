"""Section manager: creates and switches between workspace sections."""
from PySide6.QtWidgets import QStackedWidget
from PySide6.QtCore import QObject

from gui_sections.strategy_section import StrategySection
from gui_sections.marketing_section import MarketingSection
from gui_sections.content_plans_section import ContentPlansSection
from gui_sections.calendar_section import CalendarSection
from gui_sections.photo_processing_section import PhotoProcessingSection
from gui_sections.video_processing_section import VideoProcessingSection
from gui_sections.publications_section import PublicationsSection
from gui_sections.files_section import FilesSection

SECTION_CLASSES = {
    "strategy": StrategySection,
    "marketing": MarketingSection,
    "content_plans": ContentPlansSection,
    "calendar": CalendarSection,
    "photo_processing": PhotoProcessingSection,
    "video_processing": VideoProcessingSection,
    "publications": PublicationsSection,
    "files": FilesSection,
}

class SectionManager(QObject):
    """Manages section widgets and state."""

    def __init__(self, stacked_widget: QStackedWidget, parent=None):
        super().__init__(parent)
        self.stacked = stacked_widget
        self.sections = {}  # section_id -> widget
        self.states = {}    # section_id -> state dict
        self._init_sections()

    def _init_sections(self):
        for sec_id, cls in SECTION_CLASSES.items():
            widget = cls()
            self.sections[sec_id] = widget
            self.stacked.addWidget(widget)

    def show_section(self, section_id: str):
        """Switch to section."""
        if section_id not in self.sections:
            return
        # Save current state
        current = self.stacked.currentWidget()
        if current:
            for sid, w in self.sections.items():
                if w is current:
                    self.states[sid] = w.save_state()
                    break
        # Show new section
        widget = self.sections[section_id]
        self.stacked.setCurrentWidget(widget)
        # Restore state
        if section_id in self.states:
            widget.restore_state(self.states[section_id])

    def get_section(self, section_id: str):
        return self.sections.get(section_id)