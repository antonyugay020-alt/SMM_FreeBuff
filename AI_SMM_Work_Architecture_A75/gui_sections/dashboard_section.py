"""Dashboard: общая картина по проектам и быстрые действия."""
import logging
from pathlib import Path
from typing import Any, Dict, List

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QGridLayout)
from PySide6.QtCore import Qt, Signal

from gui_theme import TEXT, MUTED, TEAL

logger = logging.getLogger(__name__)


def _project_metrics(project_id: str) -> Dict[str, int]:
    from data_manager import DataManager
    dm = DataManager(project_id)
    stats = dm.get_stats()
    return {
        "plan": len(dm.get_content_plan()),
        "events": len(dm.get_calendar_events()),
        "shots": len(dm.get_shooting_tasks()),
        "media": len(dm.get_media_sources()) + len(dm.get_media_references()) + len(dm.get_media_ready()),
        "pending": stats.get("pending", 0),
    }


class MetricCard(QFrame):
    """Big number + caption."""

    def __init__(self, value: str, caption: str, color: str = TEXT, parent=None):
        super().__init__(parent)
        self.setObjectName("zone")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(2)
        number = QLabel(value)
        number.setStyleSheet(f"color: {color}; font-size: 24px; font-weight: 700;")
        layout.addWidget(number)
        label = QLabel(caption)
        label.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
        layout.addWidget(label)


class ProjectCard(QFrame):
    """One project with its counters and actions."""

    open_requested = Signal(str)
    folder_requested = Signal(str)

    def __init__(self, project: Dict[str, Any], metrics: Dict[str, int], current: bool, parent=None):
        super().__init__(parent)
        self.setObjectName("zone")
        self.project_id = project["id"]

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        head = QHBoxLayout()
        name = QLabel(project["name"])
        name.setStyleSheet(f"color: {TEXT}; font-size: 15px; font-weight: 700;")
        head.addWidget(name)
        if current:
            chip = QLabel("текущий")
            chip.setStyleSheet(
                f"color: {TEAL}; font-size: 10px; border: 1px solid {TEAL};"
                " border-radius: 8px; padding: 1px 8px;")
            head.addWidget(chip)
        head.addStretch()
        layout.addLayout(head)

        if project.get("description"):
            desc = QLabel(project["description"])
            desc.setWordWrap(True)
            desc.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
            layout.addWidget(desc)

        counters = QLabel(
            f"{metrics['plan']} позиций плана · {metrics['events']} событий · "
            f"{metrics['shots']} ТЗ · {metrics['media']} медиа")
        counters.setStyleSheet(f"color: #c9d1d9; font-size: 11px;")
        layout.addWidget(counters)

        buttons = QHBoxLayout()
        open_btn = QPushButton("Открыть")
        open_btn.setObjectName("topBtn")
        open_btn.setProperty("class", "primary")
        open_btn.clicked.connect(lambda: self.open_requested.emit(self.project_id))
        buttons.addWidget(open_btn)

        folder_btn = QPushButton("📂 Папка")
        folder_btn.setObjectName("topBtn")
        folder_btn.clicked.connect(lambda: self.folder_requested.emit(self.project_id))
        buttons.addWidget(folder_btn)
        buttons.addStretch()
        layout.addLayout(buttons)


class DashboardSection(QWidget):
    """Overview of all projects + quick actions."""

    open_project = Signal(str)
    open_folder = Signal(str)
    create_project = Signal()
    navigate = Signal(str)

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
        box.setSpacing(16)

        title = QLabel("Дашборд")
        title.setStyleSheet(f"color: {TEXT}; font-size: 22px; font-weight: 700;")
        box.addWidget(title)

        subtitle = QLabel("Все проекты, их наполнение и быстрые действия")
        subtitle.setStyleSheet(f"color: {MUTED}; font-size: 12px;")
        box.addWidget(subtitle)

        current_id = self.state.get("current_project_id") or "default"
        projects = self._projects()
        totals = {"plan": 0, "events": 0, "shots": 0, "media": 0}
        metrics_by_id = {}
        for project in projects:
            try:
                metrics = _project_metrics(project["id"])
            except Exception as exc:
                logger.warning(f"dashboard metrics failed for {project['id']}: {exc}")
                metrics = {"plan": 0, "events": 0, "shots": 0, "media": 0, "pending": 0}
            metrics_by_id[project["id"]] = metrics
            for key in totals:
                totals[key] += metrics.get(key, 0)

        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)
        stats_row.addWidget(MetricCard(str(len(projects)), "проектов", TEAL))
        stats_row.addWidget(MetricCard(str(totals["plan"]), "позиций плана"))
        stats_row.addWidget(MetricCard(str(totals["events"]), "событий в календаре"))
        stats_row.addWidget(MetricCard(str(totals["media"]), "медиафайлов"))
        box.addLayout(stats_row)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        create_btn = QPushButton("＋ Новый проект")
        create_btn.setObjectName("topBtn")
        create_btn.setProperty("class", "primary")
        create_btn.clicked.connect(self.create_project.emit)
        actions.addWidget(create_btn)

        for text, target in (("🎯 Стратегия", "strategy"), ("📅 Календарь", "calendar"),
                             ("📢 Публикации", "publications"), ("⚙️ Настройки", "settings")):
            btn = QPushButton(text)
            btn.setObjectName("topBtn")
            btn.clicked.connect(lambda checked=False, t=target: self.navigate.emit(t))
            actions.addWidget(btn)
        actions.addStretch()
        box.addLayout(actions)

        heading = QLabel("Проекты")
        heading.setStyleSheet(f"color: {TEXT}; font-size: 14px; font-weight: 700; margin-top: 6px;")
        box.addWidget(heading)

        if not projects:
            empty = QLabel("Проектов пока нет. Создайте первый — база и папка появятся сами.")
            empty.setStyleSheet(f"color: {MUTED}; font-size: 12px; padding: 18px;")
            box.addWidget(empty)
        else:
            grid = QGridLayout()
            grid.setSpacing(12)
            for index, project in enumerate(projects):
                card = ProjectCard(project, metrics_by_id[project["id"]],
                                   current=project["id"] == current_id)
                card.open_requested.connect(self.open_project.emit)
                card.folder_requested.connect(self.open_folder.emit)
                grid.addWidget(card, index // 2, index % 2)
            box.addLayout(grid)

        box.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
