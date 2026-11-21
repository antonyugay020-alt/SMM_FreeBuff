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