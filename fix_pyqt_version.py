#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix: replace PyQt6 imports with PyQt5 in gui_ai_panel.py.
Safe: compile-gate on rewrite.
Run: python fix_pyqt_version.py
"""

from pathlib import Path
import re

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

print("\n=== Fix PyQt version ===\n")

panel_path = BASE / "gui_ai_panel.py"
content = panel_path.read_text(encoding='utf-8')

# 1. Replace PyQt6 with PyQt5
if "PyQt6" in content:
    content = content.replace("PyQt6", "PyQt5")
    print("[OK] Replaced PyQt6 -> PyQt5")
else:
    print("[=] No PyQt6 imports found")

# 2. Remove duplicate imports (keep only one of each)
# Find all import lines and deduplicate
lines = content.split('\n')
seen_imports = set()
new_lines = []

for line in lines:
    stripped = line.strip()
    if stripped.startswith('from PyQt5') or stripped.startswith('import PyQt5'):
        # Normalize for dedup (ignore whitespace)
        key = re.sub(r'\s+', ' ', stripped)
        if key in seen_imports:
            # Skip duplicate
            print(f"  [SKIP] Duplicate: {stripped[:70]}")
            continue
        seen_imports.add(key)
    new_lines.append(line)

content = '\n'.join(new_lines)

# 3. Verify required classes are imported
required = ['QFrame', 'QVBoxLayout', 'QLabel', 'QPixmap', 'Qt']
missing = [cls for cls in required if cls not in content]

if missing:
    print(f"\n[!] Missing classes: {missing}")
    print("Adding fallback imports...")
    
    # Add missing imports after first PyQt5 import
    lines = content.split('\n')
    insert_idx = 0
    for i, line in enumerate(lines):
        if line.strip().startswith('from PyQt5'):
            insert_idx = i + 1
            break
    
    fallbacks = []
    if 'QFrame' in missing or 'QVBoxLayout' in missing or 'QLabel' in missing:
        fallbacks.append("from PyQt5.QtWidgets import QFrame, QVBoxLayout, QLabel")
    if 'QPixmap' in missing:
        fallbacks.append("from PyQt5.QtGui import QPixmap")
    if 'Qt' in missing:
        fallbacks.append("from PyQt5.QtCore import Qt")
    
    for fb in fallbacks:
        lines.insert(insert_idx, fb)
        insert_idx += 1
        print(f"  [OK] Added: {fb}")
    
    content = '\n'.join(lines)
else:
    print("\n[=] All required classes present")

# Compile gate
try:
    compile(content, str(panel_path), 'exec')
    panel_path.write_text(content, encoding='utf-8', newline='\n')
    print("\n[OK] gui_ai_panel.py updated (compile-gate passed)")
except SyntaxError as e:
    print(f"\n[ROLLBACK] syntax error at line {e.lineno}: {e.msg}")
    print("File NOT modified.")

print("\n=== Done ===")
print("Now run: .\\START.bat")