"""Project tree: hierarchical navigation (Projects → Body → Sections)."""
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QAbstractItemView
from PySide6.QtCore import Qt, Signal

# Section definitions: (id, display_name, icon)
SECTIONS = [
    ("files", "Файлы", "📁"),
    ("strategy", "Стратегия", "🎯"),
    ("marketing", "Маркетинг", "📊"),
    ("content_plans", "Контент-планы", "📝"),
    ("calendar", "Календарь", "📅"),
    ("photo_processing", "Обработка фото", "🖼️"),
    ("video_processing", "Обработка видео", "🎬"),
    ("publications", "Публикации", "📢"),
]

class ProjectTree(QTreeWidget):
    """Hierarchical tree: Projects → Body → Sections."""
    section_selected = Signal(str, str)  # project_id, section_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderHidden(True)
        self.setIndentation(16)
        self.setAnimated(True)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.itemClicked.connect(self._on_item_clicked)
        self._project_items = {}  # project_id -> QTreeWidgetItem

    def add_project(self, project_id, name):
        """Add project with its sections."""
        proj_item = QTreeWidgetItem([f"📂 {name}"])
        proj_item.setData(0, Qt.UserRole, {"type": "project", "id": project_id})
        proj_item.setExpanded(True)

        # Body item
        body_item = QTreeWidgetItem(["    📋 Тело проекта"])
        body_item.setData(0, Qt.UserRole, {"type": "body", "project_id": project_id})
        proj_item.addChild(body_item)

        # Sections
        for sec_id, sec_name, sec_icon in SECTIONS:
            sec_item = QTreeWidgetItem([f"    {sec_icon} {sec_name}"])
            sec_item.setData(0, Qt.UserRole, {
                "type": "section",
                "project_id": project_id,
                "section_id": sec_id
            })
            proj_item.addChild(sec_item)

        self.addTopLevelItem(proj_item)
        self._project_items[project_id] = proj_item
        return proj_item

    def remove_project(self, project_id):
        if project_id in self._project_items:
            idx = self.indexOfTopLevelItem(self._project_items[project_id])
            self.takeTopLevelItem(idx)
            del self._project_items[project_id]

    def _on_item_clicked(self, item, column):
        data = item.data(0, Qt.UserRole)
        if not data:
            return
        if data.get("type") == "section":
            self.section_selected.emit(data["project_id"], data["section_id"])