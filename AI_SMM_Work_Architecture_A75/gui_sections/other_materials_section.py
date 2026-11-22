"""Other Materials section: File manager for archive, buffer, docs, references."""
import logging
from pathlib import Path
from typing import Dict, Any, List

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QTreeWidget, QTreeWidgetItem, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QSplitter,
    QComboBox, QLineEdit, QMessageBox, QScrollArea, QGridLayout)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QColor

logger = logging.getLogger(__name__)

# Folder structure only; files come from the project data
FOLDER_META = {
    "archive": {"name": "📁 Архив", "desc": "Старые кампании и неиспользованные наработки"},
    "buffer": {"name": "📁 Буфер", "desc": "Загружено, но ещё не распределено"},
    "documents": {"name": "📁 Документы", "desc": "Брифы, гайдлайны, договоры"},
    "references": {"name": "📁 Референсы", "desc": "Визуальные референсы бренда"},
    "templates": {"name": "📁 Шаблоны", "desc": "Шаблоны постов, stories, документов"},
}


def folders_from_data(data_manager) -> Dict[str, Dict[str, Any]]:
    """Build the folder tree from project data instead of a demo constant."""
    files = {}
    if data_manager is not None and hasattr(data_manager, "get_other_files"):
        files = data_manager.get_other_files() or {}
    folders = {}
    for folder_id, meta_item in FOLDER_META.items():
        folders[folder_id] = {"name": meta_item["name"], "desc": meta_item["desc"],
                              "files": list(files.get(folder_id, []))}
    return folders


class FileTree(QWidget):
    """Folder tree on the left."""
    folder_selected = Signal(str)

    def __init__(self, folders: Dict[str, Dict[str, Any]], parent=None):
        super().__init__(parent)
        self.folders = folders
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        title = QLabel("📂 Папки")
        title.setStyleSheet("color: #e6edf3; font-size: 14px; font-weight: bold; padding: 12px; background-color: #121820; border-bottom: 1px solid #1e252e;")
        layout.addWidget(title)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setStyleSheet("""
            QTreeWidget { background-color: #0a0e13; color: #c9d1d9; border: none; font-size: 12px; }
            QTreeWidget::item { padding: 8px; border-radius: 4px; }
            QTreeWidget::item:hover { background-color: #121820; }
            QTreeWidget::item:selected { background-color: #1f6feb; color: white; }
        """)
        self.tree.itemClicked.connect(self._on_item_clicked)

        for folder_id, folder_data in self.folders.items():
            item = QTreeWidgetItem([folder_data["name"]])
            item.setData(0, Qt.UserRole, folder_id)
            
            # File count
            count = len(folder_data.get("files", []))
            item.setText(0, f"{folder_data['name']} ({count})")
            
            self.tree.addTopLevelItem(item)

        self.tree.expandAll()
        layout.addWidget(self.tree, stretch=1)

    def _on_item_clicked(self, item, column):
        folder_id = item.data(0, Qt.UserRole)
        if folder_id:
            self.folder_selected.emit(folder_id)


class FileList(QWidget):
    """File list table."""
    def __init__(self, files: List[Dict[str, Any]], parent=None):
        super().__init__(parent)
        self.files = files
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header with actions
        header = QHBoxLayout()
        title = QLabel("📄 Файлы")
        title.setStyleSheet("color: #e6edf3; font-size: 14px; font-weight: bold;")
        header.addWidget(title)

        header.addStretch()

        # Search
        search = QLineEdit()
        search.setPlaceholderText("🔍 Поиск по имени или тегам...")
        search.setObjectName("searchBox")
        search.setFixedWidth(250)
        header.addWidget(search)

        # Type filter
        type_filter = QComboBox()
        type_filter.addItem("Все типы")
        type_filter.addItem("🖼️ Изображения")
        type_filter.addItem("🎬 Видео")
        type_filter.addItem("📄 Документы")
        type_filter.addItem("📦 Архивы")
        type_filter.setObjectName("filterCombo")
        type_filter.setFixedWidth(150)
        header.addWidget(type_filter)

        # Upload button
        upload_btn = QPushButton("📥 Загрузить")
        upload_btn.setObjectName("topBtn")
        upload_btn.setStyleSheet("font-size: 12px; padding: 6px 12px;")
        upload_btn.clicked.connect(lambda: QMessageBox.information(self, "Загрузка", "В полной версии откроется диалог выбора файлов."))
        header.addWidget(upload_btn)

        layout.addLayout(header)

        # File table
        table = QTableWidget()
        table.setObjectName("calendar")
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["Имя", "Тип", "Размер", "Дата", "Теги"])
        table.setRowCount(len(self.files))
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.verticalHeader().setVisible(False)

        for row, file_data in enumerate(self.files):
            # Name with icon
            icon = FILE_ICONS.get(file_data["type"], "📎")
            name_item = QTableWidgetItem(f"{icon} {file_data['name']}")
            table.setItem(row, 0, name_item)

            # Type
            type_item = QTableWidgetItem(file_data["type"].capitalize())
            type_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row, 1, type_item)

            # Size
            size_item = QTableWidgetItem(file_data["size"])
            table.setItem(row, 2, size_item)

            # Date
            date_item = QTableWidgetItem(file_data["date"])
            table.setItem(row, 3, date_item)

            # Tags
            tags = ", ".join(file_data.get("tags", []))
            tags_item = QTableWidgetItem(tags)
            tags_item.setForeground(QColor("#58a6ff"))
            table.setItem(row, 4, tags_item)

        table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        table.setColumnWidth(0, 250)
        table.setColumnWidth(1, 100)
        table.setColumnWidth(2, 100)
        table.setColumnWidth(3, 120)
        table.setColumnWidth(4, 200)

        table.setMinimumHeight(300)
        layout.addWidget(table, stretch=1)

        # Footer
        footer = QLabel(f"Всего файлов: {len(self.files)}")
        footer.setStyleSheet("color: #8b949e; font-size: 12px; padding: 8px;")
        layout.addWidget(footer)


class FilePreview(QWidget):
    """File preview panel."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("👁 Предпросмотр")
        title.setStyleSheet("color: #e6edf3; font-size: 14px; font-weight: bold; border-bottom: 1px solid #1e252e; padding-bottom: 8px;")
        layout.addWidget(title)

        self.preview_label = QLabel("Выберите файл для предпросмотра")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumHeight(300)
        self.preview_label.setStyleSheet("background-color: #0a0e13; border: 2px dashed #1e252e; border-radius: 6px; font-size: 14px; color: #8b949e; padding: 40px;")
        layout.addWidget(self.preview_label, stretch=1)

        # File info
        self.info_label = QLabel("")
        self.info_label.setStyleSheet("color: #8b949e; font-size: 11px; padding: 8px; background-color: #121820; border-radius: 4px;")
        layout.addWidget(self.info_label)

        # Actions
        actions = QHBoxLayout()
        download_btn = QPushButton("⬇️ Скачать")
        download_btn.setObjectName("topBtn")
        download_btn.setStyleSheet("font-size: 11px; padding: 6px 12px;")
        download_btn.clicked.connect(lambda: QMessageBox.information(self, "Скачать", "В полной версии файл скачается."))
        actions.addWidget(download_btn)

        move_btn = QPushButton("📁 Переместить")
        move_btn.setObjectName("topBtn")
        move_btn.setStyleSheet("font-size: 11px; padding: 6px 12px;")
        move_btn.clicked.connect(lambda: QMessageBox.information(self, "Переместить", "В полной версии откроется выбор папки."))
        actions.addWidget(move_btn)

        delete_btn = QPushButton("🗑️ Удалить")
        delete_btn.setObjectName("topBtn")
        delete_btn.setStyleSheet("font-size: 11px; padding: 6px 12px; background-color: #da3633; color: white; border: none;")
        delete_btn.clicked.connect(lambda: QMessageBox.information(self, "Удалить", "В полной версии файл удалится."))
        actions.addWidget(delete_btn)

        layout.addLayout(actions)

    def set_file(self, file_data: Dict[str, Any]):
        """Show file preview."""
        self.preview_label.setText(f"📄 {file_data['name']}\n\nПредпросмотр недоступен для этого типа файла")
        self.preview_label.setStyleSheet("background-color: #0a0e13; border: 2px solid #1e252e; border-radius: 6px; font-size: 13px; color: #e6edf3; padding: 40px;")

        info = f"Тип: {file_data['type']}\nРазмер: {file_data['size']}\nДата: {file_data['date']}\nТеги: {', '.join(file_data.get('tags', []))}"
        self.info_label.setText(info)


class OtherMaterialsSection(QWidget):
    """Other Materials section: file manager."""

    def __init__(self, app_state: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.state = app_state if isinstance(app_state, dict) else {}
        data_manager = self.state.get("data_manager") if isinstance(app_state, dict) else None
        self.dm = data_manager if hasattr(data_manager, "get_other_files") else app_state
        if not hasattr(self.dm, "get_other_files"):
            self.dm = None
        self.folders = folders_from_data(self.dm)
        self.current_folder = "buffer"
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QFrame()
        header.setObjectName("zoneHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 12, 16, 12)

        title = QLabel("📦 Прочие материалы")
        title.setStyleSheet("color: #e6edf3; font-size: 18px; font-weight: bold;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Tags cloud
        tags_label = QLabel("Популярные теги:")
        tags_label.setStyleSheet("color: #8b949e; font-size: 12px;")
        header_layout.addWidget(tags_label)

        for tag in ["#бренд", "#2025", "#архив", "#шаблон"]:
            tag_btn = QPushButton(tag)
            tag_btn.setObjectName("topBtn")
            tag_btn.setStyleSheet("font-size: 11px; padding: 4px 10px;")
            header_layout.addWidget(tag_btn)

        layout.addWidget(header)

        # Main splitter: tree | file list | preview
        splitter = QSplitter(Qt.Horizontal)

        # Left: folder tree
        self.file_tree = FileTree(self.folders)
        self.file_tree.folder_selected.connect(self._on_folder_selected)
        self.file_tree.setFixedWidth(250)
        splitter.addWidget(self.file_tree)

        # Center: file list
        self.file_list_widget = QWidget()
        self.file_list_layout = QVBoxLayout(self.file_list_widget)
        self.file_list_layout.setContentsMargins(0, 0, 0, 0)
        self.file_list_layout.setSpacing(0)

        self._load_folder(self.current_folder)

        splitter.addWidget(self.file_list_widget)

        # Right: preview
        self.file_preview = FilePreview()
        self.file_preview.setFixedWidth(300)
        splitter.addWidget(self.file_preview)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        splitter.setStretchFactor(2, 1)
        splitter.setHandleWidth(6)
        splitter.setSizes([250, 700, 300])
        splitter.setStyleSheet("""
            QSplitter::handle { background-color: #1e252e; border-radius: 2px; }
            QSplitter::handle:hover { background-color: #58a6ff; }
        """)

        layout.addWidget(splitter, stretch=1)

    def _load_folder(self, folder_id: str):
        """Load files for selected folder."""
        # Clear current
        while self.file_list_layout.count():
            item = self.file_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        folder_data = self.folders.get(folder_id, {"name": "Неизвестно", "desc": "", "files": []})
        
        # Folder title
        folder_title = QLabel(f"{folder_data['name']} — {folder_data['desc']}")
        folder_title.setStyleSheet("color: #e6edf3; font-size: 16px; font-weight: bold; padding: 16px; background-color: #121820; border-bottom: 1px solid #1e252e;")
        self.file_list_layout.addWidget(folder_title)

        # File list
        file_list = FileList(folder_data.get("files", []))
        self.file_list_layout.addWidget(file_list, stretch=1)

    def _on_folder_selected(self, folder_id: str):
        """Handle folder selection."""
        self.current_folder = folder_id
        self._load_folder(folder_id)

