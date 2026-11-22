"""Уборка файлов, которые тест оставляет в папке медиа приложения.

Приложение складывает импортированные копии и результаты обработки в `media/images`
(`ai_core.MEDIA_IMAGES`), а кэш кадров — в `media/images/.thumbs`. Тесты, которым нужна
именно эта папка (там же их ищет GUI), регистрируют уборку через `cleanup_media`:
файлы удаляются и при обычном завершении, и при падении проверки.
"""
from __future__ import annotations

import atexit
from pathlib import Path


def cleanup_media(*patterns: str) -> Path:
    """Удалить файлы по шаблонам из `media/images` и `.thumbs`, вернуть папку медиа."""
    import ai_core

    base = Path(ai_core.MEDIA_IMAGES)

    def run() -> None:
        for pattern in patterns:
            for path in base.glob(pattern):
                if path.is_file():
                    path.unlink(missing_ok=True)
            thumbs = base / ".thumbs"
            for path in thumbs.glob(pattern):
                if path.is_file():
                    path.unlink(missing_ok=True)
        thumbs = base / ".thumbs"
        if thumbs.is_dir() and not any(thumbs.iterdir()):
            thumbs.rmdir()

    run()
    atexit.register(run)
    return base
