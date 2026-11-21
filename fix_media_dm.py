#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix: Replace self.state with self.dm in MediaContentSection.
Run: python fix_media_dm.py
"""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

print("\n=== Fixing MediaContentSection state->dm ===\n")

mc_path = BASE / "gui_sections" / "media_content_section.py"
lines = mc_path.read_text(encoding='utf-8').split('\n')

# Find MediaContentSection class and fix its __init__
in_class = False
fixed_init = False
fixed_refs = 0

for i, line in enumerate(lines):
    if 'class MediaContentSection' in line:
        in_class = True
        print(f"[OK] Found MediaContentSection at line {i}")
    
    if in_class:
        # Fix __init__ signature and body
        if 'def __init__(self, app_state' in line:
            lines[i] = line.replace('app_state', 'data_manager')
            print(f"[OK] Line {i}: Fixed __init__ signature")
        
        if 'self.state = app_state' in line:
            lines[i] = '        self.dm = data_manager'
            print(f"[OK] Line {i}: Replaced self.state with self.dm")
            fixed_init = True
        
        # Fix all self.state references inside the class
        if 'self.state' in line and 'def __init__' not in line:
            lines[i] = line.replace('self.state', 'self.dm')
            fixed_refs += 1

# Also fix ProcessingPanel if it uses self.state
in_proc = False
for i, line in enumerate(lines):
    if 'class ProcessingPanel' in line:
        in_proc = True
    if in_proc and 'def __init__(self, app_state' in line:
        lines[i] = line.replace('app_state', 'data_manager')
        print(f"[OK] Line {i}: Fixed ProcessingPanel __init__ signature")
    if in_proc and 'self.state = app_state' in line:
        lines[i] = '        self.dm = data_manager'
        print(f"[OK] Line {i}: Fixed ProcessingPanel state->dm")
    if in_proc and 'self.state' in line and 'def __init__' not in line:
        lines[i] = line.replace('self.state', 'self.dm')

mc_path.write_text('\n'.join(lines), encoding='utf-8', newline='\n')

print(f"\n[OK] Fixed {fixed_refs} self.state references")
print("\nRun START.bat")