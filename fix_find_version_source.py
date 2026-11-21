#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Broad search: find where 'История версий' and version data come from.
Run: python fix_find_version_source.py
"""

from pathlib import Path
import re

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

print("\n=== Broad Version Search ===\n")

# 1. Search ALL .py files for version-related strings
print("[1/3] Searching all .py files...")
search_terms = [
    "История версий",
    "Версия",
    "version",
    "history",
    "v1.0",
    "v1.1",
    "Обновлено",
]

for term in search_terms:
    print(f"\n  --- '{term}' ---")
    count = 0
    for py_file in sorted(BASE.rglob("*.py")):
        try:
            txt = py_file.read_text(encoding='utf-8')
        except Exception:
            continue
        for i, line in enumerate(txt.split('\n'), 1):
            if term.lower() in line.lower():
                # Skip pure comments and imports
                stripped = line.strip()
                if stripped.startswith('#') or stripped.startswith('from ') or stripped.startswith('import '):
                    continue
                count += 1
                if count <= 5:  # limit output
                    print(f"    {py_file.name}:{i}: {stripped[:120]}")
    if count == 0:
        print("    (not found)")

# 2. Check project_data.json for version fields
print("\n[2/3] Checking project_data.json...")
json_files = list(BASE.rglob("project_data.json")) + list(BASE.rglob("*.json"))
for jf in json_files[:5]:
    try:
        txt = jf.read_text(encoding='utf-8')
        if any(t in txt for t in ["version", "history", "v1.0", "v1.1"]):
            print(f"  [MATCH] {jf.name}")
            # Show relevant lines
            for i, line in enumerate(txt.split('\n'), 1):
                if any(t in line.lower() for t in ["version", "history", "v1."]):
                    print(f"    Line {i}: {line.strip()[:100]}")
    except Exception:
        pass

# 3. Search for right-side panel rendering (where "История версий" appears)
print("\n[3/3] Searching for right panel / sidebar rendering...")
for py_file in sorted(BASE.rglob("*.py")):
    try:
        txt = py_file.read_text(encoding='utf-8')
    except Exception:
        continue
    # Look for patterns that build a right-side panel with version info
    if re.search(r'(right|side|panel|sidebar).*version', txt, re.I):
        print(f"  [PANEL] {py_file.name}")
    if 'История' in txt and ('верс' in txt.lower() or 'version' in txt.lower()):
        print(f"  [HISTORY] {py_file.name}")

print("\n=== Done ===")