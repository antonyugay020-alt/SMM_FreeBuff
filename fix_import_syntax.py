#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix: Repair syntax error in gui_main.py caused by literal \\n in code.
Run: python fix_import_syntax.py
"""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

print("\n=== Fixing Import Syntax ===\n")

gui_path = BASE / "gui_main.py"
content = gui_path.read_text(encoding='utf-8')

# Fix the broken line: replace literal \n with actual newline
broken = 'import_btn.clicked.connect(self._on_import_media)\\n        top_layout.addWidget(import_btn)'
fixed = 'import_btn.clicked.connect(self._on_import_media)\n        top_layout.addWidget(import_btn)'

if broken in content:
    content = content.replace(broken, fixed)
    gui_path.write_text(content, encoding='utf-8', newline='\n')
    print("[OK] Fixed literal \\n in gui_main.py")
else:
    print("[INFO] Broken line not found — may already be fixed or different issue")
    # Show context around import_btn
    for i, line in enumerate(content.split('\n')):
        if 'import_btn' in line:
            print(f"  Line {i}: {line!r}")

print("\nRun START.bat")