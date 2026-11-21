#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Add _add_image_bubble method right before send_message().
Safe: compile-gate on rewrite.
Run: python fix_add_image_bubble.py
"""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

print("\n=== Add _add_image_bubble ===\n")

panel_path = BASE / "gui_ai_panel.py"
content = panel_path.read_text(encoding='utf-8')

# 1. Check if method already exists
if "_add_image_bubble" in content:
    print("[=] _add_image_bubble already exists")
else:
    # Insert right before "def send_message(self):"
    target = "    def send_message(self):"
    if target in content:
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
        content = content.replace(target, method_code + target, 1)
        print("[OK] Added _add_image_bubble before send_message")
    else:
        print("[!] Could not find 'def send_message(self):'")

# 2. Check required imports
required_imports = {
    "QFrame": "from PyQt6.QtWidgets import QFrame",
    "QVBoxLayout": "from PyQt6.QtWidgets import QVBoxLayout",
    "QLabel": "from PyQt6.QtWidgets import QLabel",
    "QPixmap": "from PyQt6.QtGui import QPixmap",
    "Qt": "from PyQt6.QtCore import Qt",
}

missing = []
for cls, imp in required_imports.items():
    if cls not in content:
        missing.append(imp)

if missing:
    # Add missing imports at the top
    lines = content.split('\n')
    insert_idx = 0
    for i, line in enumerate(lines):
        if line.startswith('import ') or line.startswith('from '):
            insert_idx = i + 1
    
    for imp in missing:
        lines.insert(insert_idx, imp)
        insert_idx += 1
        print(f"[OK] Added import: {imp}")
    
    content = '\n'.join(lines)
else:
    print("[=] All required imports present")

# Compile gate
try:
    compile(content, str(panel_path), 'exec')
    panel_path.write_text(content, encoding='utf-8', newline='\n')
    print("\n[OK] gui_ai_panel.py updated (compile-gate passed)")
except SyntaxError as e:
    print(f"\n[ROLLBACK] syntax error at line {e.lineno}: {e.msg}")
    print("File NOT modified.")

print("\n=== Done ===")