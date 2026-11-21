#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix: Make all three panels resizable via QSplitter.
- Left panel: min 180px, default 240px
- Center: flexible (takes remaining space)
- Right (AI): min 280px, default 360px, can collapse to 0
Run: python fix_resizable_panels.py
"""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

def write(rel, content):
    p = BASE / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding='utf-8', newline='\n')
    print(f"  [OK] {rel}")

print("\n=== Making Panels Resizable ===\n")

# Read current gui_main.py
gui_main_path = BASE / "gui_main.py"
content = gui_main_path.read_text(encoding='utf-8')

# 1. Add QSplitter to imports
content = content.replace(
    "from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,\n    QLabel, QPushButton, QScrollArea, QFrame, QComboBox, QLineEdit, QProgressBar)",
    "from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,\n    QLabel, QPushButton, QScrollArea, QFrame, QComboBox, QLineEdit, QProgressBar, QSplitter)"
)

# 2. Replace fixed left panel width with min width
content = content.replace(
    'left.setFixedWidth(240)',
    'left.setMinimumWidth(180)\n        left.setMaximumWidth(500)'
)

# 3. Replace fixed AI panel width with min width
content = content.replace(
    'self.ai_panel.setFixedWidth(360)',
    'self.ai_panel.setMinimumWidth(280)\n        self.ai_panel.setMaximumWidth(600)'
)

# 4. Replace QHBoxLayout with QSplitter for main layout
# Find the section where we add left, center, ai_panel to main_layout
old_main_layout = """        main_layout.addWidget(left)

        # CENTER: Workspace ==="""

new_main_layout = """        # Will be added to splitter below

        # CENTER: Workspace ==="""
content = content.replace(old_main_layout, new_main_layout)

# Replace the end of _build_ui where we add center and ai_panel
old_end = """        main_layout.addWidget(center, stretch=1)

        # === RIGHT: AI Panel ==="""

new_end = """        # Will be added to splitter below

        # === RIGHT: AI Panel ==="""
content = content.replace(old_end, new_end)

# Replace the final part where ai_panel is added
old_final = """        self.ai_panel.setMinimumWidth(280)
        self.ai_panel.setMaximumWidth(600)
        main_layout.addWidget(self.ai_panel)

        # Status bar"""

new_final = """        self.ai_panel.setMinimumWidth(280)
        self.ai_panel.setMaximumWidth(600)

        # Create main splitter with 3 panels
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.addWidget(left)
        self.main_splitter.addWidget(center)
        self.main_splitter.addWidget(self.ai_panel)
        self.main_splitter.setStretchFactor(0, 0)  # Left: fixed ratio
        self.main_splitter.setStretchFactor(1, 1)  # Center: flexible
        self.main_splitter.setStretchFactor(2, 0)  # Right: fixed ratio
        self.main_splitter.setSizes([240, 1000, 360])  # Initial sizes
        self.main_splitter.setHandleWidth(4)
        self.main_splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #30363d;
            }
            QSplitter::handle:hover {
                background-color: #58a6ff;
            }
        """)

        main_layout.addWidget(self.main_splitter)

        # Status bar"""
content = content.replace(old_final, new_final)

# Remove the now-unused main_layout spacing
content = content.replace(
    "        main_layout.setContentsMargins(0, 0, 0, 0)\n        main_layout.setSpacing(0)",
    "        main_layout.setContentsMargins(0, 0, 0, 0)\n        main_layout.setSpacing(0)\n\n        # Note: main_layout now contains only the splitter"
)

gui_main_path.write_text(content, encoding='utf-8', newline='\n')
print("  [OK] Updated gui_main.py with QSplitter")

# Also update media_content_section.py to use splitter properly
media_path = BASE / "gui_sections" / "media_content_section.py"
if media_path.exists():
    media_content = media_path.read_text(encoding='utf-8')
    
    # Make processing panel resizable too
    media_content = media_content.replace(
        'self.processing_panel.setFixedWidth(340)',
        'self.processing_panel.setMinimumWidth(280)\n        self.processing_panel.setMaximumWidth(500)'
    )
    
    # Add splitter handle styling
    media_content = media_content.replace(
        'splitter.setStretchFactor(1, 1)',
        '''splitter.setStretchFactor(1, 1)
        splitter.setHandleWidth(4)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #30363d;
            }
            QSplitter::handle:hover {
                background-color: #58a6ff;
            }
        """)'''
    )
    
    media_path.write_text(media_content, encoding='utf-8', newline='\n')
    print("  [OK] Updated media_content_section.py splitter styling")

print("\n=== Resizable Panels Applied ===")
print("\nChanges:")
print("  [OK] Main window uses QSplitter for 3 panels")
print("  [OK] Left panel: 180-500px (default 240px)")
print("  [OK] Center: flexible (takes remaining space)")
print("  [OK] Right (AI): 280-600px (default 360px)")
print("  [OK] Splitter handles: 4px wide, blue on hover")
print("  [OK] Media section splitter also resizable")
print("\nNow you can drag panel borders to resize them.")
print("\nRun START.bat to test.")