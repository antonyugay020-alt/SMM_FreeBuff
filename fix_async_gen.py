#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Этап1/шаг1: генерация в отдельном потоке, чат не замерзает. compile-gate."""
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent / "AI_SMM_Work_Architecture_A75"
p = BASE / "gui_ai_panel.py"
c = p.read_text(encoding='utf-8')
ch = 0

# 1. импорты QThread/QObject/Signal в существующую строку QtCore
m = re.search(r'(from PySide6\.QtCore import )([^\n]+)', c)
if m:
    names = [x.strip() for x in m.group(2).split(',') if x.strip()]
    for need in ("QThread", "QObject", "Signal"):
        if need not in names:
            names.append(need)
    c = c[:m.start()] + "from PySide6.QtCore import " + ", ".join(names) + c[m.end():]
    ch += 1
    print("[OK] QtCore imports:", ", ".join(names))
else:
    print("[!] QtCore import line not found")

# 2. воркер-класс перед AIPanel
worker = '''class _GenWorker(QObject):
    done = Signal(object)
    def __init__(self, prompt):
        super().__init__()
        self.prompt = prompt
    def run(self):
        try:
            client = ComfyUIClient()
            img = client.generate_image(
                positive_prompt=self.prompt + ", photorealistic, high quality, 8k, professional",
                negative_prompt="blurry, low quality, distorted, ugly, watermark, bad anatomy, poorly drawn, extra fingers, deformed faces",
            )
            self.done.emit(("ok", str(img)) if img else ("err", "Ошибка генерации. Проверь, что ComfyUI запущен (порт 8188)."))
        except Exception as e:
            self.done.emit(("err", f"Ошибка: {e}"))

'''
if "_GenWorker" not in c:
    cm = re.search(r'(?m)^class AIPanel\b', c)
    if cm:
        c = c[:cm.start()] + worker + c[cm.start():]
        ch += 1
        print("[OK] _GenWorker inserted")
    else:
        print("[!] class AIPanel not found")

# 3. метод-обработчик перед send_message
handler = '''    def _on_gen_done(self, result):
        self._gen_busy = False
        kind, payload = result
        if kind == "ok":
            self._add_image_bubble(payload)
            self._add_bubble("system", "✅ Изображение сгенерировано!")
        else:
            self._add_bubble("system", f"❌ {payload}")

'''
if "_on_gen_done" not in c:
    tgt = "    def send_message(self):"
    if tgt in c:
        c = c.replace(tgt, handler + tgt, 1)
        ch += 1
        print("[OK] _on_gen_done inserted")
    else:
        print("[!] send_message not found")

# 4. замена синхронного триггера на потоковый
new_trig = '''        # Check for image generation request (async, non-blocking)
        lower_text = text.lower()
        if any(kw in lower_text for kw in ["сгенерируй картинку", "сгенерируй изображение", "нарисуй", "создай картинку", "сгенерируй фото"]):
            if getattr(self, "_gen_busy", False):
                self._add_bubble("system", "⏳ Уже генерирую предыдущий запрос, подожди окончания.")
                return
            prompt = text
            for kw in ["сгенерируй картинку:", "сгенерируй изображение:", "нарисуй:", "создай картинку:", "сгенерируй фото:"]:
                if kw in lower_text:
                    prompt = text.split(kw, 1)[-1].strip()
                    break
            self._gen_busy = True
            self._add_bubble("system", f"🎨 Генерирую: «{prompt}»... (SDXL + апскейл, 1–2 мин; чат не замерзнет)")
            self.chat_scroll.verticalScrollBar().setValue(self.chat_scroll.verticalScrollBar().maximum())
            self._gen_thread = QThread()
            self._gen_worker = _GenWorker(prompt)
            self._gen_worker.moveToThread(self._gen_thread)
            self._gen_thread.started.connect(self._gen_worker.run)
            self._gen_worker.done.connect(self._on_gen_done)
            self._gen_worker.done.connect(self._gen_thread.quit)
            self._gen_thread.finished.connect(self._gen_thread.deleteLater)
            self._gen_thread.start()
            return'''

old_pat = r'        # Check for image generation request.*?\n            return'
if re.search(old_pat, c, re.DOTALL):
    c = re.sub(old_pat, new_trig, c, count=1, flags=re.DOTALL)
    ch += 1
    print("[OK] trigger switched to async thread")
else:
    print("[!] sync trigger block not found (file left intact)")

try:
    compile(c, str(p), 'exec')
    p.write_text(c, encoding='utf-8', newline='\n')
    print(f"\n[OK] applied, changes={ch}, compile-gate passed")
except SyntaxError as e:
    print(f"\n[ROLLBACK] line {e.lineno}: {e.msg} — file NOT modified")