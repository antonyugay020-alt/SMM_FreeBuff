"""Разовый обмер: какие обычные фразы правило не разбирает (модель «не понимает»)."""
import sys, tempfile
from pathlib import Path

APP = Path(__file__).resolve().parents[2] / "AI_SMM_Work_Architecture_A75"
sys.path.insert(0, str(APP))

from ai_core import AICore, LLMResult
from data_manager import DataManager


class Dumb:
    """Модель, которой ничего не понятно: как qwen3:8b на незнакомой формулировке."""

    name = "dumb"

    def available(self):
        return True

    def chat(self, system, user, temperature=0.2, max_tokens=2048, fmt=""):
        return LLMResult(text="не знаю", provider=self.name, model="dumb")


PHRASES = [
    "создай стратегию для кофейни у дома",
    "составь контент-план на 10 постов",
    "придумай 7 тем для рилс",
    "нужно 5 постов для инстаграма",
    "напиши подпись к первому посту",
    "напиши подписи ко всем постам",
    "проверь план",
    "добавь в календарь все посты",
    "покажи календарь на неделю",
    "поставь посты на следующую неделю",
    "перенеси посты на следующую неделю",
    "собери пакет для инстаграма",
    "сделай выгрузку публикаций за март",
    "выгрузи план в pdf",
    "распечатай стратегию",
    "проверь доступ к инстаграму",
    "подготовь ТЗ на съёмку",
    "сделай субтитры для видео",
    "обработай видео для рилс",
    "что зашло за месяц",
    "проанализируй вовлечённость",
    "заполни бренд-профиль",
    "отмени последнее действие",
    "покажи журнал действий",
    "что в проекте",
    "убери последний пост из плана",
    "добавь пост на 3 марта про латте",
    "поставь хештеги к посту",
    "сократи подпись до 300 символов",
    "сделай отчёт по плану",
]


def run(text):
    dm = DataManager("probe", tempfile.mkdtemp(prefix="probe_"))
    core = AICore(dm, {"monthly_budget_usd": 0},
                  app_db_path=Path(tempfile.mkdtemp(prefix="probe_db_")) / "app.db",
                  providers=(Dumb(), None))
    decision = core.router._rules(text)
    reply = core.handle(text)
    return decision, reply


for text in PHRASES:
    decision, reply = run(text)
    tool = (getattr(decision, "tool", "") or "") if decision else ""
    args = (getattr(decision, "args", {}) or {}) if decision else {}
    clarify = (getattr(decision, "clarify", "") or "") if decision else ""
    head = (reply.text or "").replace("\n", " ")[:110]
    if tool:
        verdict = f"RULE {tool} {args}"
    elif clarify:
        verdict = "CLARIFY " + clarify[:70]
    else:
        verdict = "NONE"
    print(f"{text}\n    -> {verdict}\n    ответ: {head}\n")
