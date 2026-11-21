#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Remove unsupported 'cursor:' CSS declarations from all QSS styles in project.
Safe: .py files are rewritten only if they still compile afterwards.
Run: python fix_cursor_cleanup.py
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = ROOT / "AI_SMM_Work_Architecture_A75"

# cursor: pointer;   (with semicolon)
pattern_with_semi = re.compile(r'[ \t]*cursor\s*:\s*[^;{}]+;[ \t]*')
# cursor: pointer    (no semicolon, right before closing brace)
pattern_no_semi = re.compile(r'[ \t]*cursor\s*:\s*[^;{}]+(?=[ \t]*[}])')

print("\n=== Cursor Property Cleanup ===\n")

total = 0
for path in sorted(BASE.rglob("*")):
    if not path.is_file():
        continue
    if path.suffix.lower() not in (".py", ".qss"):
        continue

    text = path.read_text(encoding="utf-8")
    new_text, n1 = pattern_with_semi.subn("", text)
    new_text, n2 = pattern_no_semi.subn("", new_text)
    n = n1 + n2

    if n == 0:
        print(f"  [=] {path.name}: clean")
        continue

    # Compile gate for python files
    if path.suffix.lower() == ".py":
        try:
            compile(new_text, str(path), "exec")
        except SyntaxError as e:
            print(f"  [SKIP] {path.name}: removal would break syntax at line {e.lineno}")
            continue

    path.write_text(new_text, encoding="utf-8", newline="\n")
    print(f"  [OK] {path.name}: removed {n} cursor declaration(s)")
    total += n

print(f"\nTotal removed: {total}")
print("\nRun START.bat and check terminal: no 'Unknown property cursor' lines should appear.")