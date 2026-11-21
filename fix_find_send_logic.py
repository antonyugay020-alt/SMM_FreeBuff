#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Find where user input is captured in gui_ai_panel.py.
Run: python fix_find_send_logic.py
"""

from pathlib import Path
import re

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

print("\n=== Find send logic ===\n")

panel_path = BASE / "gui_ai_panel.py"
content = panel_path.read_text(encoding='utf-8')

lines = content.split('\n')

# Search patterns for user input capture
patterns = [
    r'toPlainText',
    r'text\(\)',
    r'user_input',
    r'message.*=',
    r'query.*=',
    r'prompt.*=',
    r'_on_send',
    r'button.*clicked',
    r'Отправить',
    r'send',
]

print("Searching for relevant lines in gui_ai_panel.py:\n")

for i, line in enumerate(lines, 1):
    stripped = line.strip()
    if not stripped or stripped.startswith('#'):
        continue
    
    for pat in patterns:
        if re.search(pat, stripped, re.I):
            # Show context
            start = max(0, i-3)
            end = min(len(lines), i+2)
            print(f"\n--- Match at line {i} (pattern: {pat}) ---")
            for j in range(start, end):
                marker = ">>>" if j == i-1 else "   "
                print(f"  {marker} {j+1}: {lines[j][:120]}")
            break

print("\n=== Done ===")