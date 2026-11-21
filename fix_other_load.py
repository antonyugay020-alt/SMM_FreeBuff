#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix: Add other materials loading to gui_main.py.
Run: python fix_other_load.py
"""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

print("\n=== Fixing Other Materials Loading ===\n")

gui_main_path = BASE / "gui_main.py"
content = gui_main_path.read_text(encoding='utf-8')

# Show current section loading block for debugging
print("Current section loading block:")
lines = content.split('\n')
for i, line in enumerate(lines):
    if 'section_id ==' in line or 'from gui_sections' in line or 'placeholder' in line.lower():
        print(f"  {i}: {line}")

# Try multiple patterns
patterns = [
    # Pattern 1: after publications
    ('''        elif section_id == "publications":
            from gui_sections.publications_section import PublicationsSection
            self.workspace_layout.addWidget(PublicationsSection(self.state))
        else:''',
     '''        elif section_id == "publications":
            from gui_sections.publications_section import PublicationsSection
            self.workspace_layout.addWidget(PublicationsSection(self.state))
        elif section_id == "other":
            from gui_sections.other_materials_section import OtherMaterialsSection
            self.workspace_layout.addWidget(OtherMaterialsSection(self.state))
        else:'''),
    
    # Pattern 2: just before else with placeholder
    ('''        else:
            placeholder = QLabel(f'Раздел "{title}" — в разработке')''',
     '''        elif section_id == "other":
            from gui_sections.other_materials_section import OtherMaterialsSection
            self.workspace_layout.addWidget(OtherMaterialsSection(self.state))
        else:
            placeholder = QLabel(f'Раздел "{title}" — в разработке')'''),
]

fixed = False
for old, new in patterns:
    if old in content:
        content = content.replace(old, new)
        gui_main_path.write_text(content, encoding='utf-8', newline='\n')
        print(f"\n[OK] Added other materials loading (pattern {patterns.index((old, new)) + 1})")
        fixed = True
        break

if not fixed:
    print("\n[ERROR] Could not find insertion point")
    print("\nManual fix needed: add this block before the final 'else:' in _on_nav method:")
    print('''
        elif section_id == "other":
            from gui_sections.other_materials_section import OtherMaterialsSection
            self.workspace_layout.addWidget(OtherMaterialsSection(self.state))
''')

print("\nRun START.bat and click 'Прочие материалы' in left panel.")