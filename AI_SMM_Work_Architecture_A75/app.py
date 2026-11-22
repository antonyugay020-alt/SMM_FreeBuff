#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI SMM Manager - Phase 1.2: New framework entry point."""

import sys, os, logging, sqlite3
from pathlib import Path

os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PYTHONUTF8'] = '1'

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

logs_dir = ROOT_DIR / "data" / "logs"
logs_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler(logs_dir / 'app.log', encoding='utf-8')]
)
logger = logging.getLogger(__name__)

def main():
    logger.info("=== AI SMM Manager - Phase 1.2: New Framework ===")

    try:
        import yaml
        from PySide6.QtWidgets import QApplication
        from PySide6.QtGui import QFont
        from project_manager import ProjectManager
        from gui_main import MainWindow
        from gui_settings import Settings
    except ImportError as e:
        logger.error(f"Missing dependency: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    db_path = ROOT_DIR / "data" / "ai_smm_manager.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")

    project_manager = ProjectManager(str(ROOT_DIR / "data" / "ai_smm_projects.db"))
    projects = project_manager.list_projects()
    if not projects:
        project_manager.create_project("default", "Новый проект", "")

    config_path = ROOT_DIR / "config" / "config.yaml"
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    else:
        config = {}

    app_state = {
        "config": config,
        "project_manager": project_manager,
        "media_dir": str(ROOT_DIR / "media" / "images"),
        "videos_dir": str(ROOT_DIR / "media" / "videos"),
        "logs_dir": str(logs_dir),
        "root_dir": str(ROOT_DIR),
        "settings": Settings(),
    }

    logger.info("All components initialized. Starting GUI...")

    app = QApplication(sys.argv)
    app.setApplicationName("AI SMM Manager")
    app.setApplicationVersion("v2.0-phase1.2")
    app.setStyle("Fusion")
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    window = MainWindow(app_state)
    window.show()

    logger.info("GUI is running. Phase 1.2 active.")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()