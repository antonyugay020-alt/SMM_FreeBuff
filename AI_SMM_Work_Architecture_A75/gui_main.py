"""Main window: global menu | project block | project sections. Resizable via QSplitter."""
import inspect
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QScrollArea, QFrame, QComboBox, QLineEdit, QProgressBar, QSplitter,
    QInputDialog, QMessageBox)
from PySide6.QtCore import Qt, Signal, QUrl
from PySide6.QtGui import QFont, QDesktopServices

from gui_theme import DARK_THEME_QSS
from gui_ai_panel import AIPanel
from gui_settings import Settings
from data_manager import DataManager

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parent.parent

GLOBAL_NAV = [
    ("dashboard", "📊", "Дашборд"),
    ("projects", "📁", "Проекты"),
    ("settings", "⚙️", "Настройки"),
]

PROJECT_SECTIONS = [
    ("strategy", "🎯", "Стратегия"),
    ("brand_profile", "🧬", "Бренд-профиль"),
    ("content_plan", "📝", "Контент-план"),
    ("calendar", "📅", "Календарь"),
    ("shooting_tasks", "🎬", "Задания на съемку"),
    ("media_content", "🖼️", "Медиа-контент"),
    ("publications", "📢", "Публикации"),
    ("analytics", "📊", "Аналитика"),
    ("plans", "📐", "Планы и схемы"),
    ("other", "📦", "Материалы"),
]

SIMPLE_SECTIONS = {
    "content_plan": ("gui_sections.content_plan_section", "ContentPlanSection"),
    "calendar": ("gui_sections.calendar_section", "CalendarSection"),
    "shooting_tasks": ("gui_sections.shooting_tasks_section", "ShootingTasksSection"),
    "publications": ("gui_sections.publications_section", "PublicationsSection"),
    "analytics": ("gui_sections.analytics_section", "AnalyticsSection"),
    "plans": ("gui_sections.plans_section", "PlansSection"),
    "media_content": ("gui_sections.media_content_section", "MediaContentSection"),
    "other": ("gui_sections.other_materials_section", "OtherMaterialsSection"),
}

SECTION_TITLES = {
    "dashboard": ("Дашборд", "Общая картина по всем проектам"),
    "projects": ("Проекты", "Управление проектами"),
    "settings": ("Настройки", "Настройки приложения"),
    "strategy": ("Стратегия", "Целевая аудитория, позиционирование, анализ конкурентов"),
    "content_plan": ("Контент-план", "Планирование публикаций и рубрик"),
    "calendar": ("Календарь", "Визуальное планирование по дням"),
    "shooting_tasks": ("Задания на съемку", "ТЗ для фотографа/оператора"),
    "media_content": ("Медиа-контент", "Исходники, эталоны, готовые материалы"),
    "publications": ("Публикации", "Управление готовым контентом и планирование публикаций"),
    "analytics": ("Аналитика", "Метрики публикаций: охват, реакции, вовлечённость"),
    "plans": ("Планы и схемы", "План публикаций и стратегия в PDF"),
    "other": ("Материалы", "Архив, буфер, документы, референсы, шаблоны"),
    "brand_profile": ("Бренд-профиль", "Вход для стратегии и ТЗ: ниша, аудитория, tone of voice"),
}


def fmt_size(num_bytes: int) -> str:
    """Human readable size for the storage bar."""
    size = float(num_bytes or 0)
    for unit in ("Б", "КБ", "МБ"):
        if size < 1024:
            return f"{int(size)} Б" if unit == "Б" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} ГБ"

SECTIONS_WITH_IMPL = {"publications", "media_content"}

SPLITTER_STYLE = """
QSplitter::handle {
    background-color: #30363d;
}
QSplitter::handle:hover {
    background-color: #58a6ff;
}
"""


class MainWindow(QMainWindow):
    def __init__(self, app_state: Dict[str, Any]):
        super().__init__()
        self.state = app_state
        self._provided_dm = app_state.get("data_manager")
        self.data_manager = self._provided_dm or DataManager(project_id="default")
        self.state["data_manager"] = self.data_manager
        self.current_section = "strategy"
        self.projects: List[Dict[str, Any]] = []
        self.current_project_id = "default"
        self.settings = app_state.get("settings") or Settings()
        self.state["settings"] = self.settings
        self.setWindowTitle("AI SMM Manager")
        self.resize(1600, 950)
        self.setStyleSheet(DARK_THEME_QSS)
        self._build_ui()
        self._load_projects()
        self._on_nav("strategy")

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # === LEFT PANEL ===
        left = QWidget()
        left.setObjectName("leftPanel")
        left.setMinimumWidth(180)
        left.setMaximumWidth(500)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        logo = QLabel("AI SMM MANAGER")
        logo.setObjectName("logo")
        left_layout.addWidget(logo)

        self.global_buttons = {}
        for item_id, icon, label in GLOBAL_NAV:
            btn = QPushButton(f"{icon}  {label}")
            btn.setObjectName("navBtn")
            btn.clicked.connect(lambda checked, sid=item_id: self._on_nav(sid))
            self.global_buttons[item_id] = btn
            left_layout.addWidget(btn)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background-color: #30363d; max-height: 1px; margin: 8px 12px;")
        left_layout.addWidget(sep)

        proj_selector_label = QLabel("ПРОЕКТ")
        proj_selector_label.setObjectName("projectBlock")
        left_layout.addWidget(proj_selector_label)

        self.project_combo = QComboBox()
        self.project_combo.setObjectName("projectCombo")
        self.project_combo.currentIndexChanged.connect(self._on_project_changed)
        left_layout.addWidget(self.project_combo)

        self.proj_preview = QLabel("📷")
        self.proj_preview.setAlignment(Qt.AlignCenter)
        self.proj_preview.setMinimumHeight(80)
        self.proj_preview.setStyleSheet("background-color: #0d1117; border-radius: 4px; margin: 8px; font-size: 32px;")
        left_layout.addWidget(self.proj_preview)

        self.proj_name = QLabel("Не выбран")
        self.proj_name.setObjectName("projectName")
        left_layout.addWidget(self.proj_name)

        self.proj_stats = QLabel("0 исходников\n0 готовых\n0 на проверке")
        self.proj_stats.setObjectName("projectStats")
        left_layout.addWidget(self.proj_stats)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet("background-color: #30363d; max-height: 1px; margin: 8px 12px;")
        left_layout.addWidget(sep2)

        sections_label = QLabel("РАЗДЕЛЫ ПРОЕКТА")
        sections_label.setObjectName("projectBlock")
        left_layout.addWidget(sections_label)

        self.section_buttons = {}
        sections_scroll = QScrollArea()
        sections_scroll.setWidgetResizable(True)
        sections_scroll.setStyleSheet("border: none; background: transparent;")
        sections_widget = QWidget()
        sections_layout = QVBoxLayout(sections_widget)
        sections_layout.setContentsMargins(8, 4, 8, 4)
        sections_layout.setSpacing(4)

        for item_id, icon, label in PROJECT_SECTIONS:
            btn = QPushButton(f"{icon}  {label}")
            btn.setObjectName("navBtn")
            btn.clicked.connect(lambda checked, sid=item_id: self._on_nav(sid))
            self.section_buttons[item_id] = btn
            sections_layout.addWidget(btn)

        sections_layout.addStretch()
        sections_scroll.setWidget(sections_widget)
        left_layout.addWidget(sections_scroll, stretch=1)

        materials_label = QLabel("МАТЕРИАЛЫ")
        materials_label.setObjectName("projectBlock")
        left_layout.addWidget(materials_label)

        self.materials_scroll = QScrollArea()
        self.materials_scroll.setObjectName("plainScroll")
        self.materials_scroll.setWidgetResizable(True)
        self.materials_scroll.setFixedHeight(116)
        self.materials_scroll.setFrameShape(QFrame.NoFrame)
        self.materials_box = QWidget()
        self.materials_layout = QVBoxLayout(self.materials_box)
        self.materials_layout.setContentsMargins(8, 0, 8, 0)
        self.materials_layout.setSpacing(2)
        self.materials_layout.addStretch()
        self.materials_scroll.setWidget(self.materials_box)
        left_layout.addWidget(self.materials_scroll)

        storage_label = QLabel("Хранилище проекта")
        storage_label.setObjectName("projectBlock")
        left_layout.addWidget(storage_label)

        self.storage_text = QLabel("0 Б")
        self.storage_text.setObjectName("projectStats")
        left_layout.addWidget(self.storage_text)

        self.storage_bar = QProgressBar()
        self.storage_bar.setObjectName("storageBar")
        self.storage_bar.setValue(0)
        self.storage_bar.setTextVisible(False)
        self.storage_bar.setFixedHeight(8)
        self.storage_bar.setStyleSheet("margin: 0 8px 10px 8px;")
        left_layout.addWidget(self.storage_bar)

        # === CENTER ===
        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)

        top_bar = QWidget()
        top_bar.setObjectName("topBar")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(16, 10, 16, 10)

        self.section_title = QLabel("Публикации")
        self.section_title.setObjectName("sectionTitle")
        top_layout.addWidget(self.section_title)

        self.section_subtitle = QLabel("")
        self.section_subtitle.setObjectName("sectionSubtitle")
        top_layout.addWidget(self.section_subtitle)

        top_layout.addStretch()

        self.ai_toggle = QPushButton("🤖 Панель AI")
        self.ai_toggle.setObjectName("topBtn")
        self.ai_toggle.setCheckable(True)
        self.ai_toggle.setChecked(True)
        self.ai_toggle.clicked.connect(self._toggle_ai_panel)
        top_layout.addWidget(self.ai_toggle)

        search = QLineEdit()
        search.setObjectName("searchBox")
        search.setPlaceholderText("🔍 Поиск по файлам, тегам, описанию...")
        search.setFixedWidth(280)
        top_layout.addWidget(search)

        refresh_btn = QPushButton("🔄 Обновить")
        refresh_btn.setObjectName("topBtn")
        top_layout.addWidget(refresh_btn)

        import_btn = QPushButton("📥 Импорт медиа")
        import_btn.setObjectName("topBtn")
        import_btn.setProperty("class", "accent")
        import_btn.clicked.connect(self._on_import_media)
        top_layout.addWidget(import_btn)

        center_layout.addWidget(top_bar)

        self.workspace_scroll = QScrollArea()
        self.workspace_scroll.setObjectName("workspaceScroll")
        self.workspace_scroll.setWidgetResizable(True)
        self.workspace_scroll.setFrameShape(QFrame.NoFrame)

        self.workspace_content = QWidget()
        self.workspace_layout = QVBoxLayout(self.workspace_content)
        self.workspace_layout.setContentsMargins(0, 0, 0, 0)
        self.workspace_layout.setSpacing(0)

        self.workspace_scroll.setWidget(self.workspace_content)
        center_layout.addWidget(self.workspace_scroll, stretch=1)

        # === RIGHT: AI Panel ===
        self.ai_panel = AIPanel(self.state)
        self.ai_panel.setMinimumWidth(400)
        self.ai_panel.setMaximumWidth(600)

        # === MAIN SPLITTER ===
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.addWidget(left)
        self.main_splitter.addWidget(center)
        self.main_splitter.addWidget(self.ai_panel)
        self.main_splitter.setStretchFactor(0, 0)
        self.main_splitter.setStretchFactor(1, 1)
        self.main_splitter.setStretchFactor(2, 0)
        self.main_splitter.setSizes([240, 1000, 360])
        self.main_splitter.setHandleWidth(4)
        self.main_splitter.setStyleSheet(SPLITTER_STYLE)

        main_layout.addWidget(self.main_splitter)

        self.statusBar().showMessage("Готов к работе")

    def _load_projects(self):
        pm = self.state.get("project_manager")
        if pm:
            self.projects = pm.list_projects()
            if not self.projects:
                pm.create_project("default", "Новый проект", "")
                self.projects = pm.list_projects()

        self.project_combo.blockSignals(True)
        self.project_combo.clear()
        for proj in self.projects:
            self.project_combo.addItem(proj["name"], proj["id"])
        self.project_combo.blockSignals(False)

        if self.projects:
            known = any(p["id"] == self.current_project_id for p in self.projects)
            target = self.current_project_id if known else self.projects[0]["id"]
            self._switch_project(target)

    def _use_project(self, project_id: str):
        """Switch the shared DataManager to the selected project."""
        self.current_project_id = project_id
        self.state["current_project_id"] = project_id
        provided = self.state.get("data_manager")
        if provided is not None and getattr(provided, "project_id", None) == project_id:
            self.data_manager = provided
        else:
            self.data_manager = DataManager(project_id)
        self.state["data_manager"] = self.data_manager
        if hasattr(self, "ai_panel"):
            self.ai_panel.set_data_manager(self.data_manager)
        self.refresh_stats()

    def _on_nav(self, section_id: str):
        self.current_section = section_id
        
        for sid, btn in self.global_buttons.items():
            btn.setProperty("active", sid == section_id)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        
        for sid, btn in self.section_buttons.items():
            btn.setProperty("active", sid == section_id)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        title, subtitle = SECTION_TITLES.get(section_id, (section_id, ""))
        self.section_title.setText(title)
        self.section_subtitle.setText(subtitle)

        while self.workspace_layout.count():
            item = self.workspace_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()

        if section_id == "strategy":
            from gui_sections.strategy_section import StrategySection
            strategy = StrategySection(self.data_manager, self.settings)
            strategy.navigate.connect(self._on_nav)
            strategy.data_changed.connect(self.refresh_stats)
            self.workspace_layout.addWidget(strategy)
        elif section_id == "dashboard":
            from gui_sections.dashboard_section import DashboardSection
            dashboard = DashboardSection(self.state)
            dashboard.open_project.connect(self._switch_project)
            dashboard.open_folder.connect(self._open_project_folder)
            dashboard.create_project.connect(self._on_create_project)
            dashboard.navigate.connect(self._on_nav)
            self.workspace_layout.addWidget(dashboard)
        elif section_id == "projects":
            from gui_sections.projects_section import ProjectsSection
            projects = ProjectsSection(self.state)
            projects.create_project.connect(self._on_create_project)
            projects.switch_project.connect(self._switch_project)
            projects.rename_project.connect(self._on_rename_project)
            projects.open_folder.connect(self._open_project_folder)
            self.workspace_layout.addWidget(projects)
        elif section_id == "settings":
            from gui_sections.settings_section import SettingsSection
            self.workspace_layout.addWidget(SettingsSection(self.state))
        elif section_id == "brand_profile":
            from gui_sections.brand_profile_section import BrandProfileSection
            self.workspace_layout.addWidget(BrandProfileSection(self.data_manager))
        elif section_id in SIMPLE_SECTIONS:
            module_name, class_name = SIMPLE_SECTIONS[section_id]
            module = __import__(module_name, fromlist=[class_name])
            cls = getattr(module, class_name)
            takes_settings = "settings" in inspect.signature(cls.__init__).parameters
            widget = cls(self.data_manager,
                         self.settings) if takes_settings else cls(self.data_manager)
            if hasattr(widget, "data_changed"):
                widget.data_changed.connect(self.refresh_stats)
            self.workspace_layout.addWidget(widget)
        else:
            placeholder = QLabel(f'Раздел "{title}" — в разработке')
            placeholder.setAlignment(Qt.AlignCenter)
            placeholder.setStyleSheet("color: #8b949e; font-size: 16px; padding: 60px;")
            self.workspace_layout.addWidget(placeholder)

        self.statusBar().showMessage(f"Раздел: {title}")

    def _on_import_media(self):
        """Real file import dialog."""
        from PySide6.QtWidgets import QFileDialog
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Импорт медиа",
            str(Path.home()),
            "Медиа файлы (*.jpg *.jpeg *.png *.gif *.mp4 *.mov *.avi *.webp *.psd)"
        )
        if not files:
            return
        
        imported = 0
        for f in files:
            result = self.data_manager.add_media_source(f)
            if result:
                imported += 1
        
        self.refresh_stats()
        if imported > 0:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                "Импорт завершён",
                f"Импортировано файлов: {imported}\n\n"
                f"Файлы добавлены в раздел 'Медиа-контент → Исходники'."
            )
            # Refresh current section if it's media_content
            if self.current_section == "media_content":
                self._on_nav("media_content")

    def refresh_stats(self):
        """Recompute and show project stats in the left panel from DataManager."""
        try:
            stats = self.data_manager.get_stats()
            self.proj_stats.setText(
                f"{stats['sources']} исходников\n"
                f"{stats['ready']} готовых\n"
                f"{stats['pending']} на проверке\n"
                f"{stats['scheduled']} запланировано"
            )
        except Exception as e:
            logger.warning(f"refresh_stats failed: {e}")
        self._rebuild_materials()
        self._update_storage_bar()

    def _on_project_changed(self, index: int):
        if index < 0 or index >= len(self.projects):
            return
        self._switch_project(self.projects[index]["id"])

    # === Project actions ===
    def _switch_project(self, project_id: str):
        """Make the project current everywhere: combo, data manager, workspace."""
        proj = next((p for p in self.projects if p["id"] == project_id), None)
        if proj is None:
            pm = self.state.get("project_manager")
            proj = pm.get_project(project_id) if pm else None
        if proj is None:
            return

        index = self.project_combo.findData(project_id)
        if index >= 0 and index != self.project_combo.currentIndex():
            self.project_combo.blockSignals(True)
            self.project_combo.setCurrentIndex(index)
            self.project_combo.blockSignals(False)

        self.proj_name.setText(proj["name"])
        self._use_project(project_id)
        self._on_nav(self.current_section)
        self.statusBar().showMessage(f"Проект: {proj['name']}")

    def _on_create_project(self):
        name, ok = QInputDialog.getText(self, "Новый проект", "Название проекта:")
        name = (name or "").strip()
        if not ok or not name:
            return
        pm = self.state.get("project_manager")
        if pm is None:
            return
        project_id = f"p{datetime.now().strftime('%Y%m%d%H%M%S')}"
        if not pm.create_project(project_id, name, ""):
            QMessageBox.warning(self, "Проект", "Не удалось создать проект. Смотрите лог.")
            return
        self._load_projects()
        self._switch_project(project_id)
        self.statusBar().showMessage(f"Создан проект: {name}")

    def _on_rename_project(self, project_id: str, name: str):
        pm = self.state.get("project_manager")
        if pm is None or not pm.rename_project(project_id, name):
            return
        self._load_projects()
        self._switch_project(project_id)
        self.statusBar().showMessage(f"Проект переименован: {name}")

    def _open_project_folder(self, project_id: str):
        pm = self.state.get("project_manager")
        if pm is None:
            return
        path = pm.project_dir(project_id)
        path.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
        self.statusBar().showMessage(f"Папка проекта: {path}")

    def _toggle_ai_panel(self, checked: bool):
        self.ai_panel.setVisible(checked)
        self.ai_toggle.setText("🤖 Панель AI" if checked else "🤖 Показать AI")

    # === Sidebar extras ===
    def _rebuild_materials(self):
        """Show the latest media of the current project in the sidebar."""
        while self.materials_layout.count():
            item = self.materials_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()

        media: List[Dict[str, Any]] = []
        try:
            media = (list(self.data_manager.get_media_ready())
                     + list(self.data_manager.get_media_sources())
                     + list(self.data_manager.get_media_references()))
        except Exception as exc:
            logger.warning(f"materials feed failed: {exc}")

        media.sort(key=lambda m: str(m.get("date") or ""), reverse=True)
        if not media:
            empty = QLabel("Пока пусто")
            empty.setStyleSheet("color: #6b7480; font-size: 11px; padding: 4px 6px;")
            self.materials_layout.addWidget(empty)
            self.materials_layout.addStretch()
            return

        for entry in media[:8]:
            name = (entry.get("name") or "файл")[:26]
            btn = QPushButton(f"• {name}")
            btn.setObjectName("navBtn")
            btn.setToolTip(str(entry.get("name") or ""))
            btn.clicked.connect(lambda checked=False: self._on_nav("media_content"))
            self.materials_layout.addWidget(btn)
        self.materials_layout.addStretch()

    def _update_storage_bar(self):
        try:
            path = Path(self.data_manager.data_dir)
            size = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
        except Exception:
            size = 0
        limit_gb = float(self.settings.get("storage_limit_gb") or 200)
        limit = limit_gb * 1024 ** 3
        self.storage_bar.setValue(min(100, int(size / limit * 100)) if limit else 0)
        self.storage_text.setText(f"{fmt_size(size)} из {limit_gb:.0f} ГБ")
