"""Маршрут публикации через чат: текст → правило → handle → гейт → инструмент."""
import sys, tempfile, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2] / "AI_SMM_Work_Architecture_A75"
sys.path.insert(0, str(ROOT))
from data_manager import DataManager
from ai_core import AICore, StubProvider
import instagram_auth

fails = []
def check(name, cond, extra=""):
    print(("OK   " if cond else "FAIL ") + name + ("" if cond else f" :: {extra}"))
    if not cond:
        fails.append(name)

TOKEN = "IGQVJ_route_token_12345"

class Resp:
    def __init__(self, status, body):
        self.status_code = status; self._b = body
    def json(self):
        return self._b

class Graph:
    def __init__(self):
        self.calls = []
    def _r(self, url, params=None, data=None):
        self.calls.append((url, dict(data or params or {})))
        if url.endswith("/me"):
            return Resp(200, {"id": "1789", "username": "studio", "account_type": "BUSINESS"})
        if "content_publishing_limit" in url:
            return Resp(200, {"data": [{"config": {"quota_total": 50}, "quota_usage": 3}]})
        if url.endswith("/media"):
            return Resp(200, {"id": "cont_1"})
        if "cont_1" in url:
            return Resp(200, {"status_code": "FINISHED"})
        if url.endswith("/media_publish"):
            return Resp(200, {"id": "ig_999"})
        return Resp(404, {"error": {"message": "unknown"}})
    def get(self, url, params=None, timeout=None):
        return self._r(url, params=params)
    def post(self, url, data=None, timeout=None):
        return self._r(url, data=data)
    def writes(self):
        return [c for c in self.calls if c[0].endswith(("/media", "/media_publish"))]

def build(route_reply=None):
    """Свежий проект: два материала с публичным URL, живой токен, подставной Graph."""
    tmp = Path(tempfile.mkdtemp(prefix="route_"))
    photo = tmp / "p.jpg"; photo.write_bytes(b"JPEG" * 20)
    dm = DataManager("rt", str(tmp / "proj"))
    for media_id, name in (("m1", "p.jpg"), ("me_ab12cd", "q.jpg")):
        dm._data["media_ready"].append({"id": media_id, "name": name, "type": "image",
                                        "path": str(photo), "status": "approved",
                                        "remote_url": f"https://res.cloudinary.com/x/{name}"})
    dm.save()
    stub = StubProvider([json.dumps(route_reply, ensure_ascii=False)] if route_reply else [])
    core = AICore(dm, {"monthly_budget_usd": 0}, providers=(stub, None))
    core.tools.tokens = instagram_auth.TokenStore(tmp / "app.db")
    core.tools.tokens.save(TOKEN, {"username": "studio", "account_type": "BUSINESS", "ig_user_id": "1789"})
    return dm, core, stub

orig_get, orig_post = instagram_auth.requests.get, instagram_auth.requests.post
instagram_auth.PUBLISH_POLL_SEC = 0

# 1. Правило само находит материал — модель не нужна
dm, core, stub = build()
decision = core.router.route("опубликуй материал m1")
print("1 rule:", decision.layer, decision.tool, decision.args)
check("правило: instagram_publish", decision.tool == "instagram_publish", decision.tool)
check("правило: слой rules, не модель", decision.layer == "rules", decision.layer)
check("правило: media_id из текста", decision.args.get("media_id") == "m1", decision.args)
check("правило: dry_run не подставлен (default 1)", "dry_run" not in decision.args, decision.args)
check("правило: модель не спрашивали", not stub.calls, stub.calls)

# 2. «без проверки» и dry_run=0 — реальная публикация
dm, core, stub = build()
for text in ("Опубликуй материал m1 без проверки", "опубликуй материал m1, dry_run=0"):
    d = core.router.route(text)
    print(f"2 {text!r}: {d.tool} {d.args}")
    check(f"dry_run=0 в «{text}»", d.tool == "instagram_publish" and d.args.get("dry_run") == "0", d.args)

# 3. Другие формулировки и id вида me_ab12cd
dm, core, stub = build()
d = core.router.route("запости материал me_ab12cd")
check("id me_ab12cd разобран", d.args.get("media_id") == "me_ab12cd", d.args)
d = core.router.route("опубликуй me_ab12cd")
check("id без слова «материал»", d.args.get("media_id") == "me_ab12cd", d.args)
d = core.router.route("опубликуй материал")
check("без id правило не срабатывает", d.tool != "instagram_publish", (d.tool, d.clarify))
d = core.router.route("подготовь публикацию в инстаграм")
check("«подготовь публикацию» остаётся пакетом", d.tool == "instagram_pack", d.tool)

# 4. handle(): dry-run по умолчанию, «да/нет» не спрашивает, POST не идёт
dm, core, stub = build()
g = Graph()
instagram_auth.requests.get, instagram_auth.requests.post = g.get, g.post
try:
    reply = core.handle("опубликуй материал m1")
finally:
    instagram_auth.requests.get, instagram_auth.requests.post = orig_get, orig_post
print("4 handle:", reply.text[:110].replace("\n", " "), "| confirm:", reply.needs_confirmation)
check("dry-run без подтверждения", reply.needs_confirmation is False, reply.needs_confirmation)
check("дошло до проверки публикации", "Проверка прошла, публикация не запущена" in reply.text, reply.text)
check("dry-run не пишет в Instagram", not g.writes(), g.writes())
check("запись без published_id", "published_id" not in dm.get_media_ready()[0], dm.get_media_ready()[0])

# 5. «без проверки» — уходит в подтверждение, сеть на запись молчит
dm, core, stub = build()
g = Graph()
instagram_auth.requests.get, instagram_auth.requests.post = g.get, g.post
reply = core.handle("опубликуй материал m1 без проверки")
print("5 handle:", reply.text[:130].replace("\n", " "), "| confirm:", reply.needs_confirmation)
check("dry_run=0 просит подтверждение", reply.needs_confirmation is True, reply.needs_confirmation)
check("текст подтверждения", "Подтвердите" in reply.text, reply.text)
check("до «да» ничего не публикуется", not g.writes(), g.writes())

# 6. «нет» на подтверждении — ничего не публикует
reply = core.handle("нет")
check("«нет» отменяет", core.pending is None and "Отменил" in reply.text, reply.text)

# 7. «да» — публикация идёт
dm, core, stub = build()
g = Graph()
instagram_auth.requests.get, instagram_auth.requests.post = g.get, g.post
try:
    core.handle("опубликуй материал m1 без проверки")
    reply = core.handle("да")
finally:
    instagram_auth.requests.get, instagram_auth.requests.post = orig_get, orig_post
print("7 «да»:", reply.text[:100])
check("«да» публикует", "Опубликовал" in reply.text and "ig_999" in reply.text, reply.text)
check("«да»: контейнер → media_publish", any(c[0].endswith("/media_publish") for c in g.writes()), g.writes())

# 8. Без id правило молчит — модель по-прежнему может выбрать инструмент
dm, core, stub = build({"tool": "instagram_publish", "args": {"media_id": "m1"}, "confidence": 0.9})
d = core.router.route("опубликуй этот материал")
print("8 модель:", d.layer, d.tool, d.args)
check("запасной путь через модель цел", d.tool == "instagram_publish" and d.args.get("media_id") == "m1",
      (d.tool, d.args))

instagram_auth.requests.get, instagram_auth.requests.post = orig_get, orig_post
print("FAILS:", fails or "нет")
sys.exit(1 if fails else 0)
