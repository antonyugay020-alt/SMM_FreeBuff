"""AI-менеджер выполняет задачу шагами сам: модель выбирает инструменты и доводит до результата."""
import json, sys, tempfile
from pathlib import Path

APP = Path(__file__).resolve().parents[2] / "AI_SMM_Work_Architecture_A75"
sys.path.insert(0, str(APP))

from ai_core import AGENT_STEPS, AICore, LLMResult
from data_manager import DataManager


def ok(name, cond, extra=""):
    print(("AGENT_OK " if cond else "AGENT_FAIL ") + name + ("" if cond else f" :: {extra}"))
    if not cond:
        raise SystemExit(1)


class Stage:
    """Подставная модель: агентские шаги из сценария, остальное — как обычная LLM."""

    name = "stub"

    def __init__(self, script):
        self.script = list(script)
        self.calls = []
        self.agent_calls = 0

    def available(self):
        return True

    def chat(self, system, user, temperature=0.2, max_tokens=2048):
        self.calls.append(user)
        low = user.lower()
        if "AI SMM Manager" in system:
            self.agent_calls += 1
            text = (self.script.pop(0) if self.script
                    else json.dumps({"action": "done", "say": "Готово."}, ensure_ascii=False))
        elif '"sections"' in system:
            text = json.dumps({"sections": [
                {"id": "s1", "title": "Аудитория", "content": "Город 25–40, кофе домой."},
                {"id": "s2", "title": "Позиционирование", "content": "Своя обжарка."}]},
                ensure_ascii=False)
        elif '"topics"' in system:
            text = json.dumps({"topics": [
                {"topic": "Три сорта утреннего фильтра", "rubric": "Польза", "format": "Пост"},
                {"topic": "Рецепт раф дома", "rubric": "Польза", "format": "Пост"},
                {"topic": "Отзыв гостя", "rubric": "Личное", "format": "Пост"}]},
                ensure_ascii=False)
        elif "SMM-копирайтер" in system:
            text = "Свежая обжарка каждую неделю. #кофе #кофейня\nЖдём вас!"
        else:
            text = "ок"
        return LLMResult(text=text, provider=self.name, model="stub")


def build(script, providers=True):
    dm = DataManager("agent", tempfile.mkdtemp(prefix="agent_"))
    stub = Stage(script) if providers else None
    core = AICore(dm, {"monthly_budget_usd": 0},
                  app_db_path=Path(tempfile.mkdtemp(prefix="agent_db_")) / "app.db",
                  providers=(stub, None))
    return dm, core, stub


SCRIPT = [
    '{"action": "tool", "tool": "create_strategy", "args": {"brief": "кофейня у дома"}}',
    '{"action": "tool", "tool": "create_content_plan", "args": {"count": 3}}',
    '{"action": "tool", "tool": "write_captions", "args": {}}',
    '{"action": "tool", "tool": "validate_plan", "args": {}}',
    '{"action": "done", "say": "Готово: стратегия, 3 поста с подписями, план проверен."}',
]

# --- одна свободная задача, без ключевых слов: агент проходит всю цепочку ---
dm, core, stub = build(SCRIPT)
reply = core.handle("подготовь кофейне контент на неделю")
print("ответ:", reply.text.replace("\n", " | "))
ok("работал агент", reply.layer == "agent", reply.layer)
ok("несколько шагов", len(stub.calls) >= 4, len(stub.calls))
ok("стратегия создана", len(dm.get_strategy().get("sections") or []) == 2,
   dm.get_strategy())
plan = dm.get_content_plan()
ok("план создан", len(plan) == 3, len(plan))
ok("подписи у всех постов", all(str(item.get("caption") or "").strip() for item in plan),
   [(item.get("topic"), item.get("caption")) for item in plan])
tools = [entry["tool"] for entry in core.journal.list(20)]
ok("шаги в журнале", {"create_strategy", "create_content_plan", "write_captions"} <= set(tools),
   tools)
ok("итог сказан пользователю", "Готово" in reply.text, reply.text)
ok("действия можно отменить", len(reply.actions or []) >= 3, len(reply.actions or []))

# --- публикацию агент не трогает ---
dm, core, stub = build([
    '{"action": "tool", "tool": "instagram_publish", "args": {"media_id": "m1"}}',
    '{"action": "done", "say": "Публикацию выполняет человек — я не публикую."}',
])
dm._data["media_ready"].append({"id": "m1", "name": "p.jpg", "type": "image",
                                "path": "/nope/p.jpg", "status": "approved"})
dm.save()
reply = core.handle("поставь пост в инстаграм")
ok("публикация не выполнена", "published_id" not in json.dumps(dm._data))
ok("пользователю сказано про ручную публикацию", "человек" in reply.text, reply.text)
ok("запрещённый инструмент не попал в журнал",
   all(entry["tool"] != "instagram_publish" for entry in core.journal.list(10)),
   [entry["tool"] for entry in core.journal.list(10)])

# --- нет модели: не выдумывает, а честно говорит причину ---
dm, core, _ = build([], providers=False)
reply = core.handle("подготовь кофейне контент на неделю")
ok("без модели — причина, а не тишина", "не подключена" in reply.text, reply.text)
ok("без модели ничего не создано", not dm.get_content_plan())

# --- лимит шагов не даёт зациклиться ---
loop = ['{"action": "tool", "tool": "create_content_plan", "args": {"count": 1}}'] * (AGENT_STEPS + 3)
dm, core, stub = build(loop)
reply = core.handle("сделай кое-что")
ok("остановился на лимите", "лимит шагов" in reply.text or "Остановился" in reply.text,
   reply.text)
ok("шагов не больше лимита", stub.agent_calls <= AGENT_STEPS, stub.agent_calls)

# --- задача, покрытая правилом, модель не дёргает ---
dm, core, stub = build([])
core.handle("проверь план")
ok("правило быстрее модели", not stub.calls, stub.calls)

print("AGENT_DONE")
