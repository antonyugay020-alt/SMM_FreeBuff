#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Этап1/шаг2: русский мост — LLM разворачивает RU-запрос в EN-промпт для SDXL. compile-gate."""
from pathlib import Path

BASE = Path(__file__).resolve().parent / "AI_SMM_Work_Architecture_A75"
p = BASE / "gui_ai_panel.py"
c = p.read_text(encoding='utf-8')
ch = 0

BRIDGE = '''BRIDGE_SYS = ("You rewrite a user's image request (any language) into ONE detailed English "
"prompt for Stable Diffusion XL. Describe: scene type, main subjects, exact materials and "
"surfaces, lighting, camera/lens, style, quality tags. If the request implies a real-world "
"structured object (sports court, room, vehicle, product), use its correct technical terms "
"(e.g. 'hard tennis court, acrylic surface, regulation baseline and service lines'). "
"Output ONLY the prompt text. No quotes, no preamble, no explanation, no bullet points. "
"Do not invent people unless the request asks for them.")

'''

# 1. константа перед классом-воркером
if "BRIDGE_SYS" not in c:
    anchor = "class _GenWorker(QObject):"
    if anchor in c:
        c = c.replace(anchor, BRIDGE + anchor, 1)
        ch += 1; print("[OK] BRIDGE_SYS inserted")
    else:
        print("[!] _GenWorker class not found")

# 2. __init__ воркера: принять llm
old_init = "    def __init__(self, prompt):\n        super().__init__()\n        self.prompt = prompt"
new_init = "    def __init__(self, prompt, llm=None):\n        super().__init__()\n        self.prompt = prompt\n        self.llm = llm"
if old_init in c:
    c = c.replace(old_init, new_init, 1)
    ch += 1; print("[OK] _GenWorker.__init__ now takes llm")
elif "def __init__(self, prompt, llm=None)" in c:
    print("[=] __init__ already patched")
else:
    print("[!] __init__ anchor not found")

# 3. релайт внутри run() перед ComfyUIClient()
old_run = "        try:\n            client = ComfyUIClient()"
new_run = ("        try:\n"
           "            final_prompt = self.prompt\n"
           "            if self.llm is not None and getattr(self.llm, 'available', False):\n"
           "                try:\n"
           "                    rw = self.llm.generate(self.prompt, system_prompt=BRIDGE_SYS)\n"
           "                    if rw and rw.strip():\n"
           "                        final_prompt = rw.strip().strip('\"').strip()\n"
           "                except Exception:\n"
           "                    pass\n"
           "            client = ComfyUIClient()")
if old_run in c:
    c = c.replace(old_run, new_run, 1)
    ch += 1; print("[OK] RU->EN relight added in run()")
elif "final_prompt = self.prompt" in c:
    print("[=] relight already present")
else:
    print("[!] run() anchor not found")

# 4. positive_prompt uses final_prompt
old_pp = 'positive_prompt=self.prompt + ", photorealistic, high quality, 8k, professional",'
new_pp = 'positive_prompt=final_prompt + ", photorealistic, high quality, 8k, professional",'
if old_pp in c:
    c = c.replace(old_pp, new_pp, 1)
    ch += 1; print("[OK] positive_prompt switched to final_prompt")
elif new_pp in c:
    print("[=] positive_prompt already switched")
else:
    print("[!] positive_prompt anchor not found")

# 5. триггер передаёт local_llm в воркер
old_w = "self._gen_worker = _GenWorker(prompt)"
new_w = "self._gen_worker = _GenWorker(prompt, getattr(self, 'local_llm', None))"
if old_w in c:
    c = c.replace(old_w, new_w, 1)
    ch += 1; print("[OK] trigger passes local_llm to worker")
elif new_w in c:
    print("[=] trigger already passes llm")
else:
    print("[!] worker-construction anchor not found")

try:
    compile(c, str(p), 'exec')
    p.write_text(c, encoding='utf-8', newline='\n')
    print(f"\n[OK] applied, changes={ch}, compile-gate passed")
except SyntaxError as e:
    print(f"\n[ROLLBACK] line {e.lineno}: {e.msg} — file NOT modified")