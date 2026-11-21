#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix: comment out ALL references to 'subtitle' in strategy_section.py
so the NameError doesn't crash the app.
Safe: compile-gate on rewrite.
Run: python fix_subtitle_refs.py
"""

from pathlib import Path
import re

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

print("\n=== Fix subtitle references ===\n")

strategy_path = BASE / "gui_sections" / "strategy_section.py"
content = strategy_path.read_text(encoding='utf-8')

lines = content.split('\n')
new_lines = []
commented = 0

for i, line in enumerate(lines):
    stripped = line.strip()
    
    # Skip lines that are already comments
    if stripped.startswith('#'):
        new_lines.append(line)
        continue
    
    # Comment out lines that reference 'subtitle' as a variable
    # But NOT lines that are part of a string containing the word "subtitle"
    if re.search(r'\bsubtitle\b', stripped) and not stripped.startswith('"') and not stripped.startswith("'"):
        # Check it's actual code reference, not a string literal
        # Patterns: subtitle.setStyleSheet, subtitle.setText, layout.addWidget(subtitle, etc.
        if any(kw in stripped for kw in ['subtitle.setStyleSheet', 'subtitle.setText', 
                                          'addWidget(subtitle', 'subtitle.setObjectName',
                                          'subtitle.show', 'subtitle.hide', 'subtitle.delete',
                                          'subtitle.parent', 'subtitle.setFixed',
                                          'subtitle.setMinimum', 'subtitle.setMaximum',
                                          'subtitle.adjust', 'subtitle.update',
                                          'subtitle.move', 'subtitle.resize',
                                          'subtitle.setWordWrap', 'subtitle.setAlignment']):
            new_lines.append('# ' + line + '  # REMOVED (subtitle ref)')
            commented += 1
            print(f"  [OK] Line {i+1}: {stripped[:70]}")
        else:
            new_lines.append(line)
    else:
        new_lines.append(line)

content = '\n'.join(new_lines)

# Compile gate
try:
    compile(content, str(strategy_path), 'exec')
    strategy_path.write_text(content, encoding='utf-8', newline='\n')
    print(f"\n[OK] strategy_section.py updated ({commented} subtitle references commented)")
except SyntaxError as e:
    print(f"\n[ROLLBACK] syntax error at line {e.lineno}: {e.msg}")

print("\n=== Done ===")
print("Run START.bat now. Strategy section should load without errors.")