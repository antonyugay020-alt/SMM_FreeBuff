"""Shooting Tasks section: Real create/edit forms + PDF export."""
import logging
from pathlib import Path
from typing import Dict, Any, List

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QMessageBox, QSplitter, QComboBox, QScrollArea,
    QFileDialog, QDialog, QDialogButtonBox, QLineEdit, QTextEdit,
    QDateEdit, QTimeEdit, QFormLayout)
from PySide6.QtCore import Qt, QDate, QTime
from PySide6.QtGui import QColor

logger = logging.getLogger(__name__)

STATUS_COLORS = {
    "Черновик": "#8b949e",
    "Согласовано": "#58a6ff",
    "В работе": "#9e6a03",
    "Снято": "#bc8cff",
    "Смонтировано": "#3fb950",
    "Готово к обработке": "#238636",
}


class CreateTaskDialog(QDialog):
    """Form for creating a new shooting task."""
    
    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.dm = data_manager
        self.setWindowTitle("🎬 Создать задание на съёмку")
        self.setMinimumWidth(500)
        self.setStyleSheet("""
            QDialog { background-color: #161b22; }
            QLabel { color: #c9d1d9; font-size: 12px; }
            QLineEdit, QTextEdit, QComboBox, QDateEdit, QTimeEdit {
                background-color: #0d1117; color: #e6edf3; border: 1px solid #30363d;
                border-radius: 4px; padding: 6px; font-size: 12px;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus { border-color: #58a6ff; }
            QPushButton { padding: 8px 16px; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        
        title = QLabel("Новое задание на съёмку")
        title.setStyleSheet("color: #e6edf3; font-size: 16px; font-weight: bold; margin-bottom: 8px;")
        layout.addWidget(title)
        
        form = QFormLayout()
        form.setSpacing(10)
        
        # Date
        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd.MM.yyyy")
        form.addRow("📅 Дата:", self.date_edit)
        
        # Time
        self.time_edit = QTimeEdit()
        self.time_edit.setTime(QTime(10, 0))
        self.time_edit.setDisplayFormat("HH:mm")
        form.addRow("🕐 Время:", self.time_edit)
        
        # Location
        self.location_input = QLineEdit()
        self.location_input.setPlaceholderText("Например: Корт №2 (закрытый)")
        form.addRow("📍 Локация:", self.location_input)
        
        # Type
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Фото", "Видео", "Фото + Видео"])
        form.addRow("🎯 Тип съёмки:", self.type_combo)
        
        # Team
        self.team_input = QLineEdit()
        self.team_input.setPlaceholderText("Фотограф: Марина, Модель: Максим")
        form.addRow("👥 Команда:", self.team_input)
        
        # Priority
        self.priority_combo = QComboBox()
        self.priority_combo.addItems(["Высокий", "Средний", "Низкий"])
        self.priority_combo.setCurrentIndex(1)
        form.addRow("📊 Приоритет:", self.priority_combo)
        
        # Budget
        self.budget_input = QLineEdit()
        self.budget_input.setPlaceholderText("5000 ₽")
        form.addRow("💰 Бюджет:", self.budget_input)
        
        # Duration
        self.duration_input = QLineEdit()
        self.duration_input.setPlaceholderText("2 часа")
        form.addRow("⏱️ Длительность:", self.duration_input)
        
        # Content plan link (optional)
        self.cp_combo = QComboBox()
        self.cp_combo.addItem("— не привязывать —")
        for cp in self.dm.get_content_plan():
            self.cp_combo.addItem(f"{cp['date']} · {cp['topic']} ({cp['format']})", cp['id'])
        form.addRow("📝 Связь с контент-планом:", self.cp_combo)
        
        # Tech requirements
        self.tech_input = QTextEdit()
        self.tech_input.setPlaceholderText("Формат: JPEG + RAW, Ориентация: вертикальная 4:5, Разрешение: 4000x5000")
        self.tech_input.setMaximumHeight(60)
        form.addRow("⚙️ Технические требования:", self.tech_input)
        
        # Notes
        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Свет естественный + софтбокс. Акцент на эмоциях ребёнка.")
        self.notes_input.setMaximumHeight(60)
        form.addRow("📝 Примечания:", self.notes_input)
        
        layout.addLayout(form)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("✅ Создать задание")
        buttons.button(QDialogButtonBox.Cancel).setText("Отмена")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def _on_accept(self):
        """Validate and accept."""
        date_str = self.date_edit.date().toString("dd.MM.yyyy")
        time_str = self.time_edit.time().toString("HH:mm")
        location = self.location_input.text().strip()
        
        if not location:
            QMessageBox.warning(self, "Внимание", "Укажите локацию съёмки!")
            return
        
        # Get selected content plan ID
        cp_idx = self.cp_combo.currentIndex()
        cp_id = self.cp_combo.itemData(cp_idx) if cp_idx > 0 else None
        
        self.task_data = {
            "date": date_str,
            "time": time_str,
            "location": location,
            "type": self.type_combo.currentText(),
            "team": self.team_input.text().strip(),
            "priority": self.priority_combo.currentText(),
            "budget": self.budget_input.text().strip() or "0 ₽",
            "duration": self.duration_input.text().strip() or "2 часа",
            "content_plan_link": cp_id,
            "tech_req": self.tech_input.toPlainText().strip(),
            "notes": self.notes_input.toPlainText().strip(),
        }
        
        self.accept()
    
    def get_task_data(self) -> Dict[str, Any]:
        return getattr(self, 'task_data', {})


class EditTaskDialog(QDialog):
    """Form for editing an existing shooting task."""
    
    def __init__(self, task: Dict[str, Any], data_manager, parent=None):
        super().__init__(parent)
        self.dm = data_manager
        self.original_task = dict(task)
        self.setWindowTitle(f"✏️ Редактировать задание {task['id']}")
        self.setMinimumWidth(500)
        self.setStyleSheet("""
            QDialog { background-color: #161b22; }
            QLabel { color: #c9d1d9; font-size: 12px; }
            QLineEdit, QTextEdit, QComboBox, QDateEdit, QTimeEdit {
                background-color: #0d1117; color: #e6edf3; border: 1px solid #30363d;
                border-radius: 4px; padding: 6px; font-size: 12px;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus { border-color: #58a6ff; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        
        title = QLabel(f"Редактирование задания {task['id']}")
        title.setStyleSheet("color: #e6edf3; font-size: 16px; font-weight: bold; margin-bottom: 8px;")
        layout.addWidget(title)
        
        form = QFormLayout()
        form.setSpacing(10)
        
        # Date
        self.date_edit = QDateEdit()
        try:
            parts = task['date'].split('.')
            self.date_edit.setDate(QDate(int(parts[2]), int(parts[1]), int(parts[0])))
        except:
            self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd.MM.yyyy")
        form.addRow("📅 Дата:", self.date_edit)
        
        # Time
        self.time_edit = QTimeEdit()
        try:
            h, m = map(int, task['time'].split(':'))
            self.time_edit.setTime(QTime(h, m))
        except:
            self.time_edit.setTime(QTime(10, 0))
        self.time_edit.setDisplayFormat("HH:mm")
        form.addRow("🕐 Время:", self.time_edit)
        
        # Location
        self.location_input = QLineEdit(task.get('location', ''))
        form.addRow("📍 Локация:", self.location_input)
        
        # Type
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Фото", "Видео", "Фото + Видео"])
        cur_type = task.get('type', 'Фото')
        idx = self.type_combo.findText(cur_type)
        if idx >= 0:
            self.type_combo.setCurrentIndex(idx)
        form.addRow("🎯 Тип съёмки:", self.type_combo)
        
        # Status
        self.status_combo = QComboBox()
        self.status_combo.addItems(list(STATUS_COLORS.keys()))
        cur_status = task.get('status', 'Черновик')
        sidx = self.status_combo.findText(cur_status)
        if sidx >= 0:
            self.status_combo.setCurrentIndex(sidx)
        form.addRow("📊 Статус:", self.status_combo)
        
        # Team
        self.team_input = QLineEdit(task.get('team', ''))
        form.addRow("👥 Команда:", self.team_input)
        
        # Priority
        self.priority_combo = QComboBox()
        self.priority_combo.addItems(["Высокий", "Средний", "Низкий"])
        cur_priority = task.get('priority', 'Средний')
        pidx = self.priority_combo.findText(cur_priority)
        if pidx >= 0:
            self.priority_combo.setCurrentIndex(pidx)
        form.addRow("📊 Приоритет:", self.priority_combo)
        
        # Budget
        self.budget_input = QLineEdit(task.get('budget', ''))
        form.addRow("💰 Бюджет:", self.budget_input)
        
        # Duration
        self.duration_input = QLineEdit(task.get('duration', ''))
        form.addRow("⏱️ Длительность:", self.duration_input)
        
        # Tech requirements
        self.tech_input = QTextEdit(task.get('tech_req', ''))
        self.tech_input.setMaximumHeight(60)
        form.addRow("⚙️ Технические требования:", self.tech_input)
        
        # Notes
        self.notes_input = QTextEdit(task.get('notes', ''))
        self.notes_input.setMaximumHeight(60)
        form.addRow("📝 Примечания:", self.notes_input)
        
        layout.addLayout(form)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText("💾 Сохранить изменения")
        buttons.button(QDialogButtonBox.Cancel).setText("Отмена")
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def _on_save(self):
        """Validate and save changes back to original task."""
        location = self.location_input.text().strip()
        if not location:
            QMessageBox.warning(self, "Внимание", "Локация не может быть пустой!")
            return
        
        # Update original task dict (which is stored in DataManager)
        self.original_task.update({
            "date": self.date_edit.date().toString("dd.MM.yyyy"),
            "time": self.time_edit.time().toString("HH:mm"),
            "location": location,
            "type": self.type_combo.currentText(),
            "status": self.status_combo.currentText(),
            "team": self.team_input.text().strip(),
            "priority": self.priority_combo.currentText(),
            "budget": self.budget_input.text().strip() or "0 ₽",
            "duration": self.duration_input.text().strip() or "2 часа",
            "tech_req": self.tech_input.toPlainText().strip(),
            "notes": self.notes_input.toPlainText().strip(),
        })
        
        self.dm.save()
        logger.info(f"Updated task {self.original_task['id']}")
        self.accept()


class ShotListTable(QWidget):
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
            num_item = QTableWidgetItem(str(shot["num"]))
            num_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row, 0, num_item)

            desc_item = QTableWidgetItem(shot["desc"])
            table.setItem(row, 1, desc_item)

            ref_item = QTableWidgetItem(shot.get("ref", "—") if shot.get("ref") else "—")
            ref_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row, 2, ref_item)

            priority_item = QTableWidgetItem(shot["priority"])
            priority_item.setTextAlignment(Qt.AlignCenter)
            priority_color = {"Высокий": "#f85149", "Средний": "#9e6a03", "Низкий": "#8b949e"}.get(shot["priority"], "#8b949e")
            priority_item.setForeground(QColor(priority_color))
            table.setItem(row, 3, priority_item)

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

        add_btn = QPushButton("➕ Добавить кадр")
        add_btn.setObjectName("topBtn")
        add_btn.setStyleSheet("font-size: 11px; padding: 6px 12px;")
        add_btn.clicked.connect(lambda: QMessageBox.information(self, "Добавить кадр", "В полной версии откроется форма добавления кадра."))
        layout.addWidget(add_btn)


class TaskDetails(QWidget):
    def __init__(self, task: Dict[str, Any], data_manager, parent=None):
        super().__init__(parent)
        self.task = task
        self.dm = data_manager
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

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

        cp_link = self.task.get("content_plan_link")
        if cp_link:
            cp_item = self.dm.get_content_plan_item(cp_link) if self.dm else None
            if cp_item:
                cp_frame = QFrame()
                cp_frame.setStyleSheet("background-color: #161b22; border: 1px solid #58a6ff; border-radius: 6px; padding: 12px;")
                cp_layout = QVBoxLayout(cp_frame)
                cp_title = QLabel(f"📝 Связано с контент-планом: {cp_item['topic']}")
                cp_title.setStyleSheet("color: #58a6ff; font-size: 13px; font-weight: bold;")
                cp_layout.addWidget(cp_title)
                cp_details = QLabel(f"Дата: {cp_item['date']} · Формат: {cp_item['format']} · Рубрика: {cp_item['rubric']}")
                cp_details.setStyleSheet("color: #c9d1d9; font-size: 12px;")
                cp_layout.addWidget(cp_details)
                layout.addWidget(cp_frame)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background-color: #0f1419;")

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(16)

        meta_frame = QFrame()
        meta_frame.setObjectName("zone")
        meta_frame.setStyleSheet("QFrame#zone { background-color: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 16px; }")
        meta_layout = QFormLayout(meta_frame)
        meta_layout.addRow("📅 Дата:", QLabel(f"{self.task['date']} в {self.task['time']}"))
        meta_layout.addRow("📍 Локация:", QLabel(self.task['location']))
        meta_layout.addRow("🎯 Тип:", QLabel(self.task['type']))
        meta_layout.addRow("👥 Команда:", QLabel(self.task['team']))
        meta_layout.addRow("💰 Бюджет:", QLabel(self.task['budget']))
        meta_layout.addRow("⏱️ Длительность:", QLabel(self.task['duration']))
        meta_layout.addRow("📊 Приоритет:", QLabel(self.task['priority']))
        content_layout.addWidget(meta_frame)

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

        shot_list = ShotListTable(self.task['shots'])
        content_layout.addWidget(shot_list, stretch=1)
        content_layout.addStretch()

        scroll.setWidget(content)
        layout.addWidget(scroll, stretch=1)

        actions = QHBoxLayout()
        actions.setSpacing(12)

        edit_btn = QPushButton("✏️ Редактировать")
        edit_btn.setObjectName("topBtn")
        edit_btn.setStyleSheet("font-size: 12px; padding: 8px 16px;")
        edit_btn.clicked.connect(self._on_edit)
        actions.addWidget(edit_btn)

        export_btn = QPushButton("📄 Экспорт PDF")
        export_btn.setObjectName("topBtn")
        export_btn.setProperty("class", "primary")
        export_btn.setStyleSheet("font-size: 12px; font-weight: bold; padding: 8px 16px;")
        export_btn.clicked.connect(self._on_export_pdf)
        actions.addWidget(export_btn)

        ai_btn = QPushButton("🤖 AI: проверить полноту")
        ai_btn.setObjectName("topBtn")
        ai_btn.setStyleSheet("font-size: 12px; padding: 8px 16px;")
        ai_btn.clicked.connect(lambda: QMessageBox.information(self, "AI-проверка", "AI проанализирует ТЗ и предложит:\n\n• Добавить недостающие кадры\n• Уточнить технические требования\n• Проверить соответствие контент-плану"))
        actions.addWidget(ai_btn)

        actions.addStretch()
        layout.addLayout(actions)

    def _on_edit(self):
        dlg = EditTaskDialog(self.task, self.dm, self)
        if dlg.exec_() == QDialog.Accepted:
            # Reload details after edit
            win = self.window()
            if hasattr(win, "_reload_current_section"):
                win._reload_current_section()
            QMessageBox.information(self, "Сохранено", f"Задание {self.task['id']} обновлено.")

    def _on_export_pdf(self):
        from pdf_export import export_shooting_task_pdf
        default_name = f"TZ_{self.task['id']}_{self.task['date'].replace('.', '-')}.pdf"
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить ТЗ как PDF", default_name, "PDF файлы (*.pdf)"
        )
        if not path:
            return
        try:
            saved = export_shooting_task_pdf(self.task, self.dm, path)
            QMessageBox.information(
                self, "Готово",
                f"ТЗ сохранено как PDF:\n\n{saved}\n\nМожно отправить фотографу/оператору."
            )
            logger.info(f"Exported TZ PDF: {saved}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка экспорта", str(e))
            logger.error(f"PDF export failed: {e}")


class ShootingTasksSection(QWidget):
    def __init__(self, data_manager, parent=None):
        super().__init__(parent)
        self.dm = data_manager
        self.selected_task = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame()
        header.setObjectName("zoneHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 12, 16, 12)

        title = QLabel("🎬 Задания на съемку")
        title.setStyleSheet("color: #e6edf3; font-size: 18px; font-weight: bold;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        create_btn = QPushButton("➕ Создать задание")
        create_btn.setObjectName("topBtn")
        create_btn.setProperty("class", "primary")
        create_btn.setStyleSheet("font-size: 13px; font-weight: bold; padding: 8px 16px;")
        create_btn.clicked.connect(self._on_create_task)
        header_layout.addWidget(create_btn)

        layout.addWidget(header)

        splitter = QSplitter(Qt.Horizontal)

        list_widget = QWidget()
        list_layout = QVBoxLayout(list_widget)
        list_layout.setContentsMargins(16, 16, 8, 16)
        list_layout.setSpacing(12)

        filters = QHBoxLayout()
        status_filter = QComboBox()
        status_filter.addItem("Все статусы")
        for status in STATUS_COLORS:
            status_filter.addItem(status)
        status_filter.setObjectName("filterCombo")
        status_filter.setFixedWidth(180)
        filters.addWidget(status_filter)
        filters.addStretch()
        list_layout.addLayout(filters)

        tasks = self.dm.get_shooting_tasks()
        self.task_table = QTableWidget()
        self.task_table.setObjectName("calendar")
        self.task_table.setColumnCount(7)
        self.task_table.setHorizontalHeaderLabels(["ID", "Дата", "Локация", "Тип", "Контент-план", "Статус", "Приоритет"])
        self.task_table.setRowCount(len(tasks))
        self.task_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.task_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.task_table.verticalHeader().setVisible(False)
        self.task_table.itemClicked.connect(self._on_task_selected)

        for row, task in enumerate(tasks):
            for col, key in enumerate(["id", "date", "location", "type", "content_plan_link", "status", "priority"]):
                value = task.get(key, "")
                if key == "content_plan_link" and value:
                    cp_item = self.dm.get_content_plan_item(value)
                    value = cp_item["topic"] if cp_item else value
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                if key == "status":
                    color = STATUS_COLORS.get(task.get(key, ""), "#8b949e")
                    item.setForeground(QColor(color))
                elif key == "priority":
                    color = {"Высокий": "#f85149", "Средний": "#9e6a03", "Низкий": "#8b949e"}.get(task.get(key, ""), "#8b949e")
                    item.setForeground(QColor(color))
                self.task_table.setItem(row, col, item)

        self.task_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.task_table.setColumnWidth(0, 70)
        self.task_table.setColumnWidth(1, 90)
        self.task_table.setColumnWidth(2, 140)
        self.task_table.setColumnWidth(3, 90)
        self.task_table.setColumnWidth(4, 180)
        self.task_table.setColumnWidth(5, 110)
        self.task_table.setColumnWidth(6, 90)

        list_layout.addWidget(self.task_table, stretch=1)
        splitter.addWidget(list_widget)

        self.details_widget = QWidget()
        self.details_layout = QVBoxLayout(self.details_widget)
        self.details_layout.setContentsMargins(8, 16, 16, 16)

        placeholder = QLabel("👈 Выберите задание из списка")
        placeholder.setAlignment(Qt.AlignCenter)
        placeholder.setStyleSheet("color: #8b949e; font-size: 16px; padding: 60px;")
        self.details_layout.addWidget(placeholder)

        self.details_widget.setMinimumWidth(400)
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

    def _refresh_table(self):
        """Reload task table from DataManager."""
        tasks = self.dm.get_shooting_tasks()
        self.task_table.setRowCount(len(tasks))
        for row, task in enumerate(tasks):
            for col, key in enumerate(["id", "date", "location", "type", "content_plan_link", "status", "priority"]):
                value = task.get(key, "")
                if key == "content_plan_link" and value:
                    cp_item = self.dm.get_content_plan_item(value)
                    value = cp_item["topic"] if cp_item else value
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                if key == "status":
                    color = STATUS_COLORS.get(task.get(key, ""), "#8b949e")
                    item.setForeground(QColor(color))
                elif key == "priority":
                    color = {"Высокий": "#f85149", "Средний": "#9e6a03", "Низкий": "#8b949e"}.get(task.get(key, ""), "#8b949e")
                    item.setForeground(QColor(color))
                self.task_table.setItem(row, col, item)

    def _on_task_selected(self, item):
        row = item.row()
        tasks = self.dm.get_shooting_tasks()
        if row >= len(tasks):
            return
        task = tasks[row]
        self.selected_task = task

        while self.details_layout.count():
            it = self.details_layout.takeAt(0)
            if it.widget():
                it.widget().deleteLater()

        try:
            details = TaskDetails(task, self.dm)
            self.details_layout.addWidget(details)
        except Exception as e:
            logger.error(f"Failed to show task details: {e}")
            err = QLabel(f"Ошибка: {e}")
            err.setStyleSheet("color: #f85149; padding: 20px;")
            self.details_layout.addWidget(err)

    def _on_create_task(self):
        """Open real form dialog."""
        dlg = CreateTaskDialog(self.dm, self)
        if dlg.exec_() == QDialog.Accepted:
            task_data = dlg.get_task_data()
            if task_data:
                new_task = self.dm.create_shooting_task(task_data)
                if new_task:
                    self._refresh_table()
                    # Select the newly created task
                    tasks = self.dm.get_shooting_tasks()
                    for i, t in enumerate(tasks):
                        if t["id"] == new_task["id"]:
                            self.task_table.selectRow(i)
                            self._on_task_selected(self.task_table.item(i, 0))
                            break
                    
                    # Refresh stats in left panel
                    win = self.window()
                    if hasattr(win, "refresh_stats"):
                        win.refresh_stats()
                    
                    QMessageBox.information(
                        self, "Готово",
                        f"Создано задание {new_task['id']} на {new_task['date']}.\n"
                        f"Событие добавлено в календарь."
                    )
                    logger.info(f"Created task via form: {new_task['id']}")
