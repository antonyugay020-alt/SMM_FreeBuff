"""
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
    
    def rename_project(self, project_id: str, name: str,
                       description: Optional[str] = None) -> bool:
        try:
            now = datetime.utcnow().isoformat()
            if description is None:
                self.conn.execute("UPDATE projects SET name = ?, updated_at = ? WHERE id = ?",
                                  (name, now, project_id))
            else:
                self.conn.execute(
                    "UPDATE projects SET name = ?, description = ?, updated_at = ? WHERE id = ?",
                    (name, description, now, project_id))
            self.conn.commit()
            logger.info(f"Project renamed: {project_id} -> {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to rename project: {e}")
            return False

    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        for project in self.list_projects():
            if project["id"] == project_id:
                return project
        return None

    def project_dir(self, project_id: str) -> Path:
        """Where the project database and its files live."""
        return Path(__file__).resolve().parent.parent / "data" / "projects" / project_id

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
