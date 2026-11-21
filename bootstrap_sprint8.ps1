# AI SMM Manager - Sprint 8: Fix Qt6 signal serialization
# Run: powershell -NoProfile -ExecutionPolicy Bypass -File .\bootstrap_sprint8.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$utf8WithBom = New-Object System.Text.UTF8Encoding $true

Write-Host ""
Write-Host "=== AI SMM Manager - Sprint 8: Qt6 Signal Fix ===" -ForegroundColor Green
Write-Host "Root: $root"
Write-Host ""

# 1. Check venv
Write-Host "[1/3] Checking virtual environment..." -ForegroundColor Cyan
$venvPython = Join-Path $root "venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "  ERROR: venv not found." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# 2. Helper function
function Write-PyFile {
    param([string]$RelPath, [string]$Content)
    $fullPath = Join-Path $root $RelPath
    $dir = Split-Path $fullPath -Parent
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    [System.IO.File]::WriteAllText($fullPath, $Content, $utf8WithBom)
    Write-Host "  Created/Updated: $RelPath"
}

# 3. Update qt_worker_lifecycle.py - serialize result to JSON string before signal
Write-Host "[2/3] Updating qt_worker_lifecycle.py (JSON serialization in signals)..." -ForegroundColor Cyan

$qwlFixed = @'
"""
Qt Worker Lifecycle v4 - Qt6 compatible. Results serialized to JSON string before signal emission.
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
        # Only use str signals - Qt6 handles strings correctly across threads
        finished_success_json = Signal(str, str)  # task_id, result_as_json_string
        finished_error = Signal(str, str)         # task_id, error_message

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
                
                # Serialize to JSON string BEFORE emitting signal
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
'@
Write-PyFile "AI_SMM_Work_Architecture_A75\qt_worker_lifecycle.py" $qwlFixed

# 4. Update app.py - deserialize JSON in main thread, use only str signals
Write-Host "[3/3] Updating app.py with JSON-serialized signals..." -ForegroundColor Cyan

$appPyFixed = @'
import sys, os, logging, sqlite3, json
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
    logger.info("=== AI SMM Manager - Sprint 8: Qt6 JSON Signal Fix ===")
    
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
    
    # Init DB & Components
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
    
    # --- GUI ---
    app = QApplication(sys.argv)
    app.setApplicationName("AI SMM Manager")
    
    font = QFont("Arial", 10)
    app.setFont(font)
    
    window = QMainWindow()
    window.setWindowTitle("AI SMM Manager v2.0 (Sprint 8)")
    window.resize(700, 500)
    
    layout = QVBoxLayout()
    
    label = QLabel("Введите задачу для SMM-менеджера:")
    label.setFont(QFont("Arial", 11, QFont.Bold))
    layout.addWidget(label)
    
    text_input = QTextEdit()
    text_input.setFont(QFont("Consolas", 10))
    text_input.setPlainText("Создай короткий пост для Instagram про утренний кофе в кофейне для фрилансеров. Тон: дружелюбный. Не выдумывай цены.")
    layout.addWidget(text_input)
    
    output_log = QTextEdit()
    output_log.setFont(QFont("Consolas", 10))
    output_log.setReadOnly(True)
    layout.addWidget(output_log)
    
    # MessageHandler - all GUI updates happen in main thread via signals
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
        msg_handler.log("\n[START] Отправка запроса в Ollama (qwen3:8b)...")
        msg_handler.log("[INFO] Генерация -> Независимая проверка...")
        
        def work_fn(task_id):
            result = quality_gate.full_quality_gate(request, {"rule": "Не выдумывай цены"})
            return result
        
        worker = worker_manager.create_worker("gui_task_001", "default_project", work_fn)
        # Connect to JSON signal - deserialize in main thread
        worker.finished_success_json.connect(lambda tid, json_str: on_success_json(tid, json_str))
        worker.finished_error.connect(lambda tid, err: msg_handler.log(f"[ERROR] {err}"))
    
    def on_success_json(task_id, json_result):
        # Deserialize JSON in main (GUI) thread - safe
        try:
            result = json.loads(json_result)
        except json.JSONDecodeError as e:
            msg_handler.log(f"[ERROR] Failed to parse result: {e}")
            return
        
        if result.get("approved"):
            msg_handler.log("\n[OK] КОНТЕНТ ОДОБРЕН РЕЦЕНЗЕНТОМ!")
            c = result.get("content", {})
            msg_handler.log(f"Текст:\n{c.get('content')}")
            msg_handler.log(f"Хэштеги: {', '.join(c.get('hashtags', []))}")
            msg_handler.log(f"Призыв: {c.get('call_to_action')}")
        else:
            feedback = result.get('review', {}).get('final_feedback', 'Неизвестная причина')
            msg_handler.log(f"\n[FAIL] КОНТЕНТ ОТКЛОНЕН: {feedback}")
    
    btn = QPushButton("Сгенерировать и проверить")
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
'@
Write-PyFile "AI_SMM_Work_Architecture_A75\app.py" $appPyFixed

Write-Host ""
Write-Host "=== Sprint 8 completed successfully ===" -ForegroundColor Green
Write-Host "Run START.bat to launch the fixed GUI!" -ForegroundColor Green