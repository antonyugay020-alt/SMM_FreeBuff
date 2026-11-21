#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Switch default checkpoint in comfy_client.py to DreamShaper (auto-detect filename).
Safe: compile-gate on rewrite.
Run: python fix_switch_model.py
"""

import re
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

CKPT_DIR = Path(r"C:\ComfyUI_windows_portable\ComfyUI\models\checkpoints")

print("\n=== Switch model to DreamShaper ===\n")

# 1. Find dreamshaper file
ds_files = list(CKPT_DIR.glob("*dreamshaper*.safetensors")) + list(CKPT_DIR.glob("*DreamShaper*.safetensors"))
if not ds_files:
    print("[FAIL] No dreamshaper file found in checkpoints!")
    print("Available:")
    for f in CKPT_DIR.glob("*.safetensors"):
        print(f"  {f.name}")
    raise SystemExit(1)

new_model = ds_files[0].name
print(f"[OK] Found model: {new_model}")

# 2. Patch comfy_client.py
client_path = BASE / "comfy_client.py"
content = client_path.read_text(encoding='utf-8')

# Replace default checkpoint in generate_image signature
old = 'checkpoint: str = "Realistic_Vision_V6.0_NV_B1_fp16.safetensors"'
new = f'checkpoint: str = "{new_model}"'

if old in content:
    content = content.replace(old, new, 1)
    print("[OK] Replaced default checkpoint in generate_image()")
elif new in content:
    print("[=] Already switched to DreamShaper")
else:
    print("[!] Could not find old checkpoint string. Showing what's there:")
    for m in re.finditer(r'checkpoint.*?\.safetensors', content):
        print(f"    {m.group()}")

# 3. Also patch the __main__ test block if it hardcodes RV
content = content.replace(
    'positive_prompt="tennis court, autumn leaves, photorealistic"',
    'positive_prompt="empty tennis court, green surface, white lines, autumn trees, outdoor, no people, photorealistic"'
)
content = content.replace(
    'negative_prompt="blurry, low quality"',
    'negative_prompt="blurry, low quality, people, person, woman, man, face, portrait"'
)

# Compile gate
try:
    compile(content, str(client_path), 'exec')
    client_path.write_text(content, encoding='utf-8', newline='\n')
    print("\n[OK] comfy_client.py updated (compile-gate passed)")
except SyntaxError as e:
    print(f"\n[ROLLBACK] syntax error at line {e.lineno}: {e.msg}")

print("\n=== Done ===")