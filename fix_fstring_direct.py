#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Direct fix of broken f-string in gui_ai_panel.py line 158.
Run: python fix_fstring_direct.py
"""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

print("\n=== Direct Fix: Broken f-string ===\n")

panel_path = BASE / "gui_ai_panel.py"
content = panel_path.read_text(encoding='utf-8')
lines = content.split('\n')

# Print lines 150-165 for diagnosis
print("Lines 150-165:")
for i in range(149, min(165, len(lines))):
    print(f"{i+1}: {repr(lines[i])}")

# The problem is on line 158 (index 157)
# It has nested quotes inside f-string which Python can't handle
# We need to split it into two lines

target_line_idx = None
for i, line in enumerate(lines):
    if 'QLabel(f"' in line and ('🤖 AI' in line or '👤 Вы' in line):
        target_line_idx = i
        break

if target_line_idx is not None:
    old_line = lines[target_line_idx]
    print(f"\n[FOUND] Line {target_line_idx + 1}: {old_line.strip()}")
    
    # Get indentation
    indent = len(old_line) - len(old_line.lstrip())
    spaces = ' ' * indent
    
    # Split into two safe lines
    new_lines = [
        f'{spaces}role_icon = "🤖 AI" if role == "assistant" else "👤 Вы"',
        f'{spaces}header = QLabel(f"{role_icon}  {{timestamp}}")',
    ]
    
    # Replace single line with two lines
    lines[target_line_idx:target_line_idx+1] = new_lines
    
    # Rebuild content
    content = '\n'.join(lines)
    panel_path.write_text(content, encoding='utf-8', newline='\n')
    
    print(f"[OK] Replaced line {target_line_idx + 1} with 2 safe lines")
    print(f"  New line 1: {new_lines[0].strip()}")
    print(f"  New line 2: {new_lines[1].strip()}")
else:
    print("[ERROR] Could not find the broken f-string line")
    print("Searching for any QLabel with emoji...")
    for i, line in enumerate(lines):
        if 'QLabel' in line and ('\U0001F916' in line or '\U0001F464' in line):
            print(f"  Line {i+1}: {line.strip()[:80]}")

# Verify compilation
try:
    compile(content, str(panel_path), 'exec')
    print("\n[SUCCESS] File compiles without errors!")
except SyntaxError as e:
    print(f"\n[STILL BROKEN] Syntax error at line {e.lineno}: {e.msg}")
    print(f"  Text: {e.text}")

print("\nRun START.bat")