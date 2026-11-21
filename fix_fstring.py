#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix: Repair broken f-string in gui_ai_panel.py line 158.
Run: python fix_fstring.py
"""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

print("\n=== Fixing f-string in gui_ai_panel.py ===\n")

panel_path = BASE / "gui_ai_panel.py"
content = panel_path.read_text(encoding='utf-8')

lines = content.split('\n')

# Show lines around 158 for diagnosis
print("Lines 155-162:")
for i in range(154, min(162, len(lines))):
    print(f"{i+1}: {repr(lines[i])}")

# Find and fix the broken f-string pattern
# Common patterns that cause this error:
broken_patterns = [
    # Pattern 1: Nested quotes in f-string
    'header = QLabel(f"{"🤖 AI" if role == "assistant" else "👤 Вы"}  {timestamp}")',
    
    # Pattern 2: Another variation
    'header = QLabel(f\'{"🤖 AI" if role == "assistant" else "👤 Вы"}  {timestamp}\')',
    
    # Pattern 3: Mixed quotes
    'header = QLabel(f"{'🤖 AI' if role == 'assistant' else '👤 Вы'}  {timestamp}")',
]

fixed_pattern = 'icon = "🤖 AI" if role == "assistant" else "👤 Вы"\n        header = QLabel(f"{icon}  {timestamp}")'

replacements_made = 0

for pattern in broken_patterns:
    if pattern in content:
        content = content.replace(pattern, fixed_pattern)
        replacements_made += 1
        print(f"[OK] Fixed pattern: {pattern[:50]}...")

if replacements_made == 0:
    print("[!] No exact match found, trying regex approach...")
    
    # Use regex to find any similar broken f-string with conditional expressions
    import re
    
    # Match QLabel(f"...{expr if cond else expr}...") where expr contains quotes
    regex_pattern = r'(QLabel\(f["\'])(.*?)(?:\{(?:[^{}]*"(?:[^"]*)"|[^{}]*\'(?:[^\']*)\')[^{}]*\})(.*?)\1\)'
    
    # Simpler approach: just replace the specific line by finding it
    for i, line in enumerate(lines):
        if 'QLabel(f"' in line and ('🤖 AI' in line or '👤 Вы' in line):
            print(f"[FOUND] Line {i+1}: {line.strip()[:80]}")
            
            # Replace with safe version
            indent = len(line) - len(line.lstrip())
            spaces = ' ' * indent
            
            # Split into two statements
            new_lines = [
                f'{spaces}icon = "🤖 AI" if role == "assistant" else "👤 Вы"',
                f'{spaces}header = QLabel(f"{icon}  {{timestamp}}")'
            ]
            
            # Replace single line with two lines
            lines[i:i+1] = new_lines
            replacements_made += 1
            print(f"[OK] Replaced line {i+1} with safe version")
            break

if replacements_made > 0:
    content = '\n'.join(lines)
    panel_path.write_text(content, encoding='utf-8', newline='\n')
    print(f"\n[SUCCESS] Made {replacements_made} replacement(s)")
else:
    print("\n[ERROR] Could not locate broken f-string")
    print("Please manually inspect gui_ai_panel.py around line 158")

# Verify compilation
try:
    compile(content, str(panel_path), 'exec')
    print("\n[OK] File compiles successfully!")
except SyntaxError as e:
    print(f"\n[WARNING] Still has syntax error: {e.msg} at line {e.lineno}")
    print(f"  Text: {e.text}")

print("\nRun START.bat")