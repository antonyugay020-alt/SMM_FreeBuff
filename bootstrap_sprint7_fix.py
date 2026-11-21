#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI SMM Manager - Sprint 7 Fix: Remove unused QAction import.
Run: python bootstrap_sprint7_fix.py
"""

import os
import sys
from pathlib import Path

os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PYTHONUTF8'] = '1'

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = Path(__file__).resolve().parent

print("\n=== AI SMM Manager - Sprint 7 Fix ===\n")

# Fix gui_main.py - remove QAction from imports
gui_main_path = ROOT_DIR / "AI_SMM_Work_Architecture_A75" / "gui_main.py"
if gui_main_path.exists():
    content = gui_main_path.read_text(encoding='utf-8')
    
    # Remove QAction from import
    content = content.replace(
        "QFrame, QSizePolicy, QToolBar, QAction, QStatusBar",
        "QFrame, QSizePolicy, QStatusBar"
    )
    
    gui_main_path.write_text(content, encoding='utf-8')
    print("[OK] Fixed gui_main.py - removed QAction import")
else:
    print("[ERROR] gui_main.py not found")

print("\nRun START.bat to test.")