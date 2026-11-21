"""Section: Контент-планы."""
from gui_sections.base_section import BaseSection

class ContentPlansSection(BaseSection):
    SECTION_NAME = "Контент-планы"
    AVAILABLE_MODES = ["text", "table", "calendar"]

    def on_mode_changed(self, mode):
        print(f"[Контент-планы] Mode switched to: {mode}")