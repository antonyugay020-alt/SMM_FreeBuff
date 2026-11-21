"""Section: Обработка фото."""
from gui_sections.base_section import BaseSection

class PhotoProcessingSection(BaseSection):
    SECTION_NAME = "Обработка фото"
    AVAILABLE_MODES = ["editor", "batch"]

    def on_mode_changed(self, mode):
        print(f"[Обработка фото] Mode switched to: {mode}")