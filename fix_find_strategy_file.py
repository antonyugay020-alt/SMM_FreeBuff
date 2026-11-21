#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Find where strategy_section.py actually lives.
Run: python fix_find_strategy_file.py
"""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent

print("\n=== Finding strategy_section.py ===\n")

# Search in current directory and subdirectories
for py_file in ROOT_DIR.rglob("*.py"):
    if "strategy" in py_file.name.lower():
        print(f"[FOUND] {py_file}")

# Also search for any file containing "История версий"
print("\n=== Searching for 'История версий' text ===\n")
for py_file in ROOT_DIR.rglob("*.py"):
    try:
        txt = py_file.read_text(encoding='utf-8')
        if "История версий" in txt:
            print(f"[MATCH] {py_file}")
    except Exception:
        pass

print("\n=== Done ===")