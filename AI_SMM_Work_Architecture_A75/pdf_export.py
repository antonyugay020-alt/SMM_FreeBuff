"""PDF export for shooting tasks (TZ for photographer).
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
    str(Path(__file__).resolve().parent / "assets" / "DejaVuSans.ttf"),
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


def _font_or_raise() -> str:
    """TTF с кириллицей или понятная ошибка вместо PDF из квадратов."""
    font = _find_font()
    if not font:
        raise RuntimeError(_FONT_ERROR)
    return font


_FONT_ERROR = ("Не найден системный шрифт с поддержкой кириллицы "
               "(Arial / Tahoma / DejaVu). Укажи путь в FONT_CANDIDATES.")
_LIB_ERROR = "Для экспорта PDF нужна библиотека. Установи:\n\n    pip install fpdf2"


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
    font = _font_or_raise()

    if HAS_FPDF:
        return _export_fpdf(task, data_manager, output_path, font)
    elif HAS_REPORTLAB:
        return _export_reportlab(task, data_manager, output_path, font)
    else:
        raise RuntimeError(_LIB_ERROR)


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


# ---------------------------------------------------------------------------
# Content plan / strategy documents (fpdf2: tables and flowing text)
# ---------------------------------------------------------------------------
PAGE_LEFT = 12
USABLE = 210 - 2 * PAGE_LEFT  # A4 width in mm
PLAN_COLUMNS = ((20, "date", "Дата"), (86, "topic", "Тема"), (28, "rubric", "Рубрика"),
                (24, "format", "Формат"), (28, "status", "Статус"))
KPI_COLUMNS = ((70, "metric", "Метрика"), (40, "current", "Сейчас"),
               (40, "target", "Цель"), (36, "deadline", "Срок"))


def _new_document(font_path: str):
    if not HAS_FPDF:
        raise RuntimeError(_LIB_ERROR)
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.add_font("Body", "", font_path)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_left_margin(PAGE_LEFT)
    pdf.set_right_margin(PAGE_LEFT)
    pdf.add_page()
    return pdf


def _project_name(data_manager) -> str:
    strategy = (data_manager.get_strategy() or {}) if data_manager else {}
    return strategy.get("project_name") or "Проект"


def _document_head(pdf, title: str, note: str) -> None:
    pdf.set_font("Body", "", 17)
    pdf.set_text_color(20, 24, 33)
    pdf.cell(USABLE, 9, title, new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(88, 166, 255)
    pdf.set_line_width(0.6)
    y = pdf.get_y() + 1
    pdf.line(PAGE_LEFT, y, PAGE_LEFT + USABLE, y)
    pdf.ln(4)
    pdf.set_font("Body", "", 8)
    pdf.set_text_color(120, 128, 140)
    pdf.multi_cell(USABLE, 5, note)
    pdf.ln(3)


def _document_footer(pdf, project: str, kind: str) -> None:
    pdf.ln(6)
    pdf.set_font("Body", "", 7)
    pdf.set_text_color(150, 156, 166)
    pdf.cell(USABLE, 5, f"AI SMM Manager  ·  {project}  ·  {kind}",
             new_x="LMARGIN", new_y="NEXT", align="C")


def _short(value: Any, limit: int) -> str:
    text = str(value or "").replace("\n", " ").strip()
    return text if len(text) <= limit else text[:limit - 1] + "…"


def _table_head(pdf, columns) -> None:
    pdf.set_font("Body", "", 8)
    pdf.set_fill_color(230, 235, 240)
    pdf.set_text_color(40, 46, 58)
    for width, _, title in columns:
        pdf.cell(width, 6, title, border=1, fill=True, align="C")
    pdf.ln()


def _table_rows(pdf, columns, rows) -> None:
    pdf.set_font("Body", "", 8)
    for row in rows:
        pdf.set_text_color(20, 24, 33)
        for width, key, _ in columns:
            limit = 60 if key in ("topic", "metric") else 24
            pdf.cell(width, 6, _short(row.get(key), limit), border=1)
        pdf.ln()


def export_content_plan_pdf(data_manager, output_path: str) -> str:
    """Контент-план одной таблицей: дата, тема, рубрика, формат, статус."""
    font = _font_or_raise()
    items = list(data_manager.get_content_plan())
    project = _project_name(data_manager)
    pdf = _new_document(font)
    _document_head(pdf, "Контент-план",
                   f"{project}  ·  сформировано: {datetime.now():%d.%m.%Y %H:%M}  ·  "
                   f"позиций: {len(items)}")
    _table_head(pdf, PLAN_COLUMNS)
    _table_rows(pdf, PLAN_COLUMNS, items)
    _document_footer(pdf, project, "план публикаций")
    pdf.output(str(output_path))
    logger.info(f"Content plan PDF: {output_path}")
    return str(output_path)


def export_strategy_pdf(data_manager, output_path: str) -> str:
    """Стратегия текстом по блокам плюс таблица KPI."""
    font = _font_or_raise()
    strategy = (data_manager.get_strategy() or {}) if data_manager else {}
    sections = strategy.get("sections") or []
    kpis = strategy.get("kpis") or []
    project = _project_name(data_manager)
    pdf = _new_document(font)
    _document_head(pdf, "Стратегия проекта",
                   f"{project}  ·  версия {strategy.get('version') or '—'}  ·  "
                   f"блоков: {len(sections)}  ·  сформировано: {datetime.now():%d.%m.%Y %H:%M}")

    for section in sections:
        pdf.set_font("Body", "", 11)
        pdf.set_text_color(20, 24, 33)
        pdf.multi_cell(USABLE, 6, str(section.get("title") or "Блок"))
        pdf.set_font("Body", "", 9)
        pdf.set_text_color(40, 46, 58)
        pdf.multi_cell(USABLE, 5, str(section.get("content") or "—"))
        pdf.ln(3)

    pdf.ln(2)
    _fpdf_section(pdf, USABLE, "KPI")
    _table_head(pdf, KPI_COLUMNS)
    _table_rows(pdf, KPI_COLUMNS, kpis)
    if not kpis:
        pdf.ln(2)
        pdf.set_font("Body", "", 9)
        pdf.set_text_color(90, 98, 110)
        pdf.cell(USABLE, 6, "KPI не заданы.", new_x="LMARGIN", new_y="NEXT")

    _document_footer(pdf, project, "стратегия")
    pdf.output(str(output_path))
    logger.info(f"Strategy PDF: {output_path}")
    return str(output_path)
