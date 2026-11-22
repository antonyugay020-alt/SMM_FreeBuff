import sys, tempfile
from pathlib import Path
APP = Path(__file__).resolve().parents[2] / "AI_SMM_Work_Architecture_A75"
PROJECT = APP.parent
WORK = Path(tempfile.mkdtemp(prefix="smm_test_"))
import os, sys, tempfile
from pathlib import Path
ROOT = APP
sys.path.insert(0, str(APP))
from data_manager import DataManager
from ai_core import AICore
import pdf_export

def ok(name, cond, extra=""):
    print(("STEP12_OK " if cond else "STEP12_FAIL ") + name + ("" if cond else f" :: {extra}"))
    if not cond:
        raise SystemExit(1)

FONT = "/opt/freestyle/python/lib/python3.12/site-packages/matplotlib/mpl-data/fonts/ttf/DejaVuSans.ttf"
pdf_export.FONT_CANDIDATES.insert(0, FONT)

tmp = tempfile.mkdtemp(prefix="step12_")
dm = DataManager("t12", tmp)
core = AICore(dm, {"monthly_budget_usd": 0})
for pid, date, topic, status in (("cp_1","01.12.2026","Пост про кофе","Запланировано"),
                                 ("cp_2","03.12.2026","Рецепт раф","Черновик"),
                                 ("cp_3","05.12.2026","Отзыв гостя","Запланировано")):
    core.run_tool("add_record", section="content_plan",
                  fields={"id": pid, "date": date, "topic": topic, "rubric": "Польза",
                          "format": "Пост", "status": status})
core.run_tool("create_strategy", brief="кофейня",
              sections=[{"id": "s1", "title": "Аудитория", "content": "Город 25–40, кофе домой."},
                        {"id": "s2", "title": "Позиционирование", "content": "Своя обжарка."}])
core.run_tool("update_kpis", kpis=[{"metric": "Охват", "current": "1000", "target": "5000",
                                   "deadline": "31.12.2026"}])

out = Path(tmp) / "pdf"
out.mkdir()
reply = core.run_tool("export_pdf", kind="plan", dest=str(out))
path = out / [p.name for p in out.iterdir() if p.suffix == ".pdf"][0]
ok("план выгружен", path.name.endswith("-plan.pdf") and path.exists(), reply.text)
ok("файл — PDF", path.read_bytes()[:5] == b"%PDF-" and path.stat().st_size > 1000, path.stat().st_size)
ok("отчёт с путём", str(path) in reply.text, reply.text)
ok("журнал export_pdf", any(e["tool"] == "export_pdf" and e["status"] == "done"
                             for e in core.journal.list(5)), core.journal.list(3))

core.run_tool("export_pdf", kind="strategy", dest=str(out))
strat = [p for p in out.iterdir() if p.name.endswith("-strategy.pdf")]
ok("стратегия выгружена", len(strat) == 1 and strat[0].read_bytes()[:5] == b"%PDF-", strat)
strat_path = strat[0]

bad = core.run_tool("export_pdf", kind="report", dest=str(out))
ok("неизвестный вид отклонён", "Неизвестный документ" in bad.text, bad.text)

entry = [e for e in core.journal.list(5) if e["tool"] == "export_pdf"][0]
msg = core.undo(entry["id"]).text
ok("откат удаляет только созданный файл",
   "Удалил файл" in msg and not strat_path.exists() and path.exists(), msg)

empty_dir = tempfile.mkdtemp(prefix="step12_empty_")
edm = DataManager("t12e", empty_dir)
ecore = AICore(edm, {"monthly_budget_usd": 0})
before = len(ecore.journal.list(5))
r = ecore.run_tool("export_pdf", kind="plan", dest=str(out))
ok("пустой план не выгружается", "выгружать нечего" in r.text and len(ecore.journal.list(5)) == before, r.text)

pdf_export.FONT_CANDIDATES[:] = []
r = core.run_tool("export_pdf", kind="plan", dest=str(out))
ok("без шрифта — сообщение", "шрифт" in r.text.lower(), r.text)
pdf_export.FONT_CANDIDATES.insert(0, FONT)

core.run_tool("export_pdf", kind="plan")
ok("без dest — в проект", list((Path(tmp) / "exports").glob("*-plan.pdf")), tmp)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication
app = QApplication([])
import gui_sections.plans_section as ps

sec = ps.PlansSection(dm, {})
ok("детали плана в карточке", "3 позиций" in sec._details["plan"].text(), sec._details["plan"].text())
ok("детали стратегии", "2 блоков" in sec._details["strategy"].text(), sec._details["strategy"].text())
dest2 = tempfile.mkdtemp(prefix="step12_gui_")
ps.QFileDialog.getExistingDirectory = staticmethod(lambda *a, **k: dest2)
seen = {}
ps.QMessageBox.information = staticmethod(lambda parent, title, text: seen.update(t=text))
sec._export("plan")
ok("кнопка раздела выгрузила PDF", list(Path(dest2).glob("*-plan.pdf")), seen)
ok("статус раздела", sec.status.text().startswith("Выгрузил"), sec.status.text())
ps.QFileDialog.getExistingDirectory = staticmethod(lambda *a, **k: "")
sec._export("strategy")
ok("отмена выбора ничего не пишет", sec.status.text().startswith("Выгрузил"), sec.status.text())
print("STEP12_OK")
