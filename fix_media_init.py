#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix: Ensure self.dm is set BEFORE self._build_ui() in MediaContentSection.
Run: python fix_media_init.py
"""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

print("\n=== Fixing MediaContentSection init order ===\n")

mc_path = BASE / "gui_sections" / "media_content_section.py"
content = mc_path.read_text(encoding='utf-8')

# Find MediaContentSection class and fix its __init__
# The problem: self._build_ui() is called before self.dm is set

# Strategy: find the class definition and replace its __init__ block
import re

# Find the class MediaContentSection
class_pattern = re.compile(
    r'class MediaContentSection\(QWidget\):\s*\n'
    r'    """[^"]*"""\s*\n'
    r'    def __init__\(self,.*?\):\s*\n'
    r'(        [^\n]+\n)*'
    r'        self\._build_ui\(\)',
    re.DOTALL
)

match = class_pattern.search(content)
if match:
    print(f"[OK] Found MediaContentSection.__init__ at position {match.start()}")
    
    # Get the matched text
    old_init = match.group(0)
    print(f"Old init:\n{old_init[:300]}...")
    
    # Replace with correct version
    new_init = '''class MediaContentSection(QWidget):
    """Media Content section with 3 zones + processing panel."""

    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.dm = data_manager
        self._build_ui()'''
    
    content = content[:match.start()] + new_init + content[match.end():]
    print("[OK] Replaced __init__ with correct order")
else:
    print("[WARN] Could not find MediaContentSection.__init__ with regex")
    print("Trying simpler replacement...")
    
    # Fallback: simple string replacement
    old_patterns = [
        '''    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self._build_ui()
        self.dm = data_manager''',
        
        '''    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.state = data_manager
        self._build_ui()''',
    ]
    
    new_init = '''    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.dm = data_manager
        self._build_ui()'''
    
    fixed = False
    for old in old_patterns:
        if old in content:
            content = content.replace(old, new_init)
            print(f"[OK] Fixed with fallback pattern")
            fixed = True
            break
    
    if not fixed:
        print("[ERROR] Could not find any known pattern")
        print("Searching for __init__ in MediaContentSection...")
        lines = content.split('\n')
        in_class = False
        for i, line in enumerate(lines):
            if 'class MediaContentSection' in line:
                in_class = True
            if in_class and 'def __init__' in line:
                print(f"  Line {i}: {line}")
                for j in range(i+1, min(i+6, len(lines))):
                    print(f"  Line {j}: {lines[j]}")
                break

mc_path.write_text(content, encoding='utf-8', newline='\n')

# Also verify gui_main.py passes data_manager correctly
gui_path = BASE / "gui_main.py"
gui_content = gui_path.read_text(encoding='utf-8')

if 'MediaContentSection(self.data_manager)' in gui_content:
    print("[OK] gui_main.py passes data_manager correctly")
elif 'MediaContentSection(self.state)' in gui_content:
    print("[WARN] gui_main.py still passes self.state, fixing...")
    gui_content = gui_content.replace(
        'MediaContentSection(self.state)',
        'MediaContentSection(self.data_manager)'
    )
    gui_path.write_text(gui_content, encoding='utf-8', newline='\n')
    print("[OK] Fixed gui_main.py")

print("\nRun START.bat")