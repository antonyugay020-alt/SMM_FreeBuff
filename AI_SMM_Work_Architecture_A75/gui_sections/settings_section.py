"""Settings: провайдеры моделей, бюджет, пути хранения, бэкапы."""
import logging
from typing import Any, Dict

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QLineEdit, QComboBox, QCheckBox,
    QSpinBox, QDoubleSpinBox, QFormLayout)
from PySide6.QtCore import Qt, Signal

from gui_theme import TEXT, MUTED, TEAL, BORDER

logger = logging.getLogger(__name__)


class SettingsSection(QWidget):
    """Edits config/settings.json; values survive restarts."""

    saved = Signal()

    def __init__(self, app_state: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.state = app_state
        self.settings = app_state.get("settings")
        self._build_ui()

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

        title = QLabel("Настройки")
        title.setStyleSheet(f"color: {TEXT}; font-size: 22px; font-weight: 700;")
        box.addWidget(title)

        subtitle = QLabel("Сохраняются в `config/settings.json` и подхватываются при запуске")
        subtitle.setStyleSheet(f"color: {MUTED}; font-size: 12px;")
        box.addWidget(subtitle)

        # --- models ---
        models = QFrame()
        models.setObjectName("zone")
        form = QFormLayout(models)
        form.setContentsMargins(18, 16, 18, 16)
        form.setSpacing(10)

        self.provider = QComboBox()
        self.provider.setObjectName("formInput")
        self.provider.addItem("Локально (Ollama)", "ollama")
        self.provider.addItem("Облако (OpenAI-совместимый)", "cloud")
        form.addRow("Провайдер по умолчанию", self.provider)

        self.local_model = QLineEdit()
        self.local_model.setObjectName("formInput")
        self.local_model.setPlaceholderText("qwen2.5:7b-instruct")
        form.addRow("Локальная модель", self.local_model)

        self.cloud_model = QLineEdit()
        self.cloud_model.setObjectName("formInput")
        form.addRow("Облачная модель", self.cloud_model)

        self.cloud_endpoint = QLineEdit()
        self.cloud_endpoint.setObjectName("formInput")
        form.addRow("Облачный эндпоинт", self.cloud_endpoint)
        box.addWidget(models)

        # --- budget ---
        budget = QFrame()
        budget.setObjectName("zone")
        budget_form = QFormLayout(budget)
        budget_form.setContentsMargins(18, 16, 18, 16)
        budget_form.setSpacing(10)

        self.budget = QDoubleSpinBox()
        self.budget.setObjectName("formInput")
        self.budget.setRange(0, 10000)
        self.budget.setDecimals(2)
        self.budget.setSuffix(" $ / мес")
        budget_form.addRow("Лимит на облако", self.budget)

        self.budget_used = QLabel("0.00 $")
        budget_form.addRow("Израсходовано", self.budget_used)
        box.addWidget(budget)

        # --- storage ---
        storage = QFrame()
        storage.setObjectName("zone")
        storage_form = QFormLayout(storage)
        storage_form.setContentsMargins(18, 16, 18, 16)
        storage_form.setSpacing(10)

        self.projects_dir = QLineEdit()
        self.projects_dir.setObjectName("formInput")
        storage_form.addRow("Папка проектов", self.projects_dir)

        self.backups_dir = QLineEdit()
        self.backups_dir.setObjectName("formInput")
        storage_form.addRow("Папка бэкапов", self.backups_dir)

        self.backup_on_save = QCheckBox("Бэкап перед сохранением проекта")
        self.backup_on_save.setObjectName("formCheck")
        storage_form.addRow("", self.backup_on_save)

        self.backup_keep = QSpinBox()
        self.backup_keep.setObjectName("formInput")
        self.backup_keep.setRange(1, 100)
        self.backup_keep.setSuffix(" шт.")
        storage_form.addRow("Хранить бэкапов", self.backup_keep)

        self.storage_limit = QSpinBox()
        self.storage_limit.setObjectName("formInput")
        self.storage_limit.setRange(1, 10000)
        self.storage_limit.setSuffix(" ГБ")
        storage_form.addRow("Лимит хранилища", self.storage_limit)
        box.addWidget(storage)

        buttons = QHBoxLayout()
        save_btn = QPushButton("Сохранить настройки")
        save_btn.setObjectName("topBtn")
        save_btn.setProperty("class", "primary")
        save_btn.clicked.connect(self._on_save)
        buttons.addWidget(save_btn)

        self.status = QLabel("")
        self.status.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
        buttons.addWidget(self.status)
        buttons.addStretch()
        box.addLayout(buttons)

        box.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

        self._load_values()

    def _load_values(self):
        if not self.settings:
            self.status.setText("Хранилище настроек недоступно")
            return
        index = self.provider.findData(self.settings.get("provider"))
        self.provider.setCurrentIndex(max(index, 0))
        self.local_model.setText(str(self.settings.get("local_model") or ""))
        self.cloud_model.setText(str(self.settings.get("cloud_model") or ""))
        self.cloud_endpoint.setText(str(self.settings.get("cloud_endpoint") or ""))
        self.budget.setValue(float(self.settings.get("monthly_budget_usd") or 0))
        self.budget_used.setText(f"{float(self.settings.get('budget_used_usd') or 0):.2f} $")
        self.projects_dir.setText(str(self.settings.get("projects_dir") or ""))
        self.backups_dir.setText(str(self.settings.get("backups_dir") or ""))
        self.backup_on_save.setChecked(bool(self.settings.get("backup_on_save")))
        self.backup_keep.setValue(int(self.settings.get("backup_keep") or 10))
        self.storage_limit.setValue(int(self.settings.get("storage_limit_gb") or 200))

    def _on_save(self):
        if not self.settings:
            return
        self.settings.update({
            "provider": self.provider.currentData(),
            "local_model": self.local_model.text().strip(),
            "cloud_model": self.cloud_model.text().strip(),
            "cloud_endpoint": self.cloud_endpoint.text().strip(),
            "monthly_budget_usd": float(self.budget.value()),
            "projects_dir": self.projects_dir.text().strip(),
            "backups_dir": self.backups_dir.text().strip(),
            "backup_on_save": self.backup_on_save.isChecked(),
            "backup_keep": int(self.backup_keep.value()),
            "storage_limit_gb": int(self.storage_limit.value()),
        })
        ok = self.settings.save()
        self.status.setText("Сохранено" if ok else "Не удалось сохранить")
        self.status.setStyleSheet(f"color: {TEAL if ok else '#f87171'}; font-size: 11px;")
        if ok:
            self.saved.emit()
