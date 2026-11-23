"""Проверка самого живого прогона: live_agent.py против двойника Ollama.

Живой qwen3:8b нужен только на машине пользователя. Здесь проверяется, что
`work/tests/live_agent.py` действительно доводит задачи до конца и не падает
на своём коде: поднимается локальный HTTP-двойник Ollama, который отвечает
шагами агента, и живой скрипт запускается как есть.
"""
import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
APP = HERE.parents[1] / "AI_SMM_Work_Architecture_A75"
fails = []


def check(name, cond, extra=""):
    print(("OK   " if cond else "FAIL ") + name + ("" if cond else f" :: {extra}"))
    if not cond:
        fails.append(name)


SECTIONS = [{"id": "about", "title": "О проекте", "content": "Кофейня у дома."},
            {"id": "audience", "title": "Аудитория", "content": "Жители района."},
            {"id": "usp", "title": "Отличие", "content": "Своя обжарка."}]
TOPICS = [{"topic": "Свежая обжарка каждое утро", "rubric": "продукт", "format": "Пост"},
          {"topic": "Что взять, если не пьёте кофе", "rubric": "меню", "format": "Пост"},
          {"topic": "Как выбрать зерно домой", "rubric": "продукт", "format": "Пост"},
          {"topic": "Завтрак за 5 минут", "rubric": "меню", "format": "Пост"},
          {"topic": "Кто обжаривает ваш кофе", "rubric": "люди", "format": "Пост"}]


def answer(system, user):
    if "AI SMM Manager" in system:
        # только сама задача: в промпте есть ещё диалог и история шагов
        task = user.split("Задача пользователя:", 1)[-1].splitlines()[0].strip().lower()
        done = (user.split("Уже сделано:")[-1]
                .split("Доступные инструменты:")[0].lower())
        if "подтвердил" in user.lower():
            # после «да» агент продолжает задачу сам: проверка и ТЗ без новой фразы
            if "validate_plan" not in done:
                return json.dumps({"tool": "validate_plan", "args": {}}, ensure_ascii=False)
            if "create_shooting_task" not in done:
                return json.dumps({"tool": "create_shooting_task", "args": {}}, ensure_ascii=False)
            return json.dumps({"action": "done", "say": "Довёл: подписи, проверка и ТЗ."},
                              ensure_ascii=False)
        if "проверь" in task:
            if "validate_plan" not in done:
                return json.dumps({"tool": "validate_plan", "args": {}}, ensure_ascii=False)
            return json.dumps({"action": "done", "say": "Проверка: план в порядке."},
                              ensure_ascii=False)
        if "create_content_plan" not in done:
            count = 5 if "5 постов" in task else 3
            return json.dumps({"tool": "create_content_plan", "args": {"count": count}},
                              ensure_ascii=False)
        if "write_captions" not in done:
            return json.dumps({"tool": "write_captions", "args": {}}, ensure_ascii=False)
        return json.dumps({"action": "done", "say": "Готово: план и подписи."},
                          ensure_ascii=False)
    if '"sections"' in system:
        return json.dumps({"sections": SECTIONS}, ensure_ascii=False)
    if '"topics"' in system:
        return json.dumps({"topics": TOPICS}, ensure_ascii=False)
    if "SMM-копирайтер" in system:
        return "Свежая обжарка каждое утро — заходите за чашкой."
    return "ок"


AGENT_FORMATS = []


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self.reply({"models": [{"name": "qwen3:8b"}]} if self.path.startswith("/api/tags") else {})

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
            payload = json.loads(self.rfile.read(length) or b"{}")
            messages = payload.get("messages") or [{}, {}]
            system = str((messages[0] or {}).get("content") or "")
            user = str((messages[1] or {}).get("content") or "")
            if "AI SMM Manager" in system:
                AGENT_FORMATS.append(payload.get("format"))
        except Exception:
            self.reply({"message": {"content": "ок"}})
            return
        self.reply({"message": {"content": answer(system, user)},
                    "prompt_eval_count": 20, "eval_count": 20})


server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
host = f"http://127.0.0.1:{server.server_address[1]}"

env = dict(os.environ, LIVE_AGENT_HOST=host, LIVE_AGENT_MODEL="qwen3:8b",
           QT_QPA_PLATFORM="offscreen", PYTHONIOENCODING="utf-8:replace")
result = subprocess.run([sys.executable, str(HERE / "live_agent.py")],
                        capture_output=True, text=True, env=env, cwd=str(HERE),
                        encoding="utf-8", errors="replace", timeout=240)
server.shutdown()

out = result.stdout
print(out[-1500:])
if result.stderr.strip():
    print(result.stderr[-800:])
check("живой скрипт завершился без провалов", result.returncode == 0,
      f"код {result.returncode}")
check("прошёл все четыре задачи", out.count("шаги:") == 4, out.count("шаги:"))
check("в первой задаче было два шага", "create_content_plan, write_captions" in out)
check("подписи появились", "есть подписи у постов" in out and "FAIL" not in out.split("есть подписи")[1][:8])
check("итог: провалов 0", "провалов: 0" in out)
check("шаг агента идёт в Ollama с format=json",
      bool(AGENT_FORMATS) and all(one == "json" for one in AGENT_FORMATS), AGENT_FORMATS)

print("\nLIVE_HARNESS_DONE")
raise SystemExit(1 if fails else 0)
