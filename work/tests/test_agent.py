"""AI-менеджер выполняет задачу шагами сам: модель выбирает инструменты и доводит до результата."""
import json, sys, tempfile
from datetime import datetime, timedelta
from pathlib import Path

APP = Path(__file__).resolve().parents[2] / "AI_SMM_Work_Architecture_A75"
sys.path.insert(0, str(APP))

from ai_core import AGENT_STEPS, AICore, LLMResult, review_badge
from data_manager import DataManager


def ok(name, cond, extra=""):
    print(("AGENT_OK " if cond else "AGENT_FAIL ") + name + ("" if cond else f" :: {extra}"))
    if not cond:
        raise SystemExit(1)


class Stage:
    """Подставная модель: агентские шаги из сценария, остальное — как обычная LLM."""

    name = "stub"

    def __init__(self, script, agent=None):
        self.script = list(script)
        self.calls = []
        self.formats = []
        self.agent_calls = 0
        # со сценарием — это шаги агента; без сценария модель шаги не ведёт (как слабая)
        self.agent = bool(script) if agent is None else agent

    def available(self):
        return True

    def chat(self, system, user, temperature=0.2, max_tokens=2048, fmt=""):
        self.calls.append(user)
        self.formats.append(fmt)
        low = user.lower()
        if "AI SMM Manager" in system and self.agent:
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


class Editor:
    """Модель-редактор: вердикты по подписям, без шагов агента."""

    name = "cloud"
    model = "editor-stub"

    def __init__(self, verdicts):
        self.verdicts = list(verdicts)
        self.calls = []

    def available(self):
        return True

    def chat(self, system, user, temperature=0.2, max_tokens=2048):
        self.calls.append((system, user))
        text = (self.verdicts.pop(0) if self.verdicts
                else json.dumps({"approved": True, "text": "", "note": ""}, ensure_ascii=False))
        return LLMResult(text=text, provider=self.name, model=self.model)


class Dead:
    """Провайдер, которого нет: поведение без модели не зависит от машины."""

    name = "stub"
    calls = []
    formats = []
    agent_calls = 0

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
ok("несколько шагов", len(stub.calls) >= 3, len(stub.calls))
ok("стратегия создана", len(dm.get_strategy().get("sections") or []) == 2,
   dm.get_strategy())
plan = dm.get_content_plan()
ok("план создан", len(plan) == 3, len(plan))
ok("пачка подписей спрашивает «да/нет»", reply.needs_confirmation, reply.text)
ok("в вопросе сколько подписей и каких",
   "3 шт." in reply.text and "Три сорта утреннего фильтра" in reply.text, reply.text)
ok("до «да» подписей нет",
   not any(str(item.get("caption") or "").strip() for item in plan),
   [(item.get("topic"), item.get("caption")) for item in plan])
ok("до «да» действия задачи видны", len(reply.actions or []) >= 2, len(reply.actions or []))
reply = core.handle("да")
plan = dm.get_content_plan()
ok("подписи у всех постов", all(str(item.get("caption") or "").strip() for item in plan),
   [(item.get("topic"), item.get("caption")) for item in plan])
tools = [entry["tool"] for entry in core.journal.list(20)]
ok("шаги в журнале", {"create_strategy", "create_content_plan", "write_captions"} <= set(tools),
   tools)
ok("после «да» задача дошла до проверки сама, без новой фразы",
   "план проверен" in reply.text and not stub.script, (reply.text, stub.script))
ok("продолжение осталось агентским ответом", reply.layer == "agent", reply.layer)

# --- «нет» на пачку подписей не запускает продолжение ---
dm, core, stub = build([
    '{"action": "tool", "tool": "create_content_plan", "args": {"count": 2}}',
    '{"action": "tool", "tool": "write_captions", "args": {}}',
])
reply = core.handle("подготовь контент")
ok("пачка подписей ждёт ответа", reply.needs_confirmation, reply.text)
ok("прерванная задача запомнена", core.resume_task != "", core.resume_task)
calls_before = len(stub.calls)
reply = core.handle("нет")
ok("«нет» не продолжает задачу и не пишет подписи",
   core.resume_task == ""
   and not any(str(item.get("caption") or "").strip() for item in dm.get_content_plan()),
   (core.resume_task, reply.text))
ok("«нет» не зовёт модель ещё раз", len(stub.calls) == calls_before,
   stub.calls[calls_before:])

# --- продолжение не повторяет уже сделанные шаги ---
class RepeatAware(Stage):
    """Модель, которая повторила бы создание плана, если бы ей не сказали, что уже сделано."""

    def __init__(self):
        super().__init__(['{"action": "tool", "tool": "create_content_plan", '
                          '"args": {"count": 2}}',
                          '{"action": "tool", "tool": "write_captions", "args": {}}'])
        self.repeats = 0

    def chat(self, system, user, temperature=0.2, max_tokens=2048, fmt=""):
        if "AI SMM Manager" in system and "Пользователь подтвердил" in user:
            done = user.split("Уже сделано:")[-1].split("Доступные инструменты:")[0]
            if "create_content_plan" not in done:
                self.repeats += 1
                text = '{"tool": "create_content_plan", "args": {"count": 2}}'
            else:
                text = '{"action": "done", "say": "Готово: план и подписи."}'
            return LLMResult(text=text, provider=self.name, model="stub")
        return super().chat(system, user, temperature, max_tokens, fmt)


dm = DataManager("agent", tempfile.mkdtemp(prefix="agent_"))
stage = RepeatAware()
core = AICore(dm, {"monthly_budget_usd": 0},
              app_db_path=Path(tempfile.mkdtemp(prefix="agent_db_")) / "app.db",
              providers=(stage, None))
reply = core.handle("подготовь контент")
plan_ids_before = [str(item.get("id")) for item in dm.get_content_plan()]
ok("план создан до вопроса", len(plan_ids_before) == 2, plan_ids_before)
ok("пачка подписей ждёт ответа", reply.needs_confirmation, reply.text)
ok("сделанные шаги переданы продолжению",
   any("create_content_plan" in step for step in core.resume_steps), core.resume_steps)
reply = core.handle("да")
plan_after = dm.get_content_plan()
ok("продолжение не создало план заново",
   [str(item.get("id")) for item in plan_after] == plan_ids_before,
   [str(item.get("id")) for item in plan_after])
ok("модель не попросила повторить создание плана", stage.repeats == 0, stage.repeats)
ok("подписи написаны и итог сказан",
   all(str(item.get("caption") or "").strip() for item in plan_after)
   and "Готово" in reply.text,
   (reply.text, [item.get("caption") for item in plan_after]))
ok("после продолжения задача снята с ожидания",
   core.resume_task == "" and core.resume_steps == [] and core.resume_pending == [],
   (core.resume_task, core.resume_steps, core.resume_pending))

# --- раннее «готово» после «да» не оставляет план без ТЗ и проверки ---
class EarlyDone(Stage):
    """Модель, которая после «да» сразу говорит «готово», не доделав ТЗ."""

    def __init__(self):
        super().__init__(['{"action": "tool", "tool": "create_content_plan", '
                          '"args": {"count": 2}}',
                          '{"action": "tool", "tool": "write_captions", "args": {}}'])

    def chat(self, system, user, temperature=0.2, max_tokens=2048, fmt=""):
        if "AI SMM Manager" in system and "Пользователь подтвердил" in user:
            return LLMResult(text='{"action": "done", "say": "Готово: подписи."}',
                             provider=self.name, model="stub")
        return super().chat(system, user, temperature, max_tokens, fmt)


dm = DataManager("agent", tempfile.mkdtemp(prefix="agent_"))
stage = EarlyDone()
core = AICore(dm, {"monthly_budget_usd": 0},
              app_db_path=Path(tempfile.mkdtemp(prefix="agent_db_")) / "app.db",
              providers=(stage, None))
reply = core.handle("подготовь контент")
plan_before = [str(item.get("id")) for item in dm.get_content_plan()]
ok("пачка подписей ждёт ответа перед ранним «готово»", reply.needs_confirmation, reply.text)
ok("незакрытые позиции переданы продолжению",
   len(core.resume_pending) == 2, core.resume_pending)
reply = core.handle("да")
plan_after = dm.get_content_plan()
ok("план не задвоен и после раннего «готово»",
   [str(item.get("id")) for item in plan_after] == plan_before, plan_before)
ok("подписи написаны", all(str(item.get("caption") or "").strip() for item in plan_after),
   [item.get("caption") for item in plan_after])
ok("раннее «готово» не оставило план без ТЗ",
   all(item.get("shooting_task_id") for item in plan_after),
   [(item.get("topic"), item.get("shooting_task_id")) for item in plan_after])
ok("проверка плана доделана после продолжения",
   "Проверка плана" in reply.text, reply.text)
ok("сказано, что доделал сам", "Довёл до конца сам" in reply.text, reply.text)
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

# --- dry-run публикации: проверка не оставляет записи об изменении ---
class FakeTokenStore:
    def load_token(self):
        return "IGAA-test"


dm, core, stub = build([])
dm._data["media_ready"].append({"id": "m1", "name": "p.jpg", "type": "image",
                                "path": "/nope/p.jpg", "status": "approved",
                                "remote_url": "https://res.cloudinary.com/demo/p.jpg"})
dm.save()
import instagram_auth
orig_access, orig_limit = instagram_auth.check_access, instagram_auth.publishing_limit
instagram_auth.check_access = lambda token: {"ok": True, "ig_user_id": "1789", "username": "studio"}
instagram_auth.publishing_limit = lambda token, ig_user_id: {"left": 5, "total": 50, "used": 45}
core.tools.tokens = FakeTokenStore()
out = core.tools.instagram_publish("m1")
ok("dry-run публикации ничего не меняет",
   out["effect"] == {} and out["undo"] == {}, out)
before = len(core.journal.list(50))
reply = core.run_tool("instagram_publish", media_id="m1")
ok("dry-run публикации говорит, что публикация не запущена",
   "не запущена" in reply.text, reply.text)
ok("dry-run публикации не оставляет записи в журнале",
   len(core.journal.list(50)) == before,
   [entry["tool"] for entry in core.journal.list(50)])
ok("dry-run не ставит отметку публикации",
   "published_id" not in dm.get_media_ready()[0]
   and "published" not in dm.get_media_ready()[0].get("processed", []),
   dm.get_media_ready()[0])
instagram_auth.check_access, instagram_auth.publishing_limit = orig_access, orig_limit

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
ok("правило, а не шаги агента", stub.agent_calls == 0, stub.agent_calls)


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
ok("пачка подписей спрашивает «да/нет», а не пишет молча",
   reply.needs_confirmation and "2 шт." in reply.text, reply.text)
ok("до «да» подписей нет",
   plan and not any(str(item.get("caption") or "").strip() for item in plan),
   [(item.get("topic"), item.get("caption")) for item in plan])
ok("модели сказано, что задача не закончена",
   any("подписей" in text and "write_captions" in text for text in stub.calls),
   stub.calls[-3:-1])
reply = core.handle("да")
plan = dm.get_content_plan()
ok("после «да» агент дописал подписи",
   plan and all(str(item.get("caption") or "").strip() for item in plan),
   [(item.get("topic"), item.get("caption")) for item in plan])
ok("после «да» агент сам сделал ТЗ, без отдельной фразы",
   plan and all(item.get("shooting_task_id") for item in plan),
   [(item.get("topic"), item.get("shooting_task_id")) for item in plan])
ok("итог после «да» называет план, подписи и ТЗ", "ТЗ" in reply.text, reply.text)
ok("продолжение задачи видно в журнале",
   {"write_captions", "create_shooting_task"}
   <= {entry["tool"] for entry in core.journal.list(10)},
   [entry["tool"] for entry in core.journal.list(10)])
ok("«нет» в следующий раз не запустит продолжение", core.resume_task == "",
   core.resume_task)

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

# --- доделка не переписывает старые посты ---
dm, core, stub = build([
    '{"action": "tool", "tool": "create_content_plan", "args": {"count": 2}}',
    '{"action": "done", "say": "План готов."}',
    '{"action": "done", "say": "План готов."}'])
old_id = dm.add_content_plan_item({"topic": "Старый пост про обжарку", "rubric": "Польза",
                                   "format": "Пост", "date": "05.01.2026",
                                   "caption": "Старая подпись, её менять нельзя."})
old_task = dm.create_shooting_task_from_content_plan(old_id)["id"]
reply = core.handle("добавь два поста в план")
old = dm.get_content_plan_item(old_id)
new_items = [item for item in dm.get_content_plan() if item.get("id") != old_id]
ok("старая подпись не переписана", old.get("caption") == "Старая подпись, её менять нельзя.",
   old.get("caption"))
ok("старое ТЗ не пересоздано", old.get("shooting_task_id") == old_task, old.get("shooting_task_id"))
ok("старое ТЗ осталось одно",
   len([task for task in dm.get_shooting_tasks()
        if task.get("content_plan_link") == old_id]) == 1,
   [task.get("id") for task in dm.get_shooting_tasks()])
ok("новые посты с подписями",
   new_items and all(str(item.get("caption") or "").strip() for item in new_items),
   [(item.get("topic"), item.get("caption")) for item in new_items])
ok("новые посты с ТЗ",
   new_items and all(item.get("shooting_task_id") for item in new_items),
   [(item.get("topic"), item.get("shooting_task_id")) for item in new_items])
ok("итог говорит только о новых позициях",
   f"Из {len(new_items)} новых позиций" in reply.text, reply.text)

# --- правило: «нужно N постов» делает позиции сразу с подписями и ТЗ ---
dm, core, stub = build([])
reply = core.handle("нужно 5 постов для инстаграма")
plan = dm.get_content_plan()
ok("правило создало пять позиций", len(plan) == 5, len(plan))
ok("правило написало подписи",
   plan and all(str(item.get("caption") or "").strip() for item in plan),
   [(item.get("topic"), item.get("caption")) for item in plan])
ok("правило создало ТЗ", plan and all(item.get("shooting_task_id") for item in plan),
   [(item.get("topic"), item.get("shooting_task_id")) for item in plan])
ok("итог правила — про новые позиции", "Из 5 новых позиций" in reply.text, reply.text)
ok("правило не спросило модель про шаги", stub.agent_calls == 0, stub.agent_calls)
ok("в журнале план, подписи и ТЗ",
   {"create_content_plan", "write_captions", "create_shooting_task"}
   <= {entry["tool"] for entry in core.journal.list(50)},
   [entry["tool"] for entry in core.journal.list(50)])

# --- фразы про календарь, выгрузку и пакет не уходят в правило «N постов» ---
for text, expected in [
        ("добавь 5 постов в календарь", "sync_plan_events"),
        ("синхронизируй 5 постов с календарём", "sync_plan_events"),
        ("подготовь 5 постов к выгрузке", "export_package"),
        ("собери 5 постов в пакет для инстаграма", "instagram_pack")]:
    decision = core.router._rules(text)
    ok(f"«{text}» — не создание новых постов",
       decision is not None and decision.tool == expected,
       getattr(decision, "tool", None))
for text, count in [("нужно 5 постов для инстаграма", 5), ("добавь 3 поста в план", 3)]:
    decision = core.router._rules(text)
    ok(f"«{text}» — новый цикл постов",
       decision is not None and decision.tool == "create_post_cycle"
       and decision.args.get("count") == count,
       (getattr(decision, "tool", None), getattr(decision, "args", None)))

# --- календарная фраза не плодит дубли, а расставляет существующие ---
dm, core, stub = build([])
for day in range(1, 6):
    dm.add_content_plan_item({"topic": f"Пост {day}", "rubric": "Польза", "format": "Пост",
                              "date": f"{day:02d}.02.2026"})
seeded = len(dm.get_content_plan())
events_before = len(dm.get_calendar_events())
reply = core.handle("добавь 5 постов в календарь")
ok("раскладка по календарю спрашивает «да/нет»", reply.needs_confirmation, reply.text)
ok("в вопросе сколько новых событий", "новых событий: 5" in reply.text, reply.text)
ok("до «да» календарь не тронут",
   len(dm.get_calendar_events()) == events_before, dm.get_calendar_events())
reply = core.handle("да")
ok("календарная фраза не создала дубли", len(dm.get_content_plan()) == seeded,
   f"{seeded} → {len(dm.get_content_plan())}")
ok("календарная фраза расставила события",
   len(dm.get_calendar_events()) > events_before,
   f"{events_before} → {len(dm.get_calendar_events())}")
ok("итог календарной фразы — про перенос, а не про создание",
   "план" in (reply.text or "").lower() or "календар" in (reply.text or "").lower(),
   reply.text)

# --- обычные фразы SMM-специалиста: решает правило, без модели ---
def seeded_plan(count=3):
    dm, core, stub = build([])
    for day in range(1, count + 1):
        dm.add_content_plan_item({"topic": f"Пост {day}", "rubric": "Польза", "format": "Пост",
                                  "date": f"{day:02d}.04.2027"})
    return dm, core, stub


dm, core, stub = seeded_plan()
for text, tool in [
        ("поставь посты на следующую неделю", "schedule_posts"),
        ("перенеси посты на следующую неделю", "schedule_posts"),
        ("подготовь ТЗ на съёмку", "create_shooting_task"),
        ("распечатай стратегию", "export_pdf"),
        ("поставь хештеги к посту", "write_captions"),
        ("убери последний пост из плана", "delete_record"),
        ("добавь пост про латте", "create_content_plan"),
        ("что зашло за месяц", "analyze_performance")]:
    decision = core.router._rules(text)
    ok(f"«{text}» — {tool}", decision is not None and decision.tool == tool,
       getattr(decision, "tool", None))
ok("частотные фразы делает правило, а не шаги агента",
   stub.agent_calls == 0, stub.agent_calls)
ok("аналитика за месяц — 30 дней",
   core.router._rules("что зашло за месяц").args.get("period_days") == 30)
ok("аналитика за квартал — 90 дней",
   core.router._rules("что зашло за квартал").args.get("period_days") == 90)

# --- «поставь посты на следующую неделю» реально меняет даты ---
dm, core, stub = seeded_plan()
reply = core.handle("поставь посты на следующую неделю")
ok("недельная фраза выполнена сразу",
   not reply.needs_confirmation and "Запланировал" in reply.text, reply.text)
dates = [str(item.get("date")) for item in dm.get_content_plan()]
ok("посты перенесены на следующую неделю",
   all(date not in ("01.04.2027", "02.04.2027", "03.04.2027") for date in dates), dates)
ok("после переноса статус — запланировано",
   all(item.get("status") == "Запланировано" for item in dm.get_content_plan()),
   [item.get("status") for item in dm.get_content_plan()])

dm, core, stub = seeded_plan(5)
reply = core.handle("перенеси посты на следующую неделю")
ok("пять постов — просит подтверждение", reply.needs_confirmation, reply.text)
core.handle("да")
ok("после «да» пять постов запланированы",
   all(item.get("status") == "Запланировано" for item in dm.get_content_plan()),
   [item.get("status") for item in dm.get_content_plan()])

# --- один пост по фразе: тема и дата из текста ---
dm, core, stub = build([])
core.handle("добавь пост про латте")
plan = dm.get_content_plan()
ok("«добавь пост про латте» — одна позиция", len(plan) == 1, plan)
ok("тема взята из фразы", "латте" in str(plan[0].get("topic")).lower(), plan[0].get("topic"))
dm, core, stub = build([])
core.handle("добавь пост на 3 марта про латте")
plan = dm.get_content_plan()
ok("дата из фразы стоит в позиции",
   len(plan) == 1 and str(plan[0].get("date")).startswith("03.03."), plan)

# --- «убери последний пост» удаляет именно его, но только после «да» ---
dm, core, stub = seeded_plan()
last_id = str(dm.get_content_plan()[-1]["id"])
reply = core.handle("убери последний пост из плана")
ok("удаление по фразе просит подтверждение", reply.needs_confirmation, reply.text)
last_item = dm.get_content_plan()[-1]
ok("в вопросе тема и дата, а не id",
   str(last_item["topic"]) in reply.text and str(last_item["date"]) in reply.text
   and last_id not in reply.text, reply.text)
ok("сырые аргументы в вопрос не попали",
   '"section"' not in reply.text and "item_id" not in reply.text, reply.text)
ok("до «да» ничего не удалено",
   len(dm.get_content_plan()) == 3, len(dm.get_content_plan()))
core.handle("нет")
ok("«нет» ничего не удаляет", len(dm.get_content_plan()) == 3, len(dm.get_content_plan()))
reply = core.handle("убери последний пост из плана")
ok("после «нет» фраза снова спрашивает", reply.needs_confirmation, reply.text)
core.handle("да")
ok("после «да» пост удалён из плана", len(dm.get_content_plan()) == 2,
   len(dm.get_content_plan()))
ok("удалён последний, а не первый",
   all(str(item["id"]) != last_id for item in dm.get_content_plan()))

# --- удаление берёт раздел из фразы, а не всегда контент-план ---
dm, core, stub = seeded_plan()
dm._data["calendar_events"] = [
    {"id": "ev_1", "date": "01.04.2027", "title": "Пост 1", "link": "cp_1"},
    {"id": "ev_2", "date": "02.04.2027", "title": "Пост 2", "link": "cp_2"}]
dm._data["shooting_tasks"] = [{"id": "st_1", "plan_id": "cp_1", "title": "ТЗ 1"}]
dm.save()
reply = core.handle("удали пост из календаря")
ok("удаление из календаря ждёт подтверждения",
   len(dm.get_calendar_events()) == 2, dm.get_calendar_events())
ok("в вопросе календаря название и дата события",
   "Пост 2" in reply.text and "02.04.2027" in reply.text and "ev_2" not in reply.text,
   reply.text)
core.handle("да")
ok("удаление из календаря не трогает план",
   len(dm.get_content_plan()) == 3, len(dm.get_content_plan()))
ok("удаление из календаря убрало событие",
   len(dm.get_calendar_events()) == 1, dm.get_calendar_events())
core.handle("удали ТЗ")
core.handle("да")
ok("удаление ТЗ не трогает план",
   len(dm.get_content_plan()) == 3 and not dm.get_shooting_tasks(),
   (len(dm.get_content_plan()), dm.get_shooting_tasks()))
core.handle("удали пост из плана")
core.handle("да")
ok("удаление из плана убрало позицию", len(dm.get_content_plan()) == 2,
   len(dm.get_content_plan()))
decision = core.router._rules("удали запись")
ok("непонятный раздел — уточняет, а не удаляет",
   decision is not None and not decision.tool and "Уточни" in (decision.clarify or ""),
   getattr(decision, "clarify", None))

# --- публикации, медиа и стратегия: чтение и действия правилами ---
dm, core, stub = seeded_plan()
core.run_tool("create_strategy", brief="кофейня", sections=[
    {"id": "s1", "title": "Аудитория", "content": "Город 25–40."},
    {"id": "s2", "title": "Позиционирование", "content": "Своя обжарка."}])
dm._data["other_files"] = {"Материалы": [{"id": "mat_1", "name": "p1.jpg"}]}
dm._data["media_ready"].append({"id": "m1", "name": "p1.jpg", "type": "image",
                                "path": "/nope/p1.jpg", "status": "approved"})
dm.save()
for text, tool, scope in [
        ("покажи материалы", "get_project_context", "media"),
        ("что готово к публикации", "get_project_context", "media"),
        ("какие блоки в стратегии", "get_project_context", "strategy"),
        ("какие у нас kpi", "get_project_context", "strategy"),
        ("выложи материал m1 на публичный url", "host_media", None),
        ("обнови kpi: охват 5000", "update_kpis", None),
        ("убери материал mat_1 из списка", "delete_material", None),
        ("сожми фото до 1080", "batch_photo", None),
        ("обрежь фотографии под квадрат", "batch_photo", None)]:
    decision = core.router._rules(text)
    ok(f"«{text}» — {tool}",
       decision is not None and decision.tool == tool
       and (scope is None or decision.args.get("scope") == scope),
       getattr(decision, "tool", None))
ok("чтение медиа и стратегии — правилом, а не шагами агента",
   stub.agent_calls == 0, stub.agent_calls)
reply = core.handle("покажи материалы")
ok("чтение материалов даёт список", "Материалов готовых" in reply.text, reply.text)
reply = core.handle("какие блоки в стратегии")
ok("чтение стратегии называет блоки", "Аудитория" in reply.text, reply.text)
reply = core.handle("обнови kpi: охват 5000")
ok("обновление KPI сначала спрашивает «да/нет»", reply.needs_confirmation, reply.text)
ok("в вопросе KPI: было/станет и новое значение",
   "было строк" in reply.text and "5000" in reply.text
   and "заменены" in reply.text, reply.text)
ok("до «да» KPI не тронуты",
   not ((dm.get_strategy() or {}).get("kpis") or []),
   (dm.get_strategy() or {}).get("kpis"))
reply = core.handle("да")
kpis = (dm.get_strategy() or {}).get("kpis") or []
ok("KPI обновлены из фразы",
   any(str(row.get("current")) == "5000" for row in kpis), kpis)
reply = core.handle("убери материал mat_1 из списка")
ok("удаление материала просит подтверждение",
   reply.needs_confirmation and bool(dm.get_other_files().get("Материалы")), reply.text)
ok("в вопросе материала имя файла, а не id",
   "p1.jpg" in reply.text and "mat_1" not in reply.text, reply.text)
core.handle("да")
ok("после «да» материал убран из «Материалов»",
   not dm.get_other_files().get("Материалы"), dm.get_other_files())
decision = core.router._rules("перепиши блок аудитория")
ok("правка блока без текста — спрашивает текст",
   decision is not None and not decision.tool and "Аудитория" in (decision.clarify or ""),
   getattr(decision, "clarify", None))
reply = core.handle("перепиши блок аудитория на город 25–40, кофе домой")
ok("правка блока стратегии сначала спрашивает «да/нет»", reply.needs_confirmation, reply.text)
ok("в вопросе название блока и начало нового текста",
   "Аудитория" in reply.text and "город 25–40" in reply.text
   and "заменится" in reply.text, reply.text)
before_block = str(dm.get_strategy_section_by_id("s1").get("content") or "")
ok("до «да» текст блока прежний", before_block == "Город 25–40.", before_block)
reply = core.handle("да")
after_block = str(dm.get_strategy_section_by_id("s1").get("content") or "")
ok("после «да» блок переписан",
   "город 25–40" in after_block and after_block != before_block, after_block)
reply = core.run_tool("update_strategy_section", section_id="s1", content="Своя обжарка и точка.")
ok("путь окна переписывает блок без второго вопроса",
   not reply.needs_confirmation
   and dm.get_strategy_section_by_id("s1")["content"] == "Своя обжарка и точка.", reply.text)
reply = core.run_tool("update_kpis", kpis=[{"metric": "Охват", "current": "1", "target": "2"}])
ok("путь окна пишет KPI без второго вопроса",
   not reply.needs_confirmation
   and len((dm.get_strategy() or {}).get("kpis") or []) == 1, reply.text)
for text in ("добавь раздел в стратегию про конкурентов",
             "удали блок стратегии про конкурентов",
             "перемести материал m1 в папку рилс"):
    decision = core.router._rules(text)
    ok(f"«{text}» — честное объяснение, а не «Не понял»",
       decision is not None and not decision.tool and bool(decision.clarify),
       getattr(decision, "clarify", None))

# --- третий обмер: профиль на чтение, номер поста, проверка подписей, Excel ---
dm, core, stub = seeded_plan()
dm.save_brand_profile({"client_name": "Кофейня «Каз»", "niche": "кофе домой",
                       "tone_of_voice": "дружелюбный"})
decision = core.router._rules("покажи бренд-профиль")
ok("«покажи бренд-профиль» — чтение, а не интервью",
   decision is not None and decision.tool == "get_project_context"
   and decision.args.get("scope") == "profile", getattr(decision, "tool", None))
reply = core.handle("покажи бренд-профиль")
ok("чтение профиля показывает поля и не начинает интервью",
   "Кофейня «Каз»" in reply.text and "Как называется клиент" not in reply.text, reply.text)
decision = core.router._rules("заполни бренд-профиль заново")
ok("«заполни бренд-профиль заново» — по-прежнему интервью",
   decision is not None and decision.tool == "brand_profile_interview",
   getattr(decision, "tool", None))

dm, core, stub = seeded_plan()
plan_ids = [str(item["id"]) for item in dm.get_content_plan()]
decision = core.router._rules("перепиши подпись второго поста короче")
ok("«второго поста» — вторая позиция, а не последняя",
   decision is not None and decision.tool == "write_captions"
   and decision.args.get("plan_id") == plan_ids[1], getattr(decision, "args", None))
reply = core.handle("перепиши подпись второго поста короче")
plan = dm.get_content_plan()
ok("подпись получил второй пост, первый не тронут",
   bool(plan[1].get("caption")) and not plan[0].get("caption"),
   [item.get("caption") for item in plan])
decision = core.router._rules("убери вторую позицию из плана")
ok("порядковый номер работает и при удалении",
   decision is not None and decision.tool == "delete_record"
   and decision.args.get("item_id") == plan_ids[1], getattr(decision, "args", None))

dm, core, stub = seeded_plan()
decision = core.router._rules("проверь, все ли посты с подписями")
ok("«проверь, все ли посты с подписями» — validate_plan",
   decision is not None and decision.tool == "validate_plan", getattr(decision, "tool", None))
reply = core.handle("проверь, все ли посты с подписями")
ok("проверка подписей считает позиции без подписи",
   "без подписи" in reply.text and "3 из 3" in reply.text, reply.text)

dm, core, stub = seeded_plan()
decision = core.router._rules("экспортируй план в excel")
ok("«экспортируй план в excel» — честный отказ",
   decision is not None and not decision.tool and "Excel" in (decision.clarify or ""),
   getattr(decision, "clarify", None))
reply = core.handle("экспортируй план в excel")
ok("Excel не уходит в пакет и не просит подтверждения",
   not reply.needs_confirmation and "PDF" in reply.text, reply.text)
ok("фразы третьего обмера — правилом, а не шагами агента",
   stub.agent_calls == 0, stub.agent_calls)

# --- четвёртый обмер: ближайшие посты, «завтра», смена даты, «в план пост про …» ---
dm, core, stub = seeded_plan()
decision = core.router._rules("покажи ближайшие посты")
ok("«покажи ближайшие посты» — чтение плана без действий",
   decision is not None and decision.tool == "get_project_context"
   and decision.args.get("scope") == "upcoming", getattr(decision, "tool", None))
reply = core.handle("покажи ближайшие посты")
ok("ближайшие посты: дата, тема и статус",
   "01.04.2027" in reply.text and "Пост 1" in reply.text and "Ближайшие посты" in reply.text,
   reply.text)

tomorrow = (datetime.now().date() + timedelta(days=1)).strftime("%d.%m.%Y")
far = (datetime.now().date() + timedelta(days=10)).strftime("%d.%m.%Y")
dm, core, stub = build([])
dm.add_content_plan_item({"topic": "Завтрашний пост", "rubric": "Польза", "format": "Пост",
                          "date": tomorrow})
dm.add_content_plan_item({"topic": "Дальний пост", "rubric": "Польза", "format": "Пост",
                          "date": far})
decision = core.router._rules("что выходит завтра")
ok("«что выходит завтра» — дата завтра в аргументах",
   decision is not None and decision.args.get("date") == tomorrow,
   getattr(decision, "args", None))
reply = core.handle("что выходит завтра")
ok("в ответе только завтрашний пост",
   "Завтрашний пост" in reply.text and "Дальний пост" not in reply.text, reply.text)

dm, core, stub = seeded_plan()
plan_ids = [str(item["id"]) for item in dm.get_content_plan()]
dm._data["calendar_events"] = [{"id": "ev_1", "date": "01.04.2027",
                                "title": "Пост 1", "link": plan_ids[0]}]
dm.save()
decision = core.router._rules("измени дату поста на 5 декабря")
ok("«измени дату поста на 5 декабря» — edit_record по плану",
   decision is not None and decision.tool == "edit_record"
   and decision.args.get("section") == "content_plan"
   and str(decision.args.get("fields", {}).get("date") or "").startswith("05.12."),
   getattr(decision, "args", None))
new_date = str((decision.args or {}).get("fields", {}).get("date") or "")
ok("без номера берётся ближайшая будущая позиция, а не последняя",
   decision.args.get("item_id") == plan_ids[0], getattr(decision, "args", None))
reply = core.handle("измени дату поста на 5 декабря")
ok("смена даты сначала спрашивает «да/нет»", reply.needs_confirmation, reply.text)
ok("до «да» дата прежняя",
   str(dm.get_content_plan()[0]["date"]) == "01.04.2027", dm.get_content_plan()[0])
reply = core.handle("да")
dates = [str(item.get("date")) for item in dm.get_content_plan()]
ok("дата изменена у одной позиции, остальные не тронуты",
   dates == [new_date, "02.04.2027", "03.04.2027"], dates)
ok("ответ называет новую дату", new_date in reply.text, reply.text)
ok("событие календаря переехало вместе с датой",
   str(dm.get_calendar_events()[0].get("date")) == new_date, dm.get_calendar_events())
decision = core.router._rules("измени дату второго поста на 5 декабря")
ok("порядковый номер работает и при смене даты",
   decision is not None and decision.args.get("item_id") == plan_ids[1],
   getattr(decision, "args", None))
decision = core.router._rules("перенеси пост на завтра")
ok("«перенеси пост на завтра» — смена даты, а не чтение ближайших",
   decision is not None and decision.tool == "edit_record"
   and decision.args.get("fields", {}).get("date") == tomorrow,
   getattr(decision, "tool", None))

# --- «перенеси пост на завтра» реально двигает ближайшую позицию ---
dm, core, stub = seeded_plan()
move_ids = [str(item["id"]) for item in dm.get_content_plan()]
reply = core.handle("перенеси пост на завтра")
ok("перенос даты тоже спрашивает «да/нет»", reply.needs_confirmation, reply.text)
ok("до «да» даты прежние",
   [str(item.get("date")) for item in dm.get_content_plan()]
   == ["01.04.2027", "02.04.2027", "03.04.2027"],
   [item.get("date") for item in dm.get_content_plan()])
reply = core.handle("да")
dates = [str(item.get("date")) for item in dm.get_content_plan()]
ok("завтрашняя дата встала в ближайшую позицию",
   dates == [tomorrow, "02.04.2027", "03.04.2027"], dates)
ok("ответ называет новую дату", tomorrow in reply.text, reply.text)
ok("«перенеси пост на завтра» — правилом, а не шагами агента",
   stub.agent_calls == 0, stub.agent_calls)
ok("перенос даты можно отменить", any(entry["tool"] == "edit_record"
                                      for entry in core.journal.list(10)), core.journal.list(10))

# --- номер важнее порядка: явная дата и номер адресуют свою позицию ---
dm, core, stub = seeded_plan()
order_ids = [str(item["id"]) for item in dm.get_content_plan()]
decision = core.router._rules("перенеси третий пост на завтра")
ok("номер сильнее «ближайшей» при переносе",
   decision is not None and decision.args.get("item_id") == order_ids[2],
   getattr(decision, "args", None))

# --- полная дата дд.мм.гггг понимается правилом смены даты ---
dm, core, stub = seeded_plan()
full_ids = [str(item["id"]) for item in dm.get_content_plan()]
decision = core.router._rules("перенеси пост на 05.12.2026")
ok("полная дата дд.мм.гггг не превращается в вопрос",
   decision is not None and decision.tool == "edit_record"
   and decision.args.get("fields", {}).get("date") == "05.12.2026",
   getattr(decision, "args", None))
ok("полная дата двигает ближайшую будущую позицию",
   decision is not None and decision.args.get("item_id") == full_ids[0],
   getattr(decision, "args", None))
core.handle("перенеси пост на 05.12.2026")
reply = core.handle("да")
dates = [str(item.get("date")) for item in dm.get_content_plan()]
ok("дата дд.мм.гггг записана в позицию",
   dates == ["05.12.2026", "02.04.2027", "03.04.2027"], dates)
ok("ответ называет дату из фразы, модель не тронута",
   "05.12.2026" in reply.text and stub.agent_calls == 0, (reply.text, stub.agent_calls))
decision = core.router._rules("перенеси пост на 02.04.2027")
ok("дата из фразы адресует позицию",
   decision is not None and decision.args.get("item_id") == full_ids[1],
   getattr(decision, "args", None))
decision = core.router._rules("измени дату поста на 01.06.2027")
ok("полная дата работает и в «измени дату»",
   decision is not None and decision.args.get("fields", {}).get("date") == "01.06.2027",
   getattr(decision, "args", None))
broken = core.router._rules("перенеси пост на 31.02.2027")
ok("несуществующая дата — вопрос, а не выдумка",
   broken is not None and not broken.tool and "дату" in (broken.clarify or ""),
   getattr(broken, "clarify", None))

# --- названная дата уже стоит: менять нечего, а не «Обновил» ---
dm, core, stub = seeded_plan()
before_dates = [str(item.get("date")) for item in dm.get_content_plan()]
decision = core.router._rules("измени дату поста на 02.04.2027")
ok("та же дата — всё равно edit_record по нужной позиции",
   decision is not None and decision.tool == "edit_record",
   getattr(decision, "tool", None))
reply = core.handle("измени дату поста на 02.04.2027")
ok("та же дата — лишнего вопроса нет", not reply.needs_confirmation, reply.text)
ok("та же дата — ответ «менять нечего», а не «Обновил»",
   "Менять нечего" in reply.text and "Обновил" not in reply.text, reply.text)
ok("даты после такой фразы не изменились",
   [str(item.get("date")) for item in dm.get_content_plan()] == before_dates,
   dm.get_content_plan())

# --- правка записи: вопрос до записи, «нет» ничего не меняет ---
dm, core, stub = seeded_plan()
target_id = str(dm.get_content_plan()[0]["id"])
dm._data["content_plan"][0]["caption"] = "Старая подпись"
dm.save()
EDIT = {"section": "content_plan", "item_id": target_id,
        "fields": {"caption": "Новая подпись"}}
reply = core._execute("edit_record", EDIT, "rules")
ok("правка записи сначала спрашивает «да/нет»", reply.needs_confirmation, reply.text)
ok("в вопросе запись, поле и новое значение словами",
   "Пост 1" in reply.text and "подпись" in reply.text
   and "Новая подпись" in reply.text, reply.text)
ok("до «да» подпись прежняя",
   dm.get_content_plan()[0]["caption"] == "Старая подпись", dm.get_content_plan()[0])
reply = core.handle("нет")
ok("«нет» оставляет текст прежним и снимает вопрос",
   dm.get_content_plan()[0]["caption"] == "Старая подпись"
   and not reply.needs_confirmation and core.pending is None,
   (dm.get_content_plan()[0], reply.text))
core._execute("edit_record", EDIT, "rules")
reply = core.handle("да")
ok("после «да» правка записана и попала в журнал",
   dm.get_content_plan()[0]["caption"] == "Новая подпись"
   and any(entry["tool"] == "edit_record" for entry in core.journal.list(5)),
   (dm.get_content_plan()[0], [entry["tool"] for entry in core.journal.list(5)]))
reply = core.run_tool("edit_record", section="content_plan", item_id=target_id,
                      fields={"date": "06.12.2027"})
ok("путь окна пишет без второго вопроса",
   not reply.needs_confirmation
   and str(dm.get_content_plan()[0]["date"]) == "06.12.2027", reply.text)

# --- «что писать завтра» и «сделай календарь на месяц» ---
dm, core, stub = build([])
dm.add_content_plan_item({"topic": "Завтрашний пост", "rubric": "Польза", "format": "Пост",
                          "date": tomorrow})
decision = core.router._rules("что писать завтра")
ok("«что писать завтра» — чтение плана на завтра",
   decision is not None and decision.tool == "get_project_context"
   and decision.args.get("scope") == "upcoming"
   and decision.args.get("date") == tomorrow, getattr(decision, "args", None))
reply = core.handle("что писать завтра")
ok("в ответе пост на завтра и пометка об отсутствии подписи",
   "Завтрашний пост" in reply.text and "без подписи" in reply.text, reply.text)
ok("«что писать завтра» — правилом, а не шагами агента",
   stub.agent_calls == 0, stub.agent_calls)

dm, core, stub = seeded_plan()
decision = core.router._rules("сделай календарь на месяц")
ok("«сделай календарь на месяц» — события из плана",
   decision is not None and decision.tool == "sync_plan_events",
   getattr(decision, "tool", None))
reply = core.handle("сделай календарь на месяц")
ok("«сделай календарь на месяц» спрашивает «да/нет»", reply.needs_confirmation, reply.text)
ok("до «да» событий нет", not dm.get_calendar_events(), dm.get_calendar_events())
reply = core.handle("да")
ok("события календаря созданы по датам плана",
   len(dm.get_calendar_events()) == 3, dm.get_calendar_events())
ok("ответ говорит, сколько событий пришло из плана", "Из плана" in reply.text, reply.text)
ok("«сделай календарь на месяц» — правилом, а не шагами агента",
   stub.agent_calls == 0, stub.agent_calls)

# --- «что писать» — только с днём или периодом ---
dm, core, stub = seeded_plan()
decision = core.router._rules("что писать в подписи к посту")
ok("«что писать в подписи к посту» — не ближайшие посты",
   decision is not None and decision.args.get("scope") != "upcoming",
   getattr(decision, "args", None))
ok("«что писать в подписи к посту» — это про подпись",
   decision is not None and decision.tool == "write_captions",
   getattr(decision, "tool", None))
decision = core.router._rules("что писать на этой неделе")
ok("«что писать на этой неделе» — ближайшие посты",
   decision is not None and decision.tool == "get_project_context"
   and decision.args.get("scope") == "upcoming", getattr(decision, "args", None))

# --- «напиши 3 идеи для сторис» ---
dm, core, stub = build([])
decision = core.router._rules("напиши 3 идеи для сторис")
ok("«идеи для сторис» — план формата Stories",
   decision is not None and decision.tool == "create_content_plan"
   and decision.args.get("count") == 3
   and decision.args.get("format") == "Stories", getattr(decision, "args", None))
reply = core.handle("напиши 3 идеи для сторис")
items = dm.get_content_plan()
ok("создано три позиции формата Stories",
   len(items) == 3 and all(item.get("format") == "Stories" for item in items),
   [(item.get("format"), item.get("topic")) for item in items])
ok("«идеи для сторис» — ответ о позициях плана",
   "контент-плана" in reply.text, reply.text)

# --- «сделай из поста рилс» и «подготовь сторис по посту» ---
dm, core, stub = seeded_plan()
source = dm.get_content_plan()[-1]
source_id = str(source["id"])
decision = core.router._rules("сделай из поста рилс")
ok("«сделай из поста рилс» — версия поста, а не новый пост с нуля",
   decision is not None and decision.tool == "adapt_post"
   and decision.args.get("plan_id") == source_id
   and decision.args.get("format") == "Reels", getattr(decision, "args", None))
reply = core.handle("сделай из поста рилс")
items = dm.get_content_plan()
made = items[-1]
ok("Reels-версия на ту же дату и с той же темой",
   len(items) == 4 and made.get("format") == "Reels"
   and made.get("topic") == source.get("topic") and made.get("date") == source.get("date"),
   [(item.get("date"), item.get("topic"), item.get("format")) for item in items])
ok("у Reels-версии есть ТЗ и ссылка на исходный пост",
   bool(made.get("shooting_task_id")) and made.get("based_on") == source_id
   and any(task.get("content_plan_link") == str(made["id"]) for task in dm.get_shooting_tasks()),
   (made.get("shooting_task_id"), made.get("based_on"), dm.get_shooting_tasks()))
ok("исходный пост не переписан",
   dm.get_content_plan_item(source_id).get("format") == "Пост"
   and not dm.get_content_plan_item(source_id).get("shooting_task_id"),
   dm.get_content_plan_item(source_id))
ok("ответ называет исходный пост, формат и ТЗ",
   "Reels" in reply.text and str(source.get("topic")) in reply.text and "ТЗ" in reply.text,
   reply.text)
ok("«сделай из поста рилс» — правилом, а не шагами агента",
   stub.agent_calls == 0, stub.agent_calls)
ok("версия попала в журнал и откатывается",
   any(entry["tool"] == "adapt_post" for entry in core.journal.list(10)),
   [entry["tool"] for entry in core.journal.list(10)])
core.undo(reply.actions[0]["id"])
ok("откат убирает версию и её ТЗ",
   len(dm.get_content_plan()) == 3 and not dm.get_shooting_tasks(),
   (len(dm.get_content_plan()), dm.get_shooting_tasks()))

dm, core, stub = seeded_plan()
source = dm.get_content_plan()[1]
decision = core.router._rules("сделай из второго поста рилс")
ok("номер выбирает исходный пост, а не последний",
   decision is not None and decision.args.get("plan_id") == str(source["id"]),
   getattr(decision, "args", None))

dm, core, stub = seeded_plan()
source = dm.get_content_plan()[-1]
decision = core.router._rules("подготовь сторис по посту")
ok("«подготовь сторис по посту» — Stories из поста",
   decision is not None and decision.tool == "adapt_post"
   and decision.args.get("plan_id") == str(source["id"])
   and decision.args.get("format") == "Stories", getattr(decision, "args", None))
reply = core.handle("подготовь сторис по посту")
made = dm.get_content_plan()[-1]
ok("сторис-версия: формат Stories, та же тема и дата",
   len(dm.get_content_plan()) == 4 and made.get("format") == "Stories"
   and made.get("topic") == source.get("topic") and made.get("date") == source.get("date"),
   [(item.get("date"), item.get("topic"), item.get("format")) for item in dm.get_content_plan()])
ok("в ответе про сторис сказано, что текст пустой",
   "Stories" in reply.text and "пустой" in reply.text, reply.text)
again = core.handle("подготовь сторис по посту")
ok("повтор фразы не создаёт второй дубль",
   len(dm.get_content_plan()) == 4 and "уже есть" in again.text,
   (len(dm.get_content_plan()), again.text))
ok("«подготовь сторис по посту» — правилом, а не шагами агента",
   stub.agent_calls == 0, stub.agent_calls)

dm, core, stub = build([])
decision = core.router._rules("подготовь сторис по посту")
ok("без постов — вопрос, а не выдумка",
   decision is not None and not decision.tool and "пост" in (decision.clarify or "").lower(),
   getattr(decision, "clarify", None))

# --- «сделай отчёт по плану» — счёт по плану без модели ---
dm, core, stub = seeded_plan()
decision = core.router._rules("сделай отчёт по плану")
ok("«сделай отчёт по плану» — plan_report",
   decision is not None and decision.tool == "plan_report", getattr(decision, "tool", None))
reply = core.handle("сделай отчёт по плану")
ok("отчёт называет количество позиций и даты",
   "позиций 3" in reply.text and "01.04.2027 — 1" in reply.text
   and "03.04.2027 — 1" in reply.text, reply.text)
ok("отчёт считает позиции без подписи и без ТЗ",
   "Без подписи: 3 из 3" in reply.text and "Без ТЗ: 3 из 3" in reply.text, reply.text)
ok("«сделай отчёт по плану» — правилом, а не шагами агента",
   stub.agent_calls == 0, stub.agent_calls)
ok("отчёт ничего не меняет в проекте",
   len(dm.get_content_plan()) == 3 and not core.journal.list(10),
   (len(dm.get_content_plan()), core.journal.list(10)))

dm, core, stub = build([])
done_id = dm.add_content_plan_item({"topic": "С подписью и ТЗ", "rubric": "Польза",
                                    "format": "Пост", "date": "01.04.2027",
                                    "caption": "Готовая подпись"})
dm.create_shooting_task_from_content_plan(done_id)
dm.add_content_plan_item({"topic": "Без подписи", "rubric": "Польза", "format": "Пост",
                          "date": "03.04.2027"})
dm.add_content_plan_item({"topic": "Без даты", "rubric": "Польза", "format": "Пост",
                          "date": ""})
reply = core.handle("сделай отчёт по плану")
ok("отчёт делит позиции на датированные и без даты",
   "позиций 3, с датой 2, без даты 1" in reply.text, reply.text)
ok("отчёт называет позиции без подписи по дате и теме",
   "Без подписи: 2 из 3 — 03.04.2027 «Без подписи», без даты «Без даты»" in reply.text,
   reply.text)
ok("отчёт называет позиции без ТЗ и не задевает готовую",
   "Без ТЗ: 2 из 3" in reply.text and "С подписью и ТЗ" not in reply.text,
   reply.text)
ok("отчёт не идёт шагами агента и не пишет в журнал",
   stub.agent_calls == 0 and not core.journal.list(10),
   (stub.agent_calls, core.journal.list(10)))

dm, core, stub = build([])
reply = core.handle("сделай отчёт по плану")
ok("отчёт по пустому плану — честный ответ, а не нули без слов",
   "план пуст" in reply.text, reply.text)

for text in ("сделай отчёт по стратегии", "собери отчёт по метрикам"):
    decision = core.router._rules(text)
    ok(f"«{text}» — не отчёт по плану",
       decision is None or decision.tool != "plan_report", getattr(decision, "tool", None))

# --- будущих позиций нет: двигаем последнюю, а не молчим ---
dm, core, stub = build([])
dm.add_content_plan_item({"topic": "Старый", "rubric": "Польза", "format": "Пост",
                          "date": "01.01.2020"})
dm.add_content_plan_item({"topic": "Свежий", "rubric": "Польза", "format": "Пост",
                          "date": "01.02.2020"})
past_ids = [str(item["id"]) for item in dm.get_content_plan()]
decision = core.router._rules("измени дату поста на 5 декабря")
ok("будущих позиций нет — берётся последняя",
   decision is not None and decision.args.get("item_id") == past_ids[-1],
   getattr(decision, "args", None))
vague = core.router._rules("перенеси пост на утро")
ok("перенос без понятной даты — вопрос, а не догадка",
   vague is not None and not vague.tool and "дату" in (vague.clarify or ""),
   getattr(vague, "clarify", None))
fresh = core.router._rules("поставь пост про осень")
ok("«поставь пост про осень» по-прежнему создаёт пост, а не переносит",
   fresh is not None and fresh.tool == "create_content_plan",
   getattr(fresh, "tool", None))

dm, core, stub = build([])
decision = core.router._rules("добавь в план пост про осень")
ok("«добавь в план пост про осень» — одна позиция с темой из фразы",
   decision is not None and decision.tool == "create_content_plan"
   and decision.args.get("topics") == ["осень"], getattr(decision, "args", None))
reply = core.handle("добавь в план пост про осень")
plan = dm.get_content_plan()
ok("пост про осень в плане",
   len(plan) == 1 and "осень" in str(plan[0].get("topic")).lower(), plan)
ok("фраза про осень — правилом, а не шагами агента",
   stub.agent_calls == 0, stub.agent_calls)

# --- проверка плана и Excel не перехватывают чтение таблицы ---
dm, core, stub = seeded_plan()
for text in ("покажи таблицу постов", "покажи все посты", "покажи план"):
    decision = core.router._rules(text)
    ok(f"«{text}» — чтение плана, а не проверка и не Excel",
       decision is not None and decision.tool == "get_project_context"
       and decision.args.get("scope") == "plan", getattr(decision, "tool", None))
reply = core.handle("покажи таблицу постов")
ok("в ответе таблица позиций",
   "Позиции плана (3)" in reply.text and "01.04.2027" in reply.text, reply.text)
ok("«покажи таблицу постов» — правилом, без шагов агента и без подтверждения",
   stub.agent_calls == 0 and not reply.needs_confirmation, stub.agent_calls)
decision = core.router._rules("проверь, все ли посты с подписями")
ok("проверка плана не перехвачена чтением таблицы",
   decision is not None and decision.tool == "validate_plan", getattr(decision, "tool", None))
decision = core.router._rules("выгрузи план в таблицу")
ok("экспорт в таблицу — по-прежнему честный отказ",
   decision is not None and not decision.tool and "Excel" in (decision.clarify or ""),
   getattr(decision, "clarify", None))

# --- обработка всех фото просит подтверждение ---
from PIL import Image

dm, core, stub = build([])
photos = Path(tempfile.mkdtemp(prefix="photos_"))
for index in (1, 2):
    file_path = photos / f"p{index}.jpg"
    Image.new("RGB", (40, 40), (index * 40, 80, 120)).save(file_path)
    dm._data["media_ready"].append({"id": f"m{index}", "name": file_path.name,
                                    "type": "image", "path": str(file_path),
                                    "status": "approved"})
dm.save()
import ai_core

saved_media_dir = ai_core.MEDIA_IMAGES
ai_core.MEDIA_IMAGES = photos / "out"   # не пишем готовые файлы в репозиторий
reply = core.handle("сожми фото до 1080")
ok("обработка фото просит подтверждение", reply.needs_confirmation, reply.text)
ok("до подтверждения файлы не тронуты",
   not any(record.get("processed") for record in dm._data["media_ready"]),
   dm._data["media_ready"])
core.handle("нет")
ok("отказ ничего не меняет",
   not any(record.get("processed") for record in dm._data["media_ready"]),
   dm._data["media_ready"])
core.handle("сожми фото до 1080")
reply = core.handle("покажи план")
ok("другая фраза отменяет и обработку фото",
   "Отменил" in reply.text and core.pending is None
   and not any(record.get("processed") for record in dm._data["media_ready"]),
   (reply.text, dm._data["media_ready"]))
core.handle("сожми фото до 1080")
core.handle("да")
ok("после «да» фото обработаны",
   all("compress" in (record.get("processed") or []) for record in dm._data["media_ready"]),
   [record.get("processed") for record in dm._data["media_ready"]])
ai_core.MEDIA_IMAGES = saved_media_dir

# --- агент не обходит подтверждение обработки фото ---
dm, core, stub = build([
    '{"action": "tool", "tool": "batch_photo", '
    '"args": {"media_ids": ["m1", "m2"], "operations": ["compress"]}}',
    '{"action": "done", "say": "Готово."}'])
agent_photos = Path(tempfile.mkdtemp(prefix="photos_agent_"))
for index in (1, 2):
    file_path = agent_photos / f"q{index}.jpg"
    Image.new("RGB", (40, 40), (60, 60, 120)).save(file_path)
    dm._data["media_ready"].append({"id": f"m{index}", "name": file_path.name,
                                    "type": "image", "path": str(file_path),
                                    "status": "approved"})
dm.save()
ai_core.MEDIA_IMAGES = agent_photos / "out"
reply = core.handle("приведи фотографии в порядок")
ok("агент упирается в подтверждение",
   reply.needs_confirmation and "Подтвердите" in reply.text, reply.text)
ok("агент не тронул файлы",
   not any(record.get("processed") for record in dm._data["media_ready"]),
   dm._data["media_ready"])
core.handle("да")
ok("после «да» агентское действие выполнено",
   all("compress" in (record.get("processed") or []) for record in dm._data["media_ready"]),
   [record.get("processed") for record in dm._data["media_ready"]])
ai_core.MEDIA_IMAGES = saved_media_dir

# --- нет плана: отказ понятный, а не «Не хватает данных» ---
dm, core, stub = build([])
reply = core.handle("напиши подпись к первому посту")
ok("подпись без плана — понятный отказ",
   "позиций" in reply.text and "plan_id" not in reply.text, reply.text)
reply = core.handle("убери последний пост из плана")
ok("удаление без плана — понятный отказ", "нечего" in reply.text, reply.text)
reply = core.handle("подготовь ТЗ на съёмку")
ok("ТЗ без плана — понятный ответ",
   "план" in reply.text.lower() and "plan_id" not in reply.text, reply.text)

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

# --- модель первая: задачу ведёт агент, даже если правило её знает ---
dm, core, stub = build([
    '{"action": "tool", "tool": "plan_report", "args": {}}',
    '{"action": "done", "say": "Отчёт по плану собран."}'])
dm.add_content_plan_item({"topic": "Пост 1", "rubric": "Польза", "format": "Пост",
                          "date": "01.04.2027"})
reply = core.handle("сделай отчёт по плану")
ok("при модели задачу ведёт агент, а не правило",
   reply.layer == "agent" and stub.agent_calls == 2, (reply.layer, stub.agent_calls))
ok("агент взял отчёт из плана, а не сочинил", "Отчёт по плану" in reply.text, reply.text)

# --- модель спросила — ответ продолжает ту же задачу ---
dm, core, stub = build([
    '{"action": "ask", "say": "Какой пост: последний или по дате?"}',
    '{"action": "tool", "tool": "plan_report", "args": {}}',
    '{"action": "done", "say": "Отчёт по плану готов."}'])
dm.add_content_plan_item({"topic": "Пост 1", "rubric": "Польза", "format": "Пост",
                          "date": "01.04.2027"})
first = core.handle("сделай отчёт по плану")
ok("вопрос модели доходит до человека",
   first.asked and "Какой пост" in first.text, (first.asked, first.text))
ok("задача с вопросом запомнена", core.open_task != "", core.open_task)
second = core.handle("последний")
ok("ответ человека продолжает задачу, а не начинает новую",
   "Уточнение от пользователя: последний" in stub.calls[-2], stub.calls[-2][-300:])
ok("после уточнения задача доведена", "Отчёт по плану" in second.text, second.text)
ok("запомненная задача сброшена", core.open_task == "", core.open_task)

# --- диалог попадает в контекст модели ---
dm, core, stub = build([
    '{"action": "tool", "tool": "plan_report", "args": {}}',
    '{"action": "done", "say": "Первый отчёт готов."}',
    '{"action": "tool", "tool": "plan_report", "args": {}}',
    '{"action": "done", "say": "Второй отчёт готов."}'])
dm.add_content_plan_item({"topic": "Пост 1", "rubric": "Польза", "format": "Пост",
                          "date": "01.04.2027"})
core.handle("сделай отчёт по плану")
core.handle("повтори в том же духе")
ok("модель видит предыдущий ответ в диалоге",
   "Первый отчёт готов" in stub.calls[-2], stub.calls[-2][-400:])

# --- без модели прежние правила продолжают работать ---
dm, core, stub = build([], providers=False)
dm.add_content_plan_item({"topic": "Пост 1", "rubric": "Польза", "format": "Пост",
                          "date": "01.04.2027"})
reply = core.handle("покажи план")
ok("без модели фраза по-прежнему работает", "Позиции плана" in reply.text, reply.text)

# --- журнал и откат правило забирает до модели ---
dm, core, stub = build([
    '{"action": "tool", "tool": "create_content_plan", "args": {"count": 2}}',
    '{"action": "done", "say": "Создал план."}'])
reply = core.handle("журнал действий")
ok("журнал решает правило, а не агент",
   stub.agent_calls == 0 and "Журнал" in reply.text, (stub.agent_calls, reply.text))
ok("журнал не создал пост", not dm.get_content_plan(), dm.get_content_plan())

def build_with_editor(script, verdicts):
    """Креатор — Stage, редактор — облачная заглушка (как «облако» в настройках)."""
    dm = DataManager("agent", tempfile.mkdtemp(prefix="agent_"))
    stage = Stage(script)
    editor = Editor(verdicts)
    core = AICore(dm, {"monthly_budget_usd": 0},
                  app_db_path=Path(tempfile.mkdtemp(prefix="agent_db_")) / "app.db",
                  providers=(stage, editor))
    return dm, core, stage, editor


# --- редактор по запросу: одна проверка на все подписи ---
VERDICTS = json.dumps({"reviews": [
    {"id": "cp_001", "approved": False,
     "text": "Свежая обжарка каждое утро. #кофе #пар", "note": "убрал воду"},
    {"id": "cp_002", "approved": True, "text": "Готовая подпись.", "note": ""}]},
    ensure_ascii=False)
dm, core, stub, editor = build_with_editor([
    '{"action": "tool", "tool": "review_captions", "args": {}}',
    '{"action": "done", "say": "Редактор посмотрел подписи."}'], [VERDICTS])
first_id = dm.add_content_plan_item({"topic": "Обжарка", "rubric": "Польза", "format": "Пост",
                                     "date": "01.04.2027",
                                     "caption": "Мы очень-очень стараемся, заходите к нам почаще."})
second_id = dm.add_content_plan_item({"topic": "Отзыв", "rubric": "Личное", "format": "Пост",
                                      "date": "02.04.2027", "caption": "Готовая подпись."})
reply = core.handle("проверь подписи редактором")
ok("проверка редактором сначала спрашивает «да/нет»", reply.needs_confirmation, reply.text)
ok("в вопросе обе подписи и предупреждение о замене текста",
   "«Обжарка»" in reply.text and "«Отзыв»" in reply.text and "заменится" in reply.text,
   reply.text)
ok("до «да» редактор не вызван и подписи целы",
   not editor.calls
   and dm.get_content_plan_item(first_id)["caption"].startswith("Мы очень-очень"),
   (editor.calls, dm.get_content_plan_item(first_id).get("caption")))
reply = core.handle("нет")
ok("«нет» не зовёт редактора и не меняет подписи",
   not editor.calls and core.pending is None
   and dm.get_content_plan_item(first_id)["caption"].startswith("Мы очень-очень"),
   (editor.calls, reply.text))
core._execute("review_captions", {}, "rules")
reply = core.handle("да")
ok("после «да» редактор проверяет все подписи одним вызовом",
   len(editor.calls) == 1, len(editor.calls))
ok("в одном запросе обе подписи", "cp_002" in editor.calls[0][1], editor.calls[0][1][:200])
ok("слабую подпись редактор переписал",
   str(dm.get_content_plan_item(first_id)["caption"]).startswith("Свежая обжарка"),
   dm.get_content_plan_item(first_id).get("caption"))
ok("сильную подпись редактор не тронул",
   dm.get_content_plan_item(second_id)["caption"] == "Готовая подпись.",
   dm.get_content_plan_item(second_id).get("caption"))
ok("вердикты сохранены у обеих позиций",
   dm.get_content_plan_item(first_id).get("caption_review", {}).get("approved") is False
   and dm.get_content_plan_item(second_id).get("caption_review", {}).get("approved") is True,
   (dm.get_content_plan_item(first_id).get("caption_review"),
    dm.get_content_plan_item(second_id).get("caption_review")))
ok("в карточке видно, что редактор переписал и почему",
   review_badge(dm.get_content_plan_item(first_id))
   == "Редактор (editor-stub): переписал — убрал воду",
   review_badge(dm.get_content_plan_item(first_id)))
ok("в карточке видно одобрение",
   review_badge(dm.get_content_plan_item(second_id)) == "Редактор (editor-stub): одобрил",
   review_badge(dm.get_content_plan_item(second_id)))
ok("у непроверенной подписи бейджа нет", review_badge({}) == "", review_badge({}))
ok("правка редактора — отдельное действие с откатом",
   any(entry["tool"] == "review_captions" for entry in core.journal.list(10)),
   [entry["tool"] for entry in core.journal.list(10)])
core.undo(reply.actions[0]["id"])
ok("откат возвращает обе подписи",
   dm.get_content_plan_item(first_id)["caption"] == "Мы очень-очень стараемся, заходите к нам почаще."
   and dm.get_content_plan_item(second_id)["caption"] == "Готовая подпись.",
   (dm.get_content_plan_item(first_id).get("caption"),
    dm.get_content_plan_item(second_id).get("caption")))

# --- редактор не входит в пробелы автоматически ---
dm, core, stub, editor = build_with_editor([], [])
item_id = dm.add_content_plan_item({"topic": "Обжарка", "rubric": "Польза", "format": "Пост",
                                    "date": "01.04.2027", "caption": "Готовая подпись."})
gaps = core._agent()._plan_gaps([item_id])
ok("непроверенная подпись не мешает «готово»",
   not any(tool == "review_captions" for tool, _ in gaps), gaps)
ok("редактор не вызывается без запроса", len(editor.calls) == 0, len(editor.calls))

# --- без редактора — честный ответ, а не тишина ---
dm, core, stub = build([])
item_id = dm.add_content_plan_item({"topic": "Обжарка", "rubric": "Польза", "format": "Пост",
                                    "date": "01.04.2027", "caption": "Готовая подпись."})
reply = core._execute("review_captions", {}, "rules")
ok("без редактора сказано, что его нет", "Редактор не настроен" in reply.text, reply.text)
ok("без редактора подпись не тронута",
   dm.get_content_plan_item(item_id)["caption"] == "Готовая подпись.",
   dm.get_content_plan_item(item_id).get("caption"))

# --- модель тоже не удаляет без «да» ---
dm, core, stub = seeded_plan()
target_id = str(dm.get_content_plan()[0]["id"])
dm, core, stub = build([
    '{"action": "tool", "tool": "delete_record", "args": {"section": "content_plan", '
    '"item_id": "' + target_id + '"}}',
    '{"action": "done", "say": "Удалил пост."}'])
dm.add_content_plan_item({"topic": "Пост 1", "rubric": "Польза", "format": "Пост",
                          "date": "01.04.2027"})
reply = core.handle("убери первый пост из плана")
ok("агент упирается в подтверждение удаления",
   reply.needs_confirmation and len(dm.get_content_plan()) == 1, reply.text)
ok("действие ждёт ответа, а не выполнено", len(core.pending or ()) == 2, core.pending)
core.handle("да")
ok("после «да» агентское удаление выполнено", not dm.get_content_plan(), dm.get_content_plan())

# --- кнопка в окне удаляет сразу: там свой диалог подтверждения ---
dm, core, stub = seeded_plan()
target_id = str(dm.get_content_plan()[0]["id"])
reply = core.run_tool("delete_record", section="content_plan", item_id=target_id)
ok("GUI-путь по-прежнему удаляет без вопроса",
   not reply.needs_confirmation and len(dm.get_content_plan()) == 2,
   (reply.needs_confirmation, len(dm.get_content_plan())))

dm, core, stub = build([])
dm._data["other_files"] = {"Материалы": [{"id": "mat_1", "name": "p1.jpg"}]}
dm.save()
reply = core.run_tool("delete_material", item_id="mat_1")
ok("GUI-путь убирает материал без вопроса",
   not reply.needs_confirmation and not dm.get_other_files().get("Материалы"), reply.text)

# --- выкладка на публичный URL: вопрос до загрузки и честный откат ---
class FakeHost:
    """Хостинг без сети: запоминает загрузки и удаления."""

    def __init__(self, delete_ok=True):
        self.uploads = []
        self.deleted = []
        self.delete_ok = delete_ok

    def upload(self, file_path, public_id):
        self.uploads.append((file_path, public_id))
        return {"url": f"https://res.cloudinary.com/demo/image/upload/{public_id}.jpg",
                "public_id": public_id, "resource_type": "image"}

    def delete(self, public_id, resource_type="image"):
        self.deleted.append((public_id, resource_type))
        return self.delete_ok


host_dir = Path(tempfile.mkdtemp(prefix="host_"))
host_photo = host_dir / "пляж.jpg"
host_photo.write_bytes(b"JPEG" * 100)
dm, core, stub = build([])
dm._data["media_ready"].append({"id": "m1", "name": "пляж.jpg", "type": "image",
                                "path": str(host_photo), "status": "approved"})
dm.save()
host = FakeHost()
core.tools.cloudinary = host
reply = core.handle("выложи материал m1 на публичный url")
ok("выкладка на URL просит подтверждение", reply.needs_confirmation, reply.text)
ok("в вопросе имя файла и предупреждение о публичности",
   "пляж.jpg" in reply.text and "публичн" in reply.text.lower(), reply.text)
ok("до «да» ничего не загружено",
   not host.uploads and "remote_url" not in dm.get_media_ready()[0],
   (host.uploads, dm.get_media_ready()[0]))
reply = core.handle("нет")
ok("«нет» отменяет выкладку", not host.uploads and not reply.needs_confirmation,
   (host.uploads, reply.text))
core.handle("выложи материал m1 на публичный url")
core.handle("да")
record = dm.get_media_ready()[0]
ok("после «да» файл выложен и ссылка записана",
   len(host.uploads) == 1 and str(record.get("remote_url") or "").startswith("https://"),
   (host.uploads, record))

core.tools._cloudinary_client = lambda: None   # ключей нет: файл с хостинга не удалить
message = core.undo(core.journal.list(1)[0]["id"]).text
ok("откат без ключей прямо говорит, что файл остался публичным",
   "остался публичным" in message and "Cloudinary" in message, message)
ok("откат без ключей убрал ссылку из записи",
   not dm.get_media_ready()[0].get("remote_url"), dm.get_media_ready()[0])
del core.tools._cloudinary_client

host_broken = FakeHost(delete_ok=False)
core.tools.cloudinary = host_broken
core.handle("выложи материал m1 на публичный url")
core.handle("да")
message = core.undo(core.journal.list(1)[0]["id"]).text
ok("если хостинг не подтвердил удаление — сказано про публичность",
   "мог остаться публичным" in message, message)

host_ok = FakeHost()
core.tools.cloudinary = host_ok
core.handle("выложи материал m1 на публичный url")
core.handle("да")
message = core.undo(core.journal.list(1)[0]["id"]).text
ok("откат с ключами удаляет файл с хостинга",
   bool(host_ok.deleted) and "удалён" in message, (host_ok.deleted, message))

# --- импорт, PDF и пакет спрашивают до записи ---
imp_dir = Path(tempfile.mkdtemp(prefix="imp_"))
imp_photo = imp_dir / "t13_import.png"
imp_photo.write_bytes(b"PNG" * 100)
imp_doc = imp_dir / "brief.txt"
imp_doc.write_text("бриф", encoding="utf-8")

dm, core, stub = build([])
reply = core._execute("import_media", {"paths": [str(imp_photo)], "zone": "ready"}, "agent")
ok("импорт в медиатеку спрашивает", reply.needs_confirmation, reply.text)
ok("в вопросе зона и число файлов",
   "Готовые материалы" in reply.text and "файлов: 1" in reply.text, reply.text)
ok("до «да» медиатека пуста", not dm.get_media_ready(), dm.get_media_ready())
core.handle("да")
ready = dm.get_media_ready()
ok("после «да» файл в медиатеке", len(ready) == 1, ready)
Path(ready[0]["path"]).unlink(missing_ok=True)

dm, core, stub = build([])
reply = core._execute("import_materials", {"paths": [str(imp_doc)], "folder": "documents"},
                      "agent")
ok("импорт в «Материалы» спрашивает",
   reply.needs_confirmation and "Документы" in reply.text and "файлов: 1" in reply.text,
   reply.text)
ok("до «да» материалов нет", not dm.get_other_files().get("documents"), dm.get_other_files())
core.handle("да")
ok("после «да» материал на месте", len(dm.get_other_files().get("documents") or []) == 1,
   dm.get_other_files())

dm, core, stub = seeded_plan()
reply = core._execute("export_pdf", {"kind": "plan", "dest": str(imp_dir)}, "agent")
ok("выгрузка PDF спрашивает",
   reply.needs_confirmation and "план публикаций" in reply.text
   and "позиций: 3" in reply.text, reply.text)
ok("до «да» файла нет", not list(imp_dir.glob("*.pdf")), list(imp_dir.glob("*.pdf")))
core.handle("да")
ok("после «да» PDF появился", bool(list(imp_dir.glob("*.pdf"))), list(imp_dir.glob("*.pdf")))

dm, core, stub = seeded_plan()
pack_dir = imp_dir / "pack"
reply = core._execute("instagram_pack", {"dest": str(pack_dir)}, "agent")
ok("пакет под Instagram спрашивает",
   reply.needs_confirmation and "позиций плана: 3" in reply.text, reply.text)
ok("до «да» папки нет", not pack_dir.exists(), pack_dir)
core.handle("да")
ok("после «да» пакет собран",
   bool(list(pack_dir.glob("*/manifest.csv"))), list(pack_dir.iterdir()))

class FakeVideo:
    """Обработчик видео без ffmpeg: пишет заглушки и запоминает вызовы."""

    ffmpeg_available = True

    def __init__(self):
        self.exported = []
        self.burned = []

    def export_for_platform(self, source, target, dest):
        Path(dest).write_bytes(b"MP4" * 50)
        self.exported.append((source, target))
        return True

    def get_video_info(self, path):
        return {"width": 1080, "height": 1920}

    def extract_audio(self, source):
        audio = Path(source).with_suffix(".wav")
        audio.write_bytes(b"WAV" * 10)
        return str(audio)

    def transcribe(self, audio, language="ru"):
        return {"segments": [{"start": 0.0, "end": 1.0, "text": "привет"}]}

    def generate_srt(self, segments, dest):
        Path(dest).write_text("1\n00:00:00,000 --> 00:00:01,000\nпривет\n",
                              encoding="utf-8")
        return True

    def burn_subtitles(self, source, srt, dest):
        Path(dest).write_bytes(b"MP4" * 50)
        self.burned.append(str(dest))
        return True


# --- видео и субтитры спрашивают даже для одного файла ---
video_dir = Path(tempfile.mkdtemp(prefix="vid_"))
clip = video_dir / "t14_clip.mp4"
clip.write_bytes(b"MP4" * 100)

dm, core, stub = build([])
dm._data["media_ready"].append({"id": "mv1", "name": "t14_clip.mp4", "type": "video",
                                "path": str(clip)})
dm.save()
video = FakeVideo()
core.tools.video = video
reply = core._execute("process_video",
                      {"media_ids": ["mv1"], "platform": "instagram_reels"}, "agent")
ok("видео спрашивает подтверждение и для одного файла", reply.needs_confirmation, reply.text)
ok("в вопросе число файлов и площадка",
   "1 файл" in reply.text and "Reels 9:16" in reply.text, reply.text)
ok("до «да» видео не обработано",
   not video.exported and dm.get_media_ready()[0]["path"] == str(clip),
   (video.exported, dm.get_media_ready()[0]))
core.handle("нет")
ok("«нет» не трогает видео", not video.exported, video.exported)
core._execute("process_video", {"media_ids": ["mv1"], "platform": "instagram_reels"},
              "agent")
core.handle("да")
record = dm.get_media_ready()[0]
ok("после «да» запись на готовом файле",
   bool(video.exported) and Path(record["path"]).is_file()
   and Path(record["path"]) != clip, (video.exported, record))
Path(record["path"]).unlink(missing_ok=True)

dm, core, stub = build([])
dm._data["media_ready"].append({"id": "mv2", "name": "t14_clip.mp4", "type": "video",
                                "path": str(clip)})
dm.save()
video = FakeVideo()
core.tools.video = video
reply = core._execute("make_subtitles",
                      {"media_ids": ["mv2"], "language": "ru", "burn": True}, "agent")
ok("субтитры спрашивают подтверждение и для одного файла",
   reply.needs_confirmation, reply.text)
ok("в вопросе число файлов и операция",
   "1 файл" in reply.text and "выжечь субтитры" in reply.text, reply.text)
ok("до «да» .srt нет", not list((Path(dm.data_dir) / "subtitles").glob("*.srt")))
core.handle("да")
srt = list((Path(dm.data_dir) / "subtitles").glob("*.srt"))
ok("после «да» субтитры сделаны и видео заменено",
   bool(srt) and bool(video.burned) and Path(dm.get_media_ready()[0]["path"]).is_file(),
   (srt, video.burned))
Path(dm.get_media_ready()[0]["path"]).unlink(missing_ok=True)

# --- откат без обратной операции: статус записи не меняется ---
dm, core, stub = build([])
audit_id = core.journal.log("instagram_publish", {"item_id": "cp_001"},
                            {"note": "проверка без публикации: ничего не отправлено"}, {},
                            actor="user")
reply = core.undo(audit_id)
ok("без обратной операции откат говорит об этом прямо",
   "нет обратной операции" in reply.text, reply.text)
ok("без обратной операции запись не помечена отменённой",
   core.journal.get(audit_id)["status"] == "done", dict(core.journal.get(audit_id)))
ok("несостоявшийся откат не пишет служебную запись «undo»",
   not any(entry["tool"] == "undo" for entry in core.journal.list(10)),
   [entry["tool"] for entry in core.journal.list(10)])

reply = core.handle("отмени последнее")
ok("«отмени последнее» тоже не врёт про отмену",
   "нет обратной операции" in reply.text, reply.text)
ok("после «отмени последнее» статус прежний",
   core.journal.get(audit_id)["status"] == "done", dict(core.journal.get(audit_id)))

real_id = core.journal.log("demo_change", {}, {"note": "добавил пост"},
                           {"op": "restore_section", "section": "content_plan", "data": []},
                           actor="user")
reply = core.undo(real_id)
ok("настоящий откат по-прежнему помечает запись отменённой",
   core.journal.get(real_id)["status"] == "undone" and "Откатил" in reply.text,
   (dict(core.journal.get(real_id)), reply.text))
ok("служебная запись «undo» появляется только за настоящий откат",
   [entry["tool"] for entry in core.journal.list(10)].count("undo") == 1,
   [entry["tool"] for entry in core.journal.list(10)])

# --- другая фраза вместо «да/нет» — явная отмена, а не тихая ---
dm, core, stub = seeded_plan()
before_ids = [str(item["id"]) for item in dm.get_content_plan()]
reply = core.handle("удали последний пост из плана")
ok("удаление ждёт ответа",
   reply.needs_confirmation and len(dm.get_content_plan()) == 3, reply.text)
reply = core.handle("покажи план")
ok("другая фраза отменяет удаление и говорит об этом",
   "Отменил" in reply.text and "Ничего не изменено" in reply.text, reply.text)
ok("в отмене названо, что именно отменено",
   "удалить запись" in reply.text.lower(), reply.text)
ok("новая фраза не выполнилась молча под шумок отмены",
   "Позиции плана" not in reply.text, reply.text)
ok("после отмены ничего не удалено",
   [str(item["id"]) for item in dm.get_content_plan()] == before_ids,
   dm.get_content_plan())
ok("подтверждение больше не ждёт ответа", core.pending is None, core.pending)
reply = core.handle("да")
ok("позднее «да» уже ничего не выполняет",
   len(dm.get_content_plan()) == 3, (len(dm.get_content_plan()), reply.text))

print("AGENT_DONE")
