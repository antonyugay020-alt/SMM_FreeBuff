from pathlib import Path

p = Path("AI_SMM_Work_Architecture_A75/gui_main.py")
text = p.read_text(encoding='utf-8')

# Fix 1: QAction -> QtGui
text = text.replace(
    "QAction, QStatusBar\n)",
    "QStatusBar\n)"
)
text = text.replace(
    "from PySide6.QtGui import QFont, QPixmap",
    "from PySide6.QtGui import QAction, QFont, QPixmap"
)

p.write_text(text, encoding='utf-8')
print("Fixed: QAction moved to QtGui")