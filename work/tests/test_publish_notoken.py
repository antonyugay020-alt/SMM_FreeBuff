"""Без токена Meta: отказ вместо вида, что опубликовали. Сеть под ловушкой."""
import sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2] / "AI_SMM_Work_Architecture_A75"
sys.path.insert(0, str(ROOT))
from data_manager import DataManager
from ai_core import AICore
import instagram_auth

fails = []
def check(name, cond, extra=""):
    print(("OK   " if cond else "FAIL ") + name + ("" if cond else f" :: {extra}"))
    if not cond:
        fails.append(name)

class Tripwire:
    """Любой сетевой вызов — провал теста, а не тихий запрос."""
    def __init__(self):
        self.calls = []
    def _boom(self, method, url):
        self.calls.append((method, url))
        raise AssertionError(f"сеть без токена: {method} {url}")
    def get(self, url, **kw):
        self._boom("get", url)
    def post(self, url, **kw):
        self._boom("post", url)

trip = Tripwire()
orig_get, orig_post = instagram_auth.requests.get, instagram_auth.requests.post
instagram_auth.requests.get, instagram_auth.requests.post = trip.get, trip.post

tmp = Path(tempfile.mkdtemp(prefix="notoken_"))
photo = tmp / "p.jpg"; photo.write_bytes(b"JPEG" * 20)
dm = DataManager("nt", str(tmp / "proj"))
core = AICore(dm, {"monthly_budget_usd": 0})
core.tools.tokens = instagram_auth.TokenStore(tmp / "app.db")   # база есть, строки с токеном нет
dm._data["media_ready"].append({"id": "m1", "name": "p.jpg", "type": "image", "path": str(photo),
                                "status": "approved",
                                "remote_url": "https://res.cloudinary.com/x/p.jpg"})
dm.save()
record = dm._data["media_ready"][0]

# 1. dry-run по умолчанию
r = core.tools.instagram_publish("m1")
print("1 dry-run:", r["summary"])
check("dry-run без токена — отказ", "Токен Instagram не сохранён" in r["summary"], r["summary"])
check("dry-run без токена — не выдаёт себя за проверку", "Проверка прошла" not in r["summary"], r["summary"])

# 2. «настоящая» публикация без токена
r = core.tools.instagram_publish("m1", "0")
print("2 publish:", r["summary"])
check("публикация без токена — отказ", "Токен Instagram не сохранён" in r["summary"], r["summary"])
check("публикация без токена — нет id", "published_id" not in (r.get("effect") or {}), r.get("effect"))
check("публикация без токена — нет отметки", "published_id" not in record and "published" not in record.get("processed", []), record)
check("публикация без токена — статус не тронут", record.get("status") == "approved", record.get("status"))

# 3. статус доступа
r = core.tools.instagram_status()
print("3 status:", r["summary"])
check("статус без токена — отказ", "не сохранён" in r["summary"], r["summary"])

# 4. ни одного сетевого вызова за все три попытки
check("сеть не тронута", not trip.calls, trip.calls)

# 5. журнал: отказ не выглядит успехом
core.run_tool("instagram_publish", media_id="m1", dry_run="0")
rows = [a for a in core.journal.list(10) if a["tool"] == "instagram_publish"]
print("5 журнал:", [(a.get("status"), str(a.get("result"))[:60]) for a in rows])
check("в журнале нет успешной публикации",
      all("ig_" not in str(a.get("result") or "") for a in rows),
      [str(a.get("result"))[:80] for a in rows])

# 6. подтверждение через «да» всё равно упирается в отсутствие токена
core.pending = ("instagram_publish", {"media_id": "m1", "dry_run": "0"})
reply = core.handle("да")
print("6 «да»:", reply.text[:120])
check("«да» без токена — отказ, а не публикация",
      "Токен Instagram не сохранён" in reply.text and "Опубликовал" not in reply.text, reply.text)

# 7. «нет» ничего не запускает
core.pending = ("instagram_publish", {"media_id": "m1", "dry_run": "0"})
reply = core.handle("нет")
check("«нет» отменяет", core.pending is None and "Отменил" in reply.text, reply.text)

# 8. как гейт подтверждения связан с dry-run (наблюдение, без оценки)
spec = core.registry.get("instagram_publish")
print("8 подтверждение:", "dry-run 1 ->", spec.needs_confirmation({"media_id": "m1"}),
      "| dry-run 0 ->", spec.needs_confirmation({"media_id": "m1", "dry_run": "0"}))

instagram_auth.requests.get, instagram_auth.requests.post = orig_get, orig_post
print("FAILS:", fails or "нет")
sys.exit(1 if fails else 0)
