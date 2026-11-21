#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix: Make processing panel visible + fix drag-and-drop.
Run: python fix_media_visible.py
"""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

def write(rel, content):
    p = BASE / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding='utf-8', newline='\n')
    print(f"  [OK] {rel}")

print("\n=== Fixing Media Visibility + Drag-Drop ===\n")

# Read current file
media_path = BASE / "gui_sections" / "media_content_section.py"
content = media_path.read_text(encoding='utf-8')

# Fix 1: Change splitter initial sizes so processing panel is visible
# Current: splitter.setSizes([1000, 380]) — but columns_container might be too wide
# Fix: reduce columns width, ensure processing panel gets space
content = content.replace(
    'splitter.setSizes([1000, 380])',
    'splitter.setSizes([900, 400])'
)

# Fix 2: Simplify drag-and-drop — remove startDragDistance check that might fail
old_drag = """    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return
        if not hasattr(self, '_drag_start_pos'):
            return
        if (event.pos() - self._drag_start_pos).manhattanLength() < QApplication.instance().startDragDistance():
            return

        # Start drag
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(DRAG_MIME_TYPE, QByteArray(json.dumps(self.file_data).encode('utf-8')))
        mime.setData("zone".encode('utf-8'), QByteArray(self.zone.encode('utf-8')))
        drag.setMimeData(mime)

        # Visual feedback
        self.setStyleSheet(\"\"\"
            QFrame#thumb { background-color: #161b22; border: 2px dashed #58a6ff; border-radius: 6px; opacity: 0.6; }
        \"\"\")
        drag.exec_(Qt.MoveAction)
        # Restore style
        self._on_checked(self.checkbox.checkState())"""

new_drag = """    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return
        if not hasattr(self, '_drag_start_pos'):
            return
        # Simple distance check
        distance = (event.pos() - self._drag_start_pos).manhattanLength()
        if distance < 10:
            return

        # Start drag
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(DRAG_MIME_TYPE, QByteArray(json.dumps(self.file_data).encode('utf-8')))
        mime.setData("zone".encode('utf-8'), QByteArray(self.zone.encode('utf-8')))
        drag.setMimeData(mime)

        # Visual feedback
        self.setStyleSheet(\"\"\"
            QFrame#thumb { background-color: #161b22; border: 2px dashed #58a6ff; border-radius: 6px; }
        \"\"\")
        result = drag.exec_(Qt.MoveAction)
        # Restore style after drag
        self._on_checked(self.checkbox.checkState())
        logger.info(f"Drag result: {result}")"""

content = content.replace(old_drag, new_drag)

# Fix 3: Add logging to drag events for debugging
old_drag_enter = """    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(DRAG_MIME_TYPE):
            event.acceptProposedAction()
            self.setStyleSheet(self.styleSheet().replace("border: 1px solid #30363d;", "border: 2px dashed #58a6ff;"))"""

new_drag_enter = """    def dragEnterEvent(self, event):
        logger.info(f"dragEnterEvent on {self.zone}, formats: {event.mimeData().formats()}")
        if event.mimeData().hasFormat(DRAG_MIME_TYPE):
            event.acceptProposedAction()
            logger.info(f"Accepted drag on {self.zone}")
            # Add highlight class
            self.setProperty("drag-over", True)
            self.style().unpolish(self)
            self.style().polish(self)"""

content = content.replace(old_drag_enter, new_drag_enter)

old_drag_leave = """    def dragLeaveEvent(self, event):
        self.setStyleSheet(self.styleSheet().replace("border: 2px dashed #58a6ff;", "border: 1px solid #30363d;"))"""

new_drag_leave = """    def dragLeaveEvent(self, event):
        logger.info(f"dragLeaveEvent on {self.zone}")
        self.setProperty("drag-over", False)
        self.style().unpolish(self)
        self.style().polish(self)"""

content = content.replace(old_drag_leave, new_drag_leave)

old_drop = """    def dropEvent(self, event):
        self.setStyleSheet(self.styleSheet().replace("border: 2px dashed #58a6ff;", "border: 1px solid #30363d;"))
        if not event.mimeData().hasFormat(DRAG_MIME_TYPE):
            return

        data = json.loads(bytes(event.mimeData().data(DRAG_MIME_TYPE)).decode('utf-8'))
        source_zone = bytes(event.mimeData().data("zone".encode('utf-8'))).decode('utf-8')

        # Remove from source column
        parent_section = self._find_parent_section()
        if parent_section:
            parent_section.move_card(data, source_zone, self.zone)

        event.acceptProposedAction()"""

new_drop = """    def dropEvent(self, event):
        logger.info(f"dropEvent on {self.zone}")
        self.setProperty("drag-over", False)
        self.style().unpolish(self)
        self.style().polish(self)
        
        if not event.mimeData().hasFormat(DRAG_MIME_TYPE):
            logger.info(f"No DRAG_MIME_TYPE, formats: {event.mimeData().formats()}")
            return

        data = json.loads(bytes(event.mimeData().data(DRAG_MIME_TYPE)).decode('utf-8'))
        source_zone = bytes(event.mimeData().data("zone".encode('utf-8'))).decode('utf-8')
        logger.info(f"Dropped {data.get('name')} from {source_zone} to {self.zone}")

        # Remove from source column
        parent_section = self._find_parent_section()
        if parent_section:
            parent_section.move_card(data, source_zone, self.zone)

        event.acceptProposedAction()"""

content = content.replace(old_drop, new_drop)

# Fix 4: Add drag-over style to QSS
old_zone_style = """        self.setStyleSheet(f\"\"\"
            QFrame#zone {{
                background-color: #161b22;
                border: 1px solid #30363d;
                border-top: 4px solid {color};
                border-radius: 6px;
            }}
            QFrame#zone.drag-over {{
                border: 2px dashed {color};
                background-color: #1c2333;
            }}
        \"\"\")"""

new_zone_style = """        self.setStyleSheet(f\"\"\"
            QFrame#zone {{
                background-color: #161b22;
                border: 1px solid #30363d;
                border-top: 4px solid {color};
                border-radius: 6px;
            }}
            QFrame#zone[drag-over="true"] {{
                border: 2px dashed {color};
                background-color: #1c2333;
            }}
        \"\"\")"""

content = content.replace(old_zone_style, new_zone_style)

# Fix 5: Make sure processing panel is always visible by setting min width on columns_container
old_cols_min = """        self.sources_col.setMinimumWidth(300)
        self.references_col.setMinimumWidth(300)
        self.ready_col.setMinimumWidth(300)"""

new_cols_min = """        self.sources_col.setMinimumWidth(260)
        self.sources_col.setMaximumWidth(400)
        self.references_col.setMinimumWidth(260)
        self.references_col.setMaximumWidth(400)
        self.ready_col.setMinimumWidth(260)
        self.ready_col.setMaximumWidth(400)"""

content = content.replace(old_cols_min, new_cols_min)

media_path.write_text(content, encoding='utf-8', newline='\n')
print("  [OK] Fixed drag-drop and panel visibility")

print("\n=== Fixes Applied ===")
print("\nChanges:")
print("  [OK] Processing panel now visible (splitter sizes 900/400)")
print("  [OK] Simplified drag distance check (10px instead of QApplication)")
print("  [OK] Added logging to drag events for debugging")
print("  [OK] Fixed drag-over styling with property selector")
print("  [OK] Column width limits: 260-400px each")
print("\nRun START.bat and:")
print("  1. Click 'Медиа-контент' in left panel")
print("  2. You should see 3 columns + processing panel on the right")
print("  3. Drag a card from 'Исходники' to 'Готовые материалы'")
print("  4. Check terminal for drag logs")