#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix: Add content_plan loading to gui_main.py + fix syntax error.
Run: python fix_content_plan_load.py
"""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

def write(rel, content):
    p = BASE / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding='utf-8', newline='\n')
    print(f"  [OK] {rel}")

print("\n=== Fixing Content Plan Loading ===\n")

# 1. Fix syntax error in content_plan_section.py
print("[1/2] Fixing syntax error in content_plan_section.py...")

cp_path = BASE / "gui_sections" / "content_plan_section.py"
cp_content = cp_path.read_text(encoding='utf-8')

# Fix the broken generator expression
old_broken = '''        # Recommendations
        if abs(actual_percent - target_percent) > 10 for actual_percent in [((rubric_counts.get(r, 0) / total * 100) if total > 0 else 0) for r in RUBRICS]:
            rec_frame = QFrame()'''

new_fixed = '''        # Recommendations
        has_deviation = False
        for r in RUBRICS:
            actual_p = (rubric_counts.get(r, 0) / total * 100) if total > 0 else 0
            target_p = RUBRICS[r]["target_percent"]
            if abs(actual_p - target_p) > 10:
                has_deviation = True
                break
        
        if has_deviation:
            rec_frame = QFrame()'''

cp_content = cp_content.replace(old_broken, new_fixed)

# Also fix the calendar legend layout bug
old_legend_bug = '''        legend.addStretch()
        layout.addLayout(layout)'''

new_legend_fix = '''        legend.addStretch()
        layout.addLayout(legend)'''

cp_content = cp_content.replace(old_legend_bug, new_legend_fix)

cp_path.write_text(cp_content, encoding='utf-8', newline='\n')
print("  [OK] Fixed syntax errors")

# 2. Add content_plan loading to gui_main.py
print("[2/2] Adding content_plan loading to gui_main.py...")

gui_main_path = BASE / "gui_main.py"
gui_main_content = gui_main_path.read_text(encoding='utf-8')

# Find the section loading block and add content_plan
old_load_block = '''        if section_id == "strategy":
            from gui_sections.strategy_section import StrategySection
            self.workspace_layout.addWidget(StrategySection(self.state))
        elif section_id == "publications":'''

new_load_block = '''        if section_id == "strategy":
            from gui_sections.strategy_section import StrategySection
            self.workspace_layout.addWidget(StrategySection(self.state))
        elif section_id == "content_plan":
            from gui_sections.content_plan_section import ContentPlanSection
            self.workspace_layout.addWidget(ContentPlanSection(self.state))
        elif section_id == "publications":'''

if old_load_block in gui_main_content:
    gui_main_content = gui_main_content.replace(old_load_block, new_load_block)
    gui_main_path.write_text(gui_main_content, encoding='utf-8', newline='\n')
    print("  [OK] Added content_plan loading")
else:
    # Try alternative pattern
    old_alt = '''        if section_id == "publications":'''
    new_alt = '''        if section_id == "content_plan":
            from gui_sections.content_plan_section import ContentPlanSection
            self.workspace_layout.addWidget(ContentPlanSection(self.state))
        elif section_id == "publications":'''
    
    if old_alt in gui_main_content:
        gui_main_content = gui_main_content.replace(old_alt, new_alt)
        gui_main_path.write_text(gui_main_content, encoding='utf-8', newline='\n')
        print("  [OK] Added content_plan loading (alternative pattern)")
    else:
        print("  [WARN] Could not find insertion point, manual edit needed")

print("\n=== Content Plan Loading Fixed ===")
print("\nRun START.bat and click 'Контент-план' in left panel.")
print("You should see the table with demo data.")