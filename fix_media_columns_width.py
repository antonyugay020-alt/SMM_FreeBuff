#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix: Improve media content columns width and splitter visibility.
Run: python fix_media_columns_width.py
"""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

def write(rel, content):
    p = BASE / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding='utf-8', newline='\n')
    print(f"  [OK] {rel}")

print("\n=== Fixing Media Columns Width ===\n")

# Read current media_content_section.py
media_path = BASE / "gui_sections" / "media_content_section.py"
content = media_path.read_text(encoding='utf-8')

# 1. Increase card minimum width
content = content.replace(
    'self.setMinimumWidth(180)\n        self.setMaximumWidth(200)',
    'self.setMinimumWidth(200)\n        self.setMaximumWidth(220)'
)

# 2. Change grid from 2 columns to 1 column (wider cards)
content = content.replace(
    'if col >= 2:\n                col = 0\n                row += 1',
    'if col >= 1:\n                col = 0\n                row += 1'
)

# 3. Add minimum width to columns
content = content.replace(
    'columns_layout.addWidget(self.sources_col, stretch=1)',
    'self.sources_col.setMinimumWidth(280)\n        columns_layout.addWidget(self.sources_col, stretch=1)'
)

content = content.replace(
    'columns_layout.addWidget(self.references_col, stretch=1)',
    'self.references_col.setMinimumWidth(280)\n        columns_layout.addWidget(self.references_col, stretch=1)'
)

content = content.replace(
    'columns_layout.addWidget(self.ready_col, stretch=1)',
    'self.ready_col.setMinimumWidth(280)\n        columns_layout.addWidget(self.ready_col, stretch=1)'
)

# 4. Improve splitter styling in media section
old_splitter_style = '''splitter.setHandleWidth(4)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #30363d;
            }
            QSplitter::handle:hover {
                background-color: #58a6ff;
            }
        """)'''

new_splitter_style = '''splitter.setHandleWidth(6)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #30363d;
                border-radius: 2px;
            }
            QSplitter::handle:hover {
                background-color: #58a6ff;
            }
            QSplitter::handle:vertical {
                height: 6px;
            }
        """)'''

content = content.replace(old_splitter_style, new_splitter_style)

# 5. Set initial sizes for splitter
content = content.replace(
    'splitter.setStretchFactor(1, 1)',
    'splitter.setStretchFactor(1, 1)\n        splitter.setSizes([300, 300, 300, 340])'
)

media_path.write_text(content, encoding='utf-8', newline='\n')
print("  [OK] Updated media_content_section.py")

print("\n=== Media Columns Width Fixed ===")
print("\nChanges:")
print("  [OK] Cards: 200-220px width (was 180-200px)")
print("  [OK] Grid: 1 column instead of 2 (wider cards)")
print("  [OK] Columns: min 280px each")
print("  [OK] Splitter handles: 6px wide (more visible)")
print("  [OK] Initial splitter sizes: balanced")
print("\nRun START.bat to see wider columns.")