"""App settings stored in config/settings.json.

Only user-editable preferences live here; project data stays in SQLite.
"""
import json
import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parent.parent
SETTINGS_PATH = ROOT_DIR / "config" / "settings.json"

DEFAULTS: Dict[str, Any] = {
    "provider": "ollama",              # ollama | cloud
    "local_model": "qwen3:8b",
    "cloud_model": "claude-haiku-4.5",
    "cloud_endpoint": "https://openrouter.ai/api/v1",
    "monthly_budget_usd": 30,
    "budget_used_usd": 0.0,
    "projects_dir": str(ROOT_DIR / "data" / "projects"),
    "backups_dir": str(ROOT_DIR / "backups"),
    "backup_on_save": True,
    "backup_keep": 10,
    "storage_limit_gb": 200,
}


class Settings:
    """Tiny JSON settings store with defaults; survives restarts."""

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else SETTINGS_PATH
        self._values: Dict[str, Any] = dict(DEFAULTS)
        self.load()

    def load(self) -> Dict[str, Any]:
        if not self.path.exists():
            return self._values
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception as exc:  # broken file must not block the app
            logger.warning(f"settings load failed: {exc}")
            return self._values
        if isinstance(raw, dict):
            self._values.update({k: v for k, v in raw.items() if k in DEFAULTS})
        return self._values

    def save(self) -> bool:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps(self._values, ensure_ascii=False, indent=2, sort_keys=True),
                encoding="utf-8")
            return True
        except Exception as exc:
            logger.error(f"settings save failed: {exc}")
            return False

    # dict-like access
    def get(self, key: str, default: Any = None) -> Any:
        return self._values.get(key, DEFAULTS.get(key, default))

    def set(self, key: str, value: Any) -> None:
        self._values[key] = value

    def update(self, values: Dict[str, Any]) -> None:
        self._values.update({k: v for k, v in values.items() if k in DEFAULTS})

    def as_dict(self) -> Dict[str, Any]:
        return dict(self._values)
