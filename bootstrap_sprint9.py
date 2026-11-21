#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI SMM Manager - Sprint 9: Python-based file generator with guaranteed UTF-8 encoding.
Run: python bootstrap_sprint9.py
"""

import os
import sys
from pathlib import Path

# Force UTF-8
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PYTHONUTF8'] = '1'

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = Path(__file__).resolve().parent

def write_file(rel_path: str, content: str):
    """Write file with explicit UTF-8 encoding."""
    full_path = ROOT_DIR / rel_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    with open(full_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)
    print(f"  Created/Updated: {rel_path}")

print("\n=== AI SMM Manager - Sprint 9: Python File Generator ===")
print(f"Root: {ROOT_DIR}\n")

# 1. Check venv
print("[1/3] Checking virtual environment...")
venv_python = ROOT_DIR / "venv" / "Scripts" / "python.exe"
if not venv_python.exists():
    print("  ERROR: venv not found. Run bootstrap_sprint1.ps1 first.")
    input("Press Enter to exit")
    sys.exit(1)
print("  OK: venv found\n")

# 2. Update qt_worker_lifecycle.py
print("[2/3] Updating qt_worker_lifecycle.py...")

qwl_content = '''"""
Qt Worker Lifecycle v5 - Qt6 compatible with JSON serialization.
"""
import logging
import threading
import json
from typing import Dict, Callable

logger = logging.getLogger(__name__)

try:
    from PySide6.QtCore import QThread, QObject, Signal
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False
    logger.warning("PySide6 not available")

if PYSIDE6_AVAILABLE:
    class TaskWorker(QThread):
        finished_success_json = Signal(str, str)
        finished_error = Signal(str, str)

        def __init__(self, task_id: str, state_machine, work_fn: Callable, parent=None):
            super().__init__(parent)
            self.task_id = task_id
            self.state_machine = state_machine
            self.work_fn = work_fn
            self._cancellation_token = threading.Event()

        def run(self):
            try:
                if self.state_machine.is_cancelled(self.task_id):
                    self.finished_error.emit(self.task_id, "Cancelled before start")
                    return
                
                logger.info(f"Worker {self.task_id} started execution")
                result = self.work_fn(self.task_id)
                logger.info(f"Worker {self.task_id} completed execution")
                
                if self.state_machine.is_cancelled(self.task_id):
                    self.finished_error.emit(self.task_id, "Cancelled during execution")
                    return
                
                json_result = json.dumps(result, ensure_ascii=False, default=str)
                self.finished_success_json.emit(self.task_id, json_result)
                
            except Exception as e:
                logger.error(f"Task {self.task_id} failed: {e}")
                self.finished_error.emit(self.task_id, str(e))

        def cancel(self):
            self._cancellation_token.set()
            try:
                from task_state_machine import TaskState
                self.state_machine.transition(self.task_id, TaskState.CANCELLED, "Cancelled by user")
            except Exception as e:
                logger.error(f"Failed to update state on cancellation: {e}")

        def is_cancelled(self) -> bool:
            return self._cancellation_token.is_set()

    class WorkerManager(QObject):
        worker_started = Signal(str)
        worker_finished = Signal(str, bool)
        all_workers_finished = Signal()

        def __init__(self, db_connection, parent=None):
            super().__init__(parent)
            self.db = db_connection
            self._workers: Dict[str, TaskWorker] = {}
            self._lock = threading.RLock()

        def create_worker(self, task_id: str, project_id: str, work_fn: Callable) -> TaskWorker:
            with self._lock:
                if task_id in self._workers:
                    raise ValueError(f"Worker for task {task_id} already exists")
                from task_state_machine import TaskStateMachine
                sm = TaskStateMachine(self.db, project_id)
                worker = TaskWorker(task_id, sm, work_fn)
                
                worker.finished_success_json.connect(self._on_success_json)
                worker.finished_error.connect(self._on_error)
                worker.finished.connect(lambda: self._on_finished(task_id))
                
                self._workers[task_id] = worker
                worker.start()
                self.worker_started.emit(task_id)
                logger.info(f"Worker {task_id} started")
                return worker

        def cancel_worker(self, task_id: str) -> bool:
            with self._lock:
                worker = self._workers.get(task_id)
                if worker:
                    worker.cancel()
                    return True
                return False

        def has_active_workers(self) -> bool:
            with self._lock:
                return any(w.isRunning() for w in self._workers.values())

        def _on_success_json(self, task_id: str, json_result: str):
            logger.info(f"Worker {task_id} finished successfully")
            self.worker_finished.emit(task_id, True)

        def _on_error(self, task_id: str, error: str):
            logger.error(f"Worker {task_id} failed: {error}")
            self.worker_finished.emit(task_id, False)

        def _on_finished(self, task_id: str):
            with self._lock:
                worker = self._workers.pop(task_id, None)
                if worker:
                    worker.deleteLater()
            if not self.has_active_workers():
                self.all_workers_finished.emit()
'''

write_file("AI_SMM_Work_Architecture_A75/qt_worker_lifecycle.py", qwl_content)

# 3. Update app.py with proper encoding
print("[3/3] Updating app.py with proper encoding...")

app_content = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI SMM Manager - Sprint 9: Proper UTF-8 encoding throughout.
"""

import sys
import os
import logging
import sqlite3
import json
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
    handlers=[logging.StreamHandler(), logging.FileHandler(logs_dir / "app.log", encoding='utf-8')]
)
logger = logging.getLogger(__name__)

def main():
    logger.info("=== AI SMM Manager - Sprint 9: Proper UTF-8 ===")
    
    try:
        import yaml
        from PySide6.QtWidgets import QApplication, QMainWindow, QTextEdit, QPushButton, QVBoxLayout, QWidget, QLabel
        from PySide6.QtCore import Qt, Signal, QObject
        from PySide6.QtGui import QFont
        from task_state_machine import TaskStateMachine, TaskState
        from local_quality_gate import LocalQualityGate
        from ollama_client import OllamaClient
        from qt_worker_lifecycle import WorkerManager
        from media_task_router import MediaTaskRouter
    except ImportError as e:
        logger.error(f"Missing dependency: {e}")
        sys.exit(1)
    
    conn = sqlite3.connect(str(ROOT_DIR / "data" / "ai_smm_manager.db"))
    conn.execute("PRAGMA journal_mode=WAL")
    
    state_machine = TaskStateMachine(conn, "default_project")
    worker_manager = WorkerManager(conn)
    ollama = OllamaClient()
    quality_gate = LocalQualityGate(ollama_client=ollama)
    
    config_path = ROOT_DIR / "config" / "config.yaml"
    config = yaml.safe_load(open(config_path, 'r', encoding='utf-8')) if config_path.exists() else {}
    media_router = MediaTaskRouter(config)
    
    logger.info("All components initialized. Starting GUI...")
    
    app = QApplication(sys.argv)
    app.setApplicationName("AI SMM Manager")
    
    font = QFont("Arial", 10)
    app.setFont(font)
    
    window = QMainWindow()
    window.setWindowTitle("AI SMM Manager v2.0 (Sprint 9)")
    window.resize(700, 500)
    
    layout = QVBoxLayout()
    
    label = QLabel("Enter task for SMM manager:")
    label.setFont(QFont("Arial", 11, QFont.Bold))
    layout.addWidget(label)
    
    text_input = QTextEdit()
    text_input.setFont(QFont("Consolas", 10))
    text_input.setPlainText("Create a short Instagram post about morning coffee in a cafe for freelancers. Tone: friendly. Do not invent prices.")
    layout.addWidget(text_input)
    
    output_log = QTextEdit()
    output_log.setFont(QFont("Consolas", 10))
    output_log.setReadOnly(True)
    layout.addWidget(output_log)
    
    class MessageHandler(QObject):
        log_signal = Signal(str)
        
        def __init__(self, text_edit):
            super().__init__()
            self.text_edit = text_edit
            self.log_signal.connect(self._append)
        
        def _append(self, msg):
            self.text_edit.append(msg)
        
        def log(self, msg):
            self.log_signal.emit(str(msg))
    
    msg_handler = MessageHandler(output_log)
    
    def run_task():
        request = text_input.toPlainText()
        msg_handler.log("\\n[START] Sending request to Ollama (qwen3:8b)...")
        msg_handler.log("[INFO] Generation -> Independent review...")
        
        def work_fn(task_id):
            result = quality_gate.full_quality_gate(request, {"rule": "Do not invent prices"})
            return result
        
        worker = worker_manager.create_worker("gui_task_001", "default_project", work_fn)
        worker.finished_success_json.connect(lambda tid, json_str: on_success_json(tid, json_str))
        worker.finished_error.connect(lambda tid, err: msg_handler.log(f"[ERROR] {err}"))
    
    def on_success_json(task_id, json_result):
        try:
            result = json.loads(json_result)
        except json.JSONDecodeError as e:
            msg_handler.log(f"[ERROR] Failed to parse result: {e}")
            return
        
        if result.get("approved"):
            msg_handler.log("\\n[OK] CONTENT APPROVED BY REVIEWER!")
            c = result.get("content", {})
            msg_handler.log(f"Text:\\n{c.get('content')}")
            msg_handler.log(f"Hashtags: {', '.join(c.get('hashtags', []))}")
            msg_handler.log(f"Call to action: {c.get('call_to_action')}")
        else:
            feedback = result.get('review', {}).get('final_feedback', 'Unknown reason')
            msg_handler.log(f"\\n[FAIL] CONTENT REJECTED: {feedback}")
    
    btn = QPushButton("Generate and Review")
    btn.setFont(QFont("Arial", 11, QFont.Bold))
    btn.clicked.connect(run_task)
    layout.addWidget(btn)
    
    container = QWidget()
    container.setLayout(layout)
    window.setCentralWidget(container)
    
    window.show()
    logger.info("GUI is running. Architecture v2 is fully operational.")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
'''

write_file("AI_SMM_Work_Architecture_A75/app.py", app_content)

print("\n=== Sprint 9 completed successfully ===")
print("Run START.bat to launch the GUI with proper encoding!")
print("\nNote: GUI labels are now in English to avoid any encoding issues.")
print("The AI will still generate content in Russian based on your request.")