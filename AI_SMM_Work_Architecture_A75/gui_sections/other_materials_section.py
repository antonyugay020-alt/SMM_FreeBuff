"""Materials: project files in five fixed folders, imported through the AI core."""
from pathlib import Path

from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QListWidget, QListWidgetItem, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QSplitter, QComboBox, QLineEdit, QFileDialog, QMessageBox)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QPixmap

from gui_sections.section_base import DataSection
from gui_theme import TEXT, MUTED, TEAL, PANEL, BORDER

FOLDERS = (("buffer", "📥 Буфер", "Загружено, но ещё не распределено"),
           ("documents", "📄 Документы", "Брифы, гайдлайны, договоры"),
           ("references", "🎨 Референсы", "Визуальные референсы бренда"),
           ("templates", "🧩 Шаблоны", "Шаблоны постов, stories, документов"),
           ("archive", "🗄 Архив", "Старые кампании и неиспользованные наработки"))
FOLDER_NAMES = {folder: name for folder, name, _ in FOLDERS}
TYPE_ICONS = {"image": "🖼", "video": "🎬", "document": "📄", "archive": "📦", "file": "📎"}
TYPE_LABELS = {"image": "Изображение", "video": "Видео", "document": "Документ",
               "archive": "Архив", "file": "Файл"}
COLUMNS = ["Имя", "Тип", "Размер", "Дата", "Теги"]


class OtherMaterialsSection(DataSection):
    """Каталог файлов проекта: импорт, поиск, открытие и предпросмотр."""

    def __init__(self, data_manager, settings=None, parent=None):
        super().__init__(data_manager, settings, parent)
        self.folder = "buffer"
        self._records = []
        self._build_ui()
        self.refresh()

    # --- ui ---
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame()
        header.setObjectName("zoneHeader")
        head = QHBoxLayout(header)
        head.setContentsMargins(16, 12, 16, 12)
        title = QLabel("📦 Материалы")
        title.setStyleSheet(f"color: {TEXT}; font-size: 16px; font-weight: 700;")
        head.addWidget(title)
        self.count_label = QLabel("")
        self.count_label.setStyleSheet(f"color: {MUTED}; font-size: 11px; padding-left: 10px;")
        head.addWidget(self.count_label)
        head.addStretch()
        upload = QPushButton("📥 Загрузить файлы")
        upload.setObjectName("topBtn")
        upload.setProperty("class", "primary")
        upload.clicked.connect(self._on_import)
        head.addWidget(upload)
        layout.addWidget(header)

        filters = QHBoxLayout()
        filters.setContentsMargins(16, 10, 16, 6)
        self.search = QLineEdit()
        self.search.setObjectName("formInput")
        self.search.setPlaceholderText("🔍 Поиск по имени или тегам")
        self.search.textChanged.connect(self._apply_filter)
        filters.addWidget(self.search, stretch=1)
        self.type_filter = QComboBox()
        self.type_filter.setObjectName("formInput")
        self.type_filter.addItem("Все типы")
        self.type_filter.addItems(sorted(TYPE_LABELS.values()))
        self.type_filter.currentIndexChanged.connect(self._apply_filter)
        filters.addWidget(self.type_filter)
        self.status = QLabel("")
        self.status.setStyleSheet(f"color: {TEAL}; font-size: 11px;")
        filters.addWidget(self.status)
        layout.addLayout(filters)

        splitter = QSplitter(Qt.Horizontal)
        self.folder_list = QListWidget()
        self.folder_list.setObjectName("plainScroll")
        self.folder_list.setFixedWidth(220)
        self.folder_list.currentItemChanged.connect(self._on_folder_changed)
        splitter.addWidget(self.folder_list)

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setObjectName("calendar")
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.itemSelectionChanged.connect(self._show_preview)
        self.table.doubleClicked.connect(self._open_selected)
        splitter.addWidget(self.table)

        side = QFrame()
        side.setObjectName("materialsSide")
        side.setStyleSheet(f"#materialsSide {{ background: {PANEL};"
                           f" border-left: 1px solid {BORDER}; }}")
        side_box = QVBoxLayout(side)
        side_box.setContentsMargins(12, 12, 12, 12)
        self.preview = QLabel("Выберите файл")
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setWordWrap(True)
        self.preview.setMinimumHeight(200)
        self.preview.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
        side_box.addWidget(self.preview, stretch=1)
        self.info = QLabel("")
        self.info.setWordWrap(True)
        self.info.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
        side_box.addWidget(self.info)
        row = QHBoxLayout()
        open_btn = QPushButton("Открыть")
        open_btn.setObjectName("topBtn")
        open_btn.clicked.connect(self._open_selected)
        row.addWidget(open_btn)
        remove_btn = QPushButton("Убрать")
        remove_btn.setObjectName("topBtn")
        remove_btn.clicked.connect(self._remove_selected)
        row.addWidget(remove_btn)
        side_box.addLayout(row)
        side.setFixedWidth(260)
        splitter.addWidget(side)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([220, 700, 260])
        layout.addWidget(splitter, stretch=1)

    # --- data ---
    def _all(self):
        return (self.dm.get_other_files() or {}) if self.dm else {}

    def refresh(self):
        """Перебрать папки и заново применить фильтр."""
        all_files = self._all()
        self.folder_list.blockSignals(True)
        self.folder_list.clear()
        for folder_id, name, description in FOLDERS:
            item = QListWidgetItem(f"{name} ({len(all_files.get(folder_id, []))})")
            item.setData(Qt.UserRole, folder_id)
            item.setToolTip(description)
            self.folder_list.addItem(item)
            if folder_id == self.folder:
                self.folder_list.setCurrentItem(item)
        self.folder_list.blockSignals(False)
        self._apply_filter()

    def _apply_filter(self):
        """Показать файлы текущей папки по строке поиска и типу."""
        records = list(self._all().get(self.folder, []))
        query = self.search.text().strip().lower()
        wanted = self.type_filter.currentText()
        self._records = [
            record for record in records
            if (not query or query in str(record.get("name", "")).lower()
                or query in " ".join(record.get("tags") or []).lower())
            and (wanted == "Все типы"
                 or TYPE_LABELS.get(record.get("type", "file"), "Файл") == wanted)]

        self.table.setRowCount(len(self._records))
        for row, record in enumerate(self._records):
            kind = record.get("type", "file")
            values = [f"{TYPE_ICONS.get(kind, '📎')} {record.get('name', '')}",
                      TYPE_LABELS.get(kind, "Файл"), record.get("size", ""),
                      record.get("date", ""), ", ".join(record.get("tags") or [])]
            for column, value in enumerate(values):
                cell = QTableWidgetItem(str(value))
                if column == 0:
                    cell.setData(Qt.UserRole, record.get("id"))
                    cell.setToolTip(str(record.get("path") or "файл не сохранён"))
                self.table.setItem(row, column, cell)

        name = FOLDER_NAMES.get(self.folder, self.folder)
        self.count_label.setText(f"{len(records)} файлов · {name.strip()}")
        if not records:
            self.status.setText("Папка пуста — загрузите файлы кнопкой выше")
        elif not self._records:
            self.status.setText("Ничего не найдено по фильтру")
        else:
            self.status.setText("")
        self._show_preview()

    def _current_record(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._records):
            return None
        return self._records[row]

    def _on_folder_changed(self, current, _previous=None):
        if current is None:
            return
        self.folder = current.data(Qt.UserRole)
        self.refresh()

    def _show_preview(self):
        record = self._current_record()
        if record is None:
            self.preview.setPixmap(QPixmap())
            self.preview.setText("Выберите файл")
            self.info.setText("")
            return
        path = self._path_of(record)
        if record.get("type") == "image" and path is not None and path.is_file():
            pixmap = QPixmap(str(path))
            if pixmap.isNull():
                self.preview.setText("Файл не читается как изображение")
            else:
                self.preview.setPixmap(pixmap.scaled(232, 232, Qt.KeepAspectRatio,
                                                     Qt.SmoothTransformation))
        else:
            self.preview.setText(f"{record.get('name', '')}\n\n{record.get('size', '')} · "
                                 f"{record.get('date', '')}\n{record.get('type', '')}")
        self.info.setText(str(path) if path is not None else "Файл не сохранён на диске")

    @staticmethod
    def _path_of(record):
        """Путь записи или None: Path('') молча превратился бы в текущую папку."""
        raw = str(record.get("path") or "")
        return Path(raw) if raw else None

    # --- actions ---
    def _on_import(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Файлы в материалы")
        if not files:
            return
        message = self.run("import_materials", paths=files, folder=self.folder)
        self.refresh()
        self.status.setText(message)

    def _open_selected(self):
        record = self._current_record()
        if record is None:
            return
        path = self._path_of(record)
        if path is None or not path.is_file():
            QMessageBox.information(self, "Файл", "Файл не найден на диске.")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def _remove_selected(self):
        record = self._current_record()
        if record is None:
            return
        answer = QMessageBox.question(self, "Убрать материал",
                                      f"Убрать «{record.get('name')}» из списка?\n"
                                      "Файл на диске останется.")
        if answer != QMessageBox.Yes:
            return
        message = self.run("delete_material", item_id=record.get("id"))
        self.refresh()
        self.status.setText(message)
