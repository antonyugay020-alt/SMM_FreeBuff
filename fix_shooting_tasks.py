#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix: Create Shooting Tasks section with full brief functionality.
Run: python fix_shooting_tasks.py
"""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

def write(rel, content):
    p = BASE / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding='utf-8', newline='\n')
    print(f"  [OK] {rel}")

print("\n=== Creating Shooting Tasks Section ===\n")

shooting_tasks = r'''"""Shooting Tasks section: Full brief with shot list, team, references."""
import logging
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QMessageBox, QSplitter, QComboBox, QScrollArea,
    QTextEdit, QFormLayout, QLineEdit, QDateEdit, QTimeEdit, QCheckBox)
from PySide6.QtCore import Qt, QDate, QTime, Signal
from PySide6.QtGui import QPixmap, QColor

logger = logging.getLogger(__name__)

# Status colors
STATUS_COLORS = {
    "Черновик": "#8b949e",
    "Согласовано": "#58a6ff",
    "В работе": "#9e6a03",
    "Снято": "#bc8cff",
    "Смонтировано": "#3fb950",
    "Готово к обработке": "#238636",
}

# Demo shooting tasks
DEMO_TASKS = [
    {
        "id": "ST-001",
        "date": "15.11.2026",
        "time": "14:00",
        "location": "Корт №2 (закрытый)",
        "type": "Фото + Видео",
        "content_plan_link": "Пост: 5 упражнений для запястья",
        "status": "Снято",
        "team": "Фотограф: Марина, Модель: Максим (ученик)",
        "priority": "Высокий",
        "budget": "5000 ₽",
        "duration": "2 часа",
        "shots": [
            {"num": 1, "desc": "Крупный план: упражнение с эспандером", "ref": "ref_wrist_01.jpg", "priority": "Высокий", "status": "Снято"},
            {"num": 2, "desc": "Средний план: тренер показывает технику", "ref": "ref_coach_02.jpg", "priority": "Высокий", "status": "Снято"},
            {"num": 3, "desc": "Общий план: ребёнок выполняет упражнение", "ref": None, "priority": "Средний", "status": "Снято"},
            {"num": 4, "desc": "Детали: руки, ракетка, мяч", "ref": "ref_details_03.jpg", "priority": "Низкий", "status": "Снято"},
        ],
        "tech_req": "Формат: JPEG + RAW, Ориентация: вертикальная 4:5, Разрешение: 4000x5000",
        "notes": "Свет естественный + софтбокс. Акцент на эмоциях ребёнка.",
    },
    {
        "id": "ST-002",
        "date": "20.11.2026",
        "time": "15:00",
        "location": "Турнирный корт",
        "type": "Видео",
        "content_plan_link": "Reels: Закулисье турнира",
        "status": "Согласовано",
        "team": "Оператор: Антон, Ассистент: Ирина",
        "priority": "Средний",
        "budget": "3000 ₽",
        "duration": "3 часа",
        "shots": [
            {"num": 1, "desc": "Подготовка участников (разминка)", "ref": None, "priority": "Высокий", "status": "Нужен"},
            {"num": 2, "desc": "Эмоции во время матча", "ref": "ref_emotions_01.jpg", "priority": "Высокий", "status": "Нужен"},
            {"num": 3, "desc": "Награждение победителей", "ref": None, "priority": "Средний", "status": "Нужен"},
            {"num": 4, "desc": "Интервью с участниками", "ref": None, "priority": "Низкий", "status": "Нужен"},
        ],
        "tech_req": "Формат: MP4 (H.264), Разрешение: 1080x1920 (вертикальное), FPS: 30",
        "notes": "Снимать на стабилизатор. Звук через петличку.",
    },
    {
        "id": "ST-003",
        "date": "25.11.2026",
        "time": "10:00",
        "location": "Главный корт + раздевалка",
        "type": "Фото",
        "content_plan_link": "Пост: Открытие новой группы 6-8 лет",
        "status": "Черновик",
        "team": "Фотограф: Марина",
        "priority": "Высокий",
        "budget": "4000 ₽",
        "duration": "2 часа",
        "shots": [
            {"num": 1, "desc": "Групповое фото детей с тренером", "ref": None, "priority": "Высокий", "status": "Нужен"},
            {"num": 2, "desc": "Дети играют в теннис (динамика)", "ref": "ref_kids_play_01.jpg", "priority": "Высокий", "status": "Нужен"},
            {"num": 3, "desc": "Детали: детская ракетка, мячи, форма", "ref": None, "priority": "Средний", "status": "Нужен"},
            {"num": 4, "desc": "Интерьер: корт, раздевалка, зона ожидания", "ref": None, "priority": "Низкий", "status": "Нужен"},
        ],
        "tech_req": "Формат: JPEG + RAW, Ориентация: горизонтальная 16:9 и квадрат 1:1",
        "notes": "Яркие цвета, акцент на радости детей. Минимум постановки.",
    },
]


class ShotListTable(QWidget):
    """Shot list table within task details."""
    def __init__(self, shots: List[Dict[str, Any]], parent=None):
        super().__init__(parent)
        self.shots = shots
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        title = QLabel("📸 Список кадров")
        title.setStyleSheet("color: #e6edf3; font-size: 14px; font-weight: bold; margin-bottom: 8px;")
        layout.addWidget(title)

        table = QTableWidget()
        table.setObjectName("calendar")
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["№", "Описание", "Референс", "Приоритет", "Статус"])
        table.setRowCount(len(self.shots))
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.verticalHeader().setVisible(False)

        for row, shot in enumerate(self.shots):
            # Number
            num_item = QTableWidgetItem(str(shot["num"]))
            num_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row, 0, num_item)

            # Description
            desc_item = QTableWidgetItem(shot["desc"])
            table.setItem(row, 1, desc_item)

            # Reference
            ref_item = QTableWidgetItem(shot.get("ref", "—") if shot.get("ref") else "—")
            ref_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row, 2, ref_item)

            # Priority
            priority_item = QTableWidgetItem(shot["priority"])
            priority_item.setTextAlignment(Qt.AlignCenter)
            priority_color = {"Высокий": "#f85149", "Средний": "#9e6a03", "Низкий": "#8b949e"}.get(shot["priority"], "#8b949e")
            priority_item.setForeground(QColor(priority_color))
            table.setItem(row, 3, priority_item)

            # Status
            status_item = QTableWidgetItem(shot["status"])
            status_item.setTextAlignment(Qt.AlignCenter)
            status_color = {"Нужен": "#8b949e", "Снято": "#bc8cff", "Отобрано": "#238636"}.get(shot["status"], "#8b949e")
            status_item.setForeground(QColor(status_color))
            table.setItem(row, 4, status_item)

        table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        table.setColumnWidth(0, 50)
        table.setColumnWidth(1, 300)
        table.setColumnWidth(2, 150)
        table.setColumnWidth(3, 100)
        table.setColumnWidth(4, 100)

        table.setMinimumHeight(200)
        layout.addWidget(table, stretch=1)

        # Add shot button
        add_btn = QPushButton("➕ Добавить кадр")
        add_btn.setObjectName("topBtn")
        add_btn.setStyleSheet("font-size: 11px; padding: 6px 12px;")
        add_btn.clicked.connect(lambda: QMessageBox.information(self, "Добавить кадр", "В полной версии откроется форма добавления кадра."))
        layout.addWidget(add_btn)


class TaskDetails(QWidget):
    """Detailed view of a single shooting task."""
    def __init__(self, task: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.task = task
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header
        header = QHBoxLayout()
        title = QLabel(f"🎬 Задание {self.task['id']}")
        title.setStyleSheet("color: #e6edf3; font-size: 20px; font-weight: bold;")
        header.addWidget(title)

        header.addStretch()

        status = self.task["status"]
        status_color = STATUS_COLORS.get(status, "#8b949e")
        status_label = QLabel(status)
        status_label.setStyleSheet(f"background-color: {status_color}; color: white; padding: 6px 12px; border-radius: 4px; font-weight: bold;")
        header.addWidget(status_label)

        layout.addLayout(header)

        # Scrollable content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background-color: #0f1419;")

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(16)

        # Meta info
        meta_frame = QFrame()
        meta_frame.setObjectName("zone")
        meta_frame.setStyleSheet("QFrame#zone { background-color: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 16px; }")
        meta_layout = QFormLayout(meta_frame)

        meta_layout.addRow("📅 Дата:", QLabel(f"{self.task['date']} в {self.task['time']}"))
        meta_layout.addRow("📍 Локация:", QLabel(self.task['location']))
        meta_layout.addRow("🎯 Тип:", QLabel(self.task['type']))
        meta_layout.addRow("📋 Связь с контент-планом:", QLabel(self.task['content_plan_link']))
        meta_layout.addRow("👥 Команда:", QLabel(self.task['team']))
        meta_layout.addRow("💰 Бюджет:", QLabel(self.task['budget']))
        meta_layout.addRow("⏱️ Длительность:", QLabel(self.task['duration']))
        meta_layout.addRow("📊 Приоритет:", QLabel(self.task['priority']))

        content_layout.addWidget(meta_frame)

        # Technical requirements
        tech_frame = QFrame()
        tech_frame.setObjectName("zone")
        tech_frame.setStyleSheet("QFrame#zone { background-color: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 16px; }")
        tech_layout = QVBoxLayout(tech_frame)

        tech_title = QLabel("⚙️ Технические требования")
        tech_title.setStyleSheet("color: #e6edf3; font-size: 14px; font-weight: bold; margin-bottom: 8px;")
        tech_layout.addWidget(tech_title)

        tech_text = QLabel(self.task['tech_req'])
        tech_text.setStyleSheet("color: #c9d1d9; font-size: 12px;")
        tech_text.setWordWrap(True)
        tech_layout.addWidget(tech_text)

        content_layout.addWidget(tech_frame)

        # Notes
        if self.task.get('notes'):
            notes_frame = QFrame()
            notes_frame.setObjectName("zone")
            notes_frame.setStyleSheet("QFrame#zone { background-color: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 16px; }")
            notes_layout = QVBoxLayout(notes_frame)

            notes_title = QLabel("📝 Примечания")
            notes_title.setStyleSheet("color: #e6edf3; font-size: 14px; font-weight: bold; margin-bottom: 8px;")
            notes_layout.addWidget(notes_title)

            notes_text = QLabel(self.task['notes'])
            notes_text.setStyleSheet("color: #c9d1d9; font-size: 12px; font-style: italic;")
            notes_text.setWordWrap(True)
            notes_layout.addWidget(notes_text)

            content_layout.addWidget(notes_frame)

        # Shot list
        shot_list = ShotListTable(self.task['shots'])
        content_layout.addWidget(shot_list, stretch=1)

        content_layout.addStretch()

        scroll.setWidget(content)
        layout.addWidget(scroll, stretch=1)

        # Action buttons
        actions = QHBoxLayout()
        actions.setSpacing(12)

        edit_btn = QPushButton("✏️ Редактировать")
        edit_btn.setObjectName("topBtn")
        edit_btn.setStyleSheet("font-size: 12px; padding: 8px 16px;")
        edit_btn.clicked.connect(lambda: QMessageBox.information(self, "Редактировать", "В полной версии откроется форма редактирования задания."))
        actions.addWidget(edit_btn)

        export_btn = QPushButton("📄 Экспорт PDF")
        export_btn.setObjectName("topBtn")
        export_btn.setProperty("class", "primary")
        export_btn.setStyleSheet("font-size: 12px; font-weight: bold; padding: 8px 16px;")
        export_btn.clicked.connect(lambda: QMessageBox.information(self, "Экспорт PDF", "В полной версии здесь сформируется PDF-файл с ТЗ для фотографа."))
        actions.addWidget(export_btn)

        ai_btn = QPushButton("🤖 AI: проверить полноту")
        ai_btn.setObjectName("topBtn")
        ai_btn.setStyleSheet("font-size: 12px; padding: 8px 16px;")
        ai_btn.clicked.connect(lambda: QMessageBox.information(self, "AI-проверка", "AI проанализирует ТЗ и предложит:\n\n• Добавить недостающие кадры\n• Уточнить технические требования\n• Проверить соответствие контент-плану"))
        actions.addWidget(ai_btn)

        actions.addStretch()
        layout.addLayout(actions)


class ShootingTasksSection(QWidget):
    """Shooting Tasks section: list + details."""

    def __init__(self, app_state: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.state = app_state
        self.selected_task = None
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

        title = QLabel("🎬 Задания на съемку")
        title.setStyleSheet("color: #e6edf3; font-size: 18px; font-weight: bold;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Create task button
        create_btn = QPushButton("➕ Создать задание")
        create_btn.setObjectName("topBtn")
        create_btn.setProperty("class", "primary")
        create_btn.setStyleSheet("font-size: 13px; font-weight: bold; padding: 8px 16px;")
        create_btn.clicked.connect(self._on_create_task)
        header_layout.addWidget(create_btn)

        layout.addWidget(header)

        # Main splitter: task list | task details
        splitter = QSplitter(Qt.Horizontal)

        # Left: task list
        list_widget = QWidget()
        list_layout = QVBoxLayout(list_widget)
        list_layout.setContentsMargins(16, 16, 8, 16)
        list_layout.setSpacing(12)

        # Filters
        filters = QHBoxLayout()
        status_filter = QComboBox()
        status_filter.addItem("Все статусы")
        for status in STATUS_COLORS.keys():
            status_filter.addItem(status)
        status_filter.setObjectName("filterCombo")
        status_filter.setFixedWidth(180)
        filters.addWidget(status_filter)

        filters.addStretch()
        list_layout.addLayout(filters)

        # Task table
        self.task_table = QTableWidget()
        self.task_table.setObjectName("calendar")
        self.task_table.setColumnCount(7)
        self.task_table.setHorizontalHeaderLabels(["ID", "Дата", "Локация", "Тип", "Контент-план", "Статус", "Приоритет"])
        self.task_table.setRowCount(len(DEMO_TASKS))
        self.task_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.task_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.task_table.verticalHeader().setVisible(False)
        self.task_table.itemClicked.connect(self._on_task_selected)

        for row, task in enumerate(DEMO_TASKS):
            for col, key in enumerate(["id", "date", "location", "type", "content_plan_link", "status", "priority"]):
                item = QTableWidgetItem(task.get(key, ""))
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                
                if key == "status":
                    color = STATUS_COLORS.get(task.get(key, ""), "#8b949e")
                    item.setForeground(QColor(color))
                elif key == "priority":
                    color = {"Высокий": "#f85149", "Средний": "#9e6a03", "Низкий": "#8b949e"}.get(task.get(key, ""), "#8b949e")
                    item.setForeground(QColor(color))
                
                self.task_table.setItem(row, col, item)

        self.task_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.task_table.setColumnWidth(0, 80)
        self.task_table.setColumnWidth(1, 100)
        self.task_table.setColumnWidth(2, 150)
        self.task_table.setColumnWidth(3, 100)
        self.task_table.setColumnWidth(4, 200)
        self.task_table.setColumnWidth(5, 120)
        self.task_table.setColumnWidth(6, 100)

        list_layout.addWidget(self.task_table, stretch=1)

        splitter.addWidget(list_widget)

        # Right: task details (or placeholder)
        self.details_widget = QWidget()
        self.details_layout = QVBoxLayout(self.details_widget)
        self.details_layout.setContentsMargins(8, 16, 16, 16)

        placeholder = QLabel("👈 Выберите задание из списка")
        placeholder.setAlignment(Qt.AlignCenter)
        placeholder.setStyleSheet("color: #8b949e; font-size: 16px; padding: 60px;")
        self.details_layout.addWidget(placeholder)

        splitter.addWidget(self.details_widget)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        splitter.setHandleWidth(6)
        splitter.setSizes([500, 900])
        splitter.setStyleSheet("""
            QSplitter::handle { background-color: #30363d; border-radius: 2px; }
            QSplitter::handle:hover { background-color: #58a6ff; }
        """)

        layout.addWidget(splitter, stretch=1)

    def _on_task_selected(self, item):
        """Handle task selection."""
        row = item.row()
        task = DEMO_TASKS[row]
        self.selected_task = task

        # Clear details
        while self.details_layout.count():
            w = self.details_layout.takeAt(0).widget()
            if w:
                w.deleteLater()

        # Show task details
        details = TaskDetails(task)
        self.details_layout.addWidget(details)

    def _on_create_task(self):
        """Create new task."""
        QMessageBox.information(
            self,
            "Создать задание",
            "В полной версии откроется форма создания задания:\n\n"
            "• Дата, время, локация\n"
            "• Тип съёмки (фото/видео/оба)\n"
            "• Связь с пунктом контент-плана\n"
            "• Команда (фотограф, модели, ассистенты)\n"
            "• Список кадров с референсами\n"
            "• Технические требования\n\n"
            "AI может помочь заполнить форму на основе контент-плана."
        )
'''

write("gui_sections/shooting_tasks_section.py", shooting_tasks)

# 2. Add shooting_tasks loading to gui_main.py
print("[2/2] Adding shooting_tasks loading to gui_main.py...")

gui_main_path = BASE / "gui_main.py"
gui_main_content = gui_main_path.read_text(encoding='utf-8')

# Find calendar block and add shooting_tasks after it
old_block = '''        elif section_id == "calendar":
            from gui_sections.calendar_section import CalendarSection
            self.workspace_layout.addWidget(CalendarSection(self.state))
        elif section_id == "publications":'''

new_block = '''        elif section_id == "calendar":
            from gui_sections.calendar_section import CalendarSection
            self.workspace_layout.addWidget(CalendarSection(self.state))
        elif section_id == "shooting_tasks":
            from gui_sections.shooting_tasks_section import ShootingTasksSection
            self.workspace_layout.addWidget(ShootingTasksSection(self.state))
        elif section_id == "publications":'''

if old_block in gui_main_content:
    gui_main_content = gui_main_content.replace(old_block, new_block)
    gui_main_path.write_text(gui_main_content, encoding='utf-8', newline='\n')
    print("  [OK] Added shooting_tasks loading")
else:
    print("  [WARN] Could not find insertion point")

print("\n=== Shooting Tasks Section Created ===")
print("\nFeatures:")
print("  [OK] Task list table with filters")
print("  [OK] Detailed task view with meta info")
print("  [OK] Shot list table with references")
print("  [OK] Technical requirements section")
print("  [OK] Notes and team info")
print("  [OK] Status and priority color coding")
print("  [OK] Export PDF button (placeholder)")
print("  [OK] AI completeness check button (placeholder)")
print("  [OK] Create task button (placeholder)")
print("\nRun START.bat and click 'Задания на съемку' in left panel.")