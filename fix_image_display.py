#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix: improve _add_image_bubble with explicit sizing and debug output.
Safe: compile-gate on rewrite.
Run: python fix_image_display.py
"""

import re
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

print("\n=== Fix Image Display ===\n")

panel_path = BASE / "gui_ai_panel.py"
content = panel_path.read_text(encoding='utf-8')

# Find and replace _add_image_bubble method
old_method_pattern = r'    def _add_image_bubble\(self, image_path: str\):.*?(?=\n    def |\Z)'

new_method = """    def _add_image_bubble(self, image_path: str):
        \"\"\"Add generated image to chat with proper sizing.\"\"\"
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Adding image bubble: {image_path}")
        
        frame = QFrame()
        frame.setStyleSheet("background-color: #2d333b; border-radius: 8px; margin: 4px; padding: 8px;")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 10, 10, 10)
        
        label = QLabel()
        label.setAlignment(Qt.AlignCenter)
        
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            logger.info(f"Image loaded: {pixmap.width()}x{pixmap.height()}")
            # Scale to max 512px width, keep aspect ratio
            scaled = pixmap.scaled(512, 512, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            label.setPixmap(scaled)
            label.setFixedSize(scaled.size())
        else:
            label.setText("❌ Ошибка загрузки изображения")
            logger.error(f"Failed to load image: {image_path}")
            
        layout.addWidget(label)
        
        # Insert before stretch (at the end, but before addStretch)
        insert_idx = self.chat_layout.count() - 1
        self.chat_layout.insertWidget(insert_idx, frame)
        
        # Scroll to bottom
        self.chat_scroll.verticalScrollBar().setValue(self.chat_scroll.verticalScrollBar().maximum())
        logger.info("Image bubble added successfully")

"""

# Replace old method
content = re.sub(old_method_pattern, new_method, content, flags=re.DOTALL)

if "_add_image_bubble" in content:
    print("[OK] Updated _add_image_bubble method with proper sizing")
else:
    print("[!] Could not find _add_image_bubble method")

# Compile gate
try:
    compile(content, str(panel_path), 'exec')
    panel_path.write_text(content, encoding='utf-8', newline='\n')
    print("\n[OK] gui_ai_panel.py updated (compile-gate passed)")
except SyntaxError as e:
    print(f"\n[ROLLBACK] syntax error at line {e.lineno}: {e.msg}")
    print("File NOT modified.")

print("\n=== Done ===")
print("Restart AI SMM Manager and try again:")
print("  'Сгенерируй картинку: красивый осенний теннисный корт, фотореализм, 8k'")