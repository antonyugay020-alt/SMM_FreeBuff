#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Final fix for gui_ai_panel.py syntax errors."""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

print("\n=== Final Fix: gui_ai_panel.py ===\n")

panel_path = BASE / "gui_ai_panel.py"
content = panel_path.read_text(encoding='utf-8')
lines = content.split('\n')

# Print lines 155-160 for diagnosis
print("Lines 155-160:")
for i in range(154, min(160, len(lines))):
    print(f"{i+1}: {repr(lines[i])}")

# Fix line 157 (missing indent) and line 158 (broken f-string)
fixed_lines = []
for i, line in enumerate(lines):
    if i == 156:  # Line 157 (0-indexed)
        # This should have proper indentation
        fixed_lines.append('            from PySide6.QtWidgets import QLabel')
    elif i == 157:  # Line 158 (0-indexed)
        # Replace broken f-string with safe version
        fixed_lines.append('            role_icon = "🤖 AI" if role == "assistant" else "👤 Вы"')
        fixed_lines.append('            header = QLabel(role_icon + "  " + timestamp)')
    elif i == 158:  # Line 159 (0-indexed)
        # Also fix the stylesheet line which has same issue
        fixed_lines.append('            color = "#4fc3f7" if role == "assistant" else "#81c784"')
        fixed_lines.append('            header.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 11px; padding: 4px 0 2px 0;")')
    else:
        fixed_lines.append(line)

# Write back
new_content = '\n'.join(fixed_lines)
panel_path.write_text(new_content, encoding='utf-8', newline='\n')

print("\n[OK] Fixed lines 157-159")

# Verify compilation
try:
    compile(new_content, str(panel_path), 'exec')
    print("[SUCCESS] File compiles without errors!")
except SyntaxError as e:
    print(f"[ERROR] Still has syntax error at line {e.lineno}: {e.msg}")
    print(f"  Text: {e.text}")

print("\nRun START.bat")