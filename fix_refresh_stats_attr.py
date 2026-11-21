#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix: Correct attribute name in refresh_stats().
Run: python fix_refresh_stats_attr.py
"""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

print("\n=== Fixing refresh_stats attribute ===\n")

gui_path = BASE / "gui_main.py"
g = gui_path.read_text(encoding='utf-8')

# Find what the DataManager attribute is actually called
import re
match = re.search(r'self\.(\w+)\s*=\s*DataManager', g)
if match:
    attr_name = match.group(1)
    print(f"[OK] Found DataManager attribute: self.{attr_name}")
else:
    # Try alternative patterns
    for pattern in [r'self\.dm\s*=', r'self\.data_manager\s*=', r'self\.state\s*=']:
        m = re.search(pattern, g)
        if m:
            attr_name = m.group(0).split()[0].replace('self.', '').rstrip('=')
            print(f"[OK] Found attribute via pattern '{pattern}': self.{attr_name}")
            break
    else:
        attr_name = None
        print("[!] Could not determine DataManager attribute name")

# Fix refresh_stats to use correct attribute
old_method = '''    def refresh_stats(self):
        """Recompute and show project stats in the left panel from DataManager."""
        try:
            stats = self.data_manager.get_stats()'''

new_method = f'''    def refresh_stats(self):
        """Recompute and show project stats in the left panel from DataManager."""
        try:
            stats = self.{attr_name}.get_stats()''' if attr_name else old_method

g = g.replace(old_method, new_method)

# Also fix the call site (after import)
old_call = "        self.refresh_stats()\n        if imported > 0:"
new_call = "        self.refresh_stats()\n        if imported > 0:"
# This one is fine as-is since it calls self.refresh_stats() which now uses correct attr

gui_path.write_text(g, encoding='utf-8', newline='\n')

print(f"\n[OK] Fixed refresh_stats() to use self.{attr_name or '???'}")
print("\nRun START.bat")