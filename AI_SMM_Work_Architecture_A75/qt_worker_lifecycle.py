"""
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
