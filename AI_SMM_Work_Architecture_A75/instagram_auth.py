"""Instagram: токен в зашифрованном виде и read-only проверка доступа (шаг D3).

Токен лежит в общей `data/app.db` (таблица `instagram_token`), значение шифруется Fernet.
Ключ берётся из `AI_SMM_TOKEN_KEY`, иначе создаётся `data/.token_key` с правами 0600.
Токен не попадает ни в `settings.json`, ни в журнал действий, ни в текст ошибок.
"""
from __future__ import annotations

import logging
import os
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import requests
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

GRAPH_URL = "https://graph.instagram.com"
PROFESSIONAL = ("BUSINESS", "CREATOR")
SCHEMA = """
CREATE TABLE IF NOT EXISTS instagram_token (
    id           INTEGER PRIMARY KEY CHECK (id = 1),
    token_enc    TEXT,
    ig_user_id   TEXT,
    username     TEXT,
    account_type TEXT,
    updated_at   TEXT
);
"""


class TokenError(RuntimeError):
    """Проблема с токеном без раскрытия значения."""


def mask(token: str) -> str:
    """Показать только последние 4 символа: остальное не выводим ни в UI, ни в отчёт."""
    token = str(token or "")
    return f"…{token[-4:]}" if len(token) >= 8 else "…"


def _scrub(text: str, secret: str) -> str:
    """Убрать токен из текста: URL с `access_token` попадает в сообщения requests."""
    return str(text).replace(secret, "***") if secret else str(text)


class TokenStore:
    """Хранилище токена: одна строка в `app.db`, шифртекст + публичные поля аккаунта."""

    def __init__(self, db_path: Path, key: Optional[bytes] = None):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._fernet = Fernet(key or self._load_key())
        connection = sqlite3.connect(self.db_path)
        try:
            connection.executescript(SCHEMA)
            connection.commit()
        finally:
            connection.close()

    @property
    def key_path(self) -> Path:
        return self.db_path.parent / ".token_key"

    def _load_key(self) -> bytes:
        from_env = os.environ.get("AI_SMM_TOKEN_KEY", "").strip()
        if from_env:
            return from_env.encode("utf-8")
        if self.key_path.is_file():
            return self.key_path.read_bytes().strip()
        key = Fernet.generate_key()
        self.key_path.write_bytes(key)
        try:
            self.key_path.chmod(0o600)
        except OSError:
            logger.warning("не удалось выставить права 0600 на %s", self.key_path)
        return key

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def save(self, token: str, account: Optional[Dict[str, Any]] = None) -> None:
        token = str(token or "").strip()
        if not token:
            raise TokenError("пустой токен сохранять нечего")
        account = account or {}
        connection = self._connect()
        try:
            connection.execute(
                "INSERT INTO instagram_token(id, token_enc, ig_user_id, username,"
                " account_type, updated_at) VALUES (1, ?, ?, ?, ?, ?)"
                " ON CONFLICT(id) DO UPDATE SET token_enc=excluded.token_enc,"
                " ig_user_id=excluded.ig_user_id, username=excluded.username,"
                " account_type=excluded.account_type, updated_at=excluded.updated_at",
                (self._fernet.encrypt(token.encode("utf-8")).decode("ascii"),
                 str(account.get("ig_user_id") or ""), str(account.get("username") or ""),
                 str(account.get("account_type") or ""),
                 datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            connection.commit()
        finally:
            connection.close()

    def load_token(self) -> str:
        row = self._row()
        if not row or not row["token_enc"]:
            return ""
        try:
            return self._fernet.decrypt(str(row["token_enc"]).encode("ascii")).decode("utf-8")
        except (InvalidToken, ValueError) as exc:
            raise TokenError("не удалось расшифровать токен: ключ не подходит") from exc

    def account(self) -> Dict[str, str]:
        row = self._row()
        if not row:
            return {}
        return {"ig_user_id": row["ig_user_id"] or "", "username": row["username"] or "",
                "account_type": row["account_type"] or "",
                "updated_at": row["updated_at"] or ""}

    def clear(self) -> None:
        connection = self._connect()
        try:
            connection.execute("DELETE FROM instagram_token")
            connection.commit()
        finally:
            connection.close()

    def _row(self) -> Optional[sqlite3.Row]:
        connection = self._connect()
        try:
            return connection.execute("SELECT * FROM instagram_token WHERE id = 1").fetchone()
        finally:
            connection.close()


def check_access(token: str, http: Any = requests) -> Dict[str, Any]:
    """Read-only проверка: аккаунт отвечает, токен жив, тип профессиональный."""
    token = str(token or "").strip()
    if not token:
        return {"ok": False, "reason": "токен Instagram не задан"}
    try:
        response = http.get(f"{GRAPH_URL}/me",
                            params={"fields": "id,username,account_type",
                                    "access_token": token}, timeout=20)
    except Exception as exc:  # сеть: текст исключения может содержать URL с токеном
        return {"ok": False, "reason": "сеть недоступна: " + _scrub(str(exc), token)}

    try:
        body = response.json() or {}
    except ValueError:
        body = {}
    if getattr(response, "status_code", 0) != 200 or body.get("error"):
        error = body.get("error") or {}
        reason = _scrub(str(error.get("message") or "Graph API не ответил"), token)
        if str(error.get("code")) == "190" or "190" in str(error.get("code") or ""):
            reason = "токен просрочен или отозван: получи новый"
        return {"ok": False, "reason": reason}

    account_type = str(body.get("account_type") or "").upper()
    result = {"ok": True, "ig_user_id": str(body.get("id") or ""),
              "username": str(body.get("username") or ""),
              "account_type": account_type,
              "professional": account_type in PROFESSIONAL}
    if not result["professional"]:
        result["ok"] = False
        result["reason"] = ("аккаунт @" + (result["username"] or result["ig_user_id"])
                            + ": нужен Business или Creator, сейчас "
                            + (account_type or "неизвестно"))
    return result


# --- Публикация (шаг D4): контейнер → media_publish. Все вызовы сети идут через `_publish_call`. ---

PUBLISH_TIMEOUT_SEC = 60
PUBLISH_POLL_SEC = 5


class PublishError(RuntimeError):
    """Graph API отказал или не дождался готовности контейнера."""


def _graph_error(response: Any, token: str) -> str:
    try:
        body = response.json() or {}
    except ValueError:
        body = {}
    error = body.get("error") or {}
    return _scrub(str(error.get("message") or f"Graph API ответил {getattr(response, 'status_code', '?')}"),
                  token)


def _publish_call(token: str, method: str, path: str, http: Any, timeout: int, **kwargs: Any) -> Dict[str, Any]:
    """Один вызов Graph API: сеть и отказ Graph превращаются в PublishError без токена в тексте."""
    try:
        response = getattr(http, method)(f"{GRAPH_URL}/{path}", timeout=timeout, **kwargs)
    except Exception as exc:  # текст исключения может содержать URL с токеном
        raise PublishError("сеть недоступна: " + _scrub(str(exc), token))
    if getattr(response, "status_code", 0) != 200:
        raise PublishError(_graph_error(response, token))
    return response.json() or {}


def publishing_limit(token: str, ig_user_id: str, http: Any = requests) -> Dict[str, int]:
    """Read-only: сколько публикаций осталось в скользящие 24 часа."""
    body = _publish_call(token, "get", f"{ig_user_id}/content_publishing_limit", http, 20,
                         params={"fields": "config,quota_usage", "access_token": token})
    data = body.get("data") or [{}]
    usage = int(data[0].get("quota_usage") or 0)
    total = int((data[0].get("config") or {}).get("quota_total") or 50)
    return {"used": usage, "total": total, "left": max(total - usage, 0)}


def create_container(token: str, ig_user_id: str, media: Dict[str, Any], http: Any = requests) -> str:
    """POST /{ig-user-id}/media — контейнер публикации; возвращает его id."""
    payload = {"access_token": token, "media_type": media["media_type"],
               ("video_url" if media["is_video"] else "image_url"): media["url"]}
    body = _publish_call(token, "post", f"{ig_user_id}/media", http, 60, data=payload)
    container = str(body.get("id") or "")
    if not container:
        raise PublishError("Graph API не вернул id контейнера")
    return container


def wait_container(token: str, container_id: str, http: Any = requests,
                   timeout: int = PUBLISH_TIMEOUT_SEC, poll: int = PUBLISH_POLL_SEC,
                   sleep: Any = None) -> None:
    """Ждём FINISHED; для видео это может занять время. Ограничено по времени."""
    sleep = sleep or time.sleep
    waited = 0
    while True:
        body = _publish_call(token, "get", container_id, http, 20,
                             params={"fields": "status_code", "access_token": token})
        status = str(body.get("status_code") or "")
        if status == "FINISHED":
            return
        if status in ("ERROR", "EXPIRED"):
            raise PublishError(f"контейнер в статусе {status}: загрузите материал заново")
        if waited >= timeout:
            raise PublishError("Instagram ещё обрабатывает файл — контейнер не опубликован, повторите позже")
        sleep(poll)
        waited += poll


def media_publish(token: str, ig_user_id: str, container_id: str, http: Any = requests) -> str:
    """POST /{ig-user-id}/media_publish — возвращает id опубликованного медиа."""
    body = _publish_call(token, "post", f"{ig_user_id}/media_publish", http, 60,
                         data={"creation_id": container_id, "access_token": token})
    published = str(body.get("id") or "")
    if not published:
        raise PublishError("Graph API не вернул id публикации")
    return published
