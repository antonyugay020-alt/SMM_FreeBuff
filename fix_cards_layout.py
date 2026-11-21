#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix: Improve card layout - 2 columns, larger thumbnails.
Run: python fix_cards_layout.py
"""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

print("\n=== Fixing Cards Layout ===\n")

mc_path = BASE / "gui_sections" / "media_content_section.py"
content = mc_path.read_text(encoding='utf-8')

# Fix 1: Increase card width and thumbnail size
old_card_min = 'self.setMinimumWidth(200)\n        self.setMaximumWidth(260)'
new_card_min = 'self.setMinimumWidth(280)\n        self.setMaximumWidth(320)'
content = content.replace(old_card_min, new_card_min)

old_preview_size = 'scaled = pm.scaled(260, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation)'
new_preview_size = 'scaled = pm.scaled(320, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation)'
content = content.replace(old_preview_size, new_preview_size)

old_preview_min = 'preview.setMinimumHeight(120)'
new_preview_min = 'preview.setMinimumHeight(180)'
content = content.replace(old_preview_min, new_preview_min)

# Fix 2: Change grid to 2 columns in cards mode
old_grid = '''            grid = QGridLayout()
            grid.setSpacing(12)
            row, col = 0, 0
            for file_data in self.files:
                card = MediaCard(file_data, self.zone)
                card.card_clicked.connect(self.card_clicked_signal.emit)
                grid.addWidget(card, row, col)
                col += 1
                if col >= 1:
                    col = 0
                    row += 1
            self.content_layout_inner.addLayout(grid)'''

new_grid = '''            grid = QGridLayout()
            grid.setSpacing(12)
            row, col = 0, 0
            for file_data in self.files:
                card = MediaCard(file_data, self.zone)
                card.card_clicked.connect(self.card_clicked_signal.emit)
                grid.addWidget(card, row, col)
                col += 1
                if col >= 2:  # 2 columns
                    col = 0
                    row += 1
            self.content_layout_inner.addLayout(grid)'''

content = content.replace(old_grid, new_grid)

# Fix 3: Increase column width
old_col_min = 'self.sources_col.setMinimumWidth(260)\n        self.sources_col.setMaximumWidth(500)'
new_col_min = 'self.sources_col.setMinimumWidth(380)\n        self.sources_col.setMaximumWidth(700)'
content = content.replace(old_col_min, new_col_min)

old_refs_min = 'self.references_col.setMinimumWidth(260)\n        self.references_col.setMaximumWidth(500)'
new_refs_min = 'self.references_col.setMinimumWidth(380)\n        self.references_col.setMaximumWidth(700)'
content = content.replace(old_refs_min, new_refs_min)

old_ready_min = 'self.ready_col.setMinimumWidth(260)\n        self.ready_col.setMaximumWidth(500)'
new_ready_min = 'self.ready_col.setMinimumWidth(380)\n        self.ready_col.setMaximumWidth(700)'
content = content.replace(old_ready_min, new_ready_min)

# Fix 4: Adjust splitter sizes
old_splitter = 'splitter.setSizes([950, 380])'
new_splitter = 'splitter.setSizes([1100, 400])'
content = content.replace(old_splitter, new_splitter)

mc_path.write_text(content, encoding='utf-8', newline='\n')

print("[OK] Increased card width to 280-320px")
print("[OK] Increased thumbnail size to 320x180px")
print("[OK] Changed grid to 2 columns")
print("[OK] Increased column width to 380-700px")
print("[OK] Adjusted splitter sizes")

print("\nRun START.bat")