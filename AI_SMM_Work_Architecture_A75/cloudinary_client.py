"""Cloudinary: загрузка файла по публичному URL и удаление загруженного (шаг D2).

Секреты берутся только из окружения: CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY,
CLOUDINARY_API_SECRET. Значения не логируются и не попадают в журнал действий.
"""
from __future__ import annotations

import hashlib
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tif", ".tiff", ".svg"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}


def resource_type_for(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in IMAGE_SUFFIXES:
        return "image"
    if suffix in VIDEO_SUFFIXES:
        return "video"
    return "raw"


class CloudinaryError(RuntimeError):
    """Публичная ошибка без секретов: что именно не получилось."""


class CloudinaryClient:
    """Минимальный клиент upload/destroy поверх REST API, без SDK."""

    def __init__(self, cloud_name: str, api_key: str, api_secret: str):
        self.cloud_name = cloud_name
        self.api_key = api_key
        self.api_secret = api_secret
        self.base = f"https://api.cloudinary.com/v1_1/{cloud_name}"

    @classmethod
    def from_env(cls) -> Optional["CloudinaryClient"]:
        """Клиент из переменных окружения; без них — None (вызывающий объясняет, чего не хватает)."""
        cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME", "").strip()
        api_key = os.environ.get("CLOUDINARY_API_KEY", "").strip()
        api_secret = os.environ.get("CLOUDINARY_API_SECRET", "").strip()
        if not (cloud_name and api_key and api_secret):
            return None
        return cls(cloud_name, api_key, api_secret)

    def _sign(self, params: Dict[str, str]) -> str:
        text = "&".join(f"{key}={params[key]}" for key in sorted(params))
        return hashlib.sha1((text + self.api_secret).encode("utf-8")).hexdigest()

    def upload(self, file_path: str, public_id: str) -> Dict[str, Any]:
        """Загрузить файл; возвращает {"url", "public_id", "resource_type"}."""
        path = Path(file_path)
        if not path.is_file():
            raise CloudinaryError(f"файл не найден: {path.name}")
        resource_type = resource_type_for(path)
        timestamp = str(int(time.time()))
        params = {"timestamp": timestamp, "public_id": public_id}
        data = {"api_key": self.api_key, "timestamp": timestamp,
                "public_id": public_id, "signature": self._sign(params)}
        try:
            with path.open("rb") as handle:
                response = requests.post(
                    f"{self.base}/{resource_type}/upload",
                    data=data, files={"file": (path.name, handle)},
                    timeout=180)
        except requests.RequestException as exc:
            raise CloudinaryError(f"сеть к Cloudinary недоступна: {exc}") from exc
        if response.status_code != 200:
            raise CloudinaryError(
                f"Cloudinary отклонил загрузку ({response.status_code}): "
                f"{_error_message(response)}")
        body = response.json()
        url = body.get("secure_url") or ""
        loaded_id = body.get("public_id") or public_id
        if not url:
            raise CloudinaryError("Cloudinary вернул ответ без публичного URL")
        return {"url": url, "public_id": loaded_id,
                "resource_type": body.get("resource_type") or resource_type}

    def delete(self, public_id: str, resource_type: str = "image") -> bool:
        """Удалить загруженный ресурс; True, если удалился или его уже нет."""
        timestamp = str(int(time.time()))
        params = {"public_id": public_id, "timestamp": timestamp}
        data = {"api_key": self.api_key, "timestamp": timestamp,
                "public_id": public_id, "signature": self._sign(params)}
        try:
            response = requests.post(
                f"{self.base}/{resource_type}/destroy", data=data, timeout=60)
        except requests.RequestException as exc:
            logger.warning("cloudinary delete failed: %s", exc)
            return False
        if response.status_code != 200:
            logger.warning("cloudinary delete rejected (%s): %s",
                           response.status_code, _error_message(response))
            return False
        result = (response.json() or {}).get("result", "")
        return result in ("ok", "not found")


def _error_message(response: Any) -> str:
    try:
        return str((response.json() or {}).get("error", {}).get("message") or "")[:200]
    except ValueError:
        return ""
