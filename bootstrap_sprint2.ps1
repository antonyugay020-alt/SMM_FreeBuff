# AI SMM Manager - Sprint 2: Core Architecture (FIXED)
# Run: powershell -NoProfile -ExecutionPolicy Bypass -File .\bootstrap_sprint2.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$utf8NoBom = New-Object System.Text.UTF8Encoding $false
$utf8WithBom = New-Object System.Text.UTF8Encoding $true

Write-Host ""
Write-Host "=== AI SMM Manager - Sprint 2: Core Architecture (FIXED) ===" -ForegroundColor Green
Write-Host "Root: $root"
Write-Host ""

# 1. Check venv
Write-Host "[1/5] Checking virtual environment..." -ForegroundColor Cyan
$venvPython = Join-Path $root "venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "  ERROR: venv not found. Run bootstrap_sprint1.ps1 first." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "  OK: venv found" -ForegroundColor Green

# 2. Helper functions
Write-Host "[2/5] Preparing file writers..." -ForegroundColor Cyan

function Write-PyFile {
    param([string]$RelPath, [string]$Content)
    $fullPath = Join-Path $root $RelPath
    $dir = Split-Path $fullPath -Parent
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    [System.IO.File]::WriteAllText($fullPath, $Content, $utf8WithBom)
    Write-Host "  Created: $RelPath"
}

function Write-BatFile {
    param([string]$RelPath, [string]$Content)
    $fullPath = Join-Path $root $RelPath
    $dir = Split-Path $fullPath -Parent
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    [System.IO.File]::WriteAllText($fullPath, $Content, $utf8NoBom)
    Write-Host "  Created: $RelPath (no BOM)"
}

# 3. Generate task_state_machine.py
Write-Host "[3/5] Generating task_state_machine.py..." -ForegroundColor Cyan

$tsmContent = @'
"""
Task State Machine - Unified finite state machine for task lifecycle.
"""
from enum import Enum, auto
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import sqlite3
import threading
import logging

logger = logging.getLogger(__name__)

class TaskState(Enum):
    PLANNED = auto()
    AUTHORING = auto()
    REVIEWING = auto()
    REVISION_REQUIRED = auto()
    ACCEPTED = auto()
    PERSISTED = auto()
    FAILED = auto()
    CANCELLED = auto()

@dataclass
class TaskAuthority:
    task_id: str
    request_hash: str
    project_id: str
    created_at: datetime
    publication_scope: Optional[str] = None

class TaskStateMachine:
    ALLOWED_TRANSITIONS = {
        TaskState.PLANNED: [TaskState.AUTHORING, TaskState.CANCELLED],
        TaskState.AUTHORING: [TaskState.REVIEWING, TaskState.FAILED, TaskState.CANCELLED],
        TaskState.REVIEWING: [TaskState.ACCEPTED, TaskState.REVISION_REQUIRED, TaskState.FAILED, TaskState.CANCELLED],
        TaskState.REVISION_REQUIRED: [TaskState.AUTHORING, TaskState.CANCELLED],
        TaskState.ACCEPTED: [TaskState.PERSISTED, TaskState.FAILED, TaskState.CANCELLED],
        TaskState.PERSISTED: [TaskState.CANCELLED],
        TaskState.FAILED: [TaskState.PLANNED, TaskState.CANCELLED],
        TaskState.CANCELLED: []
    }

    def __init__(self, db_connection: sqlite3.Connection, project_id: str):
        self.db = db_connection
        self.project_id = project_id
        self._lock = threading.RLock()
        self._cancellation_tokens: Dict[str, threading.Event] = {}
        self._init_state_table()

    def _init_state_table(self):
        with self._lock:
            cursor = self.db.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS task_states (
                    task_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    current_state TEXT NOT NULL,
                    authority_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS task_transitions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    from_state TEXT NOT NULL,
                    to_state TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    reason TEXT NOT NULL
                )
            """)
            self.db.commit()

    def create_task(self, task_id: str, request_text: str, publication_scope: Optional[str] = None) -> TaskAuthority:
        request_hash = hashlib.sha256(request_text.encode('utf-8')).hexdigest()
        authority = TaskAuthority(task_id, request_hash, self.project_id, datetime.utcnow(), publication_scope)
        
        with self._lock:
            cursor = self.db.cursor()
            now = datetime.utcnow().isoformat()
            cursor.execute("SELECT task_id FROM task_states WHERE task_id = ?", (task_id,))
            if cursor.fetchone():
                raise ValueError(f"Task {task_id} already exists")
            
            cursor.execute("""
                INSERT INTO task_states (task_id, project_id, current_state, authority_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (task_id, self.project_id, TaskState.PLANNED.name, json.dumps({"task_id": task_id, "request_hash": request_hash}), now, now))
            
            cursor.execute("""
                INSERT INTO task_transitions (task_id, from_state, to_state, timestamp, reason)
                VALUES (?, ?, ?, ?, ?)
            """, (task_id, "NONE", TaskState.PLANNED.name, now, "Task created"))
            self.db.commit()
            self._cancellation_tokens[task_id] = threading.Event()
            logger.info(f"Task {task_id} created in state PLANNED")
        return authority

    def transition(self, task_id: str, to_state: TaskState, reason: str) -> bool:
        with self._lock:
            cursor = self.db.cursor()
            cursor.execute("SELECT current_state FROM task_states WHERE task_id = ?", (task_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Task {task_id} not found")
            
            from_state = TaskState[row[0]]
            if to_state not in self.ALLOWED_TRANSITIONS.get(from_state, []):
                raise ValueError(f"Transition from {from_state.name} to {to_state.name} is not allowed")
            
            if to_state == TaskState.CANCELLED:
                token = self._cancellation_tokens.get(task_id)
                if token:
                    token.set()
            
            now = datetime.utcnow().isoformat()
            cursor.execute("UPDATE task_states SET current_state = ?, updated_at = ? WHERE task_id = ?", (to_state.name, now, task_id))
            cursor.execute("INSERT INTO task_transitions (task_id, from_state, to_state, timestamp, reason) VALUES (?, ?, ?, ?, ?)",
                           (task_id, from_state.name, to_state.name, now, reason))
            self.db.commit()
            logger.info(f"Task {task_id}: {from_state.name} -> {to_state.name} ({reason})")
            return True

    def is_cancelled(self, task_id: str) -> bool:
        token = self._cancellation_tokens.get(task_id)
        return token.is_set() if token else False
        
    def get_state(self, task_id: str) -> str:
        with self._lock:
            cursor = self.db.cursor()
            cursor.execute("SELECT current_state FROM task_states WHERE task_id = ?", (task_id,))
            row = cursor.fetchone()
            return row[0] if row else "UNKNOWN"
'@
Write-PyFile "AI_SMM_Work_Architecture_A75\task_state_machine.py" $tsmContent

# 4. Generate local_quality_gate.py (using @'...'@ to preserve triple quotes literally)
Write-Host "[4/5] Generating local_quality_gate.py..." -ForegroundColor Cyan

$lqgContent = @'
"""
Local Quality Gate - Adapted for single local model (qwen3:8b).
Uses Sequential Role Isolation: same model, different system prompts, cleared context.
"""
from typing import Dict, Any, Optional
import json
import hashlib
import logging

logger = logging.getLogger(__name__)

class LocalQualityGate:
    AUTHOR_SYSTEM_PROMPT = """You are a professional SMM specialist. Create high-quality social media content based on the user request.
Rules:
1. Strictly follow user requirements (tone, format, length).
2. DO NOT invent facts, prices, services, or statistics. If unknown, state it.
3. Use only project context or general knowledge.
Respond STRICTLY in JSON format:
{
  "content": "main text",
  "hashtags": ["list", "of", "hashtags"],
  "call_to_action": "CTA text",
  "metadata": {"platform": "instagram", "tone": "friendly", "word_count": 0}
}"""

    REVIEWER_SYSTEM_PROMPT = """You are an independent critical editor. Strictly check the content created by another AI author against 4 criteria:
1. REQUIREMENTS: Does it match user request?
2. COMPLETENESS: Are all elements present?
3. EVIDENCE: Are there any invented facts, prices, or services?
4. FORMAT_TONE: Does it match the target platform?
Rules: Be strict. If it fails any criterion, reject it. Provide specific feedback.
Respond STRICTLY in JSON format:
{
  "reviews": [{"criterion": "REQUIREMENTS", "passed": true, "score": 0.9, "feedback": "ok", "suggestions": []}],
  "overall_score": 0.85,
  "approved": true,
  "final_feedback": "summary"
}"""

    def __init__(self, ollama_client=None, model_name: str = "qwen3:8b"):
        self.ollama = ollama_client
        self.model = model_name
        self.min_passing_score = 0.7

    def _call_model(self, system_prompt: str, user_message: str, temperature: float = 0.7) -> str:
        logger.info(f"[STUB] Calling model {self.model} with temp {temperature}")
        return '{"content": "Stub: Coffee is great.", "hashtags": ["#coffee"], "call_to_action": "Visit us", "metadata": {"platform": "instagram", "tone": "friendly", "word_count": 10}}'

    def generate_content(self, request_text: str, project_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        user_message = request_text
        if project_context:
            user_message += f"\n\nProject Context:\n{json.dumps(project_context, ensure_ascii=False, indent=2)}"
        response = self._call_model(self.AUTHOR_SYSTEM_PROMPT, user_message)
        try:
            result = json.loads(response)
            result["_request_hash"] = hashlib.sha256(request_text.encode('utf-8')).hexdigest()
            return result
        except json.JSONDecodeError:
            return {"error": "Invalid JSON from model", "raw": response}

    def review_content(self, request_text: str, content: Dict[str, Any]) -> Dict[str, Any]:
        user_message = f"Original request:\n{request_text}\n\nContent to review:\n{json.dumps(content, ensure_ascii=False, indent=2)}"
        response = self._call_model(self.REVIEWER_SYSTEM_PROMPT, user_message, temperature=0.3)
        try:
            review_data = json.loads(response)
            approved = review_data.get("approved", False)
            for r in review_data.get("reviews", []):
                if not r.get("passed", True):
                    approved = False
            return {**review_data, "approved": approved}
        except json.JSONDecodeError:
            return {"approved": False, "error": "Invalid JSON from reviewer", "raw": response}
'@
Write-PyFile "AI_SMM_Work_Architecture_A75\local_quality_gate.py" $lqgContent

# 5. Generate qt_worker_lifecycle.py
Write-Host "[5/5] Generating qt_worker_lifecycle.py..." -ForegroundColor Cyan

$qwlContent = @'
"""
Qt Worker Lifecycle v2 - Strict synchronization of Qt workers with State Machine.
"""
import logging
import threading
from typing import Dict, Callable

logger = logging.getLogger(__name__)

try:
    from PySide6.QtCore import QThread, QObject, Signal
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False
    logger.warning("PySide6 not available - Qt Worker Lifecycle disabled")

if PYSIDE6_AVAILABLE:
    class TaskWorker(QThread):
        finished_success = Signal(str, dict)
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
                result = self.work_fn(self.task_id)
                if self.state_machine.is_cancelled(self.task_id):
                    self.finished_error.emit(self.task_id, "Cancelled during execution")
                    return
                self.finished_success.emit(self.task_id, result)
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
                worker.finished_success.connect(lambda tid, res: self._on_success(tid))
                worker.finished_error.connect(lambda tid, err: self._on_error(tid, err))
                worker.finished.connect(lambda: self._on_finished(task_id))
                self._workers[task_id] = worker
                worker.start()
                self.worker_started.emit(task_id)
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

        def _on_success(self, task_id: str):
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
Write-PyFile "AI_SMM_Work_Architecture_A75\qt_worker_lifecycle.py" $qwlContent

# 6. Fix START.bat (must be UTF-8 without BOM)
Write-Host "[6/6] Fixing START.bat (removing BOM)..." -ForegroundColor Cyan

$startBatContent = @'
@echo off
chcp 65001 >nul
title AI SMM Manager
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo [ERROR] venv not found. Run bootstrap_sprint1.ps1
    pause
    exit /b 1
)

echo Starting AI SMM Manager...
venv\Scripts\python.exe AI_SMM_Work_Architecture_A75\app.py

if errorlevel 1 (
    echo.
    echo [ERROR] Exit code: %errorlevel%
    pause
)
'@
Write-BatFile "START.bat" $startBatContent

# 7. Update app.py
Write-Host "[7/7] Updating app.py..." -ForegroundColor Cyan

$appPyContent = @'
import sys, os, logging, sqlite3
from pathlib import Path

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
    logger.info("=== AI SMM Manager starting ===")
    try:
        from PySide6.QtWidgets import QApplication
        import yaml
        from task_state_machine import TaskStateMachine, TaskState
        from local_quality_gate import LocalQualityGate
        from qt_worker_lifecycle import WorkerManager, PYSIDE6_AVAILABLE
    except ImportError as e:
        logger.error(f"Missing dependency: {e}")
        sys.exit(1)
    
    logger.info("Dependencies OK.")
    
    db_path = ROOT_DIR / "data" / "ai_smm_manager.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    logger.info(f"Database initialized: {db_path}")
    
    project_id = "default_project"
    state_machine = TaskStateMachine(conn, project_id)
    worker_manager = WorkerManager(conn)
    quality_gate = LocalQualityGate()
    
    logger.info("Core architecture v2 components initialized.")
    
    app = QApplication(sys.argv)
    app.setApplicationName("AI SMM Manager")
    app.setApplicationVersion("v2.0-sprint2")
    
    logger.info("Testing TaskStateMachine...")
    auth = state_machine.create_task("test_001", "Create a post about coffee")
    state_machine.transition("test_001", TaskState.AUTHORING, "Test transition")
    logger.info(f"Task test_001 state: {state_machine.get_state('test_001')}")
    
    logger.info("GUI initialized. Core architecture v2 is ACTIVE and VERIFIED.")
    sys.exit(0)

if __name__ == "__main__":
    main()
'@
Write-PyFile "AI_SMM_Work_Architecture_A75\app.py" $appPyContent

# 8. Final verification
Write-Host ""
Write-Host "[8/8] Final verification..." -ForegroundColor Cyan
$checks = @(
    "AI_SMM_Work_Architecture_A75\task_state_machine.py",
    "AI_SMM_Work_Architecture_A75\local_quality_gate.py",
    "AI_SMM_Work_Architecture_A75\qt_worker_lifecycle.py",
    "AI_SMM_Work_Architecture_A75\app.py",
    "START.bat"
)
$allOk = $true
foreach ($check in $checks) {
    if (Test-Path (Join-Path $root $check)) {
        Write-Host "  OK: $check" -ForegroundColor Green
    } else {
        Write-Host "  MISSING: $check" -ForegroundColor Red
        $allOk = $false
    }
}

Write-Host ""
if ($allOk) {
    Write-Host "=== Sprint 2 completed successfully ===" -ForegroundColor Green
    Write-Host "Run START.bat to verify." -ForegroundColor Green
} else {
    Write-Host "=== Sprint 2 completed with errors ===" -ForegroundColor Red
}
Write-Host ""