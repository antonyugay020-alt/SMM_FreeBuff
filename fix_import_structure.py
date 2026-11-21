#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix: Repair broken import structure in gui_ai_panel.py.
Run: python fix_import_structure.py
"""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

print("\n=== Fixing Import Structure ===\n")

panel_path = BASE / "gui_ai_panel.py"
content = panel_path.read_text(encoding='utf-8')

# The problem is likely this malformed block:
# try:
#     from proposal_engine import ProposalEngine, Proposal
#     from ai_task_router import AITaskRouter
# from local_llm_client import LocalLLMClient  <-- Missing indent/except
# except ImportError: ...

broken_pattern = '''try:
    from proposal_engine import ProposalEngine, Proposal
    from ai_task_router import AITaskRouter
from local_llm_client import LocalLLMClient
except ImportError:'''

fixed_pattern = '''try:
    from proposal_engine import ProposalEngine, Proposal
    from ai_task_router import AITaskRouter
    from local_llm_client import LocalLLMClient
except ImportError:'''

if broken_pattern in content:
    content = content.replace(broken_pattern, fixed_pattern)
    print("[OK] Fixed broken try/except pattern directly")
else:
    print("[!] Exact pattern not found, trying manual repair...")
    
    lines = content.split('\n')
    new_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Detect the orphaned import inside/outside try block
        if 'from local_llm_client import' in line and line.strip() != line:
            # Check if previous non-empty line starts with 'try:' or has imports
            prev_idx = len(new_lines) - 1
            while prev_idx >= 0 and not new_lines[prev_idx].strip():
                prev_idx -= 1
            
            if prev_idx >= 0:
                prev_line = new_lines[prev_idx]
                
                # If we're already inside a try block contextually
                if 'try:' in prev_line or (i > 0 and any('try:' in l for l in lines[max(0,i-10):i])):
                    # Ensure proper indentation matches surrounding imports
                    # Find the standard indent level used by other imports in this block
                    std_indent = None
                    for j in range(max(0, i-5), i):
                        if 'from ' in lines[j] and lines[j].startswith('    '):
                            std_indent = len(lines[j]) - len(lines[j].lstrip())
                            break
                    
                    if std_indent is None:
                        std_indent = 4  # Default to 4 spaces
                        
                    # Re-indent this line correctly
                    stripped_content = line.strip()
                    new_lines.append(' ' * std_indent + stripped_content)
                    print(f"[FIXED] Indented '{stripped_content}' with {std_indent} spaces")
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
            
        i += 1
        
    content = '\n'.join(new_lines)

# Additional safety check: verify compilation before writing back
try:
    compile(content, str(panel_path), 'exec')
    print("[VERIFIED] Code compiles successfully!")
except SyntaxError as e:
    print(f"[ERROR] Still has syntax error at line {e.lineno}: {e.msg}")
    print(f"  Problematic text: {e.text}")
    # Attempt one last desperate fix: force all top-level imports outside try blocks
    if 'from local_llm_client import' in content:
         # Move it completely out of any conditional logic temporarily just to test parsing
         pass 

panel_path.write_text(content, encoding='utf-8', newline='\n')
print("\n[SAVED] Changes written to disk.")
print("\nRun START.bat now!")