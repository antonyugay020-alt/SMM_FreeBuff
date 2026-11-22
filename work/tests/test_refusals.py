"""Пять типовых отказов Meta на подставном Graph API: текст сообщения и отсутствие токена."""
import sys, tempfile
from pathlib import Path
APP = Path(__file__).resolve().parents[2] / "AI_SMM_Work_Architecture_A75"
PROJECT = APP.parent
WORK = Path(tempfile.mkdtemp(prefix="smm_test_"))
import sys, tempfile
from pathlib import Path

ROOT = APP
sys.path.insert(0, str(APP))
from data_manager import DataManager
from ai_core import AICore
import instagram_auth

TOKEN = "IGQVJ_super_secret_98765"
ORIG_WAIT = instagram_auth.wait_container
fails = []


class Resp:
    def __init__(self, status, body):
        self.status_code, self._b = status, body

    def json(self):
        return self._b


class Graph:
    """Подставной Graph API. mode: 190 | personal | pending | quota | net_me | net_publish."""

    def __init__(self, mode):
        self.mode = mode
        self.published = 0

    def get(self, url, params=None, timeout=None):
        if self.mode == "net_me":
            raise ConnectionError(f"HTTPSConnectionPool: /me?access_token={TOKEN} failed")
        if url.endswith("/me"):
            if self.mode == "190":
                return Resp(400, {"error": {"code": 190, "message":
                                            "Error validating access token: Session has expired " + TOKEN}})
            kind = "PERSONAL" if self.mode == "personal" else "BUSINESS"
            return Resp(200, {"id": "1789", "username": "studio", "account_type": kind})
        if "content_publishing_limit" in url:
            used = 50 if self.mode == "quota" else 3
            return Resp(200, {"data": [{"config": {"quota_total": 50}, "quota_usage": used}]})
        if "cont_1" in url:
            return Resp(200, {"status_code": "IN_PROGRESS"})
        return Resp(404, {"error": {"message": "unknown"}})

    def post(self, url, data=None, timeout=None):
        if self.mode == "net_publish":
            raise ConnectionError(f"ReadTimeout: POST {url} data=access_token={TOKEN}")
        if url.endswith("/media"):
            return Resp(200, {"id": "cont_1"})
        if url.endswith("/media_publish"):
            self.published += 1
            return Resp(200, {"id": "ig_999"})
        return Resp(404, {"error": {"message": "unknown"}})


def build(mode, tmp):
    photo = tmp / "beach.jpg"
    photo.write_bytes(b"JPEG" * 50)
    dm = DataManager("d5", str(tmp / "proj"))
    core = AICore(dm, {"monthly_budget_usd": 0})
    db = tmp / "app.db"
    instagram_auth.TokenStore(db).save(TOKEN, {"username": "studio", "account_type": "BUSINESS",
                                               "ig_user_id": "1789"})
    core.tools.tokens = instagram_auth.TokenStore(db)
    dm._data["media_ready"].append({"id": "m1", "name": "beach.jpg", "type": "image",
                                    "path": str(photo), "status": "approved",
                                    "remote_url": "https://res.cloudinary.com/x/beach.jpg"})
    dm.save()
    graph = Graph(mode)
    instagram_auth.requests.get = graph.get
    instagram_auth.requests.post = graph.post
    # ждать 60 с в тесте незачем: подменяем sleep, поведение цикла ожидания то же
    instagram_auth.wait_container = lambda t, c: ORIG_WAIT(t, c, sleep=lambda _s: None)
    return core, graph


CASES = [
    ("код 190 (токен просрочен)", "190", "1"),
    ("аккаунт не профессиональный", "personal", "1"),
    ("контейнер не дошёл до FINISHED", "pending", "0"),
    ("лимит 0 из 50", "quota", "1"),
    ("сеть недоступна на /me", "net_me", "1"),
    ("сеть недоступна при публикации", "net_publish", "0"),
]

for title, mode, dry in CASES:
    tmp = Path(tempfile.mkdtemp(prefix="ref_"))
    core, graph = build(mode, tmp)
    result = core.tools.instagram_publish("m1", dry_run=dry)
    text = result["summary"]
    print(f"\n### {title}\n{text}")
    if TOKEN in text:
        fails.append(f"{title}: токен в тексте")
    if not text.strip():
        fails.append(f"{title}: пустое сообщение")
    if mode in ("190", "personal", "quota", "net_me") and graph.published:
        fails.append(f"{title}: опубликовано, хотя не должно")
    if mode == "pending" and graph.published:
        fails.append(f"{title}: media_publish вызван до FINISHED")

print("\nFAILS:", fails or "нет")
sys.exit(1 if fails else 0)
