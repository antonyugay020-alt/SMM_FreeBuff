#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix: Correct eventFilter implementation in gui_ai_panel.py.
Run: python fix_event_filter.py
"""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

print("\n=== Fixing eventFilter ===\n")

panel_path = BASE / "gui_ai_panel.py"
content = panel_path.read_text(encoding='utf-8')

# Replace broken eventFilter method
old_method = '''    def eventFilter(self, obj, event):
        if obj == self.input_box and event.type() == event.KeyPress:
            if event.key() == Qt.Key_Return and not event.modifiers() & Qt.ShiftModifier:
                self.send_message()
                return True
        return super().eventFilter(obj, event)'''

new_method = '''    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        if obj == self.input_box and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key_Return and not (event.modifiers() & Qt.ShiftModifier):
                self.send_message()
                return True
        return super().eventFilter(obj, event)'''

if old_method in content:
    content = content.replace(old_method, new_method)
    print("[OK] Replaced eventFilter with correct implementation")
else:
    print("[WARN] Could not find exact match, trying line-by-line fix...")
    
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'def eventFilter' in line:
            # Find the end of this method (next def or class-level code)
            j = i + 1
            while j < len(lines) and not lines[j].strip().startswith('def ') and not lines[j].strip().startswith('class '):
                j += 1
            
            # Replace the entire method block
            new_lines = [
                '    def eventFilter(self, obj, event):',
                '        from PySide6.QtCore import QEvent',
                '        if obj == self.input_box and event.type() == QEvent.Type.KeyPress:',
                '            if event.key() == Qt.Key_Return and not (event.modifiers() & Qt.ShiftModifier):',
                '                self.send_message()',
                '                return True',
                '        return super().eventFilter(obj, event)',
                ''
            ]
            
            lines[i:j] = new_lines
            content = '\n'.join(lines)
            print(f"[OK] Replaced eventFilter method (lines {i+1}-{j})")
            break

# Also remove "cursor" warnings by fixing setCursor calls
content = content.replace('.setCursor(Qt.PointingHandCursor)', '.setCursor(Qt.CursorShape.PointingHandCursor)')

panel_path.write_text(content, encoding='utf-8', newline='\n')

# Verify compilation
try:
    compile(content, str(panel_path), 'exec')
    print("\n[SUCCESS] File compiles without errors!")
except SyntaxError as e:
    print(f"\n[ERROR] Still has syntax error at line {e.lineno}: {e.msg}")
    print(f"  Text: {e.text}")

print("\nRun START.bat")