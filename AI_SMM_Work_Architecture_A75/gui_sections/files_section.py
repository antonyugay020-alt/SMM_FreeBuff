"""Section: Файлы."""
from gui_sections.base_section import BaseSection

class FilesSection(BaseSection):
    SECTION_NAME = "Файлы"
    AVAILABLE_MODES = ["grid", "list"]

    def on_mode_changed(self, mode):
        print(f"[Файлы] Mode switched to: {mode}")