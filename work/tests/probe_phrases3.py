"""Обмер №3: какие ещё фразы менеджера не закрыты правилами (модель «не понимает»)."""
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
    "покажи ближайшие посты",
    "что публикуем на этой неделе",
    "что выходит завтра",
    "сколько постов осталось",
    "перенеси пост на завтра",
    "измени дату поста на 5 декабря",
    "добавь в план пост про осень",
    "напиши 3 идеи для сторис",
    "перепиши подпись второго поста короче",
    "сделай подпись короче",
    "проверь, все ли посты с подписями",
    "покажи бренд-профиль",
    "заполни бренд-профиль заново",
    "сделай из поста рилс",
    "подготовь сторис по посту",
    "экспортируй план в excel",
    "сделай календарь на месяц",
    "что писать завтра",
    "сделай отчёт по плану",
    "удали все события календаря",
    "поставь всем постам статус опубликовано",
    "скопируй план на следующий месяц",
]


def seeded():
    dm = DataManager("probe3", tempfile.mkdtemp(prefix="probe3_"))
    core = AICore(dm, {"monthly_budget_usd": 0},
                  app_db_path=Path(tempfile.mkdtemp(prefix="probe3_db_")) / "app.db",
                  providers=(Dumb(), None))
    core.run_tool("create_strategy", brief="кофейня", sections=[
        {"id": "s1", "title": "Аудитория", "content": "Город 25–40."}])
    for day in (1, 3, 5):
        core.run_tool("add_record", section="content_plan",
                      fields={"id": f"cp_{day}", "date": f"0{day}.12.2026",
                              "topic": f"Пост {day}", "rubric": "Польза", "format": "Пост",
                              "caption": "Готово", "status": "Черновик"})
    core.run_tool("add_record", section="calendar_events",
                  fields={"id": "ev_1", "date": "01.12.2026", "title": "Пост 1", "link": "cp_1"})
    return dm, core


for text in PHRASES:
    dm, core = seeded()
    decision = core.router._rules(text)
    reply = core.handle(text)
    tool = (getattr(decision, "tool", "") or "") if decision else ""
    clarify = (getattr(decision, "clarify", "") or "") if decision else ""
    verdict = (f"RULE {tool} {getattr(decision, 'args', {})}" if tool else
               ("CLARIFY " + clarify[:70] if clarify else "NONE"))
    head = (reply.text or "").replace("\n", " ")[:80]
    print(f"{text} ||| {verdict} ||| {head}")
