#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI SMM Manager - Sprint 11: Full Russian language support
Run: python bootstrap_sprint11.py
"""

import os
import sys
from pathlib import Path

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

print("\n=== AI SMM Manager - Sprint 11: Full Russian Language ===")
print(f"Root: {ROOT_DIR}\n")

# 1. Check venv
print("[1/2] Checking virtual environment...")
venv_python = ROOT_DIR / "venv" / "Scripts" / "python.exe"
if not venv_python.exists():
    print("  ERROR: venv not found.")
    input("Press Enter to exit")
    sys.exit(1)
print("  OK: venv found\n")

# 2. Update local_quality_gate.py with Russian prompts
print("[2/2] Updating local_quality_gate.py with Russian prompts...")

lqg_content = '''"""
Local Quality Gate v3 - Russian language prompts
"""
from typing import Dict, Any, Optional
import json
import hashlib
import logging
import re

logger = logging.getLogger(__name__)

class LocalQualityGate:
    AUTHOR_SYSTEM_PROMPT = """Ты — профессиональный SMM-специалист. Создай качественный контент для социальных сетей на основе запроса пользователя.
ПРАВИЛА:
1. Строго следуй требованиям пользователя (тональность, формат, длина).
2. КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО выдумывать факты, цены, услуги или статистику. Если их нет в запросе — не упоминай их.
3. Используй только информацию из контекста проекта или общие знания.
4. Отвечай СТРОГО в формате JSON:
{
  "content": "основной текст поста",
  "hashtags": ["#хэштег1", "#хэштег2"],
  "call_to_action": "призыв к действию",
  "metadata": {"platform": "instagram", "tone": "дружелюбный", "word_count": 0}
}"""

    REVIEWER_SYSTEM_PROMPT = """Ты — независимый критический редактор. Строго проверь контент по 4 критериям:
1. REQUIREMENTS: Точное соответствие запросу пользователя.
2. COMPLETENESS: Все необходимые элементы присутствуют.
3. EVIDENCE: НЕТ ЛИ выдуманных фактов, цен или услуг? (Если в запросе сказано "не выдумывай цены", наличие цен — это ПРОВАЛ).
4. FORMAT_TONE: Соответствие формата и тональности целевой платформе.
ПРАВИЛА: Будь строгим. Если контент нарушает запрет на выдумывание фактов/цен — немедленно отклоняй (approved: false).
Отвечай СТРОГО в формате JSON:
{
  "reviews": [{"criterion": "EVIDENCE", "passed": true, "score": 1.0, "feedback": "Факты не выдуманы", "suggestions": []}],
  "overall_score": 0.9,
  "approved": true,
  "final_feedback": "Контент одобрен, правила соблюдены"
}"""

    def __init__(self, ollama_client=None, model_name: str = "qwen3:8b"):
        self.model = model_name
        self.min_passing_score = 0.7
        if ollama_client is None:
            from ollama_client import OllamaClient
            self.ollama = OllamaClient(model=model_name)
        else:
            self.ollama = ollama_client

    def _call_model(self, system_prompt: str, user_message: str, temperature: float = 0.7) -> str:
        return self.ollama.generate(system_prompt, user_message, temperature)

    def _extract_json(self, response: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from response, handling markdown code blocks and extra text."""
        # Try direct parse first
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        # Try to extract from markdown code block
        pattern = r'```json\\s*(.*?)\\s*```'
        json_match = re.search(pattern, response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Try to find JSON object in text
        json_match = re.search(r'\\{.*?\\}', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass
        
        return None

    def generate_content(self, request_text: str, project_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        user_message = request_text
        if project_context:
            user_message += f"\\n\\nКонтекст проекта:\\n{json.dumps(project_context, ensure_ascii=False, indent=2)}"
        
        response = self._call_model(self.AUTHOR_SYSTEM_PROMPT, user_message)
        logger.info(f"Author response (first 200 chars): {response[:200]}")
        
        result = self._extract_json(response)
        if result:
            result["_request_hash"] = hashlib.sha256(request_text.encode('utf-8')).hexdigest()
            return result
        else:
            logger.error(f"Failed to parse author response: {response[:500]}")
            return {"error": "Invalid JSON from author", "raw": response}

    def review_content(self, request_text: str, content: Dict[str, Any]) -> Dict[str, Any]:
        user_message = f"Запрос:\\n{request_text}\\n\\nКонтент для проверки:\\n{json.dumps(content, ensure_ascii=False, indent=2)}"
        
        response = self._call_model(self.REVIEWER_SYSTEM_PROMPT, user_message, temperature=0.2)
        logger.info(f"Reviewer response (first 200 chars): {response[:200]}")
        
        review_data = self._extract_json(response)
        
        if not review_data:
            logger.error(f"Failed to parse reviewer response: {response[:500]}")
            return {
                "approved": False,
                "error": "Invalid JSON from reviewer",
                "raw": response,
                "final_feedback": "Не удалось разобрать ответ рецензента"
            }
        
        # Ensure required fields exist
        if "reviews" not in review_data:
            review_data["reviews"] = []
        if "overall_score" not in review_data:
            review_data["overall_score"] = 0.0
        if "approved" not in review_data:
            review_data["approved"] = False
        if "final_feedback" not in review_data:
            review_data["final_feedback"] = "Обратная связь не предоставлена"
        
        # Check if any review failed
        approved = review_data.get("approved", False)
        for r in review_data.get("reviews", []):
            if not r.get("passed", True):
                approved = False
        
        # Check overall score
        if review_data.get("overall_score", 0) < self.min_passing_score:
            approved = False
        
        review_data["approved"] = approved
        
        return review_data
    
    def full_quality_gate(self, request_text: str, project_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        logger.info("Starting full quality gate cycle...")
        
        content = self.generate_content(request_text, project_context)
        if "error" in content:
            return {"approved": False, "error": content["error"], "raw": content.get("raw", "")}
        
        review_result = self.review_content(request_text, content)
        
        return {
            "content": content,
            "review": review_result,
            "approved": review_result.get("approved", False)
        }
'''

write_file("AI_SMM_Work_Architecture_A75/local_quality_gate.py", lqg_content)

# 3. Update app.py with Russian GUI labels
print("[3/3] Updating app.py with Russian GUI labels...")

app_content = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI SMM Manager - Sprint 11: Full Russian language support
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
    logger.info("=== AI SMM Manager - Sprint 11: Full Russian Language ===")
    
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
    window.setWindowTitle("AI SMM Manager v2.0 (Sprint 11)")
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
        msg_handler.log("\\n[СТАРТ] Отправка запроса в Ollama (qwen3:8b)...")
        msg_handler.log("[ИНФО] Генерация -> Независимая проверка...")
        
        def work_fn(task_id):
            result = quality_gate.full_quality_gate(request, {"правило": "Не выдумывай цены"})
            return result
        
        worker = worker_manager.create_worker("gui_task_001", "default_project", work_fn)
        worker.finished_success_json.connect(lambda tid, json_str: on_success_json(tid, json_str))
        worker.finished_error.connect(lambda tid, err: msg_handler.log(f"[ОШИБКА] {err}"))
    
    def on_success_json(task_id, json_result):
        try:
            result = json.loads(json_result)
        except json.JSONDecodeError as e:
            msg_handler.log(f"[ОШИБКА] Не удалось разобрать результат: {e}")
            return
        
        if result.get("approved"):
            msg_handler.log("\\n[OK] КОНТЕНТ ОДОБРЕН РЕЦЕНЗЕНТОМ!")
            c = result.get("content", {})
            msg_handler.log(f"Текст:\\n{c.get('content')}")
            msg_handler.log(f"Хэштеги: {', '.join(c.get('hashtags', []))}")
            msg_handler.log(f"Призыв к действию: {c.get('call_to_action')}")
        else:
            feedback = result.get('review', {}).get('final_feedback', 'Неизвестная причина')
            msg_handler.log(f"\\n[ОТКЛОНЕНО] КОНТЕНТ ОТКЛОНЕН: {feedback}")
    
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
'''

write_file("AI_SMM_Work_Architecture_A75/app.py", app_content)

print("\n=== Sprint 11 completed successfully ===")
print("Run START.bat to launch the GUI with full Russian language support!")
print("\nChanges:")
print("- All GUI labels in Russian")
print("- AI prompts in Russian (will generate Russian content)")
print("- All messages and feedback in Russian")