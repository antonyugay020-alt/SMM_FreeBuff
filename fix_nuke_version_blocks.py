#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Replace entire version-related blocks with safe placeholders.
Safe: compile-gate on rewrite.
Run: python fix_nuke_version_blocks.py
"""

from pathlib import Path
import re

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

print("\n=== Nuke Version Blocks ===\n")

strategy_path = BASE / "gui_sections" / "strategy_section.py"
content = strategy_path.read_text(encoding='utf-8')

changes = 0

# 1. Replace DEMO_VERSIONS list with empty list
demo_pattern = r'DEMO_VERSIONS\s*=\s*\[[^\]]*\]'
if re.search(demo_pattern, content, re.DOTALL):
    content = re.sub(demo_pattern, 'DEMO_VERSIONS = []', content, count=1, flags=re.DOTALL)
    changes += 1
    print("[OK] Replaced DEMO_VERSIONS list with empty list")
else:
    print("[!] DEMO_VERSIONS pattern not found")

# 2. Replace version_panel creation block with pass
version_block_pattern = r'self\.version_panel\s*=\s*VersionHistory\(DEMO_VERSIONS\)[\s\S]*?splitter\.addWidget\(self\.version_panel\)'
if re.search(version_block_pattern, content):
    content = re.sub(version_block_pattern, 'pass  # Version panel removed', content, count=1)
    changes += 1
    print("[OK] Replaced version_panel creation block with pass")
else:
    print("[!] version_panel block not found")

# 3. Replace entire VersionHistory class with empty class
class_pattern = r'class VersionHistory\(QWidget\):[\s\S]*?(?=\nclass |\Z)'
if re.search(class_pattern, content):
    content = re.sub(class_pattern, 'class VersionHistory(QWidget):\n    pass  # Removed\n', content, count=1)
    changes += 1
    print("[OK] Replaced VersionHistory class with empty class")
else:
    print("[!] VersionHistory class not found")

# 4. Remove subtitle references (already done, but just in case)
content = re.sub(r'^\s*subtitle\s*=\s*QLabel.*$', '# subtitle removed', content, flags=re.MULTILINE)
content = re.sub(r'^\s*subtitle\.setStyleSheet.*$', '# subtitle removed', content, flags=re.MULTILINE)
content = re.sub(r'^\s*content_layout\.addWidget\(subtitle\).*$', '# subtitle removed', content, flags=re.MULTILINE)

# Compile gate
try:
    compile(content, str(strategy_path), 'exec')
    strategy_path.write_text(content, encoding='utf-8', newline='\n')
    print(f"\n[OK] strategy_section.py updated ({changes} blocks replaced)")
except SyntaxError as e:
    print(f"\n[ROLLBACK] syntax error at line {e.lineno}: {e.msg}")
    print("File NOT modified.")

print("\n=== Done ===")
print("NOW run: .\\START.bat")