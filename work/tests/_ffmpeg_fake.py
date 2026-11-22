"""Подмена ffmpeg/ffprobe в модуле приложения: одинаково на Linux и Windows.

PATH-заглушки не годятся: на Windows `subprocess.run(["ffmpeg", ...])` ищет
только `.exe`, а шелл-скрипт с `#!/bin/sh` не запускается вовсе. Поэтому тесты
подменяют `subprocess` в самом модуле, который зовёт ffmpeg.

    patch_ffmpeg(video_processor)                  # конвертация пишет FAKEVIDEO
    patch_ffmpeg(pubs, poster_source=poster_png)   # ffmpeg копирует картинку
    patch_ffmpeg(pubs, available=False)            # ffmpeg «не установлен»
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

PROBE_JSON = json.dumps({
    "streams": [{"codec_type": "video", "width": 1080, "height": 1920,
                 "r_frame_rate": "30000/1001", "codec_name": "h264"}],
    "format": {"duration": "12.5"},
})


class _Done:
    """Ответ subprocess.run: только то, что читает приложение."""

    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = ""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class _FakeSubprocess:
    """Минимальная замена модуля subprocess для ffmpeg/ffprobe."""

    TimeoutExpired = TimeoutError
    SubprocessError = OSError
    PIPE = -1
    STDOUT = -2
    DEVNULL = -3

    def __init__(self, poster_source=None, payload: bytes = b"FAKEVIDEO",
                 available: bool = True, probe: str = PROBE_JSON):
        self.poster_source = Path(poster_source) if poster_source else None
        self.payload = payload
        self.available = available
        self.probe = probe

    def run(self, cmd, capture_output=True, text=False, timeout=None, **kwargs):
        if not self.available:
            raise FileNotFoundError("ffmpeg не установлен")
        args = [str(part) for part in cmd]
        tool = Path(args[0]).name if args else ""
        if tool.startswith("ffprobe"):
            return _Done(0, self.probe, "")
        if args[1:2] == ["-version"]:
            return _Done(0, "ffmpeg version fake", "")
        target = Path(args[-1])
        target.parent.mkdir(parents=True, exist_ok=True)
        if self.poster_source is not None:
            shutil.copyfile(self.poster_source, target)
        else:
            target.write_bytes(self.payload)
        return _Done(0, "", "")


def patch_ffmpeg(module, **kwargs) -> _FakeSubprocess:
    """Подменить `subprocess` в модуле и вернуть заглушку (восстанавливать не нужно)."""
    fake = _FakeSubprocess(**kwargs)
    module.subprocess = fake
    return fake
