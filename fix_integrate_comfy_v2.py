#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integrate ComfyUI image generation into AI Chat Panel.
Triggers on keywords in send_message().
Safe: compile-gate on rewrite.
Run: python fix_integrate_comfy_v2.py
"""

from pathlib import Path
import re

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

print("\n=== Integrate ComfyUI v2 ===\n")

panel_path = BASE / "gui_ai_panel.py"
content = panel_path.read_text(encoding='utf-8')

changes = 0

# 1. Add imports at the top
imports_block = """from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt
from comfy_client import ComfyUIClient
"""

if "from comfy_client import ComfyUIClient" not in content:
    # Find last import line
    lines = content.split('\n')
    insert_idx = 0
    for i, line in enumerate(lines):
        if line.startswith('import ') or line.startswith('from '):
            insert_idx = i + 1
    
    lines.insert(insert_idx, imports_block.strip())
    content = '\n'.join(lines)
    changes += 1
    print("[OK] Added ComfyUI imports")
else:
    print("[=] Imports already present")

# 2. Add _add_image_bubble method
# Find the _add_bubble method and insert after it
image_method = """
    def _add_image_bubble(self, image_path: str):
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

if "_add_image_bubble" not in content:
    # Find _add_bubble method and insert after it ends
    idx = content.find("def _add_bubble(")
    if idx != -1:
        # Find next method at same indentation level
        next_method = re.search(r'\n    def [a-z]', content[idx+20:])
        if next_method:
            insert_pos = idx + 20 + next_method.start()
            content = content[:insert_pos] + image_method + content[insert_pos:]
            changes += 1
            print("[OK] Added _add_image_bubble method")
        else:
            print("[!] Could not find insertion point for _add_image_bubble")
    else:
        print("[!] _add_bubble method not found")
else:
    print("[=] _add_image_bubble already present")

# 3. Add image generation trigger in send_message
trigger_code = """
        # Check for image generation request
        lower_text = text.lower()
        if any(kw in lower_text for kw in ["сгенерируй картинку", "сгенерируй изображение", "нарисуй", "создай картинку", "сгенерируй фото"]):
            prompt = text
            for kw in ["сгенерируй картинку:", "сгенерируй изображение:", "нарисуй:", "создай картинку:", "сгенерируй фото:"]:
                if kw in lower_text:
                    prompt = text.split(kw, 1)[-1].strip()
                    break
            
            self._add_bubble("system", f"🎨 Генерирую изображение: '{prompt}'... (15-30 сек)")
            self.chat_scroll.verticalScrollBar().setValue(self.chat_scroll.verticalScrollBar().maximum())
            QApplication.processEvents()
            
            try:
                client = ComfyUIClient()
                img_path = client.generate_image(
                    positive_prompt=prompt + ", photorealistic, high quality, 8k, professional",
                    negative_prompt="blurry, low quality, distorted, ugly, watermark"
                )
                if img_path:
                    self._add_image_bubble(str(img_path))
                    self._add_bubble("system", "✅ Изображение сгенерировано!")
                else:
                    self._add_bubble("system", "❌ Ошибка генерации. Убедитесь, что ComfyUI запущен (порт 8188).")
            except Exception as e:
                self._add_bubble("system", f"❌ Ошибка: {e}")
            return
"""

if "Check for image generation request" not in content:
    # Find "if not text:" in send_message and insert after its return
    old_block = """        if not text:
            return"""
    
    if old_block in content:
        content = content.replace(old_block, old_block + trigger_code, 1)
        changes += 1
        print("[OK] Added image generation trigger in send_message")
    else:
        print("[!] Could not find 'if not text: return' block")
else:
    print("[=] Image trigger already present")

# Compile gate
try:
    compile(content, str(panel_path), 'exec')
    panel_path.write_text(content, encoding='utf-8', newline='\n')
    print(f"\n[OK] gui_ai_panel.py updated ({changes} changes, compile-gate passed)")
except SyntaxError as e:
    print(f"\n[ROLLBACK] syntax error at line {e.lineno}: {e.msg}")
    print("File NOT modified.")

print("\n=== Done ===")
print("Restart AI SMM Manager (.\\START.bat) and type in chat:")
print("  'Сгенерируй картинку: красивый осенний теннисный корт, фотореализм'")