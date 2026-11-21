#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Этап1/шаг2 (финал): мост RU->EN через Ollama qwen3:8b (+LM Studio фолбэк),
авто-выгрузка VRAM после перевода, интеграция в чат. compile-gate."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = ROOT / "AI_SMM_Work_Architecture_A75"

BRIDGE_SRC = '''# -*- coding: utf-8 -*-
"""RU->EN prompt bridge via local LLM. Ollama primary (auto-unload VRAM), LM Studio fallback."""
import json, urllib.request, logging
log = logging.getLogger(__name__)
OLLAMA_URL = "http://localhost:11434/api/generate"
LMSTUDIO_URL = "http://localhost:1234/v1/chat/completions"
SYSTEM = ("Rewrite the user's image request (any language) into ONE detailed English prompt "
          "for Stable Diffusion XL. Cover: scene, subjects, exact materials/surfaces, lighting, "
          "camera/lens, style, quality. For structured real-world objects use correct technical "
          "terms (e.g. 'hard tennis court, acrylic surface, regulation baseline and service lines'). "
          "Respect negatives: if the user says 'without people', ensure 'no people' appears and do "
          "NOT add any person. Output ONLY the prompt text, no quotes, no preamble, no bullets.")

def _post(url, payload, timeout=90):
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))

def _via_ollama(model, user_text):
    resp = _post(OLLAMA_URL, {"model": model, "system": SYSTEM, "prompt": user_text,
                              "stream": False, "keep_alive": 0})
    return (resp.get("response") or "").strip()

def _via_lmstudio(model, user_text):
    resp = _post(LMSTUDIO_URL, {"model": model,
        "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user_text}],
        "temperature": 0.3, "max_tokens": 300, "stream": False})
    return (resp["choices"][0]["message"]["content"] or "").strip()

def translate_to_prompt(ru_text, ollama_model="qwen3:8b", lmstudio_model="qwen2.5-7b-instruct"):
    try:
        out = _via_ollama(ollama_model, ru_text)
        if out:
            log.info("bridge via Ollama/%s -> %s", ollama_model, out[:160])
            return out
    except Exception as e:
        log.warning("Ollama bridge failed: %s", e)
    try:
        out = _via_lmstudio(lmstudio_model, ru_text)
        if out:
            log.info("bridge via LMStudio/%s -> %s", lmstudio_model, out[:160])
            return out
    except Exception as e:
        log.warning("LMStudio bridge failed: %s", e)
    log.warning("bridge unavailable -> raw RU text to SDXL (expect degraded output)")
    return ru_text
'''

(BASE / "prompt_bridge.py").write_text(BRIDGE_SRC, encoding='utf-8', newline='\n')
print("[OK] prompt_bridge.py written")

p = BASE / "gui_ai_panel.py"
c = p.read_text(encoding='utf-8')
ch = 0

RELIGHT = (
    "            final_prompt = self.prompt\n"
    "            try:\n"
    "                from prompt_bridge import translate_to_prompt\n"
    "                rw = translate_to_prompt(self.prompt)\n"
    "                if rw and rw.strip():\n"
    "                    final_prompt = rw.strip().strip('\"').strip()\n"
    "            except Exception:\n"
    "                pass\n"
)

if "from prompt_bridge import translate_to_prompt" in c:
    print("[=] bridge already integrated in gui")
else:
    import re
    if "if self.llm is not None" in c:
        # state after old fix_russian_bridge: replace its self.llm relight block
        pat = re.compile(r'            final_prompt = self\.prompt\n(?:.*?\n)*?            client = ComfyUIClient\(\)')
        newc, n = pat.subn(RELIGHT + "            client = ComfyUIClient()", c, count=1)
        if n:
            c = newc; ch += 1; print("[OK] replaced self.llm relight with prompt_bridge")
        else:
            print("[!] self.llm relight block not matched")
    else:
        # clean async state: insert relight before client construction
        anchor = "            client = ComfyUIClient()"
        if anchor in c:
            c = c.replace(anchor, RELIGHT + anchor, 1); ch += 1
            print("[OK] inserted prompt_bridge relight")
        else:
            print("[!] 'client = ComfyUIClient()' anchor not found")
    # switch positive_prompt to translated text (idempotent)
    if "positive_prompt=self.prompt + \"" in c:
        c = c.replace("positive_prompt=self.prompt + \"", "positive_prompt=final_prompt + \"", 1)
        ch += 1; print("[OK] positive_prompt -> final_prompt")

try:
    compile(c, str(p), 'exec')
    p.write_text(c, encoding='utf-8', newline='\n')
    print(f"\n[OK] gui patched, changes={ch}, compile-gate passed")
except SyntaxError as e:
    print(f"\n[ROLLBACK] line {e.lineno}: {e.msg} — gui NOT modified")

print("\n=== Done ===")
print("Ensure Ollama app is running (tray icon). Then: .\\START.bat")