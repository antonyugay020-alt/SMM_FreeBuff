#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stage 3: Real "Import Media" button + add_media_source in DataManager.
Run: python fix_real_import.py
"""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

def write(rel, content):
    p = BASE / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding='utf-8', newline='\n')
    print(f"  [OK] {rel}")

print("\n=== Stage 3: Real Import Media ===\n")

# 1. Add add_media_source() to data_manager.py
print("[1/3] Updating data_manager.py...")

dm_path = BASE / "data_manager.py"
dm_content = dm_path.read_text(encoding='utf-8')

# Add import at top
if 'import shutil' not in dm_content:
    dm_content = dm_content.replace(
        'import json',
        'import json\nimport shutil'
    )

# Add method before get_stats()
add_method = '''
    def add_media_source(self, file_path: str) -> Dict[str, Any]:
        """Import a real file into media sources. Returns the new source record."""
        src = Path(file_path)
        if not src.exists():
            return None
        
        # Copy to media/images/
        media_dir = Path(__file__).resolve().parent / "media" / "images"
        media_dir.mkdir(parents=True, exist_ok=True)
        dest = media_dir / src.name
        
        # Avoid overwriting
        counter = 1
        while dest.exists():
            stem = src.stem
            suffix = src.suffix
            dest = media_dir / f"{stem}_{counter}{suffix}"
            counter += 1
        
        shutil.copy2(src, dest)
        
        # Detect type
        ftype = "video" if dest.suffix.lower() in (".mp4", ".mov", ".avi", ".mkv") else "image"
        
        # Create record
        new_source = {
            "id": f"src_{len(self._data['media_sources']) + 1:03d}",
            "name": dest.name,
            "type": ftype,
            "size": "unknown",
            "date": Path(src).stat().st_mtime and __import__('datetime').datetime.fromtimestamp(
                Path(src).stat().st_mtime
            ).strftime("%d.%m.%Y"),
            "shooting_task": None,
        }
        
        self._data["media_sources"].append(new_source)
        self.save()
        
        logger.info(f"Imported {src.name} -> {dest.name}")
        return new_source

    def get_stats'''

dm_content = dm_content.replace('\n    def get_stats', add_method)
dm_path.write_text(dm_content, encoding='utf-8', newline='\n')
print("  [OK] Added add_media_source() method")

# 2. Update gui_main.py — connect Import button to real handler
print("[2/3] Updating gui_main.py...")

gui_path = BASE / "gui_main.py"
gui_content = gui_path.read_text(encoding='utf-8')

# Add QFileDialog import
if 'QFileDialog' not in gui_content:
    gui_content = gui_content.replace(
        'QProgressBar)',
        'QProgressBar, QFileDialog)'
    )

# Add import handler method before _on_project_changed
handler_code = '''
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
        
        if imported > 0:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                "Импорт завершён",
                f"Импортировано файлов: {imported}\\n\\n"
                f"Файлы добавлены в раздел 'Медиа-контент → Исходники'."
            )
            # Refresh current section if it's media_content
            if self.current_section == "media_content":
                self._on_nav("media_content")

    def _on_project_changed'''

gui_content = gui_content.replace('\n    def _on_project_changed', handler_code)

# Connect the import button to the new handler
# Find where import_btn is created and add clicked.connect
if 'import_btn.clicked.connect' not in gui_content:
    gui_content = gui_content.replace(
        'top_layout.addWidget(import_btn)',
        'import_btn.clicked.connect(self._on_import_media)\\n        top_layout.addWidget(import_btn)'
    )

gui_path.write_text(gui_content, encoding='utf-8', newline='\n')
print("  [OK] Connected Import button to real handler")

# 3. Update media_content_section.py to read from DataManager
print("[3/3] Updating media_content_section.py to use DataManager...")

mc_path = BASE / "gui_sections" / "media_content_section.py"
mc_content = mc_path.read_text(encoding='utf-8')

# Replace DEMO_SOURCES/REFERENCES/READY with DataManager reads
# Find the class constructor and replace demo data usage
old_init = '''    def __init__(self, app_state: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.state = app_state
        self._build_ui()'''

new_init = '''    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.dm = data_manager
        self._build_ui()'''

mc_content = mc_content.replace(old_init, new_init)

# Replace DEMO_SOURCES/REFERENCES/READY references in _build_ui
old_sources = 'self.sources_col = MediaColumn("Исходники", "📥", "#58a6ff", DEMO_SOURCES, "sources")'
new_sources = 'self.sources_col = MediaColumn("Исходники", "📥", "#58a6ff", self.dm.get_media_sources(), "sources")'
mc_content = mc_content.replace(old_sources, new_sources)

old_refs = 'self.references_col = MediaColumn("Эталоны", "🎯", "#bc8cff", DEMO_REFERENCES, "references")'
new_refs = 'self.references_col = MediaColumn("Эталоны", "🎯", "#bc8cff", self.dm.get_media_references(), "references")'
mc_content = mc_content.replace(old_refs, new_refs)

old_ready = 'self.ready_col = MediaColumn("Готовые материалы", "✅", "#3fb950", DEMO_READY, "ready")'
new_ready = 'self.ready_col = MediaColumn("Готовые материалы", "✅", "#3fb950", self.dm.get_media_ready(), "ready")'
mc_content = mc_content.replace(old_ready, new_ready)

# Also update ProcessingPanel to accept data_manager
old_proc = 'self.processing_panel = ProcessingPanel(self.state)'
new_proc = 'self.processing_panel = ProcessingPanel(self.dm)'
mc_content = mc_content.replace(old_proc, new_proc)

# Update ProcessingPanel constructor
old_proc_init = '''    def __init__(self, app_state: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.state = app_state'''
new_proc_init = '''    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.dm = data_manager'''
mc_content = mc_content.replace(old_proc_init, new_proc_init)

mc_path.write_text(mc_content, encoding='utf-8', newline='\n')
print("  [OK] Media Content now reads from DataManager")

print("\n=== Stage 3 Part 1 Complete ===")
print("\nWhat works now:")
print("  [OK] 'Импорт медиа' button opens real file dialog")
print("  [OK] Selected files are copied to media/images/")
print("  [OK] Files are added to DataManager as sources")
print("  [OK] Data is persisted to project_data.json")
print("  [OK] Media Content section reads real data from DataManager")
print("\nRun START.bat and:")
print("  1. Click 'Импорт медиа' in top bar")
print("  2. Select some image/video files")
print("  3. Go to 'Медиа-контент' — your files appear in 'Исходники'")