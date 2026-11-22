import sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2] / "AI_SMM_Work_Architecture_A75"
sys.path.insert(0, str(ROOT))
from data_manager import DataManager
from ai_core import AICore
import instagram_auth

def ok(name, cond, extra=""):
    print(("D4_OK " if cond else "D4_FAIL ") + name + ("" if cond else f" :: {extra}"))
    if not cond:
        raise SystemExit(1)

TOKEN = "IGQVJ_secret_token_12345"

class Resp:
    def __init__(self, status, body):
        self.status_code = status; self._b = body
    def json(self):
        return self._b

class Graph:
    """Подставной Graph API: считает вызовы публикации."""
    def __init__(self, limit_used=3, container_status="FINISHED", fail_publish=False):
        self.calls = []; self.limit_used = limit_used
        self.container_status = container_status; self.fail_publish = fail_publish
    def _r(self, url, params=None, data=None):
        self.calls.append((url, dict(data or params or {})))
        if url.endswith("/me"):
            return Resp(200, {"id": "1789", "username": "studio", "account_type": "BUSINESS"})
        if "content_publishing_limit" in url:
            return Resp(200, {"data": [{"config": {"quota_total": 50}, "quota_usage": self.limit_used}]})
        if url.endswith("/media") and data:
            return Resp(200, {"id": "cont_1"})
        if "cont_1" in url and params:
            return Resp(200, {"status_code": self.container_status})
        if url.endswith("/media_publish"):
            if self.fail_publish:
                return Resp(400, {"error": {"message": "Invalid token " + TOKEN}})
            return Resp(200, {"id": "ig_999"})
        return Resp(404, {"error": {"message": "unknown"}})
    def get(self, url, params=None, timeout=None):
        return self._r(url, params=params)
    def post(self, url, data=None, timeout=None):
        return self._r(url, data=data)

tmp = Path(tempfile.mkdtemp(prefix="d4_"))
photo = tmp / "beach.jpg"; photo.write_bytes(b"JPEG" * 50)
dm = DataManager("d4", str(tmp / "proj"))
core = AICore(dm, {"monthly_budget_usd": 0})
db = tmp / "app.db"
instagram_auth.TokenStore(db).save(TOKEN, {"username": "studio", "account_type": "BUSINESS", "ig_user_id": "1789"})
core.tools.tokens = instagram_auth.TokenStore(db)
dm._data["media_ready"].append({"id": "m1", "name": "beach.jpg", "type": "image", "path": str(photo),
                                "status": "approved", "remote_url": "https://res.cloudinary.com/x/beach.jpg"})
dm._data["media_ready"].append({"id": "m2", "name": "raw.jpg", "type": "image", "path": str(photo),
                                "status": "approved"})
dm.save()

orig_post, orig_get = instagram_auth.requests.post, instagram_auth.requests.get
g = Graph()
instagram_auth.requests.get = g.get; instagram_auth.requests.post = g.post
instagram_auth.PUBLISH_POLL_SEC = 0

# 1. Без URL — отказ, без сетевых вызовов публикации
r = core.tools.instagram_publish("m2", "0")
ok("без URL не публикует", "host_media" in r["summary"] and not any("media" in c[0] and "publish" in c[0] for c in g.calls), r)

# 2. dry-run — проверка, без контейнера и журнала
g.calls.clear()
r = core.tools.instagram_publish("m1")
ok("dry-run: проверка без публикации", "не запущена" in r["summary"] and not r["undo"], r["summary"])
ok("dry-run: нет POST", not any(c[1] and ("media" in c[0]) for c in g.calls if c[0].endswith(("/media", "/media_publish"))))
ok("dry-run: токен не в ответе", TOKEN not in r["summary"] and TOKEN not in str(r["effect"]))

# 3. Реальная публикация
g.calls.clear()
r = core.tools.instagram_publish("m1", "0")
ok("публикация: id в ответе", "ig_999" in r["summary"], r["summary"])
ok("публикация: контейнер -> media_publish", any(c[0].endswith("/media_publish") and c[1].get("creation_id") == "cont_1" for c in g.calls))
ok("публикация: тип IMAGE", any(c[0].endswith("/media") and c[1].get("media_type") == "IMAGE" for c in g.calls))
rec = dm._data["media_ready"][0]
ok("запись получила published_id и отметку", rec.get("published_id") == "ig_999" and "published" in rec.get("processed", []))
ok("откат есть", r["undo"].get("op") == "restore_sections")

# 4. Повтор без подтверждения — без новых вызовов
g.calls.clear()
r = core.tools.instagram_publish("m1", "0")
ok("дубль блокируется", "уже опубликован" in r["summary"] and not g.calls, r["summary"])

# 5. Лимит исчерпан
rec.pop("published_id", None); g.limit_used = 50; g.calls.clear()
r = core.tools.instagram_publish("m1", "0")
ok("лимит: отказ без публикации", "Лимит" in r["summary"] and not any(c[0].endswith("/media") for c in g.calls), r["summary"])
g.limit_used = 3

# 6. Ошибка публикации — токен не утекает, записи нет
g.fail_publish = True
before = dict(rec)
r = core.tools.instagram_publish("m1", "0")
ok("ошибка Graph API без утечки токена", "Instagram не опубликовал" in r["summary"] and TOKEN not in r["summary"], r["summary"])
ok("при ошибке запись не меняется", "published_id" not in rec)
g.fail_publish = False

# 7. Контейнер в ERROR
g.container_status = "ERROR"
r = core.tools.instagram_publish("m1", "0")
ok("контейнер ERROR — понятный отказ", "ERROR" in r["summary"], r["summary"])
g.container_status = "FINISHED"

# 8. Журнал: реальная публикация записана, dry-run не записан
# 9. Откат через журнал: публикация пишется в журнал, откат снимает отметку
rec2 = dm._data["media_ready"][0]
rec2.pop("published_id", None); rec2["processed"] = [x for x in rec2.get("processed", []) if x != "published"]
g.calls.clear()
rr = core.run_tool("instagram_publish", media_id="m1", dry_run="0"); print("RUN:", rr.text[:200], "| rec:", dm._data["media_ready"][0].get("published_id"), "| journal:", [a["tool"] for a in core.journal.list(5)])
row = [a for a in core.journal.list(5) if a["tool"] == "instagram_publish"]
ok("в журнале есть instagram_publish", bool(row), [a["tool"] for a in core.journal.list(5)])
print("UNDO_SPEC:", str(row[0].get("undo"))[:160]); print("ZONES:", {k: len(v) for k, v in dm._data.items() if isinstance(v, list)}); uu = core.undo(row[0]["id"]); print("UNDO_MSG:", uu.text)
cur = dm._data["media_ready"][0]
ok("откат снимает published_id и отметку", "published_id" not in cur and "published" not in cur.get("processed", []), cur)
# 10. Гейт подтверждения: dry-run без вопроса, реальная публикация и повтор — с вопросом
spec = core.registry.get("instagram_publish")
ok("гейт: dry-run по умолчанию без вопроса", spec.needs_confirmation({"media_id": "m1"}) is False)
ok("гейт: dry_run=1 без вопроса", spec.needs_confirmation({"media_id": "m1", "dry_run": "1"}) is False)
ok("гейт: dry_run=0 спрашивает", spec.needs_confirmation({"media_id": "m1", "dry_run": "0"}) is True)
ok("гейт: повтор с again спрашивает",
   spec.needs_confirmation({"media_id": "m1", "dry_run": "0", "again": "1"}) is True)
ok("гейт: dry_run=нет спрашивает", spec.needs_confirmation({"media_id": "m1", "dry_run": "нет"}) is True)
print("D4_GATE_DONE")

print("D4_DONE2")
instagram_auth.requests.get, instagram_auth.requests.post = orig_get, orig_post
print("D4_DONE")
