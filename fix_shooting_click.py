#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix: Shooting tasks click handler + column widths.
Run: python fix_shooting_click.py
"""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

print("\n=== Fixing Shooting Tasks Click ===\n")

shooting_path = BASE / "gui_sections" / "shooting_tasks_section.py"
content = shooting_path.read_text(encoding='utf-8')

# Fix 1: Better click handler with logging
old_click = '''    def _on_task_selected(self, item):
        """Handle task selection."""
        row = item.row()
        tasks = self.dm.get_shooting_tasks()
        task = tasks[row] if row < len(tasks) else None
        if not task:
            return
        
        self.selected_task = task

        # Clear details
        while self.details_layout.count():
            w = self.details_layout.takeAt(0).widget()
            if w:
                w.deleteLater()

        # Show task details
        details = TaskDetails(task, self.dm)
        self.details_layout.addWidget(details)'''

new_click = '''    def _on_task_selected(self, item):
        """Handle task selection."""
        row = item.row()
        logger.info(f"Task row clicked: {row}")
        tasks = self.dm.get_shooting_tasks()
        if row >= len(tasks):
            logger.warning(f"Row {row} out of range (tasks count: {len(tasks)})")
            return
        task = tasks[row]
        logger.info(f"Selected task: {task.get('id')}")
        
        self.selected_task = task

        # Clear details
        while self.details_layout.count():
            item = self.details_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Show task details
        try:
            details = TaskDetails(task, self.dm)
            self.details_layout.addWidget(details)
            logger.info("Task details displayed")
        except Exception as e:
            logger.error(f"Failed to show task details: {e}")
            import traceback
            traceback.print_exc()
            error_label = QLabel(f"Ошибка: {e}")
            error_label.setStyleSheet("color: #f85149; padding: 20px;")
            self.details_layout.addWidget(error_label)'''

content = content.replace(old_click, new_click)

# Fix 2: Better column widths - use Stretch for flexible columns
old_widths = '''        self.task_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.task_table.setColumnWidth(0, 80)
        self.task_table.setColumnWidth(1, 100)
        self.task_table.setColumnWidth(2, 150)
        self.task_table.setColumnWidth(3, 100)
        self.task_table.setColumnWidth(4, 200)
        self.task_table.setColumnWidth(5, 120)
        self.task_table.setColumnWidth(6, 100)'''

new_widths = '''        self.task_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.task_table.setColumnWidth(0, 70)   # ID
        self.task_table.setColumnWidth(1, 90)   # Date
        self.task_table.setColumnWidth(2, 140)  # Location
        self.task_table.setColumnWidth(3, 90)   # Type
        self.task_table.setColumnWidth(4, 180)  # Content plan
        self.task_table.setColumnWidth(5, 110)  # Status
        self.task_table.setColumnWidth(6, 90)   # Priority'''

content = content.replace(old_widths, new_widths)

# Fix 3: Make sure details widget has stretch
old_details = '''        splitter.addWidget(self.details_widget)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)'''

new_details = '''        self.details_widget.setMinimumWidth(400)
        splitter.addWidget(self.details_widget)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)'''

content = content.replace(old_details, new_details)

shooting_path.write_text(content, encoding='utf-8', newline='\n')
print("[OK] Fixed click handler with logging")
print("[OK] Adjusted column widths")
print("[OK] Set minimum width for details panel")

print("\nRun START.bat and:")
print("1. Click 'Задания на съемку'")
print("2. Click any row in the table")
print("3. Check terminal for logs if details don't appear")