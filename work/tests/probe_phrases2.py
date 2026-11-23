"""Разовый обмер №2: публикации/медиа и правки стратегии (модель «не понимает»)."""
import sys, tempfile
from pathlib import Path

APP = Path(__file__).resolve().parents[2] / "AI_SMM_Work_Architecture_A75"
sys.path.insert(0, str(APP))

from ai_core import AICore, LLMResult
from data_manager import DataManager


class Dumb:
    name = "dumb"

    def available(self):
        return True

    def chat(self, system, user, temperature=0.2, max_tokens=2048, fmt=""):
        return LLMResult(text="не знаю", provider=self.name, model="dumb")


PHRASES = [
    "покажи материалы",
    "сколько у меня медиа",
    "импортируй материалы из C:\\foto",
    "загрузи фото из папки загрузки",
    "убери материал m1 из списка",
    "что готово к публикации",
    "какие посты можно опубликовать",
    "выложи материал m1 на публичный url",
    "сожми фото до 1080",
    "обрежь фотографии под квадрат",
    "какие файлы в публикациях",
    "перемести материал m1 в папку рилс",
    "покажи стратегию",
    "какие блоки в стратегии",
    "перепиши блок аудитория",
    "поменяй раздел позиционирование",
    "добавь раздел в стратегию про конкурентов",
    "удали блок стратегии про конкурентов",
    "обнови kpi: охват 5000",
    "какие у нас kpi",
]


def seeded():
    dm = DataManager("probe2", tempfile.mkdtemp(prefix="probe2_"))
    core = AICore(dm, {"monthly_budget_usd": 0},
                  app_db_path=Path(tempfile.mkdtemp(prefix="probe2_db_")) / "app.db",
                  providers=(Dumb(), None))
    core.run_tool("create_strategy", brief="кофейня", sections=[
        {"id": "s1", "title": "Аудитория", "content": "Город 25–40."},
        {"id": "s2", "title": "Позиционирование", "content": "Своя обжарка."}])
    for day in (1, 3):
        core.run_tool("add_record", section="content_plan",
                      fields={"id": f"cp_{day}", "date": f"0{day}.12.2026",
                              "topic": f"Пост {day}", "rubric": "Польза", "format": "Пост",
                              "status": "Черновик"})
    core.run_tool("add_record", section="calendar_events",
                  fields={"id": "ev_1", "date": "01.12.2026", "title": "Пост 1",
                          "link": "cp_1"})
    dm._data["other_files"] = {"Материалы": [{"id": "mat_1", "name": "p1.jpg"}]}
    dm._data["shooting_tasks"].append({"id": "st_1", "plan_id": "cp_1", "title": "ТЗ 1"})
    for media_id, name in (("m1", "p1.jpg"), ("m2", "p2.jpg")):
        dm._data["media_ready"].append({"id": media_id, "name": name, "type": "image",
                                        "path": f"/nope/{name}", "status": "approved"})
    dm.save()
    return dm, core


for text in PHRASES:
    dm, core = seeded()
    before = (len(dm.get_content_plan()), len(dm.get_calendar_events()),
              len(dm.get_shooting_tasks()))
    decision = core.router._rules(text)
    reply = core.handle(text)
    tool = (getattr(decision, "tool", "") or "") if decision else ""
    args = (getattr(decision, "args", {}) or {}) if decision else {}
    clarify = (getattr(decision, "clarify", "") or "") if decision else ""
    head = (reply.text or "").replace("\n", " ")[:110]
    verdict = (f"RULE {tool} {args}" if tool else
               ("CLARIFY " + clarify[:80] if clarify else "NONE"))
    print(f"{text}\n    -> {verdict}\n    ответ: {head}\n")
