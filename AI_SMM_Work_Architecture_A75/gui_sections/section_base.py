"""Shared base for the content-chain sections: DataManager + AI core wiring."""
import logging
from typing import Any, Optional

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Signal

logger = logging.getLogger(__name__)


class DataSection(QWidget):
    """Section that reads/writes project data and journals changes through AICore."""

    data_changed = Signal()

    def __init__(self, data_manager, settings=None, parent=None):
        super().__init__(parent)
        self.dm = data_manager
        self.settings = settings
        self._core = None

    def core(self):
        if self._core is None and self.dm is not None:
            from ai_core import AICore
            self._core = AICore(self.dm, self.settings)
        return self._core

    def run_full(self, tool: str, **args) -> str:
        """Run a journaled tool and return its whole text (first line is the summary)."""
        core = self.core()
        if core is None:
            return "Нет проекта"
        try:
            reply = core.run_tool(tool, **args)
        except Exception as exc:
            logger.exception("tool %s failed", tool)
            return f"Ошибка: {exc}"
        if reply.actions:
            self.data_changed.emit()
        return reply.text or ""

    def run(self, tool: str, **args) -> str:
        """Run a journaled tool and return its first line for the status bar."""
        text = self.run_full(tool, **args)
        return text.splitlines()[0] if text else ""

    def add(self, section: str, fields: dict) -> str:
        return self.run("add_record", section=section, fields=fields)

    def update(self, section: str, item_id: str, fields: dict) -> str:
        return self.run("edit_record", section=section, item_id=item_id, fields=fields)

    def delete(self, section: str, item_id: str) -> str:
        return self.run("delete_record", section=section, item_id=item_id)
