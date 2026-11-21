#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Find correct widget names in AIPanel class for adding images.
Run: python fix_find_chat_widgets.py
"""

import re
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

print("\n=== Find Chat Widgets ===\n")

panel_path = BASE / "gui_ai_panel.py"
content = panel_path.read_text(encoding='utf-8')

# Find AIPanel class
class_match = re.search(r'class AIPanel.*?:(.*?)(?=\nclass |\Z)', content, re.DOTALL)
if not class_match:
    print("[FAIL] Could not find AIPanel class")
    raise SystemExit(1)

class_body = class_match.group(1)
lines = class_body.split('\n')

print("Searching for layout and scroll widgets in AIPanel:\n")

# Search for layout-related attributes
patterns = [
    r'self\.\w*layout\w*',
    r'self\.\w*scroll\w*',
    r'self\.\w*chat\w*',
    r'self\.\w*message\w*',
    r'QVBoxLayout',
    r'QScrollArea',
    r'addWidget',
]

for i, line in enumerate(lines, 1):
    stripped = line.strip()
    if not stripped or stripped.startswith('#'):
        continue
    
    for pat in patterns:
        if re.search(pat, stripped, re.I):
            print(f"  Line {i}: {stripped[:120]}")
            break

print("\n=== Done ===")