"""Section: Обработка видео."""
from gui_sections.base_section import BaseSection

class VideoProcessingSection(BaseSection):
    SECTION_NAME = "Обработка видео"
    AVAILABLE_MODES = ["editor", "timeline"]

    def on_mode_changed(self, mode):
        print(f"[Обработка видео] Mode switched to: {mode}")