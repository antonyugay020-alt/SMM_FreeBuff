"""Локальная модель: выбор из установленных, загрузка в память, понятные сообщения."""
import json, os, socket, sys, tempfile, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

APP = Path(__file__).resolve().parents[2] / "AI_SMM_Work_Architecture_A75"
sys.path.insert(0, str(APP))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from ai_core import AICore, MODEL_LIBRARY, LOCAL_MODEL_PREFERENCE
from data_manager import DataManager


def ok(name, cond, extra=""):
    print(("MODEL_OK " if cond else "MODEL_FAIL ") + name + ("" if cond else f" :: {extra}"))
    if not cond:
        raise SystemExit(1)


class _Handler(BaseHTTPRequestHandler):
    models = []
    chats = 0

    def log_message(self, *args):
        pass

    def _send(self, payload, code=200):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/tags":
            self._send({"models": [{"name": name} for name in type(self).models]})
        else:
            self._send({}, 404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        self.rfile.read(length)
        if self.path == "/api/chat":
            type(self).chats += 1
            self._send({"message": {"content": "ok"}})
        else:
            self._send({}, 404)


server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{server.server_address[1]}"

with socket.socket() as probe:
    probe.bind(("127.0.0.1", 0))
    DEAD = f"http://127.0.0.1:{probe.getsockname()[1]}"


def make_core(model="qwen2.5:7b-instruct", host=URL):
    dm = DataManager("model_test", tempfile.mkdtemp(prefix="model_test_"))
    core = AICore(dm, {"local_model": model},
                  app_db_path=Path(tempfile.mkdtemp(prefix="model_db_")) / "app.db")
    core.local.host = host
    return core


INSTALLED = ["gemma3:4b", "qwen3:8b", "nomic-embed-text:latest", "qwen2.5-coder:7b",
             "llama3.1:8b", "deepseek-r1:8b"]

# --- настроенной модели нет: берём установленную из списка предпочтений ---
_Handler.models = INSTALLED
_Handler.chats = 0
core = make_core("qwen2.5:7b-instruct")
state = core.ensure_local_model()
ok("выбрана установленная модель", state["state"] == "ready" and state["model"] == "qwen3:8b", state)
ok("модель переключена в провайдере", core.local.model == "qwen3:8b"
   and core.router.local.model == "qwen3:8b", core.local.model)
ok("модель загружена в память", state["loaded"] and _Handler.chats == 1, _Handler.chats)
ok("о подмене сказано", state["switched"] and "qwen2.5:7b-instruct" in state["message"], state)

# --- настроенная модель есть ---
_Handler.models = INSTALLED + ["qwen2.5:7b-instruct"]
core = make_core("qwen2.5:7b-instruct")
state = core.ensure_local_model()
ok("своя модель не подменяется",
   state["state"] == "ready" and not state["switched"] and state["model"] == "qwen2.5:7b-instruct",
   state)

# --- ничего подходящего не скачано: команда и ссылка ---
_Handler.models = ["nomic-embed-text:latest"]
core = make_core("qwen2.5:7b-instruct")
state = core.ensure_local_model()
ok("нечего выбрать — состояние missing", state["state"] == "missing", state)
ok("команда скачивания", state.get("command") == f"ollama pull {LOCAL_MODEL_PREFERENCE[0]}", state)
ok("ссылка на модель", f"{MODEL_LIBRARY}/qwen3" in state["message"], state["message"])
ok("видно, что установлено", "nomic-embed-text" in state.get("installed", ""), state)

# --- Ollama не запущен ---
core = make_core("qwen3:8b", host=DEAD)
state = core.ensure_local_model()
ok("offline без падения", state["state"] == "offline", state)
ok("offline подсказывает ollama serve", "ollama serve" in state["message"], state["message"])

# --- has_model понимает теги ---
provider = core.local
provider.host = URL
_Handler.models = INSTALLED
ok("has_model без тега", provider.has_model("qwen3"), provider.models())
ok("has_model с тегом", provider.has_model("qwen3:8b"))
ok("has_model чужой модели", not provider.has_model("qwen2.5:7b-instruct"))

# --- панель показывает только то, что требует внимания ---
from PySide6.QtWidgets import QApplication, QLabel
from gui_ai_panel import AIPanel

app = QApplication([])
panel = AIPanel({"settings": {}})


def texts():
    return [label.text() for label in panel.findChildren(QLabel)]


before = len(texts())
panel._show_model_state({"state": "ready", "model": "qwen3:8b", "switched": False,
                         "message": "Модель qwen3:8b загружена."})
ok("тихая загрузка не спамит", len(texts()) == before, texts()[-3:])

panel._show_model_state({"state": "ready", "model": "qwen3:8b", "switched": True,
                         "message": "В настройках была «x», её нет — работаю на «qwen3:8b»."})
ok("подмена модели видна", any("работаю на" in text for text in texts()), texts()[-3:])

panel._show_model_state({"state": "missing", "model": "x",
                         "message": "Модели «x» нет. Скачайте:\n\n    ollama pull qwen3:8b"})
ok("отсутствие модели видно вместе с командой",
   any("ollama pull qwen3:8b" in text for text in texts()), texts()[-3:])

# --- автоподмена сохраняется в настройках ---
from gui_settings import Settings

settings_path = Path(tempfile.mkdtemp(prefix="model_settings_")) / "settings.json"
settings = Settings(settings_path)
panel2 = AIPanel({"settings": settings})
panel2._show_model_state({"state": "ready", "switched": True, "model": "qwen3:8b",
                          "message": "В настройках была «qwen2.5:7b-instruct», её нет — работаю на «qwen3:8b»."})
ok("модель записана в настройки", settings.get("local_model") == "qwen3:8b",
   settings.as_dict())
ok("запись на диске",
   json.loads(settings_path.read_text(encoding="utf-8"))["local_model"] == "qwen3:8b")
ok("в чате сказано про запись",
   any("Записал в настройки" in text for text in
       [label.text() for label in panel2.findChildren(QLabel)]))
reloaded = Settings(settings_path)
ok("выбор переживает перезапуск", reloaded.get("local_model") == "qwen3:8b", reloaded.as_dict())

_Handler.models = INSTALLED
dm2 = DataManager("model_test2", tempfile.mkdtemp(prefix="model_test2_"))
core2 = AICore(dm2, reloaded,
               app_db_path=Path(tempfile.mkdtemp(prefix="model_db2_")) / "app.db")
core2.local.host = URL
state2 = core2.ensure_local_model()
ok("повторного переключения нет", state2["state"] == "ready" and not state2["switched"], state2)

# --- словарь вместо Settings тоже подходит ---
plain = AIPanel({"settings": {}})
plain._show_model_state({"state": "ready", "switched": True, "model": "qwen3:8b",
                         "message": "подмена"})
ok("словарь настроек обновлён", plain.state["settings"].get("local_model") == "qwen3:8b",
   plain.state["settings"])

print("LOCAL_MODEL_OK")
