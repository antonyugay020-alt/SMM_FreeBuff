#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Remove version label + VersionHistory panel + version buttons.
Correct path: gui_sections/strategy_section.py
Safe: compile-gate on rewrite.
Run: python fix_remove_version_ui.py
"""

from pathlib import Path
import re

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

print("\n=== Remove Version UI ===\n")

strategy_path = BASE / "gui_sections" / "strategy_section.py"
if not strategy_path.exists():
    print(f"[FAIL] File not found: {strategy_path}")
    raise SystemExit(1)

content = strategy_path.read_text(encoding='utf-8')
changes = 0

# 1. Version subtitle label
old_subtitle = 'subtitle = QLabel("Версия 1.1 · Обновлено 12.11.2026")'
if old_subtitle in content:
    content = content.replace(old_subtitle, '# ' + old_subtitle + '  # REMOVED', 1)
    changes += 1
    print("[OK] Version subtitle commented out")

# 2. Comment out instantiation / layout-add of VersionHistory
for pat in [
    r'self\.version_history\s*=\s*VersionHistory\([^)]*\)',
    r'\w*[Ll]ayout\w*\.addWidget\(self\.version_history[^)]*\)',
    r'\w*[Ll]ayout\w*\.addWidget\(version_history[^)]*\)',
]:
    for m in reversed(list(re.finditer(pat, content))):
        ls = content.rfind('\n', 0, m.start()) + 1
        le = content.find('\n', m.end())
        if le == -1: le = len(content)
        line = content[ls:le]
        content = content[:ls] + '# ' + line.lstrip() + '\n' + content[le:]
        changes += 1
        print(f"[OK] Commented: {line.strip()[:70]}")

# 3. Comment out VersionHistory class body
cs = content.find('class VersionHistory(')
if cs != -1:
    nc = content.find('\nclass ', cs + 1)
    if nc == -1: nc = len(content)
    block = content[cs:nc]
    commented = '\n'.join(('# ' + l) if l.strip() else l for l in block.split('\n'))
    content = content[:cs] + commented + content[nc:]
    changes += 1
    print("[OK] VersionHistory class commented out")

# 4. Hide version action buttons (Сохранить версию / Откатить)
for btn_text in ['Сохранить версию', 'Откатить']:
    for m in reversed(list(re.finditer(r'\w+\s*=\s*QPushButton\("' + btn_text, content))):
        ls = content.rfind('\n', 0, m.start()) + 1
        le = content.find('\n', m.end())
        if le == -1: le = len(content)
        line = content[ls:le]
        content = content[:ls] + '# ' + line.lstrip() + '\n' + content[le:]
        changes += 1
        print(f"[OK] Button '{btn_text}' commented out")

# Compile gate
try:
    compile(content, str(strategy_path), 'exec')
    strategy_path.write_text(content, encoding='utf-8', newline='\n')
    print(f"\n[OK] strategy_section.py updated ({changes} changes)")
except SyntaxError as e:
    print(f"\n[ROLLBACK] syntax error line {e.lineno}: {e.msg} - file NOT modified")

print("\n=== Done ===")