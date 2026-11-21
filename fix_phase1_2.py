#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix Phase 1.2: Fix syntax error in publications_section.py and update app.py.
Run: python fix_phase1_2.py
"""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent

print("\n=== Fixing Phase 1.2 ===\n")

# 1. Fix publications_section.py
print("[1/2] Fixing publications_section.py...")

pub_path = ROOT_DIR / "AI_SMM_Work_Architecture_A75" / "gui_sections" / "publications_section.py"

if pub_path.exists():
    content = pub_path.read_text(encoding='utf-8')
    
    # Fix the syntax error: remove extra quote and parenthesis
    content = content.replace(
        "pub.append('    def _build_media_library(self) -> QFrame:')')",
        "pub.append('    def _build_media_library(self) -> QFrame:')"
    )
    
    pub_path.write_text(content, encoding='utf-8')
    print("  [OK] Fixed syntax error in publications_section.py")
else:
    print("  [SKIP] publications_section.py not found")

# 2. Update app.py to use new gui_main
print("[2/2] Updating app.py...")

app_lines = []
app_lines.append('#!/usr/bin/env python3')
app_lines.append('# -*- coding: utf-8 -*-')
app_lines.append('"""AI SMM Manager - Phase 1.2: New framework entry point."""')
app_lines.append('')
app_lines.append('import sys, os, logging, sqlite3')
app_lines.append('from pathlib import Path')
app_lines.append('')
app_lines.append("os.environ['PYTHONIOENCODING'] = 'utf-8'")
app_lines.append("os.environ['PYTHONUTF8'] = '1'")
app_lines.append('')
app_lines.append("if sys.stdout.encoding != 'utf-8':")
app_lines.append("    sys.stdout.reconfigure(encoding='utf-8')")
app_lines.append("if sys.stderr.encoding != 'utf-8':")
app_lines.append("    sys.stderr.reconfigure(encoding='utf-8')")
app_lines.append('')
app_lines.append('ROOT_DIR = Path(__file__).resolve().parent.parent')
app_lines.append('sys.path.insert(0, str(ROOT_DIR))')
app_lines.append('sys.path.insert(0, str(Path(__file__).resolve().parent))')
app_lines.append('')
app_lines.append('logs_dir = ROOT_DIR / "data" / "logs"')
app_lines.append('logs_dir.mkdir(parents=True, exist_ok=True)')
app_lines.append('')
app_lines.append('logging.basicConfig(')
app_lines.append("    level=logging.INFO,")
app_lines.append("    format='%(asctime)s - %(levelname)s - %(message)s',")
app_lines.append("    handlers=[logging.StreamHandler(), logging.FileHandler(logs_dir / 'app.log', encoding='utf-8')]")
app_lines.append(')')
app_lines.append('logger = logging.getLogger(__name__)')
app_lines.append('')
app_lines.append('def main():')
app_lines.append('    logger.info("=== AI SMM Manager - Phase 1.2: New Framework ===")')
app_lines.append('')
app_lines.append('    try:')
app_lines.append('        import yaml')
app_lines.append('        from PySide6.QtWidgets import QApplication')
app_lines.append('        from PySide6.QtGui import QFont')
app_lines.append('        from project_manager import ProjectManager')
app_lines.append('        from gui_main import MainWindow')
app_lines.append('    except ImportError as e:')
app_lines.append('        logger.error(f"Missing dependency: {e}")')
app_lines.append('        import traceback')
app_lines.append('        traceback.print_exc()')
app_lines.append('        sys.exit(1)')
app_lines.append('')
app_lines.append('    db_path = ROOT_DIR / "data" / "ai_smm_manager.db"')
app_lines.append('    conn = sqlite3.connect(str(db_path))')
app_lines.append('    conn.execute("PRAGMA journal_mode=WAL")')
app_lines.append('')
app_lines.append('    project_manager = ProjectManager(str(ROOT_DIR / "data" / "ai_smm_projects.db"))')
app_lines.append('    projects = project_manager.list_projects()')
app_lines.append('    if not projects:')
app_lines.append('        project_manager.create_project("default", "Теннис", "")')
app_lines.append('')
app_lines.append('    config_path = ROOT_DIR / "config" / "config.yaml"')
app_lines.append('    if config_path.exists():')
app_lines.append("        with open(config_path, 'r', encoding='utf-8') as f:")
app_lines.append('            config = yaml.safe_load(f)')
app_lines.append('    else:')
app_lines.append('        config = {}')
app_lines.append('')
app_lines.append('    app_state = {')
app_lines.append('        "config": config,')
app_lines.append('        "project_manager": project_manager,')
app_lines.append('        "media_dir": str(ROOT_DIR / "media" / "images"),')
app_lines.append('        "videos_dir": str(ROOT_DIR / "media" / "videos"),')
app_lines.append('        "logs_dir": str(logs_dir),')
app_lines.append('        "root_dir": str(ROOT_DIR),')
app_lines.append('    }')
app_lines.append('')
app_lines.append('    logger.info("All components initialized. Starting GUI...")')
app_lines.append('')
app_lines.append('    app = QApplication(sys.argv)')
app_lines.append('    app.setApplicationName("AI SMM Manager")')
app_lines.append('    app.setApplicationVersion("v2.0-phase1.2")')
app_lines.append('    app.setStyle("Fusion")')
app_lines.append('    font = QFont("Segoe UI", 10)')
app_lines.append('    app.setFont(font)')
app_lines.append('')
app_lines.append('    window = MainWindow(app_state)')
app_lines.append('    window.show()')
app_lines.append('')
app_lines.append('    logger.info("GUI is running. Phase 1.2 active.")')
app_lines.append('    sys.exit(app.exec())')
app_lines.append('')
app_lines.append('if __name__ == "__main__":')
app_lines.append('    main()')

app_path = ROOT_DIR / "AI_SMM_Work_Architecture_A75" / "app.py"
app_path.write_text('\n'.join(app_lines), encoding='utf-8')
print("  [OK] Updated app.py")

print("\n=== Fixes Applied ===")
print("Run START.bat to test the new framework.")