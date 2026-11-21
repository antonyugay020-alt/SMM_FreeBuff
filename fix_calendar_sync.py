#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Step: Calendar sync - content plan items create calendar events.
Adds get_calendar_events/add_calendar_event to DataManager,
patches ContentDistributor to mirror plan items into calendar.
Safe: compile-gate on every rewritten file.
Run: python fix_calendar_sync.py
"""

from pathlib import Path
import re

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

print("\n=== Calendar Sync ===\n")

# ---------------------------------------------------------------
# 0. Audit: how does the Calendar UI read its data?
# ---------------------------------------------------------------
print("[0/3] Auditing calendar data flow...")
cal_files = sorted(set(list(BASE.glob("*calendar*")) + list(BASE.glob("*Calendar*"))))
if not cal_files:
    print("  [!] No calendar-named files found; UI may use generic section file")
for cf in cal_files:
    print(f"  [FILE] {cf.name}")
    try:
        txt = cf.read_text(encoding="utf-8")
        hits = [ln.strip() for ln in txt.split("\n")
                if re.search(r"calendar|event", ln, re.I) and ("dm." in ln or "data_manager" in ln or "get_" in ln)]
        for h in hits[:8]:
            print(f"     | {h[:110]}")
    except Exception as e:
        print(f"     | read error: {e}")

# ---------------------------------------------------------------
# 1. DataManager: add calendar methods
# ---------------------------------------------------------------
print("\n[1/3] Patching data_manager.py...")
dm_path = BASE / "data_manager.py"
dm = dm_path.read_text(encoding="utf-8")

methods = '''
    def get_calendar_events(self):
        """Return calendar events list."""
        return self._data.setdefault("calendar", [])

    def add_calendar_event(self, event):
        """Add event to calendar section. Returns created id."""
        events = self._data.setdefault("calendar", [])
        existing = [e.get("id") for e in events if isinstance(e, dict)]
        counter = len(events) + 1
        new_id = f"ev_{counter:03d}"
        while new_id in existing:
            counter += 1
            new_id = f"ev_{counter:03d}"
        event["id"] = new_id
        event.setdefault("status", "Planned")
        event.setdefault("source", "Manual")
        events.append(event)
        self.save()
        logger.info(f"Added calendar event: {new_id} ({event.get('date','')} {str(event.get('title',''))[:30]})")
        return new_id
'''

changed = False
for sig in ("def get_calendar_events(", "def add_calendar_event("):
    if sig in dm:
        print(f"  [=] already exists: {sig.strip()}")
    else:
        marker = "\n    def save("
        if marker in dm:
            dm = dm.replace(marker, methods + marker, 1)
        else:
            dm = dm.rstrip() + "\n" + methods + "\n"
        changed = True
        print(f"  [+] added: {sig.strip()}")

if changed:
    try:
        compile(dm, str(dm_path), "exec")
        dm_path.write_text(dm, encoding="utf-8", newline="\n")
        print("  [OK] data_manager.py updated (compile-gate passed)")
    except SyntaxError as e:
        print(f"  [ROLLBACK] syntax error at line {e.lineno}: {e.msg} - file NOT modified")
else:
    print("  [=] no changes needed")

# ---------------------------------------------------------------
# 2. ContentDistributor: mirror plan items into calendar
# ---------------------------------------------------------------
print("\n[2/3] Patching content_distributor.py...")
cd_path = BASE / "content_distributor.py"
cd = cd_path.read_text(encoding="utf-8")

# 2a. import timedelta
old_imp = "from datetime import datetime"
new_imp = "from datetime import datetime, timedelta"
if old_imp in cd and "timedelta" not in cd:
    cd = cd.replace(old_imp, new_imp, 1)
    print("  [OK] timedelta imported")

# 2b. capture explicit dates while parsing list items
old_append = '''                    items.append({
                        "topic": topic,
                        "description": desc,
                        "date": ""  # Will be filled later or left blank
                    })'''
new_append = '''                    date_m = re.search(r"\\b(\\d{1,2}\\.\\d{1,2}(?:\\.\\d{2,4})?)\\b", stripped)
                    items.append({
                        "topic": topic,
                        "description": desc,
                        "date": date_m.group(1) if date_m else ""
                    })'''
if old_append in cd:
    cd = cd.replace(old_append, new_append, 1)
    print("  [OK] date extraction added to _parse_content_list")
else:
    print("  [!] _parse_content_list append block not found - date extraction skipped")

# 2c. distribute(): assign fallback dates + create calendar events
old_loop = '''            for item in items:
                new_entry = {
                    "id": f"cp_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(items)}",
                    "date": item.get("date", ""),
                    "topic": item.get("topic", ""),
                    "format": item.get("format", "Post"),
                    "status": "Planned",
                    "source": "AI Generated"
                }
                self.dm.add_content_plan_item(new_entry)
                actions_taken.append(f"Added content plan item: {item['topic'][:30]}...")'''

new_loop = '''            base_date = datetime.now() + timedelta(days=1)
            auto_offset = 0
            for item in items:
                date_str = item.get("date", "")
                if not date_str:
                    d = base_date + timedelta(days=auto_offset)
                    date_str = d.strftime("%d.%m.%Y")
                    auto_offset += 1
                new_entry = {
                    "id": f"cp_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(items)}",
                    "date": date_str,
                    "topic": item.get("topic", ""),
                    "format": item.get("format", "Post"),
                    "status": "Planned",
                    "source": "AI Generated"
                }
                self.dm.add_content_plan_item(new_entry)
                actions_taken.append(f"Added content plan item: {item['topic'][:30]}...")

                # Mirror into calendar
                try:
                    ev = {
                        "date": date_str,
                        "title": str(item.get("topic", ""))[:80],
                        "description": str(item.get("description", ""))[:200],
                        "type": "Контент",
                        "source": "AI",
                        "status": "Planned",
                    }
                    self.dm.add_calendar_event(ev)
                    actions_taken.append(f"Calendar event: {date_str} - {ev['title'][:40]}")
                except Exception as e:
                    logger.warning(f"Calendar event creation failed: {e}")'''

if old_loop in cd:
    cd = cd.replace(old_loop, new_loop, 1)
    print("  [OK] distribute() now creates calendar events")
else:
    print("  [!] distribute() loop not found exactly - patch skipped")

try:
    compile(cd, str(cd_path), "exec")
    cd_path.write_text(cd, encoding="utf-8", newline="\n")
    print("  [OK] content_distributor.py updated (compile-gate passed)")
except SyntaxError as e:
    print(f"  [ROLLBACK] syntax error at line {e.lineno}: {e.msg} - file NOT modified")

# ---------------------------------------------------------------
# 3. Quick self-test with fake DataManager
# ---------------------------------------------------------------
print("\n[3/3] Self-test...")
import sys
sys.path.insert(0, str(BASE))
try:
    from content_distributor import ContentDistributor

    class FakeDM:
        def __init__(self):
            self._data = {"content_plan": [], "calendar": []}
        def add_content_plan_item(self, item):
            item["id"] = f"cp_{len(self._data['content_plan'])+1:03d}"
            self._data["content_plan"].append(item)
            return item["id"]
        def add_calendar_event(self, event):
            event["id"] = f"ev_{len(self._data['calendar'])+1:03d}"
            self._data["calendar"].append(event)
            return event["id"]

    fake = FakeDM()
    dist = ContentDistributor(fake)
    ai_text = """- Пост про осенний латте 15.11.2026
- Сторис с рецептом приготовления
- Видео закулисья съёмки"""
    res = dist.distribute("сделай контент-план", ai_text, "content_plan")
    assert res["success"], "distribution reported failure"
    assert len(fake._data["content_plan"]) == 3, "plan items missing"
    assert len(fake._data["calendar"]) == 3, "calendar events missing"
    assert fake._data["calendar"][0]["date"] == "15.11.2026", "explicit date not parsed"
    assert fake._data["calendar"][1]["date"] != "", "fallback date not assigned"
    print("  [PASS] 3 plan items -> 3 calendar events, dates ok:")
    for ev in fake._data["calendar"]:
        print(f"     | {ev['date']}  {ev['title']}")
except Exception as e:
    print(f"  [FAIL] self-test error: {e}")

print("\n=== Done ===")
print("Run START.bat, ask AI for a content plan, then open 'Календарь' section.")