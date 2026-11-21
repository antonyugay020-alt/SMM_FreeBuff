#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI SMM Manager - Sprint 12: Multi-Model Quality Gate with cloud editing
Run: python bootstrap_sprint12.py
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

print("\n=== AI SMM Manager - Sprint 12: Multi-Model Quality Gate ===")
print(f"Root: {ROOT_DIR}\n")

# 1. Check venv
print("[1/4] Checking virtual environment...")
venv_python = ROOT_DIR / "venv" / "Scripts" / "python.exe"
if not venv_python.exists():
    print("  ERROR: venv not found.")
    input("Press Enter to exit")
    sys.exit(1)
print("  OK: venv found\n")

# 2. Update config.yaml with model roles
print("[2/4] Updating config.yaml with model roles...")

config_content = """# AI SMM Manager - Configuration with Multi-Model Support

hardware:
  gpu_vram_gb: 8
  cpu_cores: 12
  ram_gb: 32

ollama:
  host: "http://localhost:11434"
  timeout: 120
  
  # Model roles configuration
  models:
    author: "qwen3:8b"              # Local model for content generation (fast)
    reviewer: "gpt-oss:20b-cloud"   # Cloud model for independent review (high quality)
    fallback_reviewer: "qwen3:8b"   # Fallback if cloud unavailable
    
  # Available models (for reference)
  available_models:
    - qwen3:8b
    - qwen2.5-coder:7b
    - gpt-oss:20b-cloud
    - gemma4:cloud
    - llama3.1:8b
    - deepseek-r1:8b
    - mistral:7b
    - gemma3:4b

media_processing:
  local_sd_model: "stable-diffusion-v1-5"
  local_whisper_model: "base"
  fallback_to_cloud_if_vram_exceeded: true
  max_local_video_resolution: "1080p"

cloud_apis:
  openai:
    api_key: ""
    enabled: false
  stability_ai:
    api_key: ""
    enabled: false

storage:
  database: "data/ai_smm_manager.db"
  projects_dir: "data/projects"
  checkpoints_dir: "data/checkpoints"
  logs_dir: "data/logs"

quality:
  min_passing_score: 0.7
  max_revision_attempts: 3
  evidence_validation: true
  
  # Multi-model quality settings
  use_different_models: true          # Use different models for author and reviewer
  prefer_cloud_for_review: true       # Prefer cloud models for review when available
  fallback_to_local_if_cloud_fails: true  # Fallback to local if cloud unavailable
"""

write_file("config/config.yaml", config_content)

# 3. Update ollama_client.py to support multiple models
print("[3/4] Updating ollama_client.py with multi-model support...")

ollama_client_content = '''"""
Ollama Client v2 - Multi-model support with cloud integration.
"""
import requests
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

class OllamaClient:
    def __init__(self, host: str = "http://localhost:11434", model: str = "qwen3:8b", timeout: int = 120):
        self.host = host.rstrip('/')
        self.model = model
        self.timeout = timeout
        self.session = requests.Session()
        self._available_models: Optional[List[str]] = None
        
    def is_available(self) -> bool:
        """Check if Ollama server is running."""
        try:
            response = self.session.get(f"{self.host}/api/tags", timeout=5)
            return response.status_code == 200
        except requests.exceptions.ConnectionError:
            logger.warning(f"Ollama server not available at {self.host}")
            return False
        except Exception as e:
            logger.error(f"Error checking Ollama availability: {e}")
            return False
    
    def get_available_models(self) -> List[str]:
        """Get list of available models."""
        if self._available_models is not None:
            return self._available_models
        
        if not self.is_available():
            return []
        
        try:
            response = self.session.get(f"{self.host}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                self._available_models = [m["name"] for m in models]
                logger.info(f"Available models: {self._available_models}")
                return self._available_models
        except Exception as e:
            logger.error(f"Error getting available models: {e}")
        
        return []
    
    def is_model_available(self, model_name: Optional[str] = None) -> bool:
        """Check if a specific model is available."""
        model = model_name or self.model
        available = self.get_available_models()
        return model in available
    
    def generate(self, system_prompt: str, user_message: str, temperature: float = 0.7, 
                 model: Optional[str] = None) -> str:
        """
        Generate content using Ollama API.
        
        Args:
            system_prompt: System prompt for the model
            user_message: User message
            temperature: Generation temperature (0.0-1.0)
            model: Model to use (overrides default)
        
        Returns:
            str: Generated text
        """
        target_model = model or self.model
        
        if not self.is_available():
            raise ConnectionError(f"Ollama server not available at {self.host}")
        
        if not self.is_model_available(target_model):
            raise RuntimeError(f"Model {target_model} not found. Available: {self.get_available_models()}")
        
        payload = {
            "model": target_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_ctx": 4096
            }
        }
        
        try:
            logger.info(f"Calling Ollama model {target_model} (temp={temperature})")
            start_time = datetime.now()
            
            response = self.session.post(
                f"{self.host}/api/chat",
                json=payload,
                timeout=self.timeout
            )
            
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"Ollama response received in {elapsed:.2f}s")
            
            if response.status_code != 200:
                raise RuntimeError(f"Ollama API error: {response.status_code} - {response.text}")
            
            result = response.json()
            return result["message"]["content"]
        
        except requests.exceptions.Timeout:
            raise TimeoutError(f"Ollama request timed out after {self.timeout}s")
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(f"Cannot connect to Ollama: {e}")
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            raise
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about available models."""
        return {
            "default_model": self.model,
            "host": self.host,
            "available": self.is_available(),
            "available_models": self.get_available_models()
        }
'''

write_file("AI_SMM_Work_Architecture_A75/ollama_client.py", ollama_client_content)

# 4. Update local_quality_gate.py with multi-model support
print("[4/4] Updating local_quality_gate.py with multi-model support...")

lqg_content = '''"""
Local Quality Gate v4 - Multi-model support with cloud editing.
Uses different models for author and reviewer roles.
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

    def __init__(self, ollama_client=None, config: Optional[Dict[str, Any]] = None):
        self.min_passing_score = 0.7
        
        if ollama_client is None:
            from ollama_client import OllamaClient
            self.ollama = OllamaClient()
        else:
            self.ollama = ollama_client
        
        # Load model configuration
        if config:
            models_config = config.get("ollama", {}).get("models", {})
            self.author_model = models_config.get("author", "qwen3:8b")
            self.reviewer_model = models_config.get("reviewer", "qwen3:8b")
            self.fallback_reviewer = models_config.get("fallback_reviewer", "qwen3:8b")
            self.use_different_models = config.get("quality", {}).get("use_different_models", True)
            self.prefer_cloud = config.get("quality", {}).get("prefer_cloud_for_review", True)
            self.fallback_to_local = config.get("quality", {}).get("fallback_to_local_if_cloud_fails", True)
        else:
            # Default configuration
            self.author_model = "qwen3:8b"
            self.reviewer_model = "qwen3:8b"
            self.fallback_reviewer = "qwen3:8b"
            self.use_different_models = False
            self.prefer_cloud = False
            self.fallback_to_local = True
        
        logger.info(f"Quality Gate initialized:")
        logger.info(f"  Author model: {self.author_model}")
        logger.info(f"  Reviewer model: {self.reviewer_model}")
        logger.info(f"  Fallback reviewer: {self.fallback_reviewer}")
        logger.info(f"  Use different models: {self.use_different_models}")

    def _call_model(self, system_prompt: str, user_message: str, temperature: float = 0.7, 
                    model: Optional[str] = None) -> str:
        """Call model with optional model override."""
        target_model = model or self.author_model
        return self.ollama.generate(system_prompt, user_message, temperature, model=target_model)

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
        
        response = self._call_model(self.AUTHOR_SYSTEM_PROMPT, user_message, model=self.author_model)
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
        
        # Try reviewer model first
        reviewer_model = self.reviewer_model
        try:
            response = self._call_model(self.REVIEWER_SYSTEM_PROMPT, user_message, temperature=0.2, model=reviewer_model)
            logger.info(f"Reviewer response (first 200 chars): {response[:200]}")
        except Exception as e:
            logger.warning(f"Reviewer model {reviewer_model} failed: {e}")
            
            # Fallback to local model if enabled
            if self.fallback_to_local and reviewer_model != self.fallback_reviewer:
                logger.info(f"Falling back to {self.fallback_reviewer}")
                reviewer_model = self.fallback_reviewer
                response = self._call_model(self.REVIEWER_SYSTEM_PROMPT, user_message, temperature=0.2, model=reviewer_model)
                logger.info(f"Reviewer response (first 200 chars): {response[:200]}")
            else:
                raise
        
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
        review_data["reviewer_model"] = reviewer_model
        
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

# 5. Update app.py to pass config to QualityGate
print("[5/5] Updating app.py to pass config to QualityGate...")

app_content = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI SMM Manager - Sprint 12: Multi-Model Quality Gate
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
    logger.info("=== AI SMM Manager - Sprint 12: Multi-Model Quality Gate ===")
    
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
    
    # Load config
    config_path = ROOT_DIR / "config" / "config.yaml"
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        logger.info("Configuration loaded.")
    else:
        config = {}
        logger.warning("config.yaml not found, using defaults.")
    
    # Initialize Ollama client
    ollama = OllamaClient()
    
    # Initialize Quality Gate with config (multi-model support)
    quality_gate = LocalQualityGate(ollama_client=ollama, config=config)
    
    media_router = MediaTaskRouter(config)
    
    logger.info("All components initialized. Starting GUI...")
    
    app = QApplication(sys.argv)
    app.setApplicationName("AI SMM Manager")
    
    font = QFont("Arial", 10)
    app.setFont(font)
    
    window = QMainWindow()
    window.setWindowTitle("AI SMM Manager v2.0 (Sprint 12 - Multi-Model)")
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
        msg_handler.log("\\n[СТАРТ] Отправка запроса в Ollama...")
        msg_handler.log(f"[ИНФО] Автор: {quality_gate.author_model}")
        msg_handler.log(f"[ИНФО] Рецензент: {quality_gate.reviewer_model}")
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
        
        reviewer_model = result.get('review', {}).get('reviewer_model', 'unknown')
        
        if result.get("approved"):
            msg_handler.log(f"\\n[OK] КОНТЕНТ ОДОБРЕН РЕЦЕНЗЕНТОМ ({reviewer_model})!")
            c = result.get("content", {})
            msg_handler.log(f"Текст:\\n{c.get('content')}")
            msg_handler.log(f"Хэштеги: {', '.join(c.get('hashtags', []))}")
            msg_handler.log(f"Призыв к действию: {c.get('call_to_action')}")
        else:
            feedback = result.get('review', {}).get('final_feedback', 'Неизвестная причина')
            msg_handler.log(f"\\n[ОТКЛОНЕНО] КОНТЕНТ ОТКЛОНЕН ({reviewer_model}): {feedback}")
    
    btn = QPushButton("Сгенерировать и проверить")
    btn.setFont(QFont("Arial", 11, QFont.Bold))
    btn.clicked.connect(run_task)
    layout.addWidget(btn)
    
    container = QWidget()
    container.setLayout(layout)
    window.setCentralWidget(container)
    
    window.show()
    logger.info("GUI is running. Multi-model architecture is active.")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
'''

write_file("AI_SMM_Work_Architecture_A75/app.py", app_content)

print("\n=== Sprint 12 completed successfully ===")
print("Run START.bat to launch the GUI with multi-model support!")
print("\nConfiguration:")
print("- Author: qwen3:8b (local, fast)")
print("- Reviewer: gpt-oss:20b-cloud (cloud, high quality)")
print("- Fallback: qwen3:8b (if cloud unavailable)")
print("\nEdit config/config.yaml to change model roles.")