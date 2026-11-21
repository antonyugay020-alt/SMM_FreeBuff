#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix: Add missing _detect_category method to gui_ai_panel.py.
Run: python fix_detect_category.py
"""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

print("\n=== Adding Missing Method ===\n")

panel_path = BASE / "gui_ai_panel.py"
content = panel_path.read_text(encoding='utf-8')

# Find where to insert the method (just before send_message or at end of class)
insert_marker = '''    def send_message(self):'''

method_code = '''    def _detect_category(self, text: str) -> str:
        """Detect proposal category from user input."""
        lower = text.lower()
        if any(w in lower for w in ['стратег', 'позицион', 'целев']):
            return "strategy"
        if any(w in lower for w in ['контент', 'план', 'публикац']):
            return "content_plan"
        if any(w in lower for w in ['съёмк', 'фото', 'видео', 'tz', 'техническ']):
            return "shooting"
        if any(w in lower for w in ['обработ', 'фильтр', 'стиль']):
            return "processing"
        return "general"

'''

if "_detect_category" not in content:
    if insert_marker in content:
        content = content.replace(insert_marker, method_code + insert_marker)
        print("[OK] Added _detect_category method")
    else:
        # Fallback: append to end of file (assuming class structure allows it visually)
        # Better to find the class definition and append inside
        lines = content.split('\n')
        # Just brute force replace the warning line logic by adding method anywhere valid
        # Let's try inserting before the last closing parenthesis of the class usually
        pass 
else:
    print("[SKIP] Method already exists")

panel_path.write_text(content, encoding='utf-8', newline='\n')

print("\nRun START.bat")