"""AI-менеджер выполняет задачу шагами сам: модель выбирает инструменты и доводит до результата."""
import json, sys, tempfile
from datetime import datetime, timedelta
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
ok("частотные фразы не дёргают модель", not stub.calls, stub.calls)
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

# --- «убери последний пост» удаляет именно его ---
dm, core, stub = seeded_plan()
last_id = str(dm.get_content_plan()[-1]["id"])
core.handle("убери последний пост из плана")
ok("пост удалён из плана", len(dm.get_content_plan()) == 2, len(dm.get_content_plan()))
ok("удалён последний, а не первый",
   all(str(item["id"]) != last_id for item in dm.get_content_plan()))

# --- удаление берёт раздел из фразы, а не всегда контент-план ---
dm, core, stub = seeded_plan()
dm._data["calendar_events"] = [
    {"id": "ev_1", "date": "01.04.2027", "title": "Пост 1", "link": "cp_1"},
    {"id": "ev_2", "date": "02.04.2027", "title": "Пост 2", "link": "cp_2"}]
dm._data["shooting_tasks"] = [{"id": "st_1", "plan_id": "cp_1", "title": "ТЗ 1"}]
dm.save()
core.handle("удали пост из календаря")
ok("удаление из календаря не трогает план",
   len(dm.get_content_plan()) == 3, len(dm.get_content_plan()))
ok("удаление из календаря убрало событие",
   len(dm.get_calendar_events()) == 1, dm.get_calendar_events())
core.handle("удали ТЗ")
ok("удаление ТЗ не трогает план",
   len(dm.get_content_plan()) == 3 and not dm.get_shooting_tasks(),
   (len(dm.get_content_plan()), dm.get_shooting_tasks()))
core.handle("удали пост из плана")
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
ok("публикации и стратегия тоже без модели", not stub.calls, stub.calls)
reply = core.handle("покажи материалы")
ok("чтение материалов даёт список", "Материалов готовых" in reply.text, reply.text)
reply = core.handle("какие блоки в стратегии")
ok("чтение стратегии называет блоки", "Аудитория" in reply.text, reply.text)
core.handle("обнови kpi: охват 5000")
kpis = (dm.get_strategy() or {}).get("kpis") or []
ok("KPI обновлены из фразы",
   any(str(row.get("current")) == "5000" for row in kpis), kpis)
core.handle("убери материал mat_1 из списка")
ok("материал убран из «Материалов»",
   not dm.get_other_files().get("Материалы"), dm.get_other_files())
decision = core.router._rules("перепиши блок аудитория")
ok("правка блока без текста — спрашивает текст",
   decision is not None and not decision.tool and "Аудитория" in (decision.clarify or ""),
   getattr(decision, "clarify", None))
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
ok("фразы третьего обмера не дёргают модель", not stub.calls, stub.calls)

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
dates = [str(item.get("date")) for item in dm.get_content_plan()]
ok("завтрашняя дата встала в ближайшую позицию",
   dates == [tomorrow, "02.04.2027", "03.04.2027"], dates)
ok("ответ называет новую дату", tomorrow in reply.text, reply.text)
ok("«перенеси пост на завтра» не дёргает модель", not stub.calls, stub.calls)
ok("перенос даты можно отменить", any(entry["tool"] == "edit_record"
                                      for entry in core.journal.list(10)), core.journal.list(10))

# --- номер важнее порядка: явная дата и номер адресуют свою позицию ---
dm, core, stub = seeded_plan()
order_ids = [str(item["id"]) for item in dm.get_content_plan()]
decision = core.router._rules("перенеси третий пост на завтра")
ok("номер сильнее «ближайшей» при переносе",
   decision is not None and decision.args.get("item_id") == order_ids[2],
   getattr(decision, "args", None))

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
ok("фраза про осень не дёргает модель", not stub.calls, stub.calls)

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
ok("«покажи таблицу постов» не дёргает модель и не просит подтверждения",
   not stub.calls and not reply.needs_confirmation, stub.calls)
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

print("AGENT_DONE")
