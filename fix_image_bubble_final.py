#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix: ensure _add_image_bubble is properly inside AIPanel class.
Safe: compile-gate on rewrite.
Run: python fix_image_bubble_final.py
"""

import re
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

print("\n=== Fix _add_image_bubble placement ===\n")

panel_path = BASE / "gui_ai_panel.py"
content = panel_path.read_text(encoding='utf-8')

# 1. Remove ALL existing _add_image_bubble methods (may be misplaced)
lines = content.split('\n')
new_lines = []
skip_until_next_def = False
found_method = False

for i, line in enumerate(lines):
    stripped = line.strip()
    
    # Check if this line starts _add_image_bubble
    if stripped.startswith('def _add_image_bubble'):
        skip_until_next_def = True
        found_method = True
        print(f"[OK] Found _add_image_bubble at line {i+1}, removing...")
        continue
    
    # If we're skipping, check if we reached next method
    if skip_until_next_def:
        # Next method at same or less indentation
        if stripped.startswith('def ') and not stripped.startswith('def _add_image_bubble'):
            skip_until_next_def = False
            new_lines.append(line)
        # Skip continuation lines (indented or empty)
        elif line.startswith('    ') or line.strip() == '':
            continue
        else:
            skip_until_next_def = False
            new_lines.append(line)
    else:
        new_lines.append(line)

content = '\n'.join(new_lines)

if found_method:
    print("[OK] Removed old _add_image_bubble method")
else:
    print("[=] No existing _add_image_bubble found")

# 2. Add _add_image_bubble right before send_message
method_code = """    def _add_image_bubble(self, image_path: str):
        \"\"\"Add generated image to chat.\"\"\"
        frame = QFrame()
        frame.setStyleSheet("background-color: #2d333b; border-radius: 8px; margin: 4px;")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 10, 10, 10)
        
        label = QLabel()
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            scaled = pixmap.scaled(400, 400, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            label.setPixmap(scaled)
        else:
            label.setText("❌ Ошибка загрузки изображения")
            
        layout.addWidget(label)
        self.chat_layout.addWidget(frame)
        self.chat_scroll.verticalScrollBar().setValue(self.chat_scroll.verticalScrollBar().maximum())

"""

target = "    def send_message(self):"
if target in content:
    content = content.replace(target, method_code + target, 1)
    print("[OK] Added _add_image_bubble before send_message")
else:
    print("[!] Could not find send_message method")

# 3. Verify imports
required_imports = {
    'QFrame': False,
    'QVBoxLayout': False,
    'QLabel': False,
    'QPixmap': False,
    'Qt': False,
    'QApplication': False
}

for line in content.split('\n'):
    for cls in required_imports:
        if cls in line and ('from PySide6' in line or 'from PyQt' in line):
            required_imports[cls] = True

missing = [cls for cls, present in required_imports.items() if not present]

if missing:
    print(f"\n[!] Missing imports: {missing}")
    # Add missing imports
    lines = content.split('\n')
    insert_idx = 0
    for i, line in enumerate(lines):
        if line.startswith('from PySide6') or line.startswith('from PyQt'):
            insert_idx = i + 1
    
    if 'QFrame' in missing or 'QVBoxLayout' in missing or 'QLabel' in missing:
        lines.insert(insert_idx, "from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QApplication")
        insert_idx += 1
        print("  [OK] Added QtWidgets imports")
    if 'QPixmap' in missing:
        lines.insert(insert_idx, "from PySide6.QtGui import QPixmap")
        insert_idx += 1
        print("  [OK] Added QPixmap import")
    if 'Qt' in missing:
        lines.insert(insert_idx, "from PySide6.QtCore import Qt")
        insert_idx += 1
        print("  [OK] Added Qt import")
    
    content = '\n'.join(lines)
else:
    print("\n[=] All required imports present")

# Compile gate
try:
    compile(content, str(panel_path), 'exec')
    panel_path.write_text(content, encoding='utf-8', newline='\n')
    print(f"\n[OK] gui_ai_panel.py updated (compile-gate passed)")
except SyntaxError as e:
    print(f"\n[ROLLBACK] syntax error at line {e.lineno}: {e.msg}")
    print("File NOT modified.")

print("\n=== Done ===")
print("Restart AI SMM Manager and try again:")
print("  'Сгенерируй картинку: красивый осенний теннисный корт, фотореализм, 8k'")