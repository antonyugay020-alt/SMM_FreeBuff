#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug: Add logging to _simulate_response to see if Distributor is called.
Safe: compile-gate on rewrite.
Run: python fix_calendar_debug.py
"""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

print("\n=== Calendar Debug ===\n")

panel_path = BASE / "gui_ai_panel.py"
content = panel_path.read_text(encoding='utf-8')

# Find the distribution block and add debug logs
old_block = '''                    # TRIGGER CONTENT DISTRIBUTION AUTOMATICALLY
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
                        logger.error(f"Distribution failed silently: {e}")'''

new_block = '''                    # TRIGGER CONTENT DISTRIBUTION AUTOMATICALLY
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

if old_block in content:
    content = content.replace(old_block, new_block, 1)
    print("[OK] Added debug logging to distribution block")
else:
    print("[!] Distribution block not found - patch skipped")

# Compile gate
try:
    compile(content, str(panel_path), 'exec')
    panel_path.write_text(content, encoding='utf-8', newline='\n')
    print("[OK] gui_ai_panel.py updated (compile-gate passed)")
except SyntaxError as e:
    print(f"[ROLLBACK] syntax error at line {e.lineno}: {e.msg} - file NOT modified")

print("\n=== Done ===")
print("Run START.bat, ask AI for a content plan, then check terminal for [DEBUG] lines.")