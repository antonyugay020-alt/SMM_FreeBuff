import sys, tempfile
from pathlib import Path
APP = Path(__file__).resolve().parents[2] / "AI_SMM_Work_Architecture_A75"
PROJECT = APP.parent
WORK = Path(tempfile.mkdtemp(prefix="smm_test_"))
import os, sys, tempfile
sys.path.insert(0, str(APP))
from data_manager import DataManager
from ai_core import AICore

def ok(name, cond, extra=""):
    print(("STEP11_OK " if cond else "STEP11_FAIL ") + name + ("" if cond else f" :: {extra}"))
    if not cond:
        raise SystemExit(1)

tmp = tempfile.mkdtemp(prefix="step11_")
dm = DataManager("t11", tmp)
core = AICore(dm, {"monthly_budget_usd": 0})

plan = [("cp_t1","01.03.2026","Пост А","Польза","Опубликовано"),
        ("cp_t2","05.03.2026","Пост Б","Продажа","Опубликовано"),
        ("cp_t3","10.03.2026","Пост В","Польза","Черновик")]
for pid, date, topic, rubric, status in plan:
    core.run_tool("add_record", section="content_plan",
                  fields={"id": pid, "date": date, "topic": topic, "rubric": rubric,
                          "format": "Пост", "status": status})
ok("план 3 позиции", len(dm.get_content_plan()) == 3, dm.get_content_plan())

core.run_tool("add_record", section="post_metrics",
              fields={"id": "pm_1", "plan_id": "cp_t1", "reach": 1000, "likes": 80,
                      "comments": 10, "saves": 10})
core.run_tool("add_record", section="post_metrics",
              fields={"id": "pm_2", "plan_id": "cp_t2", "reach": 1000, "likes": 10,
                      "comments": 0, "saves": 0})
ok("метрики записаны", len(dm.get_post_metrics()) == 2, dm.get_post_metrics())

text = core.run_tool("analyze_performance", period_days=3650).text
lines = text.splitlines()
ok("сводка первой строкой", lines[0].startswith("Аналитика: 2 постов"), lines[0])
ok("охват с разделителем", "охват 2 000" in lines[0], lines[0])
ok("средняя вовлечённость 5.5%", "5.5%" in lines[0], lines[0])
ok("лучшая рубрика", any("«Польза»" in l and "10.0%" in l for l in lines), lines)
ok("топ по вовлечённости", any("Топ по вовлечённости" in l for l in lines), lines)
ok("слабый пост", any("Слабее остальных: 05.03.2026" in l for l in lines), lines)
ok("аналитика не пишется в журнал (read-only)",
   not [e for e in core.journal.list(20) if e["tool"] == "analyze_performance"],
   core.journal.list(3))

text30 = core.run_tool("analyze_performance", period_days=30).text
ok("период 30 дней отсекает старые", "за последние 30 дней метрик нет" in text30, text30)

dm2 = DataManager("t11", tmp)
core2 = AICore(dm2, {"monthly_budget_usd": 0})
ok("метрики пережили перезапуск",
   [int(m["reach"]) for m in dm2.get_post_metrics()] == [1000, 1000], dm2.get_post_metrics())

# --- раздел «Аналитика» (offscreen) ---
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication
app = QApplication([])
import gui_sections.analytics_section as an

sec = an.AnalyticsSection(dm2, {})
ok("в таблице только опубликованные/с метриками", sec.table.rowCount() == 2, sec.table.rowCount())
ok("ER считается", sec.table.item(0, 8).text() == "10.0%", sec.table.item(0, 8).text())
ok("счётчик в шапке", "2 с метриками" in sec.count_label.text(), sec.count_label.text())

sec.table.item(0, 4).setText("4000")
sec._flush_pending()
row = [m for m in dm2.get_post_metrics() if m["plan_id"] == "cp_t1"][0]
ok("правка охвата сохранена", int(row["reach"]) == 4000, row)
ok("правка в журнале", any(e["tool"] == "edit_record" for e in core.journal.list(5)),
   core.journal.list(3))
ok("ER пересчитан", sec.table.item(0, 8).text() == "2.5%", sec.table.item(0, 8).text())

core2.run_tool("edit_record", section="content_plan", item_id="cp_t3",
              fields={"status": "Опубликовано"})
sec.refresh()
ok("опубликованный пост появился без метрик", sec.table.rowCount() == 3, sec.table.rowCount())
sec.table.item(2, 5).setText("50")
sec._flush_pending()
ok("строка метрик создана правкой в таблице",
   any(m["plan_id"] == "cp_t3" for m in dm2.get_post_metrics()), dm2.get_post_metrics())

seen = {}
an.QMessageBox.information = staticmethod(lambda parent, title, text: seen.update(t=text))
sec._on_analyze()
ok("окно анализа открылось", "Аналитика:" in seen.get("t", ""), seen)
ok("строка статуса", sec.status.text().startswith("Аналитика:"), sec.status.text())

print("STEP11_OK")
