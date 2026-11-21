#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Final fix: remove ALL references to VersionHistory and version_panel.
Safe: compile-gate on rewrite.
Run: python fix_remove_version_final.py
"""

from pathlib import Path
import re

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

print("\n=== Final Version Removal ===\n")

strategy_path = BASE / "gui_sections" / "strategy_section.py"
content = strategy_path.read_text(encoding='utf-8')

lines = content.split('\n')
new_lines = []
commented = 0

for i, line in enumerate(lines):
    stripped = line.strip()
    
    # Skip already commented lines
    if stripped.startswith('#'):
        new_lines.append(line)
        continue
    
    # Comment out lines that reference VersionHistory or version_panel
    if any(kw in stripped for kw in ['VersionHistory', 'version_panel', 'DEMO_VERSIONS']):
        # But only if it's actual code, not a string
        if not (stripped.startswith('"') or stripped.startswith("'")):
            new_lines.append('# ' + line + '  # REMOVED (version ref)')
            commented += 1
            print(f"  [OK] Line {i+1}: {stripped[:80]}")
            continue
    
    new_lines.append(line)

content = '\n'.join(new_lines)

# Compile gate
try:
    compile(content, str(strategy_path), 'exec')
    strategy_path.write_text(content, encoding='utf-8', newline='\n')
    print(f"\n[OK] strategy_section.py updated ({commented} version references removed)")
except SyntaxError as e:
    print(f"\n[ROLLBACK] syntax error at line {e.lineno}: {e.msg}")

print("\n=== Done ===")
print("Run START.bat now. Strategy section should load without any version-related errors.")