#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI SMM Manager - Sprint 7 Fix 2: Remove QAction from ALL files.
In Qt6, QAction moved from QtWidgets to QtGui.
Since we don't use QAction at all, just remove it.
Run: python bootstrap_sprint7_fix2.py
"""

import os
import sys
import re
from pathlib import Path

os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PYTHONUTF8'] = '1'

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = Path(__file__).resolve().parent
TARGET_DIR = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

print("\n=== AI SMM Manager - Sprint 7 Fix 2: Clean QAction imports ===\n")

# Find all .py files that import QAction from QtWidgets
fixed_files = []

for py_file in TARGET_DIR.glob("*.py"):
    try:
        content = py_file.read_text(encoding='utf-8')
    except Exception:
        continue
    
    if "QAction" not in content:
        continue
    
    original = content
    
    # Pattern 1: QAction in a multi-line import from QtWidgets
    # e.g.: from PySide6.QtWidgets import (\n    QWidget, ..., QAction, ...\n)
    content = re.sub(r',\s*QAction\b', '', content)
    content = re.sub(r'\bQAction\s*,', '', content)
    content = re.sub(r'^\s*QAction\s*$', '', content, flags=re.MULTILINE)
    
    if content != original:
        py_file.write_text(content, encoding='utf-8')
        fixed_files.append(py_file.name)
        print(f"  [OK] Fixed: {py_file.name}")

if not fixed_files:
    print("  [INFO] No files needed fixing")

print(f"\nFixed {len(fixed_files)} file(s): {fixed_files}")
print("Run START.bat to test.")