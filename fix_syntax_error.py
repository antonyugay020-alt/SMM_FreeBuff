#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix: Repair syntax error in media_content_section.py at line ~252.
Run: python fix_syntax_error.py
"""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

print("\n=== Fixing Syntax Error ===\n")

mc_path = BASE / "gui_sections" / "media_content_section.py"
content = mc_path.read_text(encoding='utf-8')

# Show lines around 252 to diagnose
lines = content.split('\n')
print(f"Total lines: {len(lines)}")
print("\nLines 248-260:")
for i in range(247, min(260, len(lines))):
    print(f"{i+1}: {repr(lines[i])}")

# The issue is likely the multi-line QMessageBox.warning with backslashes
# Let's find and replace it properly

# Look for the problematic pattern
problem_patterns = [
    # Pattern 1: Broken multiline string
    '''            QMessageBox.warning(
                self, "Внимание",
                "Не выбрано ни одной карточки.\n\n"
                "Поставь галочки в левом верхнем углу каждой нужной карточки,\n"
                "затем нажми 'Одобрить' или 'Отклонить'."
            )''',
    
    # Pattern 2: Alternative broken version
    '''        if not sel:
            QMessageBox.warning(self, "Внимание", "Не выбрано ни одной карточки.\n\n"
                "Поставь галочки...\n"
                "затем нажми...")
            return''',
]

fixed_pattern = '''        if not sel:
            msg = ("Не выбрано ни одной карточки.\\n\\n"
                   "Поставь галочки в левом верхнем углу каждой нужной карточки,\\n"
                   "затем нажми \\\"Одобрить\\\" или \\\"Отклонить\\\".")
            QMessageBox.warning(self, "Внимание", msg)
            logger.debug(f"_emit_mass({action}): cards={len(self.cards)}, "
                        f"selected_flags={[getattr(c,'selected',False) for c in self.cards]}")
            return'''

# Try to find and replace various broken patterns
replacements_made = 0

# Method 1: Find the _emit_mass function and rewrite it entirely
import re

# Match the entire _emit_mass method
emit_pattern = re.compile(
    r'(    def _emit_mass\(self, action\):\n'
    r'(?:.*?\n)*?'
    r'        self\.mass_action_requested\.emit\(action, sel\)\n)',
    re.MULTILINE | re.DOTALL
)

match = emit_pattern.search(content)
if match:
    old_method = match.group(1)
    new_method = '''    def _emit_mass(self, action):
        sel = []
        for c in self.cards:
            if getattr(c, "selected", False):
                fd = getattr(c, "file_data", None)
                if fd:
                    sel.append(fd)
        
        if not sel:
            msg = ("Не выбрано ни одной карточки.\\n\\n"
                   "Поставь галочки в левом верхнем углу каждой нужной карточки,\\n"
                   "затем нажми \\\"Одобрить\\\" или \\\"Отклонить\\\".")
            QMessageBox.warning(self, "Внимание", msg)
            logger.debug("_emit_mass(%s): cards=%d, selected=%s" % (
                action, len(self.cards), 
                [getattr(c, 'selected', False) for c in self.cards]))
            return
        
        logger.info("_emit_mass(%s): %d file(s) selected" % (action, len(sel)))
        self.mass_action_requested.emit(action, sel)
'''
    content = content[:match.start()] + new_method + content[match.end():]
    replacements_made += 1
    print("[OK] Replaced _emit_mass method via regex")

# Method 2: If regex didn't work, try direct string operations
if replacements_made == 0:
    print("[!] Regex failed, trying direct replacement...")
    
    # Find the start of _emit_mass
    idx = content.find('def _emit_mass(self, action):')
    if idx != -1:
        # Find the end (next method definition or class-level code)
        next_def = content.find('\n    def ', idx + 10)
        next_class = content.find('\nclass ', idx + 10)
        end_idx = min(d for d in [next_def, next_class] if d > 0) if any(d > 0 for d in [next_def, next_class]) else len(content)
        
        old_block = content[idx:end_idx]
        print(f"[INFO] Found _emit_mass block ({end_idx - idx} chars)")
        
        new_block = '''def _emit_mass(self, action):
        sel = []
        for c in self.cards:
            if getattr(c, "selected", False):
                fd = getattr(c, "file_data", None)
                if fd:
                    sel.append(fd)
        
        if not sel:
            msg = ("Не выбрано ни одной карточки.\\n\\n"
                   "Поставь галочки в левом верхнем углу каждой нужной карточки,\\n"
                   "затем нажми \\\"Одобрить\\\" или \\\"Отклонить\\\".")
            QMessageBox.warning(self, "Внимание", msg)
            logger.debug("_emit_mass(%s): cards=%d, selected=%s" % (
                action, len(self.cards),
                [getattr(c, 'selected', False) for c in self.cards]))
            return
        
        logger.info("_emit_mass(%s): %d file(s) selected" % (action, len(sel)))
        self.mass_action_requested.emit(action, sel)

'''
        content = content[:idx] + new_block + content[end_idx:]
        replacements_made += 1
        print("[OK] Replaced _emit_mass via direct indexing")

if replacements_made == 0:
    print("[!] Could not locate _emit_mass, checking full file for syntax issues...")
    
    # Write a minimal working version of just the problematic part
    # Actually, let's check if there are other syntax errors too
    
    # Count unbalanced quotes per line near problem area
    for i, line in enumerate(lines[240:260], start=241):
        single_quotes = line.count("'") - line.count("\\'")
        double_quotes = line.count('"') - line.count('\\"')
        if single_quotes % 2 != 0 or double_quotes % 2 != 0:
            print(f"[WARN] Line {i} has odd quote count: {repr(line)}")

mc_path.write_text(content, encoding='utf-8', newline='\n')

# Verify by trying to compile
try:
    compile(content, str(mc_path), 'exec')
    print("\n[OK] File compiles successfully!")
except SyntaxError as e:
    print(f"\n[ERROR] Still has syntax error: {e.msg} at line {e.lineno}")
    print(f"  Text: {e.text}")

print("\nRun START.bat")