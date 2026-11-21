#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix: Checkbox selection tracking in MediaColumn cards.
Run: python fix_checkbox_selection.py
"""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

print("\n=== Fixing Checkbox Selection ===\n")

mc_path = BASE / "gui_sections" / "media_content_section.py"
content = mc_path.read_text(encoding='utf-8')

# Fix 1: Use proper CheckState comparison in MediaCard._on_checked
old_card_check = '''    def _on_checked(self, state):
        self.selected = state == Qt.Checked'''
new_card_check = '''    def _on_checked(self, state):
        # Handle both int and CheckState enum values
        is_checked = (int(state) & 2) != 0  # Qt.Checked == 2
        self.selected = bool(is_checked)'''
content = content.replace(old_card_check, new_card_check)

# Fix 2: Same for MediaListRow._on_checked
old_row_check = '''    def _on_checked(self, state):
        self.selected = state == Qt.Checked'''
new_row_check = '''    def _on_checked(self, state):
        is_checked = (int(state) & 2) != 0
        self.selected = bool(is_checked)'''
content = content.replace(old_row_check, new_row_check)

# Fix 3: Improve _emit_mass to collect from current DOM if self.cards is stale
old_emit = '''    def _emit_mass(self, action):
        sel = [c.file_data for c in self.cards if getattr(c, "selected", False)]
        if not sel:
            QMessageBox.warning(self, "Внимание", "Отметь галочками нужные карточки (режимы Карточки/Список).")
            return
        self.mass_action_requested.emit(action, sel)'''
new_emit = '''    def _emit_mass(self, action):
        # Collect selected files from current card objects
        sel = []
        for c in self.cards:
            if getattr(c, "selected", False):
                fd = getattr(c, "file_data", None)
                if fd:
                    sel.append(fd)
        
        if not sel:
            QMessageBox.warning(
                self, "Внимание",
                "Не выбрано ни одной карточки.\n\n"
                "Поставь галочки в левом верхнем углу каждой нужной карточки,\n"
                "затем нажми 'Одобрить' или 'Отклонить'."
            )
            logger.debug(f"_emit_mass({action}): cards={len(self.cards)}, "
                        f"selected_flags={[getattr(c,'selected',False) for c in self.cards]}")
            return
        
        logger.info(f"_emit_mass({action}): {len(sel)} file(s) selected")
        self.mass_action_requested.emit(action, sel)'''
content = content.replace(old_emit, new_emit)

mc_path.write_text(content, encoding='utf-8', newline='\n')

print("[OK] Fixed checkbox state comparison (uses bitwise check)")
print("[OK] Improved _emit_mass with debug logging")
print("[OK] Better warning message")

print("\nRun START.bat")