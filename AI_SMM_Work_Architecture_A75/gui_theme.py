"""Dark theme for AI SMM Manager — matches the approved shell design."""

BG = "#0b0f14"
PANEL = "#0f141a"
PANEL_ALT = "#121820"
BORDER = "#1e252e"
TEXT = "#e6edf3"
MUTED = "#8b949e"
TEAL = "#2dd4bf"
PURPLE = "#c08cff"

DARK_THEME_QSS = f"""
QMainWindow {{ background-color: {BG}; color: {TEXT}; }}
QWidget {{ background-color: transparent; color: {TEXT}; }}
QSplitter::handle {{ background-color: {BORDER}; }}
QSplitter::handle:hover {{ background-color: {TEAL}; }}

QWidget#leftPanel {{ background-color: {PANEL}; border-right: 1px solid {BORDER}; }}
QLabel#logo {{ color: {TEAL}; font-size: 12px; font-weight: 700; letter-spacing: 1px;
    padding: 14px 14px; border-bottom: 1px solid {BORDER}; }}

QPushButton#navBtn {{
    background-color: transparent; color: #c9d1d9; border: none;
    border-left: 3px solid transparent;
    padding: 9px 12px; text-align: left; font-size: 12px; border-radius: 6px;
}}
QPushButton#navBtn:hover {{ background-color: #151b22; color: #ffffff; }}
QPushButton#navBtn.active {{ background-color: rgba(45,212,191,0.10); color: {TEAL};
    border-left: 3px solid {TEAL}; }}

QLabel#projectBlock {{ color: {MUTED}; font-size: 9px; letter-spacing: 1px;
    padding: 10px 14px 4px 14px; }}
QLabel#projectName {{ color: {TEXT}; font-size: 13px; font-weight: 700; padding: 4px 14px; }}
QLabel#projectStats {{ color: {MUTED}; font-size: 11px; padding: 2px 14px; }}
QProgressBar#storageBar {{ background-color: #151b22; border-radius: 3px; text-align: center;
    color: {TEXT}; font-size: 9px; height: 8px; }}
QProgressBar#storageBar::chunk {{ background-color: {TEAL}; border-radius: 3px; }}

QWidget#topBar {{ background-color: {PANEL}; border-bottom: 1px solid {BORDER}; }}
QLabel#sectionTitle {{ color: {TEXT}; font-size: 18px; font-weight: 700; }}
QLabel#sectionSubtitle {{ color: {MUTED}; font-size: 11px; }}
QLineEdit#searchBox {{ background-color: {PANEL_ALT}; color: {TEXT}; border: 1px solid {BORDER};
    border-radius: 8px; padding: 6px 10px; font-size: 11px; }}
QLineEdit#searchBox:focus {{ border-color: {TEAL}; }}
QComboBox#projectCombo, QComboBox#filterCombo {{ background-color: {PANEL_ALT}; color: {TEXT};
    border: 1px solid {BORDER}; border-radius: 8px; padding: 5px 10px; font-size: 11px; }}
QPushButton#topBtn {{ background-color: {PANEL_ALT}; color: {TEXT}; border: 1px solid {BORDER};
    padding: 6px 12px; border-radius: 8px; font-size: 11px; }}
QPushButton#topBtn:hover {{ background-color: #1a222b; border-color: #2c3742; }}
QPushButton#topBtn.primary {{ background-color: {TEAL}; border-color: {TEAL}; color: #04211f;
    font-weight: 700; }}
QPushButton#topBtn.primary:hover {{ background-color: #5eead4; }}
QPushButton#topBtn.accent {{ background-color: rgba(192,140,255,0.16); border-color: rgba(192,140,255,0.5);
    color: #dcc4ff; }}
QPushButton#topBtn.accent:hover {{ background-color: rgba(192,140,255,0.26); }}

QLabel#zoneTitle {{ color: {TEXT}; font-size: 13px; font-weight: 700; padding: 4px 0; }}
QLabel#zoneTitle.blue {{ color: #5aa9ff; }}
QLabel#zoneTitle.purple {{ color: {PURPLE}; }}
QLabel#zoneTitle.green {{ color: #3fb950; }}
QLabel#zoneTitle.red {{ color: #f87171; }}
QLabel#zoneTitle.yellow {{ color: #e3b341; }}

QFrame#zone {{ background-color: {PANEL_ALT}; border: 1px solid {BORDER}; border-radius: 10px; }}
QFrame#zoneHeader {{ background-color: #121820; border-radius: 9px 9px 0 0; }}

QPushButton#statusBtn {{ background-color: transparent; color: #c9d1d9; border: 1px solid {BORDER};
    padding: 3px 9px; border-radius: 9px; font-size: 10px; }}
QPushButton#statusBtn:hover {{ border-color: #2c3742; color: #ffffff; }}
QPushButton#statusBtn.active {{ background-color: rgba(45,212,191,0.16); color: {TEAL};
    border-color: rgba(45,212,191,0.5); }}
QPushButton#statusBtn.approved {{ background-color: rgba(63,185,80,0.18); color: #3fb950;
    border-color: rgba(63,185,80,0.5); }}
QPushButton#statusBtn.rejected {{ background-color: rgba(248,81,73,0.18); color: #f85149;
    border-color: rgba(248,81,73,0.5); }}
QPushButton#statusBtn.pending {{ background-color: rgba(210,153,34,0.18); color: #d29922;
    border-color: rgba(210,153,34,0.5); }}

QLabel#thumbName {{ color: #c9d1d9; font-size: 10px; padding: 4px; }}

QTableWidget#calendar {{ background-color: #0b0f14; color: {TEXT}; border: 1px solid {BORDER};
    gridline-color: {BORDER}; font-size: 10px; border-radius: 8px; }}
QTableWidget#calendar::item {{ padding: 4px; }}
QTableWidget#calendar::item:selected {{ background-color: rgba(45,212,191,0.25); }}
QHeaderView::section {{ background-color: {PANEL_ALT}; color: {MUTED}; border: 1px solid {BORDER};
    padding: 5px; font-size: 10px; }}

QScrollArea#workspaceScroll, QScrollArea#plainScroll {{ border: none; background: transparent; }}
QScrollArea#workspaceScroll > QWidget > QWidget {{ background-color: {BG}; }}

QLineEdit#formInput, QComboBox#formInput, QSpinBox#formInput, QDoubleSpinBox#formInput {{
    background-color: #0a0e13; color: {TEXT}; border: 1px solid {BORDER};
    border-radius: 8px; padding: 6px 10px; font-size: 11px; min-width: 220px; }}
QLineEdit#formInput:focus, QComboBox#formInput:focus,
QSpinBox#formInput:focus, QDoubleSpinBox#formInput:focus {{ border-color: {TEAL}; }}
QCheckBox#formCheck {{ color: {TEXT}; font-size: 11px; spacing: 8px; }}

QScrollBar:vertical {{ background-color: transparent; width: 9px; border: none; }}
QScrollBar::handle:vertical {{ background-color: #26303a; border-radius: 4px; min-height: 24px; }}
QScrollBar::handle:vertical:hover {{ background-color: #37424e; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ background-color: transparent; height: 9px; border: none; }}
QScrollBar::handle:horizontal {{ background-color: #26303a; border-radius: 4px; min-width: 24px; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

QWidget#aiPanel {{ background-color: {PANEL}; border-left: 1px solid {BORDER}; }}
QTextEdit#chatHistory {{ background-color: #0a0e13; color: {TEXT}; border: none;
    border-radius: 8px; font-size: 11px; }}
QTextEdit#chatInput {{ background-color: #0a0e13; color: {TEXT}; border: 1px solid {BORDER};
    border-radius: 8px; font-size: 11px; }}
QPushButton#sendBtn {{ background-color: {TEAL}; color: #04211f; border: none;
    padding: 8px 16px; border-radius: 8px; font-size: 11px; font-weight: 700; }}
QPushButton#sendBtn:hover {{ background-color: #5eead4; }}

QStatusBar {{ color: {MUTED}; font-size: 10px; border-top: 1px solid {BORDER}; }}
"""
