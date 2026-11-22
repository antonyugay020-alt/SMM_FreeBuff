"""Вся регрессия одной командой.

    python work/tests/run_tests.py              # все проверки
    python work/tests/run_tests.py --publish    # только публикация в Instagram
    python work/tests/run_tests.py test_c4.py   # одна проверка по имени

Ничего не публикует и не трогает проект: тесты работают во временных каталогах,
сеть заменена заглушками, токен подставной.
Код возврата 0 — все проверки прошли, 1 — есть провалы.
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
APP = ROOT / "AI_SMM_Work_Architecture_A75"

PUBLISH_TESTS = {
    "test_host_media.py", "test_token_store.py", "test_publish.py",
    "test_publish_notoken.py", "test_publish_route.py",
}


def _app_python() -> Path | None:
    """Python с зависимостями приложения, если он есть: START.bat ждёт venv в корне, не в app."""
    candidates = [ROOT / "venv" / "Scripts" / "python.exe", ROOT / "venv" / "bin" / "python",
                  APP / ".venv" / "Scripts" / "python.exe", APP / ".venv" / "bin" / "python"]
    return next((path for path in candidates if path.is_file()), None)


SCRIPT = (HERE / "run_tests.py").relative_to(ROOT)


def hint() -> str:
    """Что делать без cryptography: сначала существующий venv, иначе установка зависимостей."""
    python = _app_python()
    lines = ["Не хватает пакета cryptography — он нужен приложению, а не тестам."]
    if python:
        lines += ["  Запустить тем же Python, что у приложения:", f"    {python} {SCRIPT}"]
    lines += ["  Поставить зависимости в свой Python:",
              f"    pip install -r {APP / 'requirements.txt'}"]
    return "\n".join(lines) + "\n"


def _stdout_encoding() -> str:
    """Кодировка консоли: на Windows cp1251 не умеет часть символов и падает на печати."""
    try:
        return sys.stdout.encoding or "utf-8"
    except Exception:
        return "utf-8"


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    publish_only = "--publish" in argv
    names = [arg for arg in argv if not arg.startswith("-")]
    files = sorted(HERE.glob("test_*.py"))
    if publish_only:
        files = [path for path in files if path.name in PUBLISH_TESTS]
    if names:
        wanted = {name if name.endswith(".py") else f"{name}.py" for name in names}
        files = [path for path in files if path.name in wanted]
    if not files:
        print(f"Не нашёл тестов рядом: {HERE}")
        return 2
    if importlib.util.find_spec("cryptography") is None:
        print(hint())
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    env.setdefault("PYTHONIOENCODING", f"{_stdout_encoding()}:replace")
    fails: list[str] = []
    for path in files:
        result = subprocess.run([sys.executable, str(path)], capture_output=True, text=True,
                                env=env, cwd=str(HERE), timeout=600,
                                encoding="utf-8", errors="replace")
        passed = result.returncode == 0
        print(("  OK  " if passed else " FAIL ") + path.name)
        if passed:
            tail = [line for line in result.stdout.splitlines() if line.strip()]
            if tail:
                print("       " + tail[-1][:100])
        else:
            fails.append(path.name)
            print(result.stdout[-3000:])
            if result.stderr.strip():
                print(result.stderr[-1500:])
            if "No module named 'cryptography'" in (result.stdout + result.stderr):
                print("  ^ не хватает cryptography — как поставить, см. подсказку выше.")
    print(f"\nтестов: {len(files)}, провалов: {len(fails)}")
    if fails:
        print("провалились: " + ", ".join(fails))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
