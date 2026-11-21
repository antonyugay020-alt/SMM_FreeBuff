#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix gui_main.py: move ROOT_DIR to correct position.
Run: python fix_sprint8_import.py
"""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent

print("\n=== Fixing gui_main.py ===\n")

# Read current file
gui_path = ROOT_DIR / "AI_SMM_Work_Architecture_A75" / "gui_main.py"
content = gui_path.read_text(encoding='utf-8')

# Remove the misplaced ROOT_DIR line
content = content.replace('ROOT_DIR = __import__("pathlib").Path(__file__).resolve().parent.parent\n', '')

# Add ROOT_DIR after imports
lines = content.split('\n')
new_lines = []
for i, line in enumerate(lines):
    new_lines.append(line)
    # Insert ROOT_DIR after the last import
    if line.startswith('from gui_ai_panel import AIPanel'):
        new_lines.append('')
        new_lines.append('ROOT_DIR = Path(__file__).resolve().parent.parent')

content = '\n'.join(new_lines)

# Write back
gui_path.write_text(content, encoding='utf-8')
print("[OK] gui_main.py fixed: ROOT_DIR moved to correct position")

print("\nRun START.bat to test.")