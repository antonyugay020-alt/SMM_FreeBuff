"""Тесты публикации в Instagram одной командой.

Запуск из папки проекта:

    python work/tests/run_publish_tests.py

Ничего не публикует: токен подставной, сеть заменена заглушкой.
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
def _venv_python() -> Path:
    """Где лежит Python приложения: Windows и POSIX раскладывают venv по-разному."""
    if os.name == "nt":
        return APP / ".venv" / "Scripts" / "python.exe"
    return APP / ".venv" / "bin" / "python"


SCRIPT = (HERE / "run_publish_tests.py").relative_to(ROOT)

HINT = (
    "Не хватает пакета cryptography — он нужен приложению, а не тестам.\n"
    "  Запустить тем же Python, что у приложения (venv):\n"
    f"    {_venv_python()} {SCRIPT}\n"
    "  Или один раз поставить зависимости в свой Python:\n"
    f"    pip install -r {APP / 'requirements.txt'}\n"
)


def _stdout_encoding() -> str:
    """Кодировка консоли: на Windows cp1251 не умеет «->» и падает на печати."""
    try:
        return sys.stdout.encoding or "utf-8"
    except Exception:
        return "utf-8"


def main() -> int:
    files = sorted(HERE.glob("test_*.py"))
    if not files:
        print(f"Не нашёл тестов рядом: {HERE}")
        return 2
    missing_crypto = importlib.util.find_spec("cryptography") is None
    if missing_crypto:
        print(HINT)
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    env.setdefault("PYTHONIOENCODING", f"{_stdout_encoding()}:replace")
    fails: list[str] = []
    for path in files:
        result = subprocess.run([sys.executable, str(path)], capture_output=True, text=True,
                                env=env, cwd=str(HERE), timeout=300,
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
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
