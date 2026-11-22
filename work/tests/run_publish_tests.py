"""Тесты публикации в Instagram одной командой.

Запуск из папки проекта:

    python work/tests/run_publish_tests.py

Ничего не публикует: токен подставной, сеть заменена заглушкой.
Код возврата 0 — все проверки прошли, 1 — есть провалы.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> int:
    files = sorted(HERE.glob("test_*.py"))
    if not files:
        print(f"Не нашёл тестов рядом: {HERE}")
        return 2
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    fails: list[str] = []
    for path in files:
        result = subprocess.run([sys.executable, str(path)], capture_output=True, text=True,
                                env=env, cwd=str(HERE), timeout=300)
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
    print(f"\nтестов: {len(files)}, провалов: {len(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
