#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix: Add calendar section loading to gui_main.py.
Run: python fix_calendar_load.py
"""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

print("\n=== Fixing Calendar Loading ===\n")

gui_main_path = BASE / "gui_main.py"
content = gui_main_path.read_text(encoding='utf-8')

# Find the content_plan block and add calendar after it
old_block = '''        elif section_id == "content_plan":
            from gui_sections.content_plan_section import ContentPlanSection
            self.workspace_layout.addWidget(ContentPlanSection(self.state))
        elif section_id == "publications":'''

new_block = '''        elif section_id == "content_plan":
            from gui_sections.content_plan_section import ContentPlanSection
            self.workspace_layout.addWidget(ContentPlanSection(self.state))
        elif section_id == "calendar":
            from gui_sections.calendar_section import CalendarSection
            self.workspace_layout.addWidget(CalendarSection(self.state))
        elif section_id == "publications":'''

if old_block in content:
    content = content.replace(old_block, new_block)
    gui_main_path.write_text(content, encoding='utf-8', newline='\n')
    print("[OK] Added calendar loading after content_plan")
else:
    # Try without content_plan (in case it wasn't added before)
    old_alt = '''        elif section_id == "publications":'''
    new_alt = '''        elif section_id == "calendar":
            from gui_sections.calendar_section import CalendarSection
            self.workspace_layout.addWidget(CalendarSection(self.state))
        elif section_id == "publications":'''
    
    if old_alt in content:
        content = content.replace(old_alt, new_alt)
        gui_main_path.write_text(content, encoding='utf-8', newline='\n')
        print("[OK] Added calendar loading (alternative)")
    else:
        print("[ERROR] Could not find insertion point")
        print("Current section loading block:")
        for line in content.split('\n'):
            if 'section_id ==' in line or 'from gui_sections' in line:
                print(f"  {line}")

print("\nRun START.bat and click 'Календарь' in left panel.")