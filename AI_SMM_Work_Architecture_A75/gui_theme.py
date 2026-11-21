"""Dark theme for AI SMM Manager."""

DARK_THEME_QSS = """
QMainWindow { background-color: #0f1419; color: #e6edf3; }
QWidget { background-color: transparent; }

QWidget#leftPanel { background-color: #161b22; border-right: 1px solid #30363d; }
QLabel#logo { color: #58a6ff; font-size: 13px; font-weight: bold; padding: 12px; border-bottom: 1px solid #30363d; }
QPushButton#navBtn {
    background-color: transparent; color: #c9d1d9; border: none;
    padding: 10px 12px; text-align: left; font-size: 13px; border-radius: 4px;
}
QPushButton#navBtn:hover { background-color: #21262d; color: #ffffff; }
QPushButton#navBtn.active { background-color: #1f6feb; color: #ffffff; }
QLabel#projectBlock { color: #8b949e; font-size: 10px; padding: 8px 12px 4px 12px; }
QLabel#projectName { color: #e6edf3; font-size: 13px; font-weight: bold; padding: 4px 12px; }
QLabel#projectStats { color: #8b949e; font-size: 11px; padding: 2px 12px; }
QProgressBar#storageBar {
    background-color: #21262d; border-radius: 3px; text-align: center;
    color: #e6edf3; font-size: 10px; height: 16px;
}
QProgressBar#storageBar::chunk { background-color: #1f6feb; border-radius: 3px; }

QWidget#topBar { background-color: #161b22; border-bottom: 1px solid #30363d; padding: 8px 16px; }
QLabel#sectionTitle { color: #e6edf3; font-size: 18px; font-weight: bold; }
QLabel#sectionSubtitle { color: #8b949e; font-size: 12px; }
QLineEdit#searchBox {
    background-color: #0d1117; color: #e6edf3; border: 1px solid #30363d;
    border-radius: 4px; padding: 6px 10px; font-size: 12px;
}
QLineEdit#searchBox:focus { border-color: #1f6feb; }
QComboBox#projectCombo, QComboBox#filterCombo {
    background-color: #21262d; color: #e6edf3; border: 1px solid #30363d;
    border-radius: 4px; padding: 6px 10px; font-size: 12px;
}
QPushButton#topBtn {
    background-color: #21262d; color: #e6edf3; border: 1px solid #30363d;
    padding: 6px 12px; border-radius: 4px; font-size: 12px;
}
QPushButton#topBtn:hover { background-color: #30363d; }
QPushButton#topBtn.primary { background-color: #1f6feb; border-color: #1f6feb; color: #ffffff; }
QPushButton#topBtn.primary:hover { background-color: #388bfd; }

QLabel#zoneTitle { color: #e6edf3; font-size: 14px; font-weight: bold; padding: 8px 12px; }
QLabel#zoneTitle.blue { color: #58a6ff; }
QLabel#zoneTitle.purple { color: #bc8cff; }
QLabel#zoneTitle.green { color: #3fb950; }
QLabel#zoneTitle.red { color: #f85149; }
QLabel#zoneTitle.yellow { color: #d29922; }

QFrame#zone { background-color: #161b22; border: 1px solid #30363d; border-radius: 6px; }
QFrame#zoneHeader { background-color: #1c2128; border-radius: 6px 6px 0 0; padding: 8px 12px; }

QPushButton#statusBtn {
    background-color: #21262d; color: #c9d1d9; border: 1px solid #30363d;
    padding: 4px 10px; border-radius: 12px; font-size: 11px;
}
QPushButton#statusBtn:hover { background-color: #30363d; }
QPushButton#statusBtn.active { background-color: #1f6feb; color: #ffffff; border-color: #1f6feb; }
QPushButton#statusBtn.approved { background-color: #238636; color: #ffffff; border-color: #238636; }
QPushButton#statusBtn.rejected { background-color: #da3633; color: #ffffff; border-color: #da3633; }
QPushButton#statusBtn.pending { background-color: #9e6a03; color: #ffffff; border-color: #9e6a03; }

QWidget#thumb { background-color: #0d1117; border: 2px solid #30363d; border-radius: 4px; }
QWidget#thumb:hover { border-color: #58a6ff; }
QWidget#thumb.selected { border-color: #1f6feb; background-color: #161b22; }
QLabel#thumbName { color: #c9d1d9; font-size: 10px; padding: 4px; }

QFrame#folderCard { background-color: #161b22; border: 1px solid #30363d; border-radius: 6px; }
QFrame#folderCard.stories { border-color: #9e6a03; }
QFrame#folderCard.reels { border-color: #1f6feb; }
QFrame#folderCard.feed { border-color: #238636; }

QTableWidget#calendar {
    background-color: #0d1117; color: #e6edf3; border: 1px solid #30363d;
    gridline-color: #30363d; font-size: 11px;
}
QTableWidget#calendar::item { padding: 4px; }
QTableWidget#calendar::item:selected { background-color: #1f6feb; }
QHeaderView::section {
    background-color: #161b22; color: #8b949e; border: 1px solid #30363d;
    padding: 6px; font-size: 11px;
}

QScrollBar:vertical { background-color: #0d1117; width: 10px; border: none; }
QScrollBar::handle:vertical { background-color: #30363d; border-radius: 5px; min-height: 20px; }
QScrollBar::handle:vertical:hover { background-color: #484f58; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

QWidget#aiPanel { background-color: #161b22; border-left: 1px solid #30363d; }
QTextEdit#chatHistory { background-color: #0d1117; color: #e6edf3; border: none; font-family: Consolas, monospace; font-size: 12px; }
QTextEdit#chatInput { background-color: #0d1117; color: #e6edf3; border: 1px solid #30363d; border-radius: 4px; font-family: Consolas, monospace; font-size: 12px; }
QPushButton#sendBtn { background-color: #1f6feb; color: #ffffff; border: none; padding: 8px 16px; border-radius: 4px; font-size: 12px; font-weight: bold; }
QPushButton#sendBtn:hover { background-color: #388bfd; }
"""
