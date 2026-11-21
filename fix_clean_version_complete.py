#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Nuke all version-related code from strategy_section.py in one pass.
Safe: compile-gate on rewrite.
Run: python fix_clean_version_complete.py
"""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

print("\n=== Nuke Version Code ===\n")

strategy_path = BASE / "gui_sections" / "strategy_section.py"
content = strategy_path.read_text(encoding='utf-8')

lines = content.split('\n')
new_lines = []
commented = 0

# Keywords that indicate version-related code
version_keywords = [
    'VersionHistory',
    'version_panel',
    'DEMO_VERSIONS',
    'subtitle',
    'Версия 1.1',
    'Обновлено',
    'История версий',
]

for i, line in enumerate(lines):
    stripped = line.strip()
    
    # Skip already commented lines
    if stripped.startswith('#'):
        new_lines.append(line)
        continue
    
    # Check if line contains any version keyword
    should_comment = False
    for kw in version_keywords:
        if kw in stripped:
            should_comment = True
            break
    
    if should_comment:
        new_lines.append('# ' + line + '  # REMOVED')
        commented += 1
        print(f"  [OK] Line {i+1}: {stripped[:90]}")
    else:
        new_lines.append(line)

content = '\n'.join(new_lines)

# Compile gate
try:
    compile(content, str(strategy_path), 'exec')
    strategy_path.write_text(content, encoding='utf-8', newline='\n')
    print(f"\n[OK] strategy_section.py updated ({commented} lines commented)")
except SyntaxError as e:
    print(f"\n[ROLLBACK] syntax error at line {e.lineno}: {e.msg}")
    print("File NOT modified.")

print("\n=== Done ===")
print("NOW run: .\\START.bat")