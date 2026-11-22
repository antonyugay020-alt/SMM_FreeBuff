"""Чат не замирает: ответ ядра считается в фоне, видно «Думаю…», ошибки не молчат."""
import os, sys, tempfile, time
from pathlib import Path
from types import SimpleNamespace

APP = Path(__file__).resolve().parents[2] / "AI_SMM_Work_Architecture_A75"
sys.path.insert(0, str(APP))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel

app = QApplication([])

from ai_core import AIReply, AICore
from data_manager import DataManager
from gui_ai_panel import AIPanel


def ok(name, cond, extra=""):
    print(("ASYNC_OK " if cond else "ASYNC_FAIL ") + name + ("" if cond else f" :: {extra}"))
    if not cond:
        raise SystemExit(1)


def labels(panel):
    return [one.text() for one in panel.findChildren(QLabel)]


def wait_for(panel, needle, limit=8.0):
    started = time.monotonic()
    while time.monotonic() - started < limit:
        app.processEvents()
        if any(needle in text for text in labels(panel)):
            return True
        time.sleep(0.02)
    return False


def wait_gone(panel, prefix, limit=3.0):
    started = time.monotonic()
    while time.monotonic() - started < limit:
        app.processEvents()
        if not any(text.startswith(prefix) for text in labels(panel)):
            return True
        time.sleep(0.02)
    return False


class FakeCore:
    """Ядро, которое «думает»: проверяем, что окно этого не ждёт."""

    def __init__(self, delay=0.6, fail=False):
        self.delay = delay
        self.fail = fail
        self.threads = []
        self.budget = SimpleNamespace(spent_month=lambda: 0.0, limit=30)

    def handle(self, text):
        import threading
        self.threads.append(threading.current_thread().name)
        time.sleep(self.delay)
        if self.fail:
            raise RuntimeError("бум")
        return AIReply(f"Готово: {text}", "rules")


panel = AIPanel({"settings": {}})
panel.resize(400, 600)

core = FakeCore()
panel.ai_core = core
panel.input_box.setPlainText("сделай стратегию")
started = time.monotonic()
panel.send_message()
elapsed = time.monotonic() - started

ok("отправка не ждёт модель", elapsed < 0.3, f"{elapsed:.2f} с")
ok("сообщение появилось сразу", any("сделай стратегию" in t for t in labels(panel)))
ok("виден прогресс", any("Думаю" in t for t in labels(panel)), labels(panel))

panel.input_box.setPlainText("и ещё одну")
panel.send_message()
ok("второй запрос не стартует поверх", any("дождись ответа" in t for t in labels(panel)),
   labels(panel))

ok("ответ пришёл в чат", wait_for(panel, "Готово: сделай стратегию"))
ok("прогресс убран", wait_gone(panel, "⏳ Думаю"), labels(panel))
ok("модель считала не в UI-потоке", core.threads and core.threads[0] != "MainThread",
   core.threads)

panel.ai_core = FakeCore(delay=0.05, fail=True)
panel._send_text("упади")
ok("ошибка видна в чате", wait_for(panel, "Ошибка ядра AI: бум"))
ok("после ошибки прогресс убран", wait_gone(panel, "⏳ Думаю"))

class Dead:
    """Модели нет: результат не должен зависеть от того, запущена ли Ollama на машине."""

    name = "stub"

    def available(self):
        return False

    def chat(self, *args, **kwargs):
        raise AssertionError("без модели никто не должен спрашивать модель")


# --- без модели объясняем причину, а не молчим ---
dm = DataManager("async_test", tempfile.mkdtemp(prefix="ai_async_"))
quiet = AICore(dm, None, providers=(Dead(), None))
reply = quiet.handle("сделай что-нибудь непонятное")
ok("без модели названа причина", "не подключена" in reply.text, reply.text)
ok("ответ не пустой", bool(reply.text.strip()))

print("AI_ASYNC_OK")
