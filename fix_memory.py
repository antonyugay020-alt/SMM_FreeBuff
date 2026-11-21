#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Memory framework: gen log + bridge log + decisions journal + standards folder.
Writes memory_core.py, patches comfy_client.py and gui_ai_panel.py (logging only). compile-gate."""
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent / "AI_SMM_Work_Architecture_A75"

MEMORY_SRC = '''# -*- coding: utf-8 -*-
"""Project memory: generation log, bridge log, decisions journal, standards folder.
CLI: python memory_core.py summary | tail [N] | mark <file.png> | standards | note "text"
"""
import sys, shutil, datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent
MEM = ROOT / "data" / "memory"
GEN = ROOT / "data" / "generated_images"
STD = ROOT / "data" / "standards"
GEN_LOG = MEM / "generations.log"
BRIDGE_LOG = MEM / "bridge.log"
DECISIONS = MEM / "decisions.md"

def _ensure():
    MEM.mkdir(parents=True, exist_ok=True)
    STD.mkdir(parents=True, exist_ok=True)

def _ts():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def log_generation(filename, prompt_en, model="", sdxl="", status="ok"):
    _ensure()
    line = f"[{_ts()}] file={filename} | model={model} | sdxl={sdxl} | status={status} | prompt_en={prompt_en[:400]}\\n"
    with GEN_LOG.open("a", encoding="utf-8") as f:
        f.write(line)

def log_bridge(ru_text, en_text):
    _ensure()
    line = f"[{_ts()}] RU: {ru_text[:200]} | EN: {en_text[:400]}\\n"
    with BRIDGE_LOG.open("a", encoding="utf-8") as f:
        f.write(line)

def log_decision(text):
    _ensure()
    with DECISIONS.open("a", encoding="utf-8") as f:
        f.write(f"- [{_ts()}] {text}\\n")

def mark_standard(filename):
    _ensure()
    src = GEN / filename
    if not src.exists():
        print(f"[!] not found: {src}")
        return
    dst = STD / f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
    shutil.copy2(src, dst)
    log_decision(f"standard marked: {dst.name}")
    print(f"[OK] copied to standards: {dst.name}")

def list_standards():
    _ensure()
    files = sorted(STD.glob("*"))
    if not files:
        print("(standards empty)")
    for f in files:
        print(f"  {f.name}")

def tail(n=15):
    _ensure()
    for p in (GEN_LOG, BRIDGE_LOG):
        print(f"--- {p.name} (last {n}) ---")
        if p.exists():
            lines = p.read_text(encoding="utf-8").splitlines()
            for ln in lines[-n:]:
                print(ln)
        else:
            print("(empty)")

def summary():
    _ensure()
    print("=== PROJECT MEMORY SUMMARY ===")
    print(f"-- standards ({len(list(STD.glob('*')))}):")
    list_standards()
    print("-- decisions (last 10):")
    if DECISIONS.exists():
        for ln in DECISIONS.read_text(encoding="utf-8").splitlines()[-10:]:
            print(ln)
    else:
        print("(empty)")
    tail(8)

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] == "summary":
        summary()
    elif args[0] == "tail":
        tail(int(args[1]) if len(args) > 1 else 15)
    elif args[0] == "mark" and len(args) > 1:
        mark_standard(args[1])
    elif args[0] == "standards":
        list_standards()
    elif args[0] == "note" and len(args) > 1:
        log_decision(" ".join(args[1:]))
        print("[OK] note added")
    else:
        print('usage: python memory_core.py summary | tail [N] | mark <file.png> | standards | note "text"')
'''

(BASE / "memory_core.py").write_text(MEMORY_SRC, encoding='utf-8', newline='\n')
print("[OK] memory_core.py written")

sys.path.insert(0, str(BASE))
import memory_core
memory_core.log_decision("memory framework installed (fix_memory.py)")
print("[OK] first decision entry appended")

ch = 0

# --- patch comfy_client.py: log each generation
p = BASE / "comfy_client.py"
c = p.read_text(encoding='utf-8')
if "log_generation" in c:
    print("[=] comfy_client already logs generations")
else:
    anchor = "        logger.info(f\"saved {p}\")\n        return p"
    ins = ("        try:\n"
           "            from memory_core import log_generation\n"
           "            log_generation(p.name, positive_prompt, model=checkpoint, sdxl=str(is_sdxl), status=\"ok\")\n"
           "        except Exception:\n"
           "            pass\n"
           "        return p")
    if anchor in c:
        c = c.replace(anchor, ins, 1)
        try:
            compile(c, str(p), 'exec')
            p.write_text(c, encoding='utf-8', newline='\n')
            ch += 1; print("[OK] comfy_client logs generations (compile-gate passed)")
        except SyntaxError as e:
            print(f"[ROLLBACK] comfy_client line {e.lineno}: {e.msg} — NOT modified")
    else:
        print("[!] comfy_client anchor 'saved {p}' not found")

# --- patch gui_ai_panel.py: log RU->EN pairs
p2 = BASE / "gui_ai_panel.py"
c2 = p2.read_text(encoding='utf-8')
if "log_bridge" in c2:
    print("[=] gui already logs bridge pairs")
else:
    anchor2 = "            client = ComfyUIClient()"
    ins2 = ("            try:\n"
            "                from memory_core import log_bridge\n"
            "                log_bridge(self.prompt, final_prompt)\n"
            "            except Exception:\n"
            "                pass\n"
            "            client = ComfyUIClient()")
    if anchor2 in c2:
        c2 = c2.replace(anchor2, ins2, 1)
        try:
            compile(c2, str(p2), 'exec')
            p2.write_text(c2, encoding='utf-8', newline='\n')
            ch += 1; print("[OK] gui logs bridge pairs (compile-gate passed)")
        except SyntaxError as e:
            print(f"[ROLLBACK] gui line {e.lineno}: {e.msg} — NOT modified")
    else:
        print("[!] gui anchor 'client = ComfyUIClient()' not found")

print(f"\n=== Done, changes={ch} ===")