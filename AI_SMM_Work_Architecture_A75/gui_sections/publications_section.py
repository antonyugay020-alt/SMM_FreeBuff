"""Publications workspace: five numbered zones (library, preview, folders, calendar, schedule).

Design reference: approved shell mockup — coloured zone frames, status pills,
media cards with badges, virtual folders with drop targets, month calendar.
"""
from __future__ import annotations

import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt, Signal, QMimeData, QRectF
from PySide6.QtGui import QPixmap, QDrag, QPainter, QPainterPath, QColor, QFontMetrics
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGridLayout, QScrollArea, QComboBox, QMessageBox, QCheckBox,
    QStackedWidget, QTimeEdit, QSizePolicy, QSpacerItem, QInputDialog, QApplication,
    QDialog, QFileDialog)
from PySide6.QtCore import QTime

from gui_sections.section_base import DataSection

logger = logging.getLogger(__name__)

DRAG_TYPE = "application/x-smm-publication"
MEDIA_DIR = Path(__file__).resolve().parent.parent.parent / "media" / "images"

# Zone accents
BLUE = "#5aa9ff"
PURPLE = "#c08cff"
PINK = "#f472b6"
RED = "#f87171"
YELLOW = "#e3b341"
TEAL = "#2dd4bf"
MUTED = "#8b949e"
TEXT = "#e6edf3"
CARD_BG = "#0e1319"
PANEL_BG = "#0b0f14"

STATUS = {
    "approved": ("Одобрено", "#3fb950"),
    "pending": ("На проверке", "#d29922"),
    "rejected": ("Отклонено", "#f85149"),
}

FILTERS = (("all", "Все"), ("pending", "На проверке"),
           ("approved", "Одобрено"), ("rejected", "Отклонено"))

# Пресеты обработки фото: подпись в меню → операции batch_photo
PHOTO_PRESETS = (("Кадрировать 4:5 + цвет + сжатие", ["crop", "color", "compress"]),
                 ("Только сжатие (JPEG 85, до 1600 px)", ["compress"]),
                 ("Только кадрирование 4:5", ["crop"]),
                 ("Только цвет", ["color"]))

MONTHS = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
          "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


# ---------- helpers ----------

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".avi", ".mkv", ".m4v", ".webm"}
POSTER_DIR = MEDIA_DIR / ".thumbs"
_PIXMAPS: Dict[str, QPixmap] = {}


def _header_button(text: str, slot) -> QPushButton:
    """Кнопка действия в шапке зоны (как «🎛 Обработать фото»)."""
    button = QPushButton(text)
    button.setCursor(Qt.PointingHandCursor)
    button.setStyleSheet("QPushButton{background:rgba(90,169,255,0.14);color:#9ecbff;"
                         "border:1px solid rgba(90,169,255,0.45);border-radius:8px;"
                         "padding:4px 10px;font-size:10px;font-weight:600;}"
                         "QPushButton:hover{border-color:#5aa9ff;}")
    button.clicked.connect(slot)
    return button


def _media_file(item: Dict[str, Any]) -> Optional[Path]:
    """Real file of a media record: stored path first, then media/images by name."""
    candidates = []
    raw = str(item.get("path") or "").strip()
    if raw:
        candidates.append(Path(raw))
    name = str(item.get("name") or "").strip()
    if name:
        candidates.append(MEDIA_DIR / name)
    for candidate in candidates:
        try:
            if candidate.is_file():
                return candidate
        except OSError:
            continue
    return None


def _video_poster(path: Path) -> Optional[Path]:
    """Кадр-превью видео через ffmpeg; кеш в `media/images/.thumbs` по пути + mtime."""
    try:
        poster = POSTER_DIR / f"{path.stem}_{int(path.stat().st_mtime)}.jpg"
    except OSError:
        return None
    if poster.is_file():
        return poster
    POSTER_DIR.mkdir(parents=True, exist_ok=True)
    for second in ("1", "0"):
        command = ["ffmpeg", "-y", "-loglevel", "error", "-ss", second,
                   "-i", str(path), "-frames:v", "1", "-vf", "scale=320:-1",
                   str(poster)]
        try:
            done = subprocess.run(command, capture_output=True, timeout=20)
        except (OSError, subprocess.SubprocessError):
            logger.debug("ffmpeg недоступен для кадра видео")
            return None
        if done.returncode == 0 and poster.is_file():
            return poster
    return None


def _pixmap_for(item: Dict[str, Any]) -> Optional[QPixmap]:
    """Decoded image for a media record (фото или кадр видео), cached by path + mtime."""
    path = _media_file(item)
    if path is None:
        return None
    suffix = path.suffix.lower()
    if suffix in VIDEO_SUFFIXES:
        path = _video_poster(path)
        if path is None:
            return None
    elif suffix not in IMAGE_SUFFIXES:
        return None
    try:
        key = f"{path}|{path.stat().st_mtime_ns}"
    except OSError:
        return None
    pm = _PIXMAPS.get(key)
    if pm is None:
        pm = QPixmap(str(path))
        if pm.isNull():
            return None
        if len(_PIXMAPS) > 200:
            _PIXMAPS.clear()
        _PIXMAPS[key] = pm
    return pm


def _rounded_pixmap(pm: QPixmap, w: int, h: int, radius: int = 8) -> QPixmap:
    scaled = pm.scaled(w, h, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    target = QPixmap(w, h)
    target.fill(Qt.transparent)
    painter = QPainter(target)
    painter.setRenderHint(QPainter.Antialiasing)
    path = QPainterPath()
    path.addRoundedRect(QRectF(0, 0, w, h), radius, radius)
    painter.setClipPath(path)
    painter.drawPixmap(int((w - scaled.width()) / 2), int((h - scaled.height()) / 2), scaled)
    painter.end()
    return target


def _elide(text: str, width: int) -> str:
    fm = QFontMetrics(QApplication.font())
    return fm.elidedText(text, Qt.ElideMiddle, width)


def _rgba(color: str, alpha: float) -> str:
    rgb = ",".join(str(int(color[i:i + 2], 16)) for i in (1, 3, 5))
    return f"rgba({rgb},{alpha})"


def _pill(text: str, color: str, bg: str = None) -> QLabel:
    label = QLabel(text)
    bg = bg or _rgba(color, 0.14)
    label.setStyleSheet(
        f"color:{color};background:{bg};border:1px solid {_rgba(color, 0.45)};"
        f"border-radius:8px;padding:2px 8px;font-size:10px;font-weight:600;")
    return label


class ZoneCard(QFrame):
    """Frame with a numbered coloured header, as in the approved mockup."""

    def __init__(self, number: str, title: str, color: str, parent=None):
        super().__init__(parent)
        self.setObjectName("zoneCard")
        self.setStyleSheet(
            f"QFrame#zoneCard{{background:{CARD_BG};border:1px solid {_rgba(color, 0.40)};"
            f"border-radius:12px;}}")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        header = QWidget()
        hl = QHBoxLayout(header)
        hl.setContentsMargins(10, 8, 10, 8)
        hl.setSpacing(8)

        badge = QLabel(number)
        badge.setFixedSize(22, 22)
        badge.setAlignment(Qt.AlignCenter)
        badge.setStyleSheet(
            f"background:{color};color:#0b0f14;border-radius:6px;font-size:12px;font-weight:800;")
        hl.addWidget(badge)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(f"color:{color};font-size:14px;font-weight:700;")
        hl.addWidget(self.title_label)
        hl.addStretch()

        self.header_layout = hl
        outer.addWidget(header)

        body = QWidget()
        self.body = QVBoxLayout(body)
        self.body.setContentsMargins(10, 2, 10, 10)
        self.body.setSpacing(8)
        outer.addWidget(body, 1)

    def add_header_widget(self, widget: QWidget):
        self.header_layout.addWidget(widget)


# ---------- media card ----------

class MediaCard(QFrame):
    clicked = Signal(dict)

    def __init__(self, item: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.item = item
        self.selected = False
        self._drag_pos = None
        self.setObjectName("mediaCard")
        self.setFixedWidth(140)
        self.setCursor(Qt.PointingHandCursor)
        self._apply_style()

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        thumb = QLabel()
        thumb.setFixedSize(140, 100)
        thumb.setAlignment(Qt.AlignCenter)
        pm = _pixmap_for(item)
        if pm:
            thumb.setPixmap(_rounded_pixmap(pm, 140, 100, 9))
        else:
            thumb.setText("VIDEO" if item.get("type") == "video" else "PHOTO")
            thumb.setStyleSheet(f"background:#151b23;color:#39424d;font-size:10px;"
                                f"letter-spacing:1px;border-top-left-radius:9px;"
                                f"border-top-right-radius:9px;")
        lay.addWidget(thumb)

        kind = QLabel("VID" if item.get("type") == "video" else "IMG")
        kind.setParent(thumb)
        kind.setStyleSheet("background:rgba(8,12,16,0.75);color:#dfe6ee;border-radius:4px;"
                           "font-size:9px;padding:1px 3px;")
        kind.move(6, 6)

        status = item.get("status", "pending")
        if status in STATUS:
            dot = QLabel()
            dot.setParent(thumb)
            dot.setFixedSize(12, 12)
            dot.setStyleSheet(f"background:{STATUS[status][1]};border-radius:6px;")
            dot.move(120, 8)

        name = QLabel(_elide(item.get("name", ""), 124))
        name.setStyleSheet(f"color:{TEXT};font-size:10px;font-weight:600;padding:6px 7px 0 7px;")
        lay.addWidget(name)

        size = QLabel(item.get("size", ""))
        size.setStyleSheet(f"color:{MUTED};font-size:9px;padding:1px 7px;")
        lay.addWidget(size)

        text, color = STATUS.get(status, ("—", MUTED))
        pill = _pill(text, color)
        pill.setStyleSheet(pill.styleSheet() + "margin:2px 6px 7px 6px;")
        lay.addWidget(pill, 0, Qt.AlignLeft)

    def _apply_style(self):
        border = "#1f6feb" if self.selected else "#1e252e"
        self.setStyleSheet(
            f"QFrame#mediaCard{{background:#121820;border:2px solid {border};border-radius:10px;}}"
            f"QFrame#mediaCard:hover{{border-color:{BLUE};}}")

    def set_selected(self, value: bool):
        self.selected = value
        self._apply_style()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.pos()
            self.clicked.emit(self.item)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton) or self._drag_pos is None:
            return
        if (event.pos() - self._drag_pos).manhattanLength() < 12:
            return
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(DRAG_TYPE, json.dumps(self.item).encode("utf-8"))
        drag.setMimeData(mime)
        drag.exec_(Qt.MoveAction)
        self._drag_pos = None


# ---------- folder card ----------

class FolderCard(QFrame):
    changed = Signal()

    def __init__(self, folder_id: str, data: Dict[str, Any], dm, parent=None):
        super().__init__(parent)
        self.folder_id = folder_id
        self.data = data
        self.dm = dm
        self.color = data.get("color", BLUE)
        self.setAcceptDrops(True)
        self.setObjectName("folderCard")
        self._apply_style()

        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(8)

        head = QHBoxLayout()
        head.setSpacing(8)
        icon = QLabel("◉")
        icon.setFixedSize(22, 22)
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet(f"background:{self.color};color:#0b0f14;border-radius:6px;"
                           f"font-size:12px;font-weight:800;")
        head.addWidget(icon)
        name = QLabel(data.get("name", folder_id))
        name.setStyleSheet(f"color:{TEXT};font-size:14px;font-weight:700;")
        head.addWidget(name)
        head.addStretch()
        plan = QPushButton("Расписание")
        plan.setCursor(Qt.PointingHandCursor)
        plan.setStyleSheet(f"background:transparent;color:{self.color};"
                           f"border:1px solid {_rgba(self.color, 0.50)};"
                           f"border-radius:6px;padding:4px 8px;font-size:10px;")
        head.addWidget(plan)
        lay.addLayout(head)

        desc = QLabel(data.get("desc", ""))
        desc.setStyleSheet(f"color:{MUTED};font-size:10px;")
        lay.addWidget(desc)

        thumbs = QHBoxLayout()
        thumbs.setSpacing(6)
        items = data.get("items", [])
        for item in items[:3]:
            thumbs.addWidget(self._thumb(item.get("name", "")))
        if len(items) < 4:
            add = QLabel("+\nДобавить")
            add.setAlignment(Qt.AlignCenter)
            add.setFixedSize(56, 56)
            add.setStyleSheet("background:transparent;border:1px dashed #2b3540;border-radius:8px;"
                              "color:#5c6874;font-size:9px;")
            thumbs.addWidget(add)
        thumbs.addStretch()
        lay.addLayout(thumbs)

        footer = QHBoxLayout()
        count = QLabel(f"{len(items)} файл(ов)")
        count.setStyleSheet(f"color:{MUTED};font-size:10px;")
        footer.addWidget(count)
        footer.addStretch()
        next_item = items[0] if items else None
        when = f"{next_item['date']} {next_item.get('time', '')}" if next_item else "—"
        nxt = QLabel(f"Следующая: {when}")
        nxt.setStyleSheet(f"color:{self.color};font-size:10px;")
        footer.addWidget(nxt)
        lay.addLayout(footer)

    def _thumb(self, name: str) -> QLabel:
        label = QLabel()
        label.setFixedSize(56, 56)
        label.setAlignment(Qt.AlignCenter)
        pm = _pixmap_for({"name": name})
        if pm:
            label.setPixmap(_rounded_pixmap(pm, 56, 56, 7))
        else:
            label.setText("IMG")
            label.setStyleSheet("background:#151b23;border-radius:7px;color:#39424d;font-size:8px;")
        return label

    def _apply_style(self, hover: bool = False):
        border = (f"2px dashed {self.color}" if hover
                  else f"1px solid {_rgba(self.color, 0.40)}")
        self.setStyleSheet(
            f"QFrame#folderCard{{background:#121820;border:{border};border-radius:10px;}}")

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(DRAG_TYPE):
            event.acceptProposedAction()
            self._apply_style(hover=True)

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(DRAG_TYPE):
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self._apply_style()

    def dropEvent(self, event):
        if not event.mimeData().hasFormat(DRAG_TYPE):
            return
        payload = json.loads(bytes(event.mimeData().data(DRAG_TYPE)).decode("utf-8"))
        self._apply_style()
        media_id = payload.get("id")
        if media_id and self.dm.move_media_ready_to_publication(media_id, self.folder_id, "12:00"):
            self.changed.emit()
        event.acceptProposedAction()


# ---------- preview panel ----------

class PreviewPanel(QWidget):
    status_changed = Signal()
    repeat_requested = Signal()

    def __init__(self, dm, parent=None):
        super().__init__(parent)
        self.dm = dm
        self.item: Optional[Dict[str, Any]] = None

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        self.image = QLabel("Выбери материал в медиатеке")
        self.image.setAlignment(Qt.AlignCenter)
        # Ignored по обеим осям: иначе minimumSizeHint картинки не даёт панели сжиматься
        self.image.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.image.setMinimumSize(0, 240)
        self.image.setStyleSheet("background:#0a0e13;border-radius:9px;color:#5c6874;font-size:11px;")
        lay.addWidget(self.image, 1)

        self.name = QLabel("—")
        self.name.setStyleSheet(f"color:{TEXT};font-size:12px;font-weight:700;")
        lay.addWidget(self.name)

        self.meta = QLabel("")
        self.meta.setStyleSheet(f"color:{MUTED};font-size:10px;")
        lay.addWidget(self.meta)

        self.badge_row = QHBoxLayout()
        self.badge_row.addStretch()
        lay.addLayout(self.badge_row)

        actions = QHBoxLayout()
        actions.setSpacing(6)
        self.reject_btn = QPushButton("Отклонить")
        self.reject_btn.setCursor(Qt.PointingHandCursor)
        self.reject_btn.setStyleSheet("background:transparent;color:#f85149;"
                                      "border:1px solid rgba(248,81,73,0.45);"
                                      "border-radius:7px;padding:6px 10px;font-size:11px;")
        self.reject_btn.clicked.connect(lambda: self._set_status("rejected"))
        actions.addWidget(self.reject_btn)

        self.repeat_btn = QPushButton("Повторить обработку")
        self.repeat_btn.setCursor(Qt.PointingHandCursor)
        self.repeat_btn.setStyleSheet("background:#191f27;color:#dfe6ee;border:1px solid #2b3540;"
                                      "border-radius:7px;padding:6px 10px;font-size:11px;")
        self.repeat_btn.clicked.connect(lambda: self.repeat_requested.emit())
        actions.addWidget(self.repeat_btn)
        lay.addLayout(actions)

        compare = QPushButton("Сравнить с исходником")
        compare.setCursor(Qt.PointingHandCursor)
        compare.setStyleSheet("background:#191f27;color:#c9d1d9;border:1px solid #2b3540;"
                              "border-radius:7px;padding:6px 10px;font-size:11px;")
        compare.clicked.connect(self._compare)
        lay.addWidget(compare)

    def show_item(self, item: Dict[str, Any]):
        self.item = item
        self.name.setText(item.get("name", "—"))
        meta = [part for part in (item.get("size", ""), item.get("date", "")) if part]
        path = _media_file(item)
        if path:
            meta.append(str(path.parent))
        self.meta.setText(" · ".join(meta))
        while self.badge_row.count() > 1:
            w = self.badge_row.takeAt(0).widget()
            if w:
                w.deleteLater()
        text, color = STATUS.get(item.get("status", "pending"), ("—", MUTED))
        self.badge_row.insertWidget(0, _pill(text, color))
        self._render()

    def _render(self):
        """Вписать текущий материал в доступную область — вызывается и при resize."""
        item = self.item
        pm = _pixmap_for(item) if item else None
        self.image.clear()
        if pm is not None:
            box_w = max(240, self.image.width() - 4)
            box_h = max(200, self.image.height() - 4)
            self.image.setPixmap(pm.scaled(box_w, box_h, Qt.KeepAspectRatio,
                                           Qt.SmoothTransformation))
        elif item is None:
            self.image.setText("Выбери материал в медиатеке")
        elif _media_file(item) is None:
            self.image.setText(f"Файл не найден: {item.get('name', '')}"
                               if item.get("name") else "Выбери материал в медиатеке")
        elif item.get("type") == "video":
            self.image.setText("Кадр видео недоступен — нужен ffmpeg")
        else:
            self.image.setText(f"Не удалось открыть: {item.get('name', '')}")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "image"):
            self._render()

    def _set_status(self, status: str):
        if not self.item:
            return
        self.item["status"] = status
        self.dm.save()
        self.show_item(self.item)
        self.status_changed.emit()

    def _compare(self):
        item = self.item
        if not item:
            return
        current = _media_file(item)
        raw = str(item.get("source_path") or "").strip()
        source = Path(raw) if raw else None
        if current is None or source is None or not source.is_file():
            QMessageBox.information(
                self, "Сравнение с исходником",
                "Исходник не сохранён. Обработай материал кнопкой "
                "«Повторить обработку» — после этого сравнивать будет с чем.")
            return
        CompareDialog(source, current, self).exec()


class CompareDialog(QDialog):
    """Исходник и обработанный файл рядом: видно кадр, цвет и сжатие."""

    def __init__(self, source: Path, current: Path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Сравнение с исходником")
        self.setStyleSheet(f"QDialog{{background:{PANEL_BG};}}")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(10)

        columns = QHBoxLayout()
        columns.setSpacing(10)
        for title, path, color in (("Исходник", source, MUTED),
                                   ("Обработано", current, TEAL)):
            columns.addLayout(self._column(title, path, color))
        lay.addLayout(columns)

        close = QPushButton("Закрыть")
        close.setCursor(Qt.PointingHandCursor)
        close.setStyleSheet("background:#191f27;color:#dfe6ee;border:1px solid #2b3540;"
                            "border-radius:7px;padding:6px 14px;font-size:11px;")
        close.clicked.connect(self.accept)
        lay.addWidget(close, 0, Qt.AlignRight)

    @staticmethod
    def _column(title: str, path: Path, color: str) -> QVBoxLayout:
        column = QVBoxLayout()
        column.setSpacing(6)
        caption = QLabel(title)
        caption.setStyleSheet(f"color:{color};font-size:11px;font-weight:700;")
        column.addWidget(caption)

        image = QLabel()
        image.setAlignment(Qt.AlignCenter)
        image.setFixedSize(300, 300)
        image.setStyleSheet("background:#0a0e13;border:1px solid #1b222a;"
                            "border-radius:9px;color:#5c6874;font-size:10px;")
        pm = _pixmap_for({"path": str(path)})
        if pm is None:
            image.setText("Не удалось открыть файл")
            size = "—"
        else:
            image.setPixmap(pm.scaled(296, 296, Qt.KeepAspectRatio,
                                      Qt.SmoothTransformation))
            kb = max(1, path.stat().st_size // 1024)
            size = f"{pm.width()}×{pm.height()} px · {kb} КБ"
        column.addWidget(image)

        info = QLabel(f"{path.name}\n{size}")
        info.setWordWrap(True)
        info.setStyleSheet(f"color:{MUTED};font-size:10px;")
        column.addWidget(info)
        return column


# ---------- section ----------

class PublicationsSection(DataSection):
    """Five-zone publications workspace."""

    def __init__(self, data_manager, settings=None, parent=None):
        super().__init__(data_manager, settings, parent)
        self.current: Optional[Dict[str, Any]] = None
        self.cards: List[MediaCard] = []
        self.filter_status = "all"
        self._cols = 4
        self._month = datetime.now().month
        self._year = datetime.now().year
        self._build_ui()

    # --- layout ---
    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        left = QVBoxLayout()
        left.setSpacing(12)
        left.addWidget(self._build_library(), 3)
        left.addWidget(self._build_folders(), 2)
        left.addWidget(self._build_calendar(), 3)
        root.addLayout(left, 1)

        right = QVBoxLayout()
        right.setSpacing(12)

        preview_zone = ZoneCard("2", "Просмотр и проверка", PURPLE)
        self.preview = PreviewPanel(self.dm)
        self.preview.status_changed.connect(self._refresh_all)
        self.preview.repeat_requested.connect(self._process_media)
        preview_zone.body.addWidget(self.preview)
        right.addWidget(preview_zone, 3)

        right.addWidget(self._build_schedule(), 2)
        wrapper = QWidget()
        wrapper.setLayout(right)
        wrapper.setMinimumWidth(300)
        wrapper.setMaximumWidth(345)
        root.addWidget(wrapper)

    # --- zone 1 ---
    def _build_library(self) -> QWidget:
        zone = ZoneCard("1", "Медиатека готовых материалов", BLUE)

        filters = QHBoxLayout()
        filters.setSpacing(6)
        self.filter_buttons = {}
        for key, label in FILTERS:
            btn = QPushButton(label)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, k=key: self._set_filter(k))
            btn.setStyleSheet(self._filter_qss())
            self.filter_buttons[key] = btn
            filters.addWidget(btn)

        filters.addStretch()
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Тип: Все", "Тип: Фото", "Тип: Видео"])
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Сортировка: По дате", "Сортировка: По имени"])
        for combo in (self.type_combo, self.sort_combo):
            self._style_combo(combo)
            combo.currentIndexChanged.connect(self._rebuild_library)
            filters.addWidget(combo)
        zone.body.addLayout(filters)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")
        holder = QWidget()
        self.grid = QGridLayout(holder)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(8)
        self.grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        scroll.setWidget(holder)
        zone.body.addWidget(scroll, 1)

        self._rebuild_library()

        zone.add_header_widget(_header_button("🎛 Обработать фото",
                                              lambda: self._process_media()))
        zone.add_header_widget(_header_button("🎬 Видео под площадку", self._process_video))
        zone.add_header_widget(_header_button("📦 Экспорт пакета", self._export_package))
        return zone

    def _filter_qss(self) -> str:
        return ("QPushButton{background:transparent;color:#8b949e;border:1px solid #2b3540;"
                "border-radius:8px;padding:3px 9px;font-size:10px;}"
                "QPushButton:hover{color:#dfe6ee;border-color:#3d4a58;}"
                "QPushButton:checked{background:rgba(90,169,255,0.15);color:#9ecbff;"
                "border-color:rgba(90,169,255,0.5);}")

    @staticmethod
    def _style_combo(combo: QComboBox):
        combo.setStyleSheet("QComboBox{background:#121820;color:#c9d1d9;border:1px solid #2b3540;"
                            "border-radius:7px;padding:3px 8px;font-size:10px;}"
                            "QComboBox::drop-down{border:none;width:14px;}")

    def _set_filter(self, key: str):
        self.filter_status = key
        for k, btn in self.filter_buttons.items():
            btn.setChecked(k == key)
        self._rebuild_library()

    def _rebuild_library(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()
        self.cards = []

        items = list(self.dm.get_media_ready())
        counts = {"all": len(items)}
        for key in ("pending", "approved", "rejected"):
            counts[key] = sum(1 for m in items if m.get("status") == key)
        for key, btn in self.filter_buttons.items():
            btn.setText(dict(FILTERS)[key] + f"  {counts[key]}")

        if self.filter_status != "all":
            items = [m for m in items if m.get("status") == self.filter_status]
        if self.type_combo.currentIndex() == 1:
            items = [m for m in items if m.get("type") == "image"]
        elif self.type_combo.currentIndex() == 2:
            items = [m for m in items if m.get("type") == "video"]
        if self.sort_combo.currentIndex() == 1:
            items.sort(key=lambda m: m.get("name", ""))

        cols = self._columns()
        self._cols = cols
        for index, item in enumerate(items):
            card = MediaCard(item)
            card.clicked.connect(self._select)
            self.cards.append(card)
            self.grid.addWidget(card, index // cols, index % cols)

        if self.current:
            for card in self.cards:
                card.set_selected(card.item is self.current)

    def _columns(self) -> int:
        available = max(300, self.width() - 415)
        return max(2, available // 148)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "grid") and self._columns() != self._cols:
            self._rebuild_library()

    def _select(self, item: Dict[str, Any]):
        self.current = item
        for card in self.cards:
            card.set_selected(card.item is item)
        self.preview.show_item(item)

    def _process_media(self, item: Optional[Dict[str, Any]] = None):
        """Выбрать пресет и прогнать материал (по умолчанию — из просмотра) через batch_photo."""
        item = item or self.current
        if not item:
            QMessageBox.information(self, "Обработка фото", "Выберите материал в медиатеке.")
            return
        presets = dict(PHOTO_PRESETS)
        choice, ok = QInputDialog.getItem(
            self, "Обработка фото",
            f"Материал: {item.get('name', '')}\nЧто сделать:", list(presets), 0, False)
        if not ok:
            return
        media_id = item.get("id")
        text = self.run_full("batch_photo", media_ids=[media_id], operations=presets[choice])
        summary = text.splitlines()[0] if text else ""
        QMessageBox.information(self, "Обработка фото", summary or "Готово")
        self._refresh_all()
        updated = next((m for m in self.dm.get_media_ready()
                        if m.get("id") == media_id), None)
        if updated:
            self._select(updated)

    def _process_video(self):
        """Выбрать площадку и подготовить текущее видео через process_video."""
        from ai_core import VIDEO_TARGETS

        item = self.current
        if not item or item.get("type") != "video":
            QMessageBox.information(self, "Видео", "Выберите видео в медиатеке.")
            return
        labels = {label: key for key, (label, _suffix) in VIDEO_TARGETS.items()}
        choice, ok = QInputDialog.getItem(
            self, "Видео под площадку",
            f"Материал: {item.get('name', '')}\nКуда готовим:", list(labels), 0, False)
        if not ok:
            return
        media_id = item.get("id")
        text = self.run_full("process_video", media_ids=[media_id], platform=labels[choice])
        summary = text.splitlines()[0] if text else ""
        QMessageBox.information(self, "Видео под площадку", summary or "Готово")
        self._refresh_all()
        updated = next((m for m in self.dm.get_media_ready() if m.get("id") == media_id), None)
        if updated:
            self._select(updated)

    def _export_package(self):
        """Выбрать папку и собрать в ней пакет публикаций (журнал — как у остальных инструментов)."""
        folder = QFileDialog.getExistingDirectory(self, "Куда сохранить пакет публикаций",
                                                  str(Path.home()))
        if not folder:
            return
        text = self.run_full("export_package", dest=folder)
        summary = text.splitlines()[0] if text else ""
        QMessageBox.information(self, "Экспорт пакета", summary or "Готово")

    # --- zone 3 ---
    def _build_folders(self) -> QWidget:
        zone = ZoneCard("3", "Папки публикаций — перетаскивай файлы или добавляй через меню", PINK)
        self.folders_row = QHBoxLayout()
        self.folders_row.setSpacing(10)
        zone.body.addLayout(self.folders_row)
        self._rebuild_folders()
        return zone

    def _rebuild_folders(self):
        while self.folders_row.count():
            item = self.folders_row.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()
        folders = self.dm.get_publications().get("folders", {})
        for folder_id, data in folders.items():
            card = FolderCard(folder_id, data, self.dm)
            card.changed.connect(self._refresh_all)
            self.folders_row.addWidget(card, 1)

    # --- zone 4 ---
    def _build_calendar(self) -> QWidget:
        zone = ZoneCard("4", "Календарь публикаций", RED)

        prev_btn = QPushButton("‹")
        next_btn = QPushButton("›")
        for btn in (prev_btn, next_btn):
            btn.setFixedWidth(26)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("background:#121820;color:#c9d1d9;border:1px solid #2b3540;"
                              "border-radius:7px;padding:3px 0;font-size:13px;")
        prev_btn.clicked.connect(lambda: self._shift_month(-1))
        next_btn.clicked.connect(lambda: self._shift_month(1))
        self.month_label = QLabel("")
        self.month_label.setStyleSheet(f"color:{TEXT};font-size:12px;font-weight:700;")
        zone.add_header_widget(prev_btn)
        zone.add_header_widget(self.month_label)
        zone.add_header_widget(next_btn)

        for label in ("День", "Неделя", "Месяц"):
            btn = QPushButton(label)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("background:#121820;color:#c9d1d9;border:1px solid #2b3540;"
                              "border-radius:7px;padding:3px 9px;font-size:10px;")
            if label == "Месяц":
                btn.setStyleSheet(btn.styleSheet() + "background:rgba(248,113,113,0.18);color:#ffb4b4;")
            zone.add_header_widget(btn)

        self.calendar_holder = QWidget()
        self.calendar_layout = QGridLayout(self.calendar_holder)
        self.calendar_holder.setMinimumHeight(330)
        self.calendar_layout.setContentsMargins(0, 0, 0, 0)
        self.calendar_layout.setSpacing(4)
        zone.body.addWidget(self.calendar_holder, 1)
        self._rebuild_calendar()
        return zone

    def _shift_month(self, delta: int):
        self._month += delta
        if self._month < 1:
            self._month = 12
            self._year -= 1
        elif self._month > 12:
            self._month = 1
            self._year += 1
        self._rebuild_calendar()

    def _folder_for(self, name: str):
        folders = self.dm.get_publications().get("folders", {})
        for data in folders.values():
            for item in data.get("items", []):
                if item.get("name") == name:
                    return data.get("name", ""), data.get("color", MUTED)
        lowered = name.lower()
        if "reels" in lowered:
            return "Reels", "#1f6feb"
        if "stories" in lowered or "сторис" in lowered:
            return "Stories", "#9e6a03"
        if "лента" in lowered or "пост" in lowered:
            return "Лента", "#238636"
        return "Пост", BLUE

    def _rebuild_calendar(self):
        while self.calendar_layout.count():
            item = self.calendar_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()
        self.month_label.setText(f"{MONTHS[self._month - 1]} {self._year}")

        for col, day in enumerate(WEEKDAYS):
            label = QLabel(day)
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet(f"color:{MUTED};font-size:9px;font-weight:600;")
            self.calendar_layout.addWidget(label, 0, col)

        events = [e for e in self.dm.get_calendar_events() if e.get("type") == "publication"]
        by_day: Dict[int, List[Dict[str, Any]]] = {}
        for event in events:
            try:
                d, m, y = map(int, event.get("date", "").split("."))
            except ValueError:
                continue
            if m == self._month and y == self._year:
                by_day.setdefault(d, []).append(event)

        first = datetime(self._year, self._month, 1)
        offset = first.weekday()
        days_in_month = (datetime(self._year + (self._month == 12),
                                  self._month % 12 + 1, 1)).toordinal() - first.toordinal()

        today = datetime.now()
        for index in range(offset + days_in_month):
            day = index - offset + 1
            cell = QFrame()
            in_month = day >= 1
            is_today = in_month and today.day == day and today.month == self._month and today.year == self._year
            border = (f"1px solid {_rgba(RED, 0.60)}" if is_today else "1px solid #1b222a")
            cell.setStyleSheet(f"QFrame{{background:#10161d;border:{border};border-radius:7px;}}")
            cell_layout = QVBoxLayout(cell)
            cell_layout.setContentsMargins(5, 4, 5, 4)
            cell_layout.setSpacing(2)

            if in_month:
                number = QLabel(str(day))
                number.setStyleSheet(f"color:{TEXT if is_today else MUTED};font-size:9px;font-weight:700;")
                cell_layout.addWidget(number)
                for event in by_day.get(day, [])[:2]:
                    name = event.get("title", "").replace("Публикация: ", "")
                    folder, color = self._folder_for(name)
                    chip = QLabel(f"{event.get('time', '')} · {folder}")
                    chip.setStyleSheet(f"background:{_rgba(color, 0.16)};color:{color};border-radius:4px;"
                                       f"padding:1px 3px;font-size:8px;")
                    cell_layout.addWidget(chip)
            cell_layout.addStretch()
            self.calendar_layout.addWidget(cell, index // 7 + 1, index % 7)

    # --- zone 5 ---
    def _build_schedule(self) -> QWidget:
        zone = ZoneCard("5", "Настройки расписания", YELLOW)
        schedule = self.dm.get_publications().get("schedule", {})

        tabs = QHBoxLayout()
        tabs.setSpacing(4)
        self.tab_buttons = []
        for index, label in enumerate(("Общие настройки", "Индивидуальное время")):
            btn = QPushButton(label)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setCheckable(True)
            btn.setChecked(index == 0)
            btn.clicked.connect(lambda checked, i=index: self._switch_tab(i))
            btn.setStyleSheet("QPushButton{background:transparent;color:#8b949e;border:none;"
                              "border-bottom:2px solid transparent;padding:4px 6px;font-size:10px;}"
                              "QPushButton:checked{color:#e3b341;border-bottom:2px solid #e3b341;}")
            self.tab_buttons.append(btn)
            tabs.addWidget(btn)
        tabs.addStretch()
        zone.body.addLayout(tabs)

        self.tab_stack = QStackedWidget()
        self.tab_stack.addWidget(self._build_general_tab(schedule))
        self.tab_stack.addWidget(self._build_times_tab(schedule))
        zone.body.addWidget(self.tab_stack, 1)

        save = QPushButton("Сохранить")
        save.setCursor(Qt.PointingHandCursor)
        save.setStyleSheet(f"background:{TEAL};color:#04211f;border:none;border-radius:8px;"
                           f"padding:7px 12px;font-size:11px;font-weight:700;")
        save.clicked.connect(self._save_schedule)
        zone.body.addWidget(save, 0, Qt.AlignRight)
        return zone

    def _switch_tab(self, index: int):
        self.tab_stack.setCurrentIndex(index)
        for i, btn in enumerate(self.tab_buttons):
            btn.setChecked(i == index)

    def _build_general_tab(self, schedule: Dict[str, Any]) -> QWidget:
        page = QWidget()
        form = QGridLayout(page)
        form.setContentsMargins(0, 4, 0, 0)
        form.setHorizontalSpacing(8)
        form.setVerticalSpacing(6)

        def row(index: int, title: str, widget: QWidget):
            label = QLabel(title)
            label.setStyleSheet(f"color:{MUTED};font-size:10px;")
            form.addWidget(label, index, 0)
            form.addWidget(widget, index, 1)

        self.tz_combo = QComboBox()
        self.tz_combo.addItems([schedule.get("timezone", "(UTC+6:00) Алматы"),
                                "(UTC+5:00) Актобе", "(UTC+6:00) Астана"])
        self._style_combo(self.tz_combo)
        row(0, "Часовой пояс", self.tz_combo)

        self.period_combo = QComboBox()
        self.period_combo.addItems([schedule.get("period", "Ежедневно"), "Через день",
                                    "3 раза в неделю", "По дням недели"])
        self._style_combo(self.period_combo)
        row(1, "Периодичность", self.period_combo)

        times = schedule.get("times", ["12:00"])
        self.time_edit = QTimeEdit()
        hour, minute = (map(int, times[0].split(":")) if times else (12, 0))
        self.time_edit.setTime(QTime(hour, minute))
        self.time_edit.setStyleSheet("QTimeEdit{background:#121820;color:#c9d1d9;border:1px solid #2b3540;"
                                     "border-radius:7px;padding:3px 6px;font-size:10px;}")
        row(2, "Время публикации", self.time_edit)

        self.count_combo = QComboBox()
        self.count_combo.addItems(["1 публикация", "2 публикации", "3 публикации"])
        self._style_combo(self.count_combo)
        row(3, "Количество за день", self.count_combo)

        self.repeat_check = QCheckBox("Повторять после завершения")
        self.repeat_check.setStyleSheet(f"QCheckBox{{color:{MUTED};font-size:10px;}}")
        form.addWidget(self.repeat_check, 4, 0, 1, 2)
        form.setRowStretch(5, 1)
        return page

    def _build_times_tab(self, schedule: Dict[str, Any]) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 4, 0, 0)
        lay.setSpacing(4)
        for value in schedule.get("times", ["12:00"]):
            label = QLabel(f"Каждый день · {value}")
            label.setStyleSheet(f"color:#c9d1d9;background:#121820;border:1px solid #2b3540;"
                                f"border-radius:7px;padding:5px 8px;font-size:10px;")
            lay.addWidget(label)
        add = QPushButton("+ Добавить время")
        add.setCursor(Qt.PointingHandCursor)
        add.setStyleSheet("background:transparent;color:#e3b341;"
                          "border:1px dashed rgba(227,179,65,0.45);"
                          "border-radius:7px;padding:5px 8px;font-size:10px;")
        lay.addWidget(add)
        lay.addStretch()
        return page

    def _save_schedule(self):
        schedule = self.dm.get_publications().setdefault("schedule", {})
        schedule["timezone"] = self.tz_combo.currentText()
        schedule["period"] = self.period_combo.currentText()
        schedule["times"] = [self.time_edit.time().toString("HH:mm")]
        self.dm.save()
        QMessageBox.information(self, "Расписание", "Настройки расписания сохранены.")
        self._rebuild_calendar()

    # --- refresh ---
    def _refresh_all(self):
        self._rebuild_library()
        self._rebuild_folders()
        self._rebuild_calendar()
        window = self.window()
        if hasattr(window, "refresh_stats"):
            window.refresh_stats()
