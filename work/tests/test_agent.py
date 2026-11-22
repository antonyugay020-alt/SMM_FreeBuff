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
        self.formats = []
        self.agent_calls = 0

    def available(self):
        return True

    def chat(self, system, user, temperature=0.2, max_tokens=2048, fmt=""):
        self.calls.append(user)
        self.formats.append(fmt)
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


class Dead:
    """Провайдер, которого нет: поведение без модели не зависит от машины."""

    name = "stub"

    def available(self):
        return False

    def chat(self, *args, **kwargs):
        raise AssertionError("без модели никто не должен спрашивать модель")


def build(script, providers=True):
    dm = DataManager("agent", tempfile.mkdtemp(prefix="agent_"))
    stub = Stage(script) if providers else Dead()
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
ok("шаг агента просит JSON у модели", "json" in stub.formats, stub.formats)

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


# --- «грязные» ответы модели: работа продолжается ---
MALFORMED = [
    ("текст вокруг JSON", 'Сейчас создам план.\n{"tool": "create_content_plan", "args": {"count": 2}}\nГотово.'),
    ("action вместо tool", '{"action": "create_content_plan", "args": {"count": 2}}'),
    ("args строкой", '{"tool": "create_content_plan", "args": "{\\"count\\": 2}"}'),
    ("вложенный step", '{"step": {"tool_name": "create_content_plan", "arguments": {"count": 2}}}'),
    ("список из шага", '[{"name": "create_content_plan", "args": {"count": 2}}]'),
    ("имя инструмента ключом", '{"create_content_plan": {"count": 2}}'),
    ("```json блок", '```json\n{"tool": "create_content_plan", "args": {"count": 2}}\n```'),
    ("function-вызов", '{"function": {"name": "create_content_plan", "arguments": "{\\"count\\": 2}"}}'),
    ("tool_calls-список", '{"tool_calls": [{"function": {"name": "create_content_plan", "arguments": {"count": 2}}}]}'),
]
for name, first in MALFORMED:
    dm, core, stub = build([first, '{"action": "done", "say": "План готов."}'])
    reply = core.handle("подготовь контент")
    ok(f"грязный ответ: {name}",
       len(dm.get_content_plan()) == 2 and "План готов" in reply.text,
       (len(dm.get_content_plan()), reply.text))

# --- done с полем answer ---
dm, core, stub = build(['{"type": "finish", "answer": "Всё готово."}'] * 2)
reply = core.handle("подготовь контент")
ok("done по полю answer", reply.layer == "agent" and "готово" in reply.text.lower(), reply.text)

# --- пустое «готово» не принимается, пока ничего не сделано ---
dm, core, stub = build([
    '{"action": "done", "say": "Готово."}',
    '{"action": "tool", "tool": "create_content_plan", "args": {"count": 1}}',
    '{"action": "done", "say": "Готово: 1 пост."}'])
reply = core.handle("нужен контент")
ok("не принял пустое «готово»", len(dm.get_content_plan()) == 1, len(dm.get_content_plan()))

# --- проза после первого шага становится ответом ---
dm, core, stub = build([
    '{"tool": "create_content_plan", "args": {"count": 1}}',
    "План создан, больше ничего не нужно."])
reply = core.handle("нужен контент")
ok("проза после шага — ответ", "План создан" in reply.text, reply.text)

# --- выдуманный инструмент не превращается в «готово» ---
dm, core, stub = build([
    '{"action": "tool", "tool": "create_week_plan", "args": {"days": 7}, "say": "Готово."}',
    '{"action": "tool", "tool": "create_content_plan", "args": {"count": 2}}',
    '{"action": "done", "say": "План на неделю готов."}'])
reply = core.handle("подготовь контент на неделю")
ok("выдуманный инструмент не закрыл задачу", len(dm.get_content_plan()) == 2,
   len(dm.get_content_plan()))
ok("модели сказано, что инструмента нет",
   any("такого инструмента нет" in text for text in stub.calls), stub.calls[-1][-300:])
ok("итог — настоящий, а не отписка модели", "План на неделю готов" in reply.text, reply.text)

# --- повтор выдуманного инструмента — остановка с причиной, а не «готово» ---
dm, core, stub = build(['{"action": "tool", "tool": "make_magic", "say": "Готово."}'] * 3)
reply = core.handle("сделай красиво")
ok("два выдуманных инструмента — честная причина",
   "которых нет" in reply.text and "make_magic" in reply.text, reply.text)
ok("на выдумке ничего не создано", not dm.get_content_plan(), dm.get_content_plan())
ok("выдумка не попала в журнал",
   all(entry["tool"] != "make_magic" for entry in core.journal.list(10)),
   [entry["tool"] for entry in core.journal.list(10)])

# --- action=tool без имени инструмента — не «готово» ---
dm, core, stub = build([
    '{"action": "tool", "args": {"count": 1}, "say": "Готово."}',
    '{"action": "tool", "tool": "create_content_plan", "args": {"count": 1}}',
    '{"action": "done", "say": "Готово: 1 пост."}'])
reply = core.handle("нужен пост")
ok("шаг без имени инструмента не закрыл задачу", len(dm.get_content_plan()) == 1,
   len(dm.get_content_plan()))
ok("итог после настоящего шага", "1 пост" in reply.text, reply.text)

# --- после плана «готово» не принимается, пока нет подписей и ТЗ ---
dm, core, stub = build([
    '{"action": "tool", "tool": "create_content_plan", "args": {"count": 2}}',
    '{"action": "done", "say": "Готово: план создан."}',
    '{"action": "tool", "tool": "write_captions", "args": {}}',
    '{"action": "tool", "tool": "create_shooting_task", "args": {}}',
    '{"action": "done", "say": "Готово: план, подписи и ТЗ."}'])
reply = core.handle("подготовь кофейне контент на неделю")
plan = dm.get_content_plan()
ok("после плана агент дописал подписи",
   plan and all(str(item.get("caption") or "").strip() for item in plan),
   [(item.get("topic"), item.get("caption")) for item in plan])
ok("после плана агент сделал ТЗ",
   plan and all(item.get("shooting_task_id") for item in plan),
   [(item.get("topic"), item.get("shooting_task_id")) for item in plan])
ok("модели сказано, что задача не закончена",
   any("подписей" in text and "write_captions" in text for text in stub.calls),
   stub.calls[-3:-1])
ok("итог называет план, подписи и ТЗ", "ТЗ" in reply.text, reply.text)

# --- если модель упёрлась в «готово», цепочка доводится сама ---
dm, core, stub = build([
    '{"action": "tool", "tool": "create_content_plan", "args": {"count": 2}}',
    '{"action": "done", "say": "План готов."}',
    '{"action": "done", "say": "План готов."}'])
reply = core.handle("подготовь контент")
plan = dm.get_content_plan()
ok("упорное «готово» не оставило план без подписей",
   plan and all(str(item.get("caption") or "").strip() for item in plan),
   [(item.get("topic"), item.get("caption")) for item in plan])
ok("упорное «готово» не оставило план без ТЗ",
   plan and all(item.get("shooting_task_id") for item in plan),
   [(item.get("topic"), item.get("shooting_task_id")) for item in plan])
ok("сказано, что доделал сам", "Довёл до конца сам" in reply.text, reply.text)
ok("слова модели не потеряны", "План готов" in reply.text, reply.text)
ok("доделка попала в журнал",
   {"write_captions", "create_shooting_task"} <= {entry["tool"] for entry in core.journal.list(10)},
   [entry["tool"] for entry in core.journal.list(10)])

# --- план без единого «готово» всё равно доводится до подписей и ТЗ ---
dm, core, stub = build(
    ['{"action": "tool", "tool": "create_content_plan", "args": {"count": 1}}'] * (AGENT_STEPS + 2))
reply = core.handle("нужен контент")
plan = dm.get_content_plan()
ok("лимит шагов не оставил план без подписей",
   plan and all(str(item.get("caption") or "").strip() for item in plan), reply.text)
ok("лимит шагов не оставил план без ТЗ",
   plan and all(item.get("shooting_task_id") for item in plan), reply.text)
ok("лимит шагов назван честно", "лимите шагов" in reply.text or "Остановился" in reply.text,
   reply.text)

# --- стратегия из строк, а не словарей, не роняет инструмент ---
dm, core, stub = build([
    '{"action": "tool", "tool": "create_strategy", "args": {"sections": '
    '["О проекте: кофейня у дома", "Аудитория: жители района"]}}',
    '{"action": "done", "say": "Стратегия готова."}'])
reply = core.handle("набросай стратегию для кофейни")
sections = dm.get_strategy().get("sections") or []
ok("стратегия из строк собрана", len(sections) == 2, sections)
ok("заголовки строк разобраны", [one.get("title") for one in sections] == ["О проекте", "Аудитория"],
   sections)
ok("итог без падения инструмента", "Стратегия готова" in reply.text, reply.text)

print("AGENT_DONE")
