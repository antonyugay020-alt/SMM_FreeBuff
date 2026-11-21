#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cleanup: remove debug logs from gui_ai_panel.py + hide app version from UI.
Safe: compile-gate on every rewritten file.
Run: python fix_cleanup_logs_version.py
"""

from pathlib import Path
import re

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

print("\n=== Cleanup: Logs + Version ===\n")

# ---------------------------------------------------------------
# 1. Remove [DEBUG] logs from gui_ai_panel.py
# ---------------------------------------------------------------
print("[1/2] Cleaning gui_ai_panel.py...")
panel_path = BASE / "gui_ai_panel.py"
content = panel_path.read_text(encoding='utf-8')

# Replace the debug block with clean version
old_debug_block = '''                    # TRIGGER CONTENT DISTRIBUTION AUTOMATICALLY
                    logger.info(f"[DEBUG] Attempting distribution: category={cat}, query={user_input[:50]}...")
                    try:
                        win = self.window()
                        if hasattr(win, 'data_manager'):
                            dm = win.data_manager
                            dist = ContentDistributor(dm)
                            logger.info(f"[DEBUG] Distributor created, calling distribute()...")
                            
                            res = dist.distribute(user_input, real_resp, cat)
                            logger.info(f"[DEBUG] Distributor returned: {res}")
                            
                            if res["success"]:
                                notify_msg = "\\n\\n✅ Контент сохранён:\\n" + "\\n".join(res["actions"])
                                self._add_bubble("system", notify_msg)
                                
                                if hasattr(win, 'refresh_stats'):
                                    win.refresh_stats()
                            else:
                                logger.info(f"[DEBUG] Distributor reported no actions: {res}")
                        else:
                            logger.warning("[DEBUG] No data_manager found on window")
                    except Exception as e:
                        logger.error(f"[DEBUG] Distribution failed: {e}", exc_info=True)'''

new_clean_block = '''                    # TRIGGER CONTENT DISTRIBUTION AUTOMATICALLY
                    try:
                        win = self.window()
                        if hasattr(win, 'data_manager'):
                            dm = win.data_manager
                            dist = ContentDistributor(dm)
                            res = dist.distribute(user_input, real_resp, cat)
                            if res["success"]:
                                notify_msg = "\\n\\n✅ Контент сохранён:\\n" + "\\n".join(res["actions"])
                                self._add_bubble("system", notify_msg)
                                if hasattr(win, 'refresh_stats'):
                                    win.refresh_stats()
                    except Exception as e:
                        logger.error(f"Distribution failed: {e}")'''

if old_debug_block in content:
    content = content.replace(old_debug_block, new_clean_block, 1)
    print("  [OK] Removed [DEBUG] logs from distribution block")
else:
    print("  [!] Debug block not found - patch skipped")

# Compile gate for panel
try:
    compile(content, str(panel_path), 'exec')
    panel_path.write_text(content, encoding='utf-8', newline='\n')
    print("  [OK] gui_ai_panel.py updated (compile-gate passed)")
except SyntaxError as e:
    print(f"  [ROLLBACK] syntax error at line {e.lineno}: {e.msg}")

# ---------------------------------------------------------------
# 2. Remove version display from UI
# ---------------------------------------------------------------
print("\n[2/2] Removing version display from UI...")

# Search for version-related strings in GUI files
gui_files = list(BASE.glob("gui_*.py")) + [BASE / "app.py"]
version_patterns = [
    r'Phase 1\.\d+',
    r'Version\s*[:=]',
    r'Версия\s*[:=]',
    r'v\d+\.\d+',
    r'__version__',
    r'app_version',
    r'APP_VERSION',
]

found = []
for gf in gui_files:
    if not gf.exists():
        continue
    txt = gf.read_text(encoding='utf-8')
    for pat in version_patterns:
        for m in re.finditer(pat, txt):
            line_no = txt[:m.start()].count('\n') + 1
            line_text = txt.split('\n')[line_no - 1].strip()
            # Skip if it's just a comment or data (not UI display)
            if not line_text.startswith('#') and 'label' in line_text.lower() or 'title' in line_text.lower() or 'setWindowTitle' in line_text:
                found.append((gf.name, line_no, line_text[:80]))

if found:
    print("  Found version references in UI code:")
    for fname, lno, txt in found:
        print(f"    {fname}:{lno}: {txt}")
else:
    print("  [=] No obvious version labels found in GUI files")

# Try to find the main window title or header that shows version
main_path = BASE / "gui_main.py"
if main_path.exists():
    main_content = main_path.read_text(encoding='utf-8')
    
    # Look for setWindowTitle or similar
    title_patterns = [
        (r'setWindowTitle\([^)]+\)', 'window title'),
        (r'QLabel\([^)]*Phase[^)]*\)', 'phase label'),
        (r'QLabel\([^)]*Версия[^)]*\)', 'version label'),
        (r'"Phase \d+\.\d+"', 'phase string'),
        (r'"Версия \d+\.\d+"', 'version string'),
    ]
    
    for pat, desc in title_patterns:
        matches = list(re.finditer(pat, main_content))
        if matches:
            print(f"  [FOUND] {desc}: {len(matches)} occurrence(s)")
            for m in matches[:3]:
                line_no = main_content[:m.start()].count('\n') + 1
                line_text = main_content.split('\n')[line_no - 1].strip()
                print(f"    Line {line_no}: {line_text[:100]}")

print("\n=== Done ===")
print("Debug logs removed. Version display needs manual check based on findings above.")
print("Run START.bat to verify clean terminal output.")