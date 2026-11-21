#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI SMM Manager - Step 6: Project Database + Checkpoints + History + Temp Cleanup.
Adds:
- Project management (create, list, delete)
- Task history with all outputs (text, images, videos)
- Checkpoints (save/restore task state)
- Automatic temp file cleanup
- Project statistics
Run: python bootstrap_step6.py
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PYTHONUTF8'] = '1'

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = Path(__file__).resolve().parent

def write_file(rel_path: str, content: str):
    full_path = ROOT_DIR / rel_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    with open(full_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)
    print(f"  Created/Updated: {rel_path}")

print("\n" + "="*70)
print("=== AI SMM Manager - Step 6: Project Database & Checkpoints ===")
print("="*70 + "\n")

# 1. Create project_manager.py
print("[1/4] Creating project_manager.py...")

project_manager_content = '''"""
Project Manager - Database for projects, tasks, checkpoints, and history.
Features:
- Create/list/delete projects
- Save task results (text, images, videos)
- Checkpoints (save/restore task state)
- Task history and statistics
- Automatic temp file cleanup
"""
import sqlite3
import json
import logging
import shutil
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

class ProjectManager:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._init_database()
        logger.info(f"Project database initialized: {self.db_path}")
    
    def _init_database(self):
        """Initialize database schema."""
        cursor = self.conn.cursor()
        
        # Projects table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                metadata_json TEXT
            )
        """)
        
        # Tasks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                type TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                request_text TEXT,
                result_json TEXT,
                created_at TEXT NOT NULL,
                completed_at TEXT,
                error_message TEXT,
                FOREIGN KEY (project_id) REFERENCES projects(id)
            )
        """)
        
        # Checkpoints table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS checkpoints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                stage TEXT NOT NULL,
                data_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            )
        """)
        
        # Media files table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS media_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER,
                created_at TEXT NOT NULL,
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            )
        """)
        
        self.conn.commit()
        logger.info("Database schema initialized")
    
    # === Projects ===
    def create_project(self, project_id: str, name: str, description: str = "") -> bool:
        try:
            cursor = self.conn.cursor()
            now = datetime.utcnow().isoformat()
            cursor.execute("""
                INSERT INTO projects (id, name, description, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (project_id, name, description, now, now))
            self.conn.commit()
            logger.info(f"Project created: {project_id} - {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to create project: {e}")
            return False
    
    def list_projects(self) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, name, description, created_at, updated_at FROM projects ORDER BY updated_at DESC")
        rows = cursor.fetchall()
        return [
            {
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "created_at": row[3],
                "updated_at": row[4]
            }
            for row in rows
        ]
    
    def delete_project(self, project_id: str) -> bool:
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM tasks WHERE project_id = ?", (project_id,))
            cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            self.conn.commit()
            logger.info(f"Project deleted: {project_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete project: {e}")
            return False
    
    # === Tasks ===
    def create_task(self, task_id: str, project_id: str, task_type: str, 
                    request_text: str = "") -> bool:
        try:
            cursor = self.conn.cursor()
            now = datetime.utcnow().isoformat()
            cursor.execute("""
                INSERT INTO tasks (id, project_id, type, status, request_text, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (task_id, project_id, task_type, "pending", request_text, now))
            
            # Update project updated_at
            cursor.execute("UPDATE projects SET updated_at = ? WHERE id = ?", (now, project_id))
            self.conn.commit()
            logger.info(f"Task created: {task_id} ({task_type})")
            return True
        except Exception as e:
            logger.error(f"Failed to create task: {e}")
            return False
    
    def complete_task(self, task_id: str, result: Dict[str, Any]) -> bool:
        try:
            cursor = self.conn.cursor()
            now = datetime.utcnow().isoformat()
            cursor.execute("""
                UPDATE tasks 
                SET status = 'completed', result_json = ?, completed_at = ?
                WHERE id = ?
            """, (json.dumps(result, ensure_ascii=False), now, task_id))
            
            # Update project
            cursor.execute("SELECT project_id FROM tasks WHERE id = ?", (task_id,))
            row = cursor.fetchone()
            if row:
                cursor.execute("UPDATE projects SET updated_at = ? WHERE id = ?", (now, row[0]))
            
            self.conn.commit()
            logger.info(f"Task completed: {task_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to complete task: {e}")
            return False
    
    def fail_task(self, task_id: str, error_message: str) -> bool:
        try:
            cursor = self.conn.cursor()
            now = datetime.utcnow().isoformat()
            cursor.execute("""
                UPDATE tasks 
                SET status = 'failed', error_message = ?, completed_at = ?
                WHERE id = ?
            """, (error_message, now, task_id))
            self.conn.commit()
            logger.info(f"Task failed: {task_id} - {error_message}")
            return True
        except Exception as e:
            logger.error(f"Failed to fail task: {e}")
            return False
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, project_id, type, status, request_text, result_json, 
                   created_at, completed_at, error_message
            FROM tasks WHERE id = ?
        """, (task_id,))
        row = cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "project_id": row[1],
                "type": row[2],
                "status": row[3],
                "request_text": row[4],
                "result": json.loads(row[5]) if row[5] else None,
                "created_at": row[6],
                "completed_at": row[7],
                "error_message": row[8]
            }
        return None
    
    def get_project_tasks(self, project_id: str) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, type, status, request_text, result_json, created_at, completed_at
            FROM tasks WHERE project_id = ? ORDER BY created_at DESC
        """, (project_id,))
        rows = cursor.fetchall()
        return [
            {
                "id": row[0],
                "type": row[1],
                "status": row[2],
                "request_text": row[3],
                "result": json.loads(row[4]) if row[4] else None,
                "created_at": row[5],
                "completed_at": row[6]
            }
            for row in rows
        ]
    
    # === Checkpoints ===
    def save_checkpoint(self, task_id: str, stage: str, data: Dict[str, Any]) -> bool:
        try:
            cursor = self.conn.cursor()
            now = datetime.utcnow().isoformat()
            cursor.execute("""
                INSERT INTO checkpoints (task_id, stage, data_json, created_at)
                VALUES (?, ?, ?, ?)
            """, (task_id, stage, json.dumps(data, ensure_ascii=False), now))
            self.conn.commit()
            logger.info(f"Checkpoint saved: {task_id} - {stage}")
            return True
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
            return False
    
    def get_checkpoint(self, task_id: str, stage: str) -> Optional[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT data_json FROM checkpoints 
            WHERE task_id = ? AND stage = ?
            ORDER BY created_at DESC LIMIT 1
        """, (task_id, stage))
        row = cursor.fetchone()
        if row:
            return json.loads(row[0])
        return None
    
    def get_task_checkpoints(self, task_id: str) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT stage, data_json, created_at FROM checkpoints
            WHERE task_id = ? ORDER BY created_at
        """, (task_id,))
        rows = cursor.fetchall()
        return [
            {
                "stage": row[0],
                "data": json.loads(row[1]),
                "created_at": row[2]
            }
            for row in rows
        ]
    
    # === Media Files ===
    def add_media_file(self, task_id: str, file_type: str, file_path: str, 
                       file_size: Optional[int] = None) -> bool:
        try:
            cursor = self.conn.cursor()
            now = datetime.utcnow().isoformat()
            cursor.execute("""
                INSERT INTO media_files (task_id, file_type, file_path, file_size, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (task_id, file_type, file_path, file_size, now))
            self.conn.commit()
            logger.info(f"Media file added: {file_path} ({file_type})")
            return True
        except Exception as e:
            logger.error(f"Failed to add media file: {e}")
            return False
    
    def get_task_media(self, task_id: str) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT file_type, file_path, file_size, created_at
            FROM media_files WHERE task_id = ?
        """, (task_id,))
        rows = cursor.fetchall()
        return [
            {
                "type": row[0],
                "path": row[1],
                "size": row[2],
                "created_at": row[3]
            }
            for row in rows
        ]
    
    # === Statistics ===
    def get_statistics(self) -> Dict[str, Any]:
        cursor = self.conn.cursor()
        
        # Total counts
        cursor.execute("SELECT COUNT(*) FROM projects")
        total_projects = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM tasks")
        total_tasks = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'completed'")
        completed_tasks = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'failed'")
        failed_tasks = cursor.fetchone()[0]
        
        # Task types
        cursor.execute("""
            SELECT type, COUNT(*) FROM tasks 
            GROUP BY type ORDER BY COUNT(*) DESC
        """)
        task_types = {row[0]: row[1] for row in cursor.fetchall()}
        
        return {
            "total_projects": total_projects,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "task_types": task_types
        }
    
    # === Cleanup ===
    def cleanup_temp_files(self, temp_dir: str) -> int:
        """Remove old temporary files."""
        temp_path = Path(temp_dir)
        if not temp_path.exists():
            return 0
        
        deleted_count = 0
        max_age_hours = 24  # Delete files older than 24 hours
        
        try:
            for file in temp_path.glob("*"):
                try:
                    # Check file age
                    file_time = datetime.fromtimestamp(file.stat().st_mtime)
                    age_hours = (datetime.now() - file_time).total_seconds() / 3600
                    
                    if age_hours > max_age_hours:
                        file.unlink()
                        deleted_count += 1
                        logger.info(f"Deleted old temp file: {file}")
                except Exception as e:
                    logger.warning(f"Failed to delete temp file {file}: {e}")
            
            logger.info(f"Cleanup completed: {deleted_count} files deleted")
            return deleted_count
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            return 0
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
'''

write_file("AI_SMM_Work_Architecture_A75/project_manager.py", project_manager_content)

# 2. Update app.py to integrate project manager
print("[2/4] Updating app.py with project management...")

app_content = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI SMM Manager - Step 6: Project Management Integration.
"""

import sys
import os
import logging
import sqlite3
import json
import time
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
    logger.info("=== AI SMM Manager - Step 6: Project Management ===")
    
    try:
        import yaml
        from PySide6.QtWidgets import (
            QApplication, QMainWindow, QTextEdit, QPushButton, QVBoxLayout, 
            QWidget, QLabel, QCheckBox, QGroupBox, QTabWidget, QComboBox, 
            QFileDialog, QListWidget, QListWidgetItem, QLineEdit, QHBoxLayout,
            QMessageBox
        )
        from PySide6.QtCore import Qt, Signal, QObject
        from PySide6.QtGui import QFont
        from task_state_machine import TaskStateMachine, TaskState
        from local_quality_gate import LocalQualityGate
        from ollama_client import OllamaClient
        from openai_client import OpenAIClient
        from local_image_generator import LocalImageGenerator
        from video_processor import VideoProcessor
        from project_manager import ProjectManager
        from qt_worker_lifecycle import WorkerManager
        from media_task_router import MediaTaskRouter
    except ImportError as e:
        logger.error(f"Missing dependency: {e}")
        sys.exit(1)
    
    # Initialize database and project manager
    db_path = ROOT_DIR / "data" / "ai_smm_manager.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    
    project_manager = ProjectManager(str(ROOT_DIR / "data" / "ai_smm_projects.db"))
    
    # Create default project if none exists
    projects = project_manager.list_projects()
    if not projects:
        project_manager.create_project("default", "Default Project", "Default SMM project")
        logger.info("Created default project")
    
    state_machine = TaskStateMachine(conn, "default")
    worker_manager = WorkerManager(conn)
    
    config_path = ROOT_DIR / "config" / "config.yaml"
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        logger.info("Configuration loaded.")
    else:
        config = {}
        logger.warning("config.yaml not found, using defaults.")
    
    ollama = OllamaClient()
    
    openai_config = config.get("openai", {})
    openai_api_key = openai_config.get("api_key", "")
    openai_enabled = openai_config.get("enabled", False)
    openai_client = OpenAIClient(api_key=openai_api_key, enabled=openai_enabled)
    
    local_img_gen = LocalImageGenerator(ollama_client=ollama)
    video_processor = VideoProcessor(whisper_model="base", openai_client=openai_client)
    
    quality_gate = LocalQualityGate(ollama_client=ollama, openai_client=openai_client, config=config)
    media_router = MediaTaskRouter(config)
    
    logger.info("All components initialized. Starting GUI...")
    
    app = QApplication(sys.argv)
    app.setApplicationName("AI SMM Manager")
    
    font = QFont("Arial", 10)
    app.setFont(font)
    
    window = QMainWindow()
    window.setWindowTitle("AI SMM Manager v2.0 (Step 6 - Projects)")
    window.resize(1000, 750)
    
    # Create tab widget
    tabs = QTabWidget()
    
    # === TAB 1: Projects & History ===
    projects_tab = QWidget()
    projects_layout = QVBoxLayout()
    
    # Statistics
    stats = project_manager.get_statistics()
    stats_label = QLabel(
        f"Проектов: {stats['total_projects']} | "
        f"Задач: {stats['total_tasks']} | "
        f"Успешно: {stats['completed_tasks']} | "
        f"Ошибок: {stats['failed_tasks']}"
    )
    stats_label.setFont(QFont("Arial", 11, QFont.Bold))
    projects_layout.addWidget(stats_label)
    
    # Project list
    project_group = QGroupBox("Проекты")
    project_layout = QHBoxLayout()
    
    project_list = QListWidget()
    for proj in project_manager.list_projects():
        item = QListWidgetItem(f"{proj['name']} ({proj['id']})")
        item.setData(Qt.UserRole, proj['id'])
        project_list.addItem(item)
    project_layout.addWidget(project_list)
    
    project_buttons = QVBoxLayout()
    new_project_btn = QPushButton("Создать")
    delete_project_btn = QPushButton("Удалить")
    refresh_projects_btn = QPushButton("Обновить")
    project_buttons.addWidget(new_project_btn)
    project_buttons.addWidget(delete_project_btn)
    project_buttons.addWidget(refresh_projects_btn)
    project_layout.addLayout(project_buttons)
    
    project_group.setLayout(project_layout)
    projects_layout.addWidget(project_group)
    
    # Task history
    history_group = QGroupBox("История задач")
    history_layout = QVBoxLayout()
    
    task_list = QListWidget()
    history_layout.addWidget(task_list)
    
    history_group.setLayout(history_layout)
    projects_layout.addWidget(history_group)
    
    projects_tab.setLayout(projects_layout)
    tabs.addTab(projects_tab, "Проекты")
    
    # === TAB 2: Text Generation ===
    text_tab = QWidget()
    text_layout = QVBoxLayout()
    
    text_label = QLabel("Введите задачу для SMM-менеджера:")
    text_label.setFont(QFont("Arial", 11, QFont.Bold))
    text_layout.addWidget(text_label)
    
    text_input = QTextEdit()
    text_input.setFont(QFont("Consolas", 10))
    text_input.setPlainText("Создай короткий пост для Instagram про утренний кофе в кофейне для фрилансеров. Тон: дружелюбный. Не выдумывай цены.")
    text_layout.addWidget(text_input)
    
    img_group = QGroupBox("Генерация изображения")
    img_layout = QVBoxLayout()
    
    use_openai_cb = QCheckBox(f"OpenAI GPT-Image ({openai_client.get_image_model() or 'недоступно'})")
    use_openai_cb.setChecked(openai_client.is_available())
    use_openai_cb.setEnabled(openai_client.is_available())
    img_layout.addWidget(use_openai_cb)
    
    use_local_sd_cb = QCheckBox(f"Stable Diffusion локально ({local_img_gen.get_info()['vram_gb']:.1f} GB VRAM)")
    use_local_sd_cb.setChecked(not openai_client.is_available())
    img_layout.addWidget(use_local_sd_cb)
    
    auto_translate_cb = QCheckBox("Автоперевод промпта RU -> EN (для SD)")
    auto_translate_cb.setChecked(True)
    img_layout.addWidget(auto_translate_cb)
    
    img_group.setLayout(img_layout)
    text_layout.addWidget(img_group)
    
    text_output = QTextEdit()
    text_output.setFont(QFont("Consolas", 10))
    text_output.setReadOnly(True)
    text_layout.addWidget(text_output)
    
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
    
    text_msg_handler = MessageHandler(text_output)
    
    def run_text_task():
        request = text_input.toPlainText()
        use_openai = use_openai_cb.isChecked()
        use_local = use_local_sd_cb.isChecked()
        auto_translate = auto_translate_cb.isChecked()
        
        # Get selected project
        selected_items = project_list.selectedItems()
        project_id = selected_items[0].data(Qt.UserRole) if selected_items else "default"
        
        task_id = f"text_{int(time.time())}"
        
        # Create task in database
        project_manager.create_task(task_id, project_id, "text_generation", request)
        project_manager.save_checkpoint(task_id, "started", {"request": request})
        
        text_msg_handler.log(f"\\n[СТАРТ] Задача: {task_id}")
        text_msg_handler.log(f"[ПРОЕКТ] {project_id}")
        text_msg_handler.log(f"[ИНФО] Автор: {quality_gate.author_model}")
        text_msg_handler.log(f"[ИНФО] Рецензент: {quality_gate.reviewer_model}")
        
        def work_fn(tid):
            result = quality_gate.full_quality_gate(request, {"правило": "Не выдумывай цены"})
            
            image_prompt = f"Professional social media photo for Instagram: {request}. High quality, vibrant colors."
            
            if use_openai and openai_client.is_available():
                text_msg_handler.log("[ИНФО] Генерация через OpenAI GPT-Image...")
                image_result = openai_client.generate_image(image_prompt, filename=f"{task_id}.png")
                if image_result:
                    result["image"] = image_result
                    text_msg_handler.log(f"[OK] OpenAI: {image_result.get('local_path', 'N/A')}")
                    project_manager.add_media_file(task_id, "image", image_result.get('local_path', ''))
            
            elif use_local and local_img_gen.is_available():
                text_msg_handler.log("[ИНФО] Генерация через Stable Diffusion...")
                image_result = local_img_gen.generate_image(image_prompt, filename=f"{task_id}.png", auto_translate=auto_translate)
                if image_result:
                    result["image"] = image_result
                    text_msg_handler.log(f"[OK] SD: {image_result.get('local_path', 'N/A')}")
                    project_manager.add_media_file(task_id, "image", image_result.get('local_path', ''))
            
            # Save checkpoint
            project_manager.save_checkpoint(task_id, "completed", result)
            
            # Complete task
            project_manager.complete_task(task_id, result)
            
            return result
        
        worker = worker_manager.create_worker(task_id, project_id, work_fn)
        worker.finished_success_json.connect(lambda tid, json_str: on_text_success(tid, json_str))
        worker.finished_error.connect(lambda tid, err: on_text_error(tid, err))
    
    def on_text_success(task_id, json_result):
        try:
            result = json.loads(json_result)
        except json.JSONDecodeError as e:
            text_msg_handler.log(f"[ОШИБКА] Не удалось разобрать результат: {e}")
            project_manager.fail_task(task_id, str(e))
            return
        
        reviewer_model = result.get('review', {}).get('reviewer_model', 'unknown')
        
        if result.get("approved"):
            text_msg_handler.log(f"\\n[OK] КОНТЕНТ ОДОБРЕН ({reviewer_model})!")
            c = result.get("content", {})
            text_msg_handler.log(f"Текст:\\n{c.get('content')}")
            text_msg_handler.log(f"Хэштеги: {', '.join(c.get('hashtags', []))}")
            text_msg_handler.log(f"Призыв: {c.get('call_to_action')}")
            
            if "image" in result:
                img = result["image"]
                text_msg_handler.log(f"\\n[ИЗОБРАЖЕНИЕ] {img.get('local_path', 'N/A')}")
        else:
            feedback = result.get('review', {}).get('final_feedback', 'Неизвестная причина')
            text_msg_handler.log(f"\\n[ОТКЛОНЕНО]: {feedback}")
        
        # Refresh task list
        refresh_task_list()
    
    def on_text_error(task_id, error):
        text_msg_handler.log(f"[ОШИБКА] {error}")
        project_manager.fail_task(task_id, error)
        refresh_task_list()
    
    text_btn = QPushButton("Сгенерировать текст и изображение")
    text_btn.setFont(QFont("Arial", 11, QFont.Bold))
    text_btn.clicked.connect(run_text_task)
    text_layout.addWidget(text_btn)
    
    text_tab.setLayout(text_layout)
    tabs.addTab(text_tab, "Текст + Изображение")
    
    # === TAB 3: Video Processing ===
    video_tab = QWidget()
    video_layout = QVBoxLayout()
    
    video_label = QLabel("Видео-обработка (Whisper + FFmpeg)")
    video_label.setFont(QFont("Arial", 11, QFont.Bold))
    video_layout.addWidget(video_label)
    
    file_group = QGroupBox("Выбор файла")
    file_layout = QVBoxLayout()
    
    file_path_label = QLabel("Файл не выбран")
    file_layout.addWidget(file_path_label)
    
    def select_file():
        file_path, _ = QFileDialog.getOpenFileName(
            None, "Выберите видео или аудио файл", "",
            "Video/Audio Files (*.mp4 *.mov *.avi *.mkv *.webm *.mp3 *.wav *.m4a);;All Files (*)"
        )
        if file_path:
            file_path_label.setText(file_path)
            info = video_processor.get_video_info(file_path)
            if info:
                file_path_label.setText(f"{file_path}\\n{info['width']}x{info['height']}, {info['duration']:.1f}s, {info['fps']:.1f} fps")
    
    select_btn = QPushButton("Выбрать файл")
    select_btn.clicked.connect(select_file)
    file_layout.addWidget(select_btn)
    
    file_group.setLayout(file_layout)
    video_layout.addWidget(file_group)
    
    transcribe_group = QGroupBox("Транскрипция")
    transcribe_layout = QVBoxLayout()
    
    use_openai_whisper_cb = QCheckBox("Использовать OpenAI Whisper API (быстрее)")
    use_openai_whisper_cb.setChecked(openai_client.is_available())
    use_openai_whisper_cb.setEnabled(openai_client.is_available())
    transcribe_layout.addWidget(use_openai_whisper_cb)
    
    language_combo = QComboBox()
    language_combo.addItems(["Русский (ru)", "English (en)", "Автоопределение"])
    transcribe_layout.addWidget(QLabel("Язык:"))
    transcribe_layout.addWidget(language_combo)
    
    transcribe_group.setLayout(transcribe_layout)
    video_layout.addWidget(transcribe_group)
    
    export_group = QGroupBox("Экспорт для платформы")
    export_layout = QVBoxLayout()
    
    platform_combo = QComboBox()
    platform_combo.addItems(["Instagram Reels", "TikTok", "YouTube Shorts", "YouTube Video", "Instagram Post"])
    export_layout.addWidget(platform_combo)
    
    burn_subtitles_cb = QCheckBox("Наложить субтитры на видео")
    burn_subtitles_cb.setChecked(True)
    export_layout.addWidget(burn_subtitles_cb)
    
    export_group.setLayout(export_layout)
    video_layout.addWidget(export_group)
    
    video_output = QTextEdit()
    video_output.setFont(QFont("Consolas", 10))
    video_output.setReadOnly(True)
    video_layout.addWidget(video_output)
    
    video_msg_handler = MessageHandler(video_output)
    
    def run_video_task():
        file_path = file_path_label.text().split('\\n')[0]
        if not file_path or file_path == "Файл не выбран":
            video_msg_handler.log("[ОШИБКА] Файл не выбран")
            return
        
        selected_items = project_list.selectedItems()
        project_id = selected_items[0].data(Qt.UserRole) if selected_items else "default"
        
        use_openai_whisper = use_openai_whisper_cb.isChecked()
        burn_subtitles = burn_subtitles_cb.isChecked()
        platform_idx = platform_combo.currentIndex()
        platforms = ["instagram_reels", "tiktok", "youtube_shorts", "youtube_video", "instagram_post"]
        platform = platforms[platform_idx]
        
        language_map = {0: "ru", 1: "en", 2: None}
        language = language_map[language_combo.currentIndex()]
        
        task_id = f"video_{int(time.time())}"
        project_manager.create_task(task_id, project_id, "video_processing", f"File: {file_path}")
        
        video_msg_handler.log(f"\\n[СТАРТ] Задача: {task_id}")
        video_msg_handler.log(f"[ПРОЕКТ] {project_id}")
        video_msg_handler.log(f"[ФАЙЛ] {file_path}")
        video_msg_handler.log(f"[ПЛАТФОРМА] {platform}")
        
        def work_fn(tid):
            results = {}
            
            # Transcribe
            video_msg_handler.log("[1/3] Транскрипция...")
            transcript = video_processor.transcribe(file_path, language=language, use_openai=use_openai_whisper)
            
            if not transcript:
                video_msg_handler.log("[ОШИБКА] Транскрипция не удалась")
                return {"error": "Transcription failed"}
            
            results["transcript"] = transcript
            project_manager.save_checkpoint(tid, "transcribed", transcript)
            
            text = transcript.get('text', '')
            if not isinstance(text, str):
                text = str(text) if text else ""
            
            video_msg_handler.log(f"[OK] Транскрипция ({len(text)} символов)")
            preview = text[:200] if len(text) > 200 else text
            video_msg_handler.log(f"Текст: {preview}...")
            
            # Generate SRT
            segments = transcript.get('segments', [])
            video_msg_handler.log(f"[ИНФО] Сегментов: {len(segments)}")
            
            if segments:
                video_msg_handler.log("[2/3] Генерация субтитров...")
                srt_path = str(ROOT_DIR / "media" / "videos" / f"{tid}.srt")
                Path(srt_path).parent.mkdir(parents=True, exist_ok=True)
                
                if video_processor.generate_srt(segments, srt_path):
                    results["srt_path"] = srt_path
                    project_manager.add_media_file(tid, "subtitles", srt_path)
                    video_msg_handler.log(f"[OK] SRT: {srt_path}")
            
            # Export
            video_msg_handler.log(f"[3/3] Экспорт для {platform}...")
            output_path = str(ROOT_DIR / "media" / "videos" / f"{tid}_{platform}.mp4")
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            if burn_subtitles and results.get("srt_path"):
                temp_path = str(ROOT_DIR / "media" / "videos" / f"{tid}_temp.mp4")
                if video_processor.burn_subtitles(file_path, results["srt_path"], temp_path):
                    if video_processor.export_for_platform(temp_path, platform, output_path):
                        results["output_path"] = output_path
                        project_manager.add_media_file(tid, "video", output_path)
                        video_msg_handler.log(f"[OK] Видео: {output_path}")
                        # Cleanup temp
                        try:
                            Path(temp_path).unlink(missing_ok=True)
                        except:
                            pass
                    else:
                        video_msg_handler.log("[ОШИБКА] Экспорт не удался")
                else:
                    video_msg_handler.log("[ОШИБКА] Наложение субтитров не удалось")
            else:
                if video_processor.export_for_platform(file_path, platform, output_path):
                    results["output_path"] = output_path
                    project_manager.add_media_file(tid, "video", output_path)
                    video_msg_handler.log(f"[OK] Видео: {output_path}")
                else:
                    video_msg_handler.log("[ОШИБКА] Экспорт не удался")
            
            project_manager.save_checkpoint(tid, "completed", results)
            project_manager.complete_task(tid, results)
            
            return results
        
        worker = worker_manager.create_worker(task_id, project_id, work_fn)
        worker.finished_success_json.connect(lambda tid, json_str: on_video_success(tid, json_str))
        worker.finished_error.connect(lambda tid, err: on_video_error(tid, err))
    
    def on_video_success(task_id, json_result):
        try:
            result = json.loads(json_result)
        except json.JSONDecodeError as e:
            video_msg_handler.log(f"[ОШИБКА] Не удалось разобрать результат: {e}")
            return
        
        if "error" in result:
            video_msg_handler.log(f"[ОШИБКА] {result['error']}")
            return
        
        transcript = result.get("transcript", {})
        text = transcript.get('text', '')
        if not isinstance(text, str):
            text = str(text) if text else ""
        
        if text:
            preview = text[:300] if len(text) > 300 else text
            video_msg_handler.log(f"\\n[ТРАНСКРИПЦИЯ] {preview}...")
        
        if result.get("srt_path"):
            video_msg_handler.log(f"[СУБТИТРЫ] {result['srt_path']}")
        
        if result.get("output_path"):
            video_msg_handler.log(f"\\n[ГОТОВО] {result['output_path']}")
        else:
            video_msg_handler.log("\\n[ОШИБКА] Видео не экспортировано")
        
        refresh_task_list()
    
    def on_video_error(task_id, error):
        video_msg_handler.log(f"[ОШИБКА] {error}")
        project_manager.fail_task(task_id, error)
        refresh_task_list()
    
    video_btn = QPushButton("Обработать видео")
    video_btn.setFont(QFont("Arial", 11, QFont.Bold))
    video_btn.clicked.connect(run_video_task)
    video_layout.addWidget(video_btn)
    
    video_tab.setLayout(video_layout)
    tabs.addTab(video_tab, "Видео")
    
    # === Helper functions ===
    def refresh_task_list():
        """Refresh task list in Projects tab."""
        task_list.clear()
        selected_items = project_list.selectedItems()
        project_id = selected_items[0].data(Qt.UserRole) if selected_items else "default"
        
        tasks = project_manager.get_project_tasks(project_id)
        for task in tasks:
            status_icon = "✅" if task['status'] == 'completed' else "❌" if task['status'] == 'failed' else "⏳"
            item = QListWidgetItem(f"{status_icon} {task['type']} - {task['id']}")
            item.setData(Qt.UserRole, task['id'])
            task_list.addItem(item)
    
    def refresh_projects():
        """Refresh project list."""
        project_list.clear()
        for proj in project_manager.list_projects():
            item = QListWidgetItem(f"{proj['name']} ({proj['id']})")
            item.setData(Qt.UserRole, proj['id'])
            project_list.addItem(item)
    
    def create_new_project():
        """Create new project dialog."""
        text, ok = QInputDialog.getText(window, "Новый проект", "Название проекта:")
        if ok and text:
            project_id = f"proj_{int(time.time())}"
            if project_manager.create_project(project_id, text, ""):
                refresh_projects()
                QMessageBox.information(window, "Успех", f"Проект '{text}' создан!")
    
    def delete_selected_project():
        """Delete selected project."""
        selected_items = project_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(window, "Ошибка", "Выберите проект для удаления")
            return
        
        project_id = selected_items[0].data(Qt.UserRole)
        project_name = selected_items[0].text()
        
        reply = QMessageBox.question(
            window, "Подтверждение",
            f"Удалить проект '{project_name}' и все его задачи?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if project_manager.delete_project(project_id):
                refresh_projects()
                task_list.clear()
                QMessageBox.information(window, "Успех", "Проект удалён")
    
    # Connect buttons
    new_project_btn.clicked.connect(create_new_project)
    delete_project_btn.clicked.connect(delete_selected_project)
    refresh_projects_btn.clicked.connect(refresh_projects)
    project_list.currentItemChanged.connect(lambda: refresh_task_list())
    
    # Initial load
    refresh_task_list()
    
    # Cleanup old temp files on startup
    temp_dir = str(Path(tempfile.gettempdir()) / "ai_smm_ffmpeg")
    deleted = project_manager.cleanup_temp_files(temp_dir)
    if deleted > 0:
        logger.info(f"Cleaned up {deleted} old temp files")
    
    # Main layout
    main_layout = QVBoxLayout()
    main_layout.addWidget(tabs)
    
    container = QWidget()
    container.setLayout(main_layout)
    window.setCentralWidget(container)
    
    window.show()
    logger.info("GUI is running. Project management is active.")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
'''

# Fix the import - need to add QInputDialog
app_content = app_content.replace(
    'from PySide6.QtWidgets import (',
    'from PySide6.QtWidgets import (\n            QApplication, QMainWindow, QTextEdit, QPushButton, QVBoxLayout, \n            QWidget, QLabel, QCheckBox, QGroupBox, QTabWidget, QComboBox, \n            QFileDialog, QListWidget, QListWidgetItem, QLineEdit, QHBoxLayout,\n            QMessageBox, QInputDialog,'
)

write_file("AI_SMM_Work_Architecture_A75/app.py", app_content)

# 3. Update config.yaml with new sections
print("[3/4] Updating config.yaml...")

config_content = """# AI SMM Manager - Configuration
# Updated: Step 6 - Project Management

hardware:
  gpu_vram_gb: 12
  cpu_cores: 24
  ram_gb: 32

ollama:
  host: "http://localhost:11434"
  timeout: 120
  models:
    author: "qwen3:8b"
    reviewer: "deepseek-r1:8b"
    strategist: "deepseek-r1:8b"
    hashtag_generator: "llama3.1:8b"
    fallback_author: "llama3.1:8b"
    fallback_reviewer: "mistral:7b"
    embedding: "nomic-embed-text:latest"
    code_assistant: "qwen2.5-coder:7b"

openai:
  api_key: ""
  enabled: false
  models:
    image_generator: "gpt-image-2.5-sunburst"
    transcriber: "whisper-1"
    backup_reviewer: "gpt-4o-mini"
    backup_author: "gpt-4o-mini"
  monthly_budget_usd: 10
  max_image_size: "1024x1024"
  max_audio_minutes: 30

media_processing:
  local_image_model: "stable-diffusion-v1-5"
  local_whisper_model: "base"
  fallback_to_cloud_if_vram_exceeded: true
  max_local_video_resolution: "1080p"

storage:
  database: "data/ai_smm_manager.db"
  projects_database: "data/ai_smm_projects.db"
  projects_dir: "data/projects"
  checkpoints_dir: "data/checkpoints"
  logs_dir: "data/logs"
  media_dir: "media"
  temp_cleanup_hours: 24

quality:
  min_passing_score: 0.7
  max_revision_attempts: 3
  evidence_validation: true
  use_different_models: true
  prefer_cloud_for_review: false
  fallback_to_local_if_cloud_fails: true
"""

write_file("config/config.yaml", config_content)

# 4. Create projects and checkpoints directories
print("[4/4] Creating directories...")
for dir_name in ["data/projects", "data/checkpoints"]:
    dir_path = ROOT_DIR / dir_name
    dir_path.mkdir(parents=True, exist_ok=True)
    print(f"  [OK] Created: {dir_path}")

print("\n" + "="*70)
print("=== Step 6 Summary ===")
print("="*70)
print("\nCompleted:")
print("  [OK] Created project_manager.py")
print("       - Projects (create, list, delete)")
print("       - Tasks (save results, status tracking)")
print("       - Checkpoints (save/restore task state)")
print("       - Media files tracking")
print("       - Statistics")
print("       - Automatic temp file cleanup (24h)")
print("  [OK] Updated app.py with project management GUI")
print("       - Projects tab (list, create, delete)")
print("       - Task history per project")
print("       - Statistics dashboard")
print("       - All tasks saved to database")
print("  [OK] Updated config.yaml")
print("  [OK] Created data/projects/ and data/checkpoints/")

print("\nFeatures added:")
print("  - Every task is saved to database")
print("  - Projects organize your work")
print("  - Checkpoints allow resuming from any stage")
print("  - History of all processed content")
print("  - Automatic cleanup of old temp files")
print("  - Statistics dashboard")

print("\nNext: Run START.bat to use project management.")
print("="*70 + "\n")