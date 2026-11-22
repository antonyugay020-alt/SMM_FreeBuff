import os, sys, tempfile, logging
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.pop("AI_SMM_TOKEN_KEY", None)
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2] / "AI_SMM_Work_Architecture_A75"
sys.path.insert(0, str(ROOT))
from data_manager import DataManager
from ai_core import AICore
import instagram_auth

def ok(name, cond, extra=""):
    print(("D3_OK " if cond else "D3_FAIL ") + name + ("" if cond else f" :: {extra}"))
    if not cond:
        raise SystemExit(1)

TOKEN = "IGQVJsecretTOKENvalue1234567890abcdWXYZ"
tmp = Path(tempfile.mkdtemp(prefix="d3_"))
db = tmp / "app.db"
store = instagram_auth.TokenStore(db)
store.save(TOKEN, {"username": "studio", "account_type": "BUSINESS", "ig_user_id": "1789"})

ok("токен читается обратно", store.load_token() == TOKEN)
ok("ключ создан отдельно", store.key_path.is_file())
raw = db.read_bytes()
ok("в базе нет открытого токена", TOKEN.encode() not in raw, "нашли плейнтекст")
ok("маска только хвост", instagram_auth.mask(TOKEN) == "…WXYZ", instagram_auth.mask(TOKEN))
ok("аккаунт сохранён", store.account()["username"] == "studio", store.account())

store2 = instagram_auth.TokenStore(db)
ok("переживает перезапуск", store2.load_token() == TOKEN)

wrong = instagram_auth.TokenStore(db, key=instagram_auth.Fernet.generate_key())
try:
    wrong.load_token()
    ok("чужой ключ — ошибка", False)
except instagram_auth.TokenError as exc:
    ok("чужой ключ — понятная ошибка", "ключ не подходит" in str(exc), exc)

class Resp:
    def __init__(self, status, body):
        self.status_code = status
        self._body = body
    def json(self):
        return self._body

class Http:
    def __init__(self, resp):
        self.resp = resp
        self.calls = []
    def get(self, url, params=None, timeout=None):
        self.calls.append((url, params))
        if isinstance(self.resp, Exception):
            raise self.resp
        return self.resp

ok("ok: бизнес-аккаунт",
   instagram_auth.check_access(TOKEN, Http(Resp(200, {"id": "1789", "username": "studio",
        "account_type": "BUSINESS"})))["ok"])
res = instagram_auth.check_access(TOKEN, Http(Resp(200, {"id": "1789", "username": "pers",
        "account_type": "PERSONAL"})))
ok("личный аккаунт отклонён", not res["ok"] and "Business" in res["reason"], res)
res = instagram_auth.check_access(TOKEN, Http(Resp(400, {"error": {"code": 190,
        "message": f"Invalid token {TOKEN}"}})))
ok("код 190 — просрочен", not res["ok"] and "просрочен" in res["reason"], res)
ok("токен вычищен из ошибки", TOKEN not in res["reason"], res)
res = instagram_auth.check_access(TOKEN, Http(BaseException and RuntimeError(
    f"Max retries exceeded with url: /me?access_token={TOKEN}")))
ok("токен вычищен из сетевой ошибки", not res["ok"] and TOKEN not in res["reason"], res)
ok("пустой токен", not instagram_auth.check_access("")["ok"])

os.environ.pop("AI_SMM_TOKEN_KEY", None)
key_env = instagram_auth.Fernet.generate_key().decode()
os.environ["AI_SMM_TOKEN_KEY"] = key_env
env_store = instagram_auth.TokenStore(tmp / "env" / "app.db")
env_store.save(TOKEN)
ok("ключ из env работает", env_store.load_token() == TOKEN)
ok("с env файла ключа нет", not env_store.key_path.exists(), list(env_store.key_path.parent.iterdir()))
os.environ.pop("AI_SMM_TOKEN_KEY", None)

dm = DataManager("d3", str(tmp / "proj"))
core = AICore(dm, {"monthly_budget_usd": 0}, app_db_path=db)
ok("ядро видит сохранённый токен", core.tools._token_store().load_token() == TOKEN)
real_check = instagram_auth.check_access
instagram_auth.check_access = lambda token: {"ok": True, "username": "studio",
    "account_type": "BUSINESS", "ig_user_id": "1789", "professional": True}
r = core.run_tool("instagram_status")
ok("статус доступен", "Доступ есть" in r.text and "studio" in r.text, r.text)
ok("токен не попал в отчёт", TOKEN not in r.text, r.text)
import json
ok("статус не пишется в журнал (read-only)",
   not [e for e in core.journal.list(20) if e["tool"] == "instagram_status"], core.journal.list(3))
ok("токен не попал в журнал", TOKEN not in json.dumps(core.journal.list(20), ensure_ascii=False))
instagram_auth.check_access = lambda token: {"ok": False, "reason": "токен просрочен или отозван"}
r = core.run_tool("instagram_status")
ok("неготовый доступ — отчёт без журнала",
   "не готов" in r.text and not [e for e in core.journal.list(20)
                                if e["tool"] == "instagram_status"], r.text)
core.tools.tokens = instagram_auth.TokenStore(db)
core.tools.tokens.clear()
r = core.run_tool("instagram_status")
ok("без токена — подсказка", "не сохранён" in r.text, r.text)
instagram_auth.check_access = real_check

from PySide6.QtWidgets import QApplication
app = QApplication([])
instagram_auth.TokenStore(db).save(TOKEN, {"username": "studio", "account_type": "BUSINESS",
                                        "ig_user_id": "1789"})
import gui_sections.settings_section as gui_settings
gui_settings.SettingsSection._token_store = lambda self: instagram_auth.TokenStore(db)
sec = gui_settings.SettingsSection({"settings": None})
ok("настройки показывают сохранённый токен", "WXYZ" in sec.instagram_status.text()
   and "studio" in sec.instagram_status.text(), sec.instagram_status.text())
sec._check_token()
ok("кнопка проверки пишет состояние", "доступ" in sec.instagram_status.text().lower(),
   sec.instagram_status.text())
sec._forget_token()
ok("забыть стирает токен", "не сохранён" in sec.instagram_status.text()
   and instagram_auth.TokenStore(db).load_token() == "", sec.instagram_status.text())
print("D3_OK")
