"""Settings: провайдеры моделей, бюджет, пути хранения, бэкапы."""
import logging
from pathlib import Path
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

        model_row = QWidget()
        model_row_layout = QHBoxLayout(model_row)
        model_row_layout.setContentsMargins(0, 0, 0, 0)
        model_row_layout.setSpacing(6)
        self.local_model = QComboBox()
        self.local_model.setObjectName("formInput")
        self.local_model.setMinimumWidth(220)
        model_row_layout.addWidget(self.local_model, stretch=1)
        self.refresh_models_btn = QPushButton("Обновить")
        self.refresh_models_btn.setObjectName("topBtn")
        self.refresh_models_btn.setToolTip("Перечитать список моделей из Ollama")
        self.refresh_models_btn.clicked.connect(lambda: self.refresh_models())
        model_row_layout.addWidget(self.refresh_models_btn)
        form.addRow("Локальная модель", model_row)

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

        # --- Instagram token (шаг D3): не в settings.json, а в app.db в зашифрованном виде ---
        instagram = QFrame()
        instagram.setObjectName("zone")
        insta_form = QFormLayout(instagram)
        insta_form.setContentsMargins(18, 16, 18, 16)
        insta_form.setSpacing(10)

        self.instagram_token = QLineEdit()
        self.instagram_token.setObjectName("formInput")
        self.instagram_token.setEchoMode(QLineEdit.Password)
        self.instagram_token.setPlaceholderText("долгоживущий токен Instagram")
        insta_form.addRow("Токен Instagram", self.instagram_token)

        insta_row = QHBoxLayout()
        insta_save = QPushButton("Сохранить токен")
        insta_save.setObjectName("topBtn")
        insta_save.clicked.connect(self._save_token)
        insta_row.addWidget(insta_save)
        insta_check = QPushButton("Проверить доступ")
        insta_check.setObjectName("topBtn")
        insta_check.clicked.connect(self._check_token)
        insta_row.addWidget(insta_check)
        insta_forget = QPushButton("Забыть")
        insta_forget.setObjectName("topBtn")
        insta_forget.clicked.connect(self._forget_token)
        insta_row.addWidget(insta_forget)
        insta_row.addStretch()
        insta_form.addRow("", insta_row)

        self.instagram_status = QLabel("")
        self.instagram_status.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
        insta_form.addRow("Состояние", self.instagram_status)
        self.cloudinary_status = QLabel("")
        self.cloudinary_status.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
        insta_form.addRow("Cloudinary", self.cloudinary_status)
        self._load_cloudinary_state()
        box.addWidget(instagram)

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
        self._load_token_state()

    # --- Instagram token ---
    def _token_store(self):
        """Хранилище токена: общая база приложения, не база проекта и не settings.json."""
        import instagram_auth

        root = Path(__file__).resolve().parent.parent.parent / "data" / "app.db"
        return instagram_auth.TokenStore(root)

    def _load_cloudinary_state(self):
        """Только наличие переменных окружения: значения не читаем и не показываем."""
        import cloudinary_client

        missing = cloudinary_client.CloudinaryClient.missing_env()
        if missing:
            self.cloudinary_status.setText("не заданы: " + ", ".join(missing))
        else:
            self.cloudinary_status.setText("переменные заданы")

    def _load_token_state(self):
        import instagram_auth

        try:
            store = self._token_store()
            token = store.load_token()
            account = store.account()
        except Exception as exc:
            self.instagram_status.setText(str(exc))
            return
        if not token:
            self.instagram_status.setText("токен не сохранён")
            return
        who = account.get("username") or account.get("ig_user_id") or "аккаунт"
        self.instagram_status.setText(f"сохранён {instagram_auth.mask(token)} · {who}")

    def _save_token(self):
        import instagram_auth

        token = self.instagram_token.text().strip()
        if not token:
            self.instagram_status.setText("вставь токен в поле выше")
            return
        try:
            store = self._token_store()
            result = instagram_auth.check_access(token)
            account = {"username": result.get("username", ""),
                       "account_type": result.get("account_type", ""),
                       "ig_user_id": result.get("ig_user_id", "")} if result.get("ok") else {}
            store.save(token, account)
        except Exception as exc:
            self.instagram_status.setText(str(exc))
            return
        self.instagram_token.clear()
        self._load_token_state()
        if not account:
            self.instagram_status.setText(self.instagram_status.text()
                                          + f" · не проверен: {result.get('reason', '')}")

    def _check_token(self):
        import instagram_auth

        try:
            token = self._token_store().load_token()
        except Exception as exc:
            self.instagram_status.setText(str(exc))
            return
        if not token:
            self.instagram_status.setText("токен не сохранён")
            return
        result = instagram_auth.check_access(token)
        if result.get("ok"):
            self.instagram_status.setText(
                f"доступ есть: @{result.get('username')} ({result.get('account_type')})"
                f" · {instagram_auth.mask(token)}")
        else:
            self.instagram_status.setText("нет доступа: " + str(result.get("reason") or ""))

    def _forget_token(self):
        try:
            self._token_store().clear()
        except Exception as exc:
            self.instagram_status.setText(str(exc))
            return
        self.instagram_token.clear()
        self._load_token_state()

    # --- локальные модели ---
    NOT_INSTALLED = " — не установлена"

    def installed_models(self) -> list:
        """Модели, скачанные в Ollama; пусто, если Ollama не отвечает."""
        try:
            from ai_core import OllamaProvider
            return [name for name in OllamaProvider().models() if name]
        except Exception:
            logger.warning("не удалось прочитать модели Ollama", exc_info=True)
            return []

    def current_model(self) -> str:
        """Имя модели без пометки «не установлена»."""
        data = self.local_model.currentData()
        return str(data or self.local_model.currentText() or "").strip()

    def _fill_models(self, models, current: str) -> None:
        names = [str(name) for name in models]
        self.local_model.blockSignals(True)
        self.local_model.clear()
        for name in names:
            self.local_model.addItem(name, name)
        if current and current not in names:
            self.local_model.addItem(current + self.NOT_INSTALLED, current)
        index = self.local_model.findData(current)
        self.local_model.setCurrentIndex(index if index >= 0 else 0)
        self.local_model.blockSignals(False)

    def refresh_models(self, select: str = "") -> list:
        """Перечитать список из Ollama, сохранив выбранную модель."""
        current = select or self.current_model()
        models = self.installed_models()
        if models:
            self._fill_models(models, current)
            self.status.setText(f"Модели Ollama: {len(models)}")
        elif current:
            self._fill_models([], current)
            self.status.setText("Ollama не отвечает — оставил текущую модель")
        return models

    def _sync_saved_model(self) -> None:
        """Показать модель из настроек, без обращения к Ollama."""
        if not self.settings:
            return
        saved = str(self.settings.get("local_model") or "")
        if not self.local_model.count():
            self.refresh_models(saved)
            return
        index = self.local_model.findData(saved)
        if index < 0 and saved:
            names = [self.local_model.itemData(row) for row in range(self.local_model.count())]
            self._fill_models([name for name in names if name], saved)
        elif index >= 0:
            self.local_model.setCurrentIndex(index)

    def showEvent(self, event):
        super().showEvent(event)
        try:
            self._sync_saved_model()
        except Exception:
            logger.exception("не удалось подхватить сохранённую модель")

    def _load_values(self):
        if not self.settings:
            self.status.setText("Хранилище настроек недоступно")
            return
        index = self.provider.findData(self.settings.get("provider"))
        self.provider.setCurrentIndex(max(index, 0))
        self._sync_saved_model()
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
            "local_model": self.current_model(),
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
