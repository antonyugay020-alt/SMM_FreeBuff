#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Find the correct Qt library used in the project and fix gui_ai_panel.py imports.
Safe: compile-gate on rewrite.
Run: python fix_qt_imports.py
"""

import re
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

print("\n=== Fix Qt Imports ===\n")

# 1. Find the correct Qt library from other working files
qt_lib = None
for py_file in BASE.glob("*.py"):
    if py_file.name == "gui_ai_panel.py":
        continue  # skip the broken one
    try:
        text = py_file.read_text(encoding='utf-8')
        match = re.search(r'from (PyQt5|PyQt6|PySide2|PySide6)', text)
        if match:
            qt_lib = match.group(1)
            print(f"[OK] Found working Qt library: {qt_lib} (in {py_file.name})")
            break
    except Exception:
        pass

if not qt_lib:
    print("[FAIL] Could not find Qt library in project files!")
    raise SystemExit(1)

# 2. Fix gui_ai_panel.py
panel_path = BASE / "gui_ai_panel.py"
content = panel_path.read_text(encoding='utf-8')

# Remove bad PyQt imports I added previously
content = re.sub(r'^from PyQt[56]\.QtGui import QPixmap\n', '', content, flags=re.MULTILINE)
content = re.sub(r'^from PyQt[56]\.QtCore import Qt\n', '', content, flags=re.MULTILINE)
content = re.sub(r'^from PyQt[56]\.QtWidgets import [^\n]+\n', '', content, flags=re.MULTILINE)

# Add correct imports
imports_to_add = [
    f"from {qt_lib}.QtGui import QPixmap",
    f"from {qt_lib}.QtCore import Qt",
    f"from {qt_lib}.QtWidgets import QFrame, QVBoxLayout, QLabel, QApplication"
]

lines = content.split('\n')
insert_idx = 0
for i, line in enumerate(lines):
    if line.startswith('import ') or line.startswith('from '):
        insert_idx = i + 1

for imp in reversed(imports_to_add):
    lines.insert(insert_idx, imp)

content = '\n'.join(lines)

# Compile gate
try:
    compile(content, str(panel_path), 'exec')
    panel_path.write_text(content, encoding='utf-8', newline='\n')
    print(f"\n[OK] gui_ai_panel.py updated with {qt_lib} imports (compile-gate passed)")
except SyntaxError as e:
    print(f"\n[ROLLBACK] syntax error at line {e.lineno}: {e.msg}")
    print("File NOT modified.")

print("\n=== Done ===")
print("Now run: .\\START.bat")