#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix class names in section files to use proper camelCase.
Run: python fix_class_names.py
"""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent

print("\n=== Fixing section class names ===\n")

sections = [
    ("strategy", "Strategy"),
    ("marketing", "Marketing"),
    ("content_plans", "ContentPlans"),
    ("calendar", "Calendar"),
    ("photo_processing", "PhotoProcessing"),
    ("video_processing", "VideoProcessing"),
    ("publications", "Publications"),
    ("files", "Files"),
]

for sec_id, class_name in sections:
    file_path = ROOT_DIR / "AI_SMM_Work_Architecture_A75" / "gui_sections" / f"{sec_id}_section.py"
    
    if not file_path.exists():
        print(f"  [SKIP] {file_path.name} not found")
        continue
    
    content = file_path.read_text(encoding='utf-8')
    
    # Replace class definition
    old_class_def = f"class {sec_id.capitalize().replace('_', '')}Section(BaseSection):"
    new_class_def = f"class {class_name}Section(BaseSection):"
    
    content = content.replace(old_class_def, new_class_def)
    
    file_path.write_text(content, encoding='utf-8')
    print(f"  [OK] {file_path.name}: {new_class_def}")

print("\nAll class names fixed. Run START.bat to test.")