#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix: Repair broken try/except block in gui_ai_panel.py imports.
Run: python fix_router_import.py
"""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

print("\n=== Fixing Router Import ===\n")

panel_path = BASE / "gui_ai_panel.py"
content = panel_path.read_text(encoding='utf-8')

# The problem is this structure:
# try:
#     from proposal_engine import ProposalEngine, Proposal
# from ai_task_router import AITaskRouter  <-- ERROR HERE (missing except)
# except ImportError: ...

broken_block = '''try:
    from proposal_engine import ProposalEngine, Proposal
from ai_task_router import AITaskRouter
except ImportError:
    class ProposalEngine: pass
    class Proposal: pass'''

fixed_block = '''try:
    from proposal_engine import ProposalEngine, Proposal
    from ai_task_router import AITaskRouter
except ImportError:
    class ProposalEngine: pass
    class Proposal: pass
    class AITaskRouter: pass'''

if broken_block in content:
    content = content.replace(broken_block, fixed_block)
    print("[OK] Fixed broken try/except block")
else:
    print("[WARN] Exact pattern not found, trying line-by-line fix...")
    
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'from ai_task_router import' in line and 'try:' not in lines[max(0,i-3):i+1]:
            # This import is orphaned - move it inside the try block above
            # Find the preceding try block
            for j in range(i-1, max(0, i-10), -1):
                if 'try:' in lines[j]:
                    # Insert this import right after the first successful import in try block
                    indent = len(lines[j]) - len(lines[j].lstrip()) + 4
                    lines.insert(j+2, ' ' * indent + line.strip())
                    del lines[i+1]  # Remove original misplaced line
                    print(f"[OK] Moved router import into try block at line {j+2}")
                    break
            break
    
    content = '\n'.join(lines)

panel_path.write_text(content, encoding='utf-8', newline='\n')

# Verify compilation
try:
    compile(content, str(panel_path), 'exec')
    print("\n[SUCCESS] File compiles without errors!")
except SyntaxError as e:
    print(f"\n[ERROR] Still has syntax error at line {e.lineno}: {e.msg}")
    print(f"  Text: {e.text}")

print("\nRun START.bat")