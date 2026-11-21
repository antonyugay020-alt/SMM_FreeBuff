#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Remove "История версий" panel and version label from strategy UI.
Safe: compile-gate on rewrite.
Run: python fix_remove_version_panel.py
"""

from pathlib import Path
import re

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

print("\n=== Remove Version Panel ===\n")

# Search for version-related UI code
gui_files = list(BASE.glob("gui_*.py"))
version_ui_patterns = [
    r'История версий',
    r'Версия \d+\.\d+',
    r'version_history',
    r'version_label',
    r'Обновлено \d+\.\d+\.\d{4}',
]

print("[1/2] Searching for version UI elements...")
found_locations = []

for gf in gui_files:
    if not gf.exists():
        continue
    txt = gf.read_text(encoding='utf-8')
    for pat in version_ui_patterns:
        for m in re.finditer(pat, txt):
            line_no = txt[:m.start()].count('\n') + 1
            line_text = txt.split('\n')[line_no - 1].strip()
            found_locations.append((gf.name, line_no, line_text[:100]))

if found_locations:
    print(f"  Found {len(found_locations)} version UI references:")
    for fname, lno, txt in found_locations:
        print(f"    {fname}:{lno}: {txt}")
else:
    print("  [=] No version UI elements found")

# Try to find the specific section that renders "История версий" panel
print("\n[2/2] Looking for version panel rendering code...")

# Search in strategy-related files
strategy_files = [f for f in gui_files if 'strategy' in f.name.lower()]
if not strategy_files:
    # Try gui_main.py
    strategy_files = [BASE / "gui_main.py"]

for sf in strategy_files:
    if not sf.exists():
        continue
    content = sf.read_text(encoding='utf-8')
    
    # Look for the version history panel block
    # Common patterns: QFrame with "История версий" label, or version_label widget
    if 'История версий' in content:
        print(f"  [FOUND] 'История версий' in {sf.name}")
        # Find the block that creates this panel
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if 'История версий' in line:
                # Show context around this line
                start = max(0, i-5)
                end = min(len(lines), i+10)
                print(f"\n  Context around line {i+1}:")
                for j in range(start, end):
                    marker = ">>>" if j == i else "   "
                    print(f"  {marker} {j+1}: {lines[j]}")
                break

print("\n=== Done ===")
print("Based on findings, I'll write the exact removal code.")
print("Run this script first to locate the version panel code.")