#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integrate ComfyUI image generation into AI Chat Panel.
Triggers on keywords: "сгенерируй картинку", "сгенерируй изображение", "нарисуй".
Safe: compile-gate on rewrite.
Run: python fix_integrate_comfy.py
"""

from pathlib import Path
import re

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

print("\n=== Integrate ComfyUI into Chat ===\n")

panel_path = BASE / "gui_ai_panel.py"
content = panel_path.read_text(encoding='utf-8')

changes = 0

# 1. Add imports at the top
imports_to_add = """from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt
from comfy_client import ComfyUIClient
"""

if "from comfy_client import ComfyUIClient" not in content:
    # Find the last import line
    lines = content.split('\n')
    insert_idx = 0
    for i, line in enumerate(lines):
        if line.startswith('import ') or line.startswith('from '):
            insert_idx = i + 1
    
    lines.insert(insert_idx, imports_to_add.strip())
    content = '\n'.join(lines)
    changes += 1
    print("[OK] Added ComfyUI imports")

# 2. Add _add_image_bubble method to AIPanel class
image_bubble_method = """
    def _add_image_bubble(self, image_path: str):
        \"\"\"Add generated image to chat.\"\"\"
        frame = QFrame()
        frame.setStyleSheet("background-color: #2d333b; border-radius: 8px;")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 10, 10, 10)
        
        label = QLabel()
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            # Scale to max 400px width, keep aspect ratio
            scaled = pixmap.scaled(400, 400, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            label.setPixmap(scaled)
        else:
            label.setText("❌ Ошибка загрузки изображения")
            
        layout.addWidget(label)
        self.chat_layout.addWidget(frame)
        self.chat_scroll.verticalScrollBar().setValue(self.chat_scroll.verticalScrollBar().maximum())
"""

if "_add_image_bubble" not in content:
    # Find the end of AIPanel class or _add_bubble method to insert after
    idx = content.find("def _add_bubble(self, role: str, text: str):")
    if idx != -1:
        # Find the end of this method (next def or end of class)
        next_def = content.find("\n    def ", idx + 10)
        if next_def != -1:
            content = content[:next_def] + image_bubble_method + content[next_def:]
            changes += 1
            print("[OK] Added _add_image_bubble method")

# 3. Add image generation trigger in the send message logic
# Look for the block where user_input is processed before or after LLM call
trigger_code = """
        # Check for image generation request
        user_lower = user_input.lower()
        if any(kw in user_lower for kw in ["сгенерируй картинку", "сгенерируй изображение", "нарисуй", "создай картинку"]):
            # Extract prompt (everything after the keyword or colon)
            prompt = user_input
            for kw in ["сгенерируй картинку:", "сгенерируй изображение:", "нарисуй:", "создай картинку:"]:
                if kw in user_lower:
                    prompt = user_input.split(kw, 1)[-1].strip()
                    break
            
            self._add_bubble("system", f"🎨 Генерирую изображение: '{prompt}'... (это займёт 15-30 сек)")
            self.repaint()
            
            try:
                client = ComfyUIClient()
                img_path = client.generate_image(positive_prompt=prompt + ", photorealistic, high quality, 8k")
                if img_path:
                    self._add_image_bubble(str(img_path))
                    self._add_bubble("system", "✅ Изображение успешно сгенерировано!")
                else:
                    self._add_bubble("system", "❌ Ошибка генерации. Убедитесь, что ComfyUI запущен (порт 8188).")
            except Exception as e:
                self._add_bubble("system", f"❌ Ошибка: {e}")
            return  # Skip normal LLM processing for pure image requests
"""

# Find a good place to inject: right after user_input is captured in _on_send
if "Check for image generation request" not in content:
    # Look for "user_input = self.input_field.toPlainText().strip()"
    idx = content.find("user_input = self.input_field.toPlainText().strip()")
    if idx != -1:
        # Find the end of that line/block
        end_of_line = content.find("\n", idx)
        content = content[:end_of_line+1] + trigger_code + content[end_of_line+1:]
        changes += 1
        print("[OK] Added image generation trigger in _on_send")
    else:
        print("[!] Could not find user_input assignment. Manual patch may be needed.")

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