#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI SMM Manager - Sprint 7 Fix 3: Add ROOT_DIR definition to gui_main.py.
gui_main.py is imported as a module, so it needs its own ROOT_DIR.
Run: python bootstrap_sprint7_fix3.py
"""

import os
import sys
from pathlib import Path

os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PYTHONUTF8'] = '1'

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = Path(__file__).resolve().parent

print("\n=== AI SMM Manager - Sprint 7 Fix 3: Add ROOT_DIR to gui_main.py ===\n")

gui_main_path = ROOT_DIR / "AI_SMM_Work_Architecture_A75" / "gui_main.py"
if not gui_main_path.exists():
    print("[ERROR] gui_main.py not found")
    input("Press Enter to exit")
    sys.exit(1)

content = gui_main_path.read_text(encoding='utf-8')

# Add ROOT_DIR definition right after the imports
# Find the line "from gui_ai_panel import AIPanel" and insert after it
insert_marker = "from gui_ai_panel import AIPanel"
if insert_marker in content:
    insertion = f"""
# Module-level ROOT_DIR (gui_main is imported as module, not run directly)
ROOT_DIR = Path(__file__).resolve().parent.parent
"""
    content = content.replace(insert_marker, insert_marker + "\n" + insertion)
    gui_main_path.write_text(content, encoding='utf-8')
    print("[OK] Added ROOT_DIR definition to gui_main.py")
else:
    print("[WARN] Could not find insertion point, trying alternative...")
    # Fallback: insert after last import
    lines = content.split('\n')
    last_import_idx = 0
    for i, line in enumerate(lines):
        if line.startswith('from ') or line.startswith('import '):
            last_import_idx = i
    lines.insert(last_import_idx + 1, "")
    lines.insert(last_import_idx + 2, "# Module-level ROOT_DIR")
    lines.insert(last_import_idx + 3, "ROOT_DIR = Path(__file__).resolve().parent.parent")
    content = '\n'.join(lines)
    gui_main_path.write_text(content, encoding='utf-8')
    print("[OK] Added ROOT_DIR definition (fallback method)")

# Also check gui_components.py and gui_ai_panel.py for the same issue
for fname in ["gui_components.py", "gui_ai_panel.py"]:
    fpath = ROOT_DIR / "AI_SMM_Work_Architecture_A75" / fname
    if fpath.exists():
        fcontent = fpath.read_text(encoding='utf-8')
        if "ROOT_DIR" in fcontent and "ROOT_DIR =" not in fcontent:
            lines = fcontent.split('\n')
            last_import_idx = 0
            for i, line in enumerate(lines):
                if line.startswith('from ') or line.startswith('import '):
                    last_import_idx = i
            lines.insert(last_import_idx + 1, "")
            lines.insert(last_import_idx + 2, f"# Module-level ROOT_DIR for {fname}")
            lines.insert(last_import_idx + 3, "ROOT_DIR = Path(__file__).resolve().parent.parent")
            fpath.write_text('\n'.join(lines), encoding='utf-8')
            print(f"[OK] Added ROOT_DIR to {fname}")

print("\nRun START.bat to test.")