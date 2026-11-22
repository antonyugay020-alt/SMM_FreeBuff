"""Projects: создание, переименование, переключение, папка проекта."""
import logging
from typing import Any, Dict, List

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QInputDialog)
from PySide6.QtCore import Signal

from gui_theme import TEXT, MUTED, TEAL

logger = logging.getLogger(__name__)


class ProjectRow(QFrame):
    """One project line with actions."""

    switch_requested = Signal(str)
    rename_requested = Signal(str)
    folder_requested = Signal(str)

    def __init__(self, project: Dict[str, Any], current: bool, parent=None):
        super().__init__(parent)
        self.setObjectName("zone")
        self.project_id = project["id"]

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(14)

        info = QVBoxLayout()
        info.setSpacing(2)
        name = QLabel(project["name"])
        name.setStyleSheet(f"color: {TEXT}; font-size: 14px; font-weight: 700;")
        info.addWidget(name)
        detail = project.get("description") or "без описания"
        created = (project.get("created_at") or "")[:10]
        sub = QLabel(f"{detail} · создан {created}")
        sub.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
        info.addWidget(sub)
        layout.addLayout(info, stretch=1)

        if current:
            chip = QLabel("текущий")
            chip.setStyleSheet(
                f"color: {TEAL}; font-size: 10px; border: 1px solid {TEAL};"
                " border-radius: 8px; padding: 1px 8px;")
            layout.addWidget(chip)

        open_btn = QPushButton("Открыть")
        open_btn.setObjectName("topBtn")
        open_btn.setProperty("class", "primary")
        open_btn.clicked.connect(lambda: self.switch_requested.emit(self.project_id))
        layout.addWidget(open_btn)

        rename_btn = QPushButton("Переименовать")
        rename_btn.setObjectName("topBtn")
        rename_btn.clicked.connect(lambda: self.rename_requested.emit(self.project_id))
        layout.addWidget(rename_btn)

        folder_btn = QPushButton("📂 Папка")
        folder_btn.setObjectName("topBtn")
        folder_btn.clicked.connect(lambda: self.folder_requested.emit(self.project_id))
        layout.addWidget(folder_btn)


class ProjectsSection(QWidget):
    """Project management screen."""

    create_project = Signal()
    switch_project = Signal(str)
    rename_project = Signal(str, str)
    open_folder = Signal(str)

    def __init__(self, app_state: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.state = app_state
        self._build_ui()

    def _projects(self) -> List[Dict[str, Any]]:
        pm = self.state.get("project_manager")
        return pm.list_projects() if pm else []

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setObjectName("plainScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        box = QVBoxLayout(content)
        box.setContentsMargins(24, 20, 24, 24)
        box.setSpacing(14)

        header = QHBoxLayout()
        title = QLabel("Проекты")
        title.setStyleSheet(f"color: {TEXT}; font-size: 22px; font-weight: 700;")
        header.addWidget(title)
        header.addStretch()
        create_btn = QPushButton("＋ Новый проект")
        create_btn.setObjectName("topBtn")
        create_btn.setProperty("class", "primary")
        create_btn.clicked.connect(self.create_project.emit)
        header.addWidget(create_btn)
        box.addLayout(header)

        subtitle = QLabel("У каждого проекта своя база `data/projects/<id>/project.db` и своя папка")
        subtitle.setStyleSheet(f"color: {MUTED}; font-size: 12px;")
        box.addWidget(subtitle)

        projects = self._projects()
        current_id = self.state.get("current_project_id") or "default"

        if not projects:
            empty = QLabel("Проектов пока нет. Нажмите «Новый проект».")
            empty.setStyleSheet(f"color: {MUTED}; font-size: 12px; padding: 18px;")
            box.addWidget(empty)
        for project in projects:
            row = ProjectRow(project, current=project["id"] == current_id)
            row.switch_requested.connect(self.switch_project.emit)
            row.rename_requested.connect(self._on_rename_clicked)
            row.folder_requested.connect(self.open_folder.emit)
            box.addWidget(row)

        box.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _on_rename_clicked(self, project_id: str):
        names = {p["id"]: p["name"] for p in self._projects()}
        name, ok = QInputDialog.getText(self, "Переименовать проект", "Новое название:",
                                        text=names.get(project_id, ""))
        name = name.strip()
        if not ok or not name:
            return
        self.rename_project.emit(project_id, name)
