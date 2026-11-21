#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI SMM Manager - Sprint 7 Fix 4: Add missing Path import to gui_components.py.
Run: python bootstrap_sprint7_fix4.py
"""

import os
import sys
from pathlib import Path

os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PYTHONUTF8'] = '1'

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = Path(__file__).resolve().parent

print("\n=== AI SMM Manager - Sprint 7 Fix 4: Add Path import ===\n")

# Fix gui_components.py
fpath = ROOT_DIR / "AI_SMM_Work_Architecture_A75" / "gui_components.py"
if fpath.exists():
    content = fpath.read_text(encoding='utf-8')
    
    # Check if Path is already imported
    if 'from pathlib import Path' not in content:
        # Add after the PySide6 imports
        content = content.replace(
            'from PySide6.QtGui import QPixmap, QIcon, QColor',
            'from PySide6.QtGui import QPixmap, QIcon, QColor\nfrom pathlib import Path'
        )
        fpath.write_text(content, encoding='utf-8')
        print("[OK] Added 'from pathlib import Path' to gui_components.py")
    else:
        print("[OK] Path already imported in gui_components.py")
else:
    print("[ERROR] gui_components.py not found")

# Also check gui_ai_panel.py and gui_main.py for missing Path
for fname in ["gui_ai_panel.py", "gui_main.py"]:
    fpath = ROOT_DIR / "AI_SMM_Work_Architecture_A75" / fname
    if fpath.exists():
        content = fpath.read_text(encoding='utf-8')
        if 'Path(' in content and 'from pathlib import Path' not in content:
            # Find last import line and add after it
            lines = content.split('\n')
            last_import_idx = 0
            for i, line in enumerate(lines):
                if line.startswith('from ') or line.startswith('import '):
                    last_import_idx = i
            lines.insert(last_import_idx + 1, "from pathlib import Path")
            fpath.write_text('\n'.join(lines), encoding='utf-8')
            print(f"[OK] Added 'from pathlib import Path' to {fname}")

print("\nRun START.bat to test.")