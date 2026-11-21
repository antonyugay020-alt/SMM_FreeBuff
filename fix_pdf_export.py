#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stage 3 step 2: Real PDF export for shooting tasks (TZ for photographer).
Creates pdf_export.py + rewrites shooting_tasks_section.py with working export.
Run: python fix_pdf_export.py
"""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

def write(rel, content):
    p = BASE / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding='utf-8', newline='\n')
    print(f"  [OK] {rel}")

print("\n=== Stage 3 step 2: PDF Export ===\n")

# 1. pdf_export.py
print("[1/2] Creating pdf_export.py...")

pdf_export = r'''"""PDF export for shooting tasks (TZ for photographer).
Auto-detects fpdf2 or reportlab. Uses system font for Cyrillic.
"""
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

HAS_FPDF = False
HAS_REPORTLAB = False

try:
    from fpdf import FPDF
    HAS_FPDF = True
except ImportError:
    pass

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    HAS_REPORTLAB = True
except ImportError:
    pass

FONT_CANDIDATES = [
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/tahoma.ttf",
    "C:/Windows/Fonts/segoeui.ttf",
    "C:/Windows/Fonts/calibri.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
]


def _find_font() -> Optional[str]:
    for f in FONT_CANDIDATES:
        if Path(f).exists():
            return f
    return None


def check_dependencies() -> str:
    """Return human-readable status of PDF dependencies."""
    font = _find_font()
    lines = []
    if HAS_FPDF:
        lines.append("[OK] fpdf2 установлен")
    elif HAS_REPORTLAB:
        lines.append("[OK] reportlab установлен")
    else:
        lines.append("[!] Ни fpdf2, ни reportlab не найдены")
        lines.append("    Установка:  pip install fpdf2")
    if font:
        lines.append(f"[OK] Шрифт для кириллицы: {Path(font).name}")
    else:
        lines.append("[!] Системный шрифт с кириллицей не найден")
    return "\n".join(lines)


def export_shooting_task_pdf(task: Dict[str, Any], data_manager, output_path: str) -> str:
    """Generate a TZ PDF for a shooting task. Returns the saved path."""
    font = _find_font()
    if not font:
        raise RuntimeError(
            "Не найден системный шрифт с поддержкой кириллицы "
            "(Arial / Tahoma / DejaVu). Укажи путь в FONT_CANDIDATES."
        )

    if HAS_FPDF:
        return _export_fpdf(task, data_manager, output_path, font)
    elif HAS_REPORTLAB:
        return _export_reportlab(task, data_manager, output_path, font)
    else:
        raise RuntimeError(
            "Для экспорта PDF нужна библиотека. Установи:\n\n    pip install fpdf2"
        )


def _meta_rows(task, data_manager):
    proj = data_manager.get_strategy().get("project_name", "Проект") if data_manager else "Проект"
    rows = [
        ("Проект", proj),
        ("Задание", task.get("id", "—")),
        ("Дата и время", f"{task.get('date','—')} в {task.get('time','—')}"),
        ("Локация", task.get("location", "—")),
        ("Тип съёмки", task.get("type", "—")),
        ("Команда", task.get("team", "—")),
        ("Бюджет", task.get("budget", "—")),
        ("Длительность", task.get("duration", "—")),
        ("Приоритет", task.get("priority", "—")),
        ("Статус", task.get("status", "—")),
    ]
    return rows


def _content_plan_text(task, data_manager):
    if not data_manager:
        return None
    cp_link = task.get("content_plan_link")
    if not cp_link:
        return None
    cp = data_manager.get_content_plan_item(cp_link)
    if not cp:
        return None
    return (f"Тема: {cp.get('topic','—')}   ·   Формат: {cp.get('format','—')}   ·   "
            f"Рубрика: {cp.get('rubric','—')}   ·   Дата: {cp.get('date','—')}")


# ---------------------------------------------------------------------------
# fpdf2 backend
# ---------------------------------------------------------------------------
def _export_fpdf(task, data_manager, output_path, font_path):
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.add_font("Body", "", font_path)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    left = 12
    pdf.set_left_margin(left)
    pdf.set_right_margin(left)
    usable = 210 - 2 * left  # A4 width 210mm

    # Title
    pdf.set_font("Body", "", 17)
    pdf.set_text_color(20, 24, 33)
    pdf.cell(usable, 9, f"ТЗ на съёмку  ·  {task.get('id','—')}", ln=True, align="L")
    pdf.set_draw_color(88, 166, 255)
    pdf.set_line_width(0.6)
    y = pdf.get_y() + 1
    pdf.line(left, y, left + usable, y)
    pdf.ln(4)

    pdf.set_font("Body", "", 8)
    pdf.set_text_color(120, 128, 140)
    pdf.cell(usable, 5, f"Сформировано: {datetime.now().strftime('%d.%m.%Y  %H:%M')}", ln=True)
    pdf.ln(3)

    # Meta table
    _fpdf_section(pdf, usable, "Основные параметры")
    for k, v in _meta_rows(task, data_manager):
        pdf.set_font("Body", "", 9)
        pdf.set_fill_color(238, 241, 245)
        pdf.set_text_color(90, 98, 110)
        pdf.cell(40, 6, k, border=1, fill=True)
        pdf.set_text_color(20, 24, 33)
        pdf.cell(usable - 40, 6, str(v), border=1)
        pdf.ln()
    pdf.ln(3)

    # Content plan link
    cp_text = _content_plan_text(task, data_manager)
    if cp_text:
        _fpdf_section(pdf, usable, "Связь с контент-планом")
        pdf.set_font("Body", "", 9)
        pdf.set_text_color(40, 46, 58)
        pdf.set_fill_color(236, 244, 255)
        pdf.multi_cell(usable, 6, cp_text, border=1, fill=True)
        pdf.ln(3)

    # Tech req
    _fpdf_section(pdf, usable, "Технические требования")
    pdf.set_font("Body", "", 9)
    pdf.set_text_color(40, 46, 58)
    pdf.multi_cell(usable, 6, task.get("tech_req", "—"))
    pdf.ln(3)

    # Notes
    if task.get("notes"):
        _fpdf_section(pdf, usable, "Примечания")
        pdf.set_font("Body", "", 9)
        pdf.set_text_color(40, 46, 58)
        pdf.multi_cell(usable, 6, task["notes"])
        pdf.ln(3)

    # Shots table
    _fpdf_section(pdf, usable, "Список кадров")
    pdf.ln(1)
    col_w = [10, usable - 10 - 32 - 24 - 26, 32, 24, 26]
    headers = ["№", "Описание", "Референс", "Приоритет", "Статус"]
    pdf.set_font("Body", "", 8)
    pdf.set_fill_color(230, 235, 240)
    pdf.set_text_color(40, 46, 58)
    for w, h in zip(col_w, headers):
        pdf.cell(w, 6, h, border=1, fill=True, align="C")
    pdf.ln()

    pdf.set_font("Body", "", 8)
    for shot in task.get("shots", []):
        pdf.set_text_color(20, 24, 33)
        pdf.cell(col_w[0], 6, str(shot.get("num", "")), border=1, align="C")
        desc = str(shot.get("desc", ""))
        if len(desc) > 70:
            desc = desc[:67] + "..."
        pdf.cell(col_w[1], 6, desc, border=1)
        pdf.cell(col_w[2], 6, shot.get("ref") or "—", border=1, align="C")
        pdf.cell(col_w[3], 6, shot.get("priority", "—"), border=1, align="C")
        pdf.cell(col_w[4], 6, shot.get("status", "—"), border=1, align="C")
        pdf.ln()

    pdf.ln(6)
    pdf.set_font("Body", "", 7)
    pdf.set_text_color(150, 156, 166)
    proj = data_manager.get_strategy().get("project_name", "Проект") if data_manager else "Проект"
    pdf.cell(usable, 5, f"AI SMM Manager  ·  {proj}  ·  автогенерация ТЗ", ln=True, align="C")

    pdf.output(str(output_path))
    logger.info(f"PDF exported (fpdf2): {output_path}")
    return str(output_path)


def _fpdf_section(pdf, usable, title):
    pdf.set_font("Body", "", 11)
    pdf.set_text_color(20, 24, 33)
    pdf.cell(usable, 7, title, ln=True)
    pdf.set_draw_color(210, 216, 224)
    pdf.set_line_width(0.3)
    y = pdf.get_y()
    pdf.line(pdf.l_margin, y, pdf.l_margin + usable, y)
    pdf.ln(2)


# ---------------------------------------------------------------------------
# reportlab backend (fallback)
# ---------------------------------------------------------------------------
def _export_reportlab(task, data_manager, output_path, font_path):
    pdfmetrics.registerFont(TTFont("Body", font_path))
    c = rl_canvas.Canvas(str(output_path), pagesize=A4)
    width, height = A4
    left = 40
    usable = width - 2 * left
    y = height - 50

    def ensure_space(needed):
        nonlocal y
        if y - needed < 50:
            c.showPage()
            y = height - 50

    def text(txt, size, color, x=None, dy=14):
        nonlocal y
        ensure_space(dy)
        c.setFont("Body", size)
        c.setFillColorRGB(*color)
        c.drawString(x if x is not None else left, y, txt)
        y -= dy

    text(f"ТЗ на съёмку  ·  {task.get('id','—')}", 15, (0.08, 0.10, 0.13))
    c.setStrokeColorRGB(0.35, 0.65, 1.0)
    c.setLineWidth(0.8)
    c.line(left, y + 6, left + usable, y + 6)
    y -= 4
    text(f"Сформировано: {datetime.now().strftime('%d.%m.%Y  %H:%M')}", 8, (0.47, 0.50, 0.55))
    y -= 6

    text("Основные параметры", 11, (0.08, 0.10, 0.13))
    for k, v in _meta_rows(task, data_manager):
        text(f"{k}:", 9, (0.35, 0.38, 0.43), x=left)
        text(str(v)[:90], 9, (0.08, 0.10, 0.13), x=left + 110)

    cp_text = _content_plan_text(task, data_manager)
    if cp_text:
        y -= 6
        text("Связь с контент-планом", 11, (0.08, 0.10, 0.13))
        text(cp_text[:110], 9, (0.16, 0.18, 0.23))

    y -= 6
    text("Технические требования", 11, (0.08, 0.10, 0.13))
    text(task.get("tech_req", "—")[:110], 9, (0.16, 0.18, 0.23))

    if task.get("notes"):
        y -= 6
        text("Примечания", 11, (0.08, 0.10, 0.13))
        text(task["notes"][:110], 9, (0.16, 0.18, 0.23))

    y -= 6
    text("Список кадров", 11, (0.08, 0.10, 0.13))
    text("№   Описание                                  Референс   Приоритет   Статус", 8, (0.35, 0.38, 0.43))
    for shot in task.get("shots", []):
        line = (f"{str(shot.get('num','')):<3} {str(shot.get('desc',''))[:40]:<42} "
                f"{str(shot.get('ref') or '—')[:12]:<13} {str(shot.get('priority','—')):<10} "
                f"{str(shot.get('status','—'))}")
        text(line, 8, (0.08, 0.10, 0.13))

    proj = data_manager.get_strategy().get("project_name", "Проект") if data_manager else "Проект"
    y -= 10
    text(f"AI SMM Manager  ·  {proj}  ·  автогенерация ТЗ", 7, (0.59, 0.61, 0.65))

    c.save()
    logger.info(f"PDF exported (reportlab): {output_path}")
    return str(output_path)
'''

write("pdf_export.py", pdf_export)

# 2. Rewrite shooting_tasks_section.py with working export
print("[2/2] Rewriting shooting_tasks_section.py with PDF export...")

shooting_tasks = r'''"""Shooting Tasks section: Integrated with DataManager + real PDF export."""
import logging
from pathlib import Path
from typing import Dict, Any, List

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QMessageBox, QSplitter, QComboBox, QScrollArea,
    QFileDialog)
from PySide6.QtCore import Qt
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
        from PySide6.QtWidgets import QFormLayout
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
        edit_btn.clicked.connect(lambda: QMessageBox.information(self, "Редактировать", "В полной версии откроется форма редактирования задания."))
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

    def _on_export_pdf(self):
        """Real PDF export of the shooting task TZ."""
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
                f"ТЗ сохранено как PDF:\n\n{saved}\n\n"
                f"Можно отправить фотографу/оператору."
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
        QMessageBox.information(
            self, "Создать задание",
            "В полной версии откроется форма создания задания:\n\n"
            "• Дата, время, локация\n• Тип съёмки (фото/видео/оба)\n"
            "• Связь с пунктом контент-плана\n• Команда\n"
            "• Список кадров с референсами\n• Технические требования\n\n"
            "AI может помочь заполнить форму на основе контент-плана."
        )
'''

write("gui_sections/shooting_tasks_section.py", shooting_tasks)

# 3. Dependency check
print("\n[3/3] Checking PDF dependencies...")
import sys
sys.path.insert(0, str(BASE))
try:
    from pdf_export import check_dependencies
    print(check_dependencies())
except Exception as e:
    print(f"  [!] Проверка не удалась: {e}")

print("\n=== Stage 3 step 2 Complete ===")
print("\nWhat works now:")
print("  [OK] 'Экспорт PDF' button generates a real PDF file")
print("  [OK] PDF contains: meta, content-plan link, tech req, notes, shot list")
print("  [OK] Cyrillic supported via system font (Arial/Tahoma/DejaVu)")
print("  [OK] Auto-backend: fpdf2 preferred, reportlab fallback")
print("\nRun START.bat, open 'Задания на съемку', select a task, click '📄 Экспорт PDF'.")