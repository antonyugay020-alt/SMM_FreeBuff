"""Section: Маркетинг."""
from gui_sections.base_section import BaseSection

class MarketingSection(BaseSection):
    SECTION_NAME = "Маркетинг"
    AVAILABLE_MODES = ["text", "table"]

    def on_mode_changed(self, mode):
        print(f"[Маркетинг] Mode switched to: {mode}")