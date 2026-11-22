"""Только проверки публикации в Instagram (часть общей регрессии).

    python work/tests/run_publish_tests.py

Полная регрессия: python work/tests/run_tests.py
"""
from __future__ import annotations

import sys

from run_tests import main

if __name__ == "__main__":
    sys.exit(main(["--publish"]))
