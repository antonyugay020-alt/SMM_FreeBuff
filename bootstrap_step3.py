#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI SMM Manager - Step 3: Full OpenAI Integration (DALL-E 3, Whisper, GPT-4o-mini).
Installs openai package, configures API key, and integrates into the app.
Run: python bootstrap_step3.py
"""

import os
import sys
import subprocess
import json
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

print("\n" + "="*70)
print("=== AI SMM Manager - Step 3: Full OpenAI Integration ===")
print("="*70 + "\n")

# 1. Install openai package
print("[1/5] Installing openai package...")
venv_pip = ROOT_DIR / "venv" / "Scripts" / "pip.exe"

try:
    result = subprocess.run(
        [str(venv_pip), "install", "openai", "--quiet"],
        capture_output=True, text=True, timeout=60
    )
    if result.returncode == 0:
        print("  [OK] openai package installed")
    else:
        print(f"  [ERROR] Failed to install: {result.stderr}")
        input("Press Enter to exit")
        sys.exit(1)
except Exception as e:
    print(f"  [ERROR] {e}")
    input("Press Enter to exit")
    sys.exit(1)

# 2. Ask for OpenAI API key
print("\n[2/5] OpenAI API Key Configuration")
print("-" * 70)

config_path = ROOT_DIR / "config" / "config.yaml"
if config_path.exists():
    with open(config_path, 'r', encoding='utf-8') as f:
        current_config = f.read()
    
    # Check if key already exists
    if 'api_key: "sk-' in current_config or "api_key: 'sk-" in current_config:
        print("  [INFO] OpenAI API key already configured in config.yaml")
        use_existing = input("  Use existing key? (y/n): ").strip().lower()
        if use_existing == 'y':
            print("  [OK] Using existing key")
        else:
            api_key = input("  Enter new OpenAI API key (sk-...): ").strip()
    else:
        api_key = input("  Enter your OpenAI API key (sk-...): ").strip()
else:
    api_key = input("  Enter your OpenAI API key (sk-...): ").strip()

if api_key and api_key.startswith("sk-"):
    # Update config.yaml with the key
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            config_content = f.read()
        
        # Replace empty key with actual key
        config_content = config_content.replace('api_key: ""', f'api_key: "{api_key}"')
        config_content = config_content.replace("api_key: ''", f"api_key: '{api_key}'")
        config_content = config_content.replace('enabled: false', 'enabled: true')
        
        with open(config_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(config_content)
        
        print("  [OK] API key saved to config.yaml")
        print("  [OK] OpenAI enabled in config")
    else:
        print("  [WARNING] config.yaml not found, key not saved")
else:
    print("  [SKIP] No valid API key provided. OpenAI will remain disabled.")
    print("  You can manually add it later to config/config.yaml")

# 3. Update openai_client.py with full implementation
print("\n[3/5] Updating openai_client.py with full implementation...")

openai_client_content = '''"""
OpenAI Client v2 - Full integration with DALL-E 3, Whisper, GPT-4o-mini.
"""
import logging
import requests
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

class OpenAIClient:
    def __init__(self, api_key: str = "", enabled: bool = False):
        self.api_key = api_key
        self.enabled = enabled and bool(api_key)
        self._client = None
        
        if self.enabled:
            try:
                import openai
                self._client = openai.OpenAI(api_key=api_key)
                logger.info("OpenAI client initialized successfully")
            except ImportError:
                logger.error("openai package not installed. Run: pip install openai")
                self.enabled = False
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                self.enabled = False
        else:
            logger.info("OpenAI client disabled (no API key or enabled=false)")
    
    def is_available(self) -> bool:
        return self.enabled and self._client is not None
    
    def generate_image(self, prompt: str, size: str = "1024x1024", quality: str = "hd",
                      save_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Generate image using DALL-E 3.
        
        Args:
            prompt: Image description
            size: Image size (1024x1024, 1792x1024, 1024x1792)
            quality: "standard" or "hd"
            save_path: Optional path to save the image locally
        
        Returns:
            Dict with "url", "revised_prompt", and optionally "local_path"
        """
        if not self.is_available():
            logger.warning("OpenAI not available for image generation")
            return None
        
        try:
            logger.info(f"Generating image with DALL-E 3: {prompt[:50]}...")
            
            response = self._client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size=size,
                quality=quality,
                n=1
            )
            
            image_url = response.data[0].url
            revised_prompt = response.data[0].revised_prompt
            
            result = {
                "url": image_url,
                "revised_prompt": revised_prompt
            }
            
            # Download and save locally if path provided
            if save_path:
                try:
                    img_response = requests.get(image_url, timeout=30)
                    img_response.raise_for_status()
                    
                    save_path_obj = Path(save_path)
                    save_path_obj.parent.mkdir(parents=True, exist_ok=True)
                    
                    with open(save_path_obj, 'wb') as f:
                        f.write(img_response.content)
                    
                    result["local_path"] = str(save_path_obj)
                    logger.info(f"Image saved to {save_path_obj}")
                except Exception as e:
                    logger.error(f"Failed to download image: {e}")
            
            return result
        
        except Exception as e:
            logger.error(f"DALL-E 3 generation failed: {e}")
            return None
    
    def transcribe_audio(self, audio_file_path: str, language: Optional[str] = None,
                        response_format: str = "text") -> Optional[str]:
        """
        Transcribe audio using Whisper API.
        
        Args:
            audio_file_path: Path to audio/video file
            language: Optional language code (e.g., "ru", "en")
            response_format: "text", "json", "srt", "verbose_json"
        
        Returns:
            Transcription text
        """
        if not self.is_available():
            logger.warning("OpenAI not available for transcription")
            return None
        
        try:
            logger.info(f"Transcribing audio: {audio_file_path}")
            
            with open(audio_file_path, "rb") as audio_file:
                kwargs = {
                    "model": "whisper-1",
                    "file": audio_file,
                    "response_format": response_format
                }
                if language:
                    kwargs["language"] = language
                
                response = self._client.audio.transcriptions.create(**kwargs)
            
            if response_format == "text":
                return response
            else:
                return response.text if hasattr(response, 'text') else str(response)
        
        except Exception as e:
            logger.error(f"Whisper transcription failed: {e}")
            return None
    
    def chat(self, system_prompt: str, user_message: str, 
             model: str = "gpt-4o-mini", temperature: float = 0.7) -> Optional[str]:
        """
        Chat completion using GPT-4o-mini (fast and cheap).
        
        Args:
            system_prompt: System prompt
            user_message: User message
            model: Model to use (gpt-4o-mini, gpt-4o, gpt-3.5-turbo)
            temperature: Generation temperature
        
        Returns:
            Response text
        """
        if not self.is_available():
            logger.warning("OpenAI not available for chat")
            return None
        
        try:
            response = self._client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=temperature,
                max_tokens=1000
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            logger.error(f"OpenAI chat failed: {e}")
            return None
    
    def generate_and_review(self, request: str, context: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        Combined generation and review using GPT-4o-mini.
        Faster alternative to local multi-model setup.
        
        Returns:
            Dict with "content", "review", "approved"
        """
        if not self.is_available():
            return None
        
        # Generate content
        author_prompt = """Ты — профессиональный SMM-специалист. Создай качественный контент.
ПРАВИЛА:
1. Строго следуй требованиям.
2. НЕ выдумывай факты, цены, услуги.
3. Отвечай в формате JSON:
{"content": "текст", "hashtags": ["#tag1"], "call_to_action": "призыв", "metadata": {"platform": "instagram"}}"""
        
        user_msg = request
        if context:
            user_msg += f"\\n\\nКонтекст: {json.dumps(context, ensure_ascii=False)}"
        
        content_response = self.chat(author_prompt, user_msg, temperature=0.7)
        
        if not content_response:
            return None
        
        # Parse content
        try:
            import json
            content = json.loads(content_response)
        except:
            content = {"content": content_response, "hashtags": [], "call_to_action": ""}
        
        # Review
        reviewer_prompt = """Ты — критический редактор. Проверь контент по критериям:
1. REQUIREMENTS: соответствие запросу
2. EVIDENCE: нет выдуманных фактов/цен
3. FORMAT_TONE: соответствие платформе

Отвечай в формате JSON:
{"approved": true/false, "overall_score": 0.0-1.0, "final_feedback": "комментарий"}"""
        
        review_msg = f"Запрос: {request}\\n\\nКонтент: {json.dumps(content, ensure_ascii=False)}"
        review_response = self.chat(reviewer_prompt, review_msg, temperature=0.2)
        
        try:
            review = json.loads(review_response)
        except:
            review = {"approved": False, "overall_score": 0.0, "final_feedback": "Parse error"}
        
        return {
            "content": content,
            "review": review,
            "approved": review.get("approved", False),
            "source": "openai-gpt4o-mini"
        }
'''

write_file("AI_SMM_Work_Architecture_A75/openai_client.py", openai_client_content)

# 4. Update local_quality_gate.py to support OpenAI as alternative
print("[4/5] Updating local_quality_gate.py with OpenAI support...")

lqg_content = '''"""
Local Quality Gate v6 - Hybrid: Local Ollama + OpenAI fallback.
Uses local models by default, OpenAI as optional alternative.
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

    REVIEWER_SYSTEM_PROMPT = """Ты — независимый критический редактор с аналитическим складом ума. Твоя задача — строго проверить контент по 4 критериям.

КРИТЕРИИ ПРОВЕРКИ:
1. REQUIREMENTS: Точное соответствие запросу пользователя (тональность, формат, длина).
2. COMPLETENESS: Все необходимые элементы присутствуют (текст, хэштеги, призыв к действию).
3. EVIDENCE: НЕТ ЛИ выдуманных фактов, цен, услуг или статистики? Если в запросе явно сказано "не выдумывай цены" — наличие любых цен в контенте автоматически означает ПРОВАЛ по этому критерию.
4. FORMAT_TONE: Соответствие формата и тональности целевой платформе (Instagram, VK, Telegram и т.д.).

ПРАВИЛА:
- Будь строгим, но справедливым.
- Если контент нарушает запрет на выдумывание фактов/цен — немедленно отклоняй (approved: false).
- Указывай конкретные замечания в feedback.
- Не придумывай требования, которых не было в запросе.

Отвечай СТРОГО в формате JSON:
{
  "reviews": [
    {"criterion": "REQUIREMENTS", "passed": true, "score": 0.9, "feedback": "Соответствует запросу", "suggestions": []},
    {"criterion": "COMPLETENESS", "passed": true, "score": 1.0, "feedback": "Все элементы на месте", "suggestions": []},
    {"criterion": "EVIDENCE", "passed": true, "score": 1.0, "feedback": "Факты не выдуманы", "suggestions": []},
    {"criterion": "FORMAT_TONE", "passed": true, "score": 0.95, "feedback": "Тон подходит для Instagram", "suggestions": []}
  ],
  "overall_score": 0.94,
  "approved": true,
  "final_feedback": "Контент одобрен. Все правила соблюдены."
}"""

    def __init__(self, ollama_client=None, openai_client=None, config: Optional[Dict[str, Any]] = None):
        self.min_passing_score = 0.7
        
        if ollama_client is None:
            from ollama_client import OllamaClient
            self.ollama = OllamaClient()
        else:
            self.ollama = ollama_client
        
        self.openai = openai_client
        
        # Load model configuration
        if config:
            models_config = config.get("ollama", {}).get("models", {})
            self.author_model = models_config.get("author", "qwen3:8b")
            self.reviewer_model = models_config.get("reviewer", "deepseek-r1:8b")
            self.fallback_author = models_config.get("fallback_author", "llama3.1:8b")
            self.fallback_reviewer = models_config.get("fallback_reviewer", "mistral:7b")
            self.use_different_models = config.get("quality", {}).get("use_different_models", True)
            self.prefer_openai = config.get("openai", {}).get("enabled", False)
        else:
            self.author_model = "qwen3:8b"
            self.reviewer_model = "deepseek-r1:8b"
            self.fallback_author = "llama3.1:8b"
            self.fallback_reviewer = "mistral:7b"
            self.use_different_models = True
            self.prefer_openai = False
        
        logger.info(f"Quality Gate initialized:")
        logger.info(f"  Author model: {self.author_model}")
        logger.info(f"  Reviewer model: {self.reviewer_model} (reasoning)")
        logger.info(f"  OpenAI enabled: {self.prefer_openai and self.openai is not None}")

    def _call_model(self, system_prompt: str, user_message: str, temperature: float = 0.7, 
                    model: Optional[str] = None, max_retries: int = 2, use_openai: bool = False) -> str:
        """Call model with automatic fallback."""
        
        # Try OpenAI first if enabled and requested
        if use_openai and self.openai and self.openai.is_available():
            try:
                logger.info("Using OpenAI GPT-4o-mini")
                response = self.openai.chat(system_prompt, user_message, model="gpt-4o-mini", temperature=temperature)
                if response:
                    return response
            except Exception as e:
                logger.warning(f"OpenAI failed, falling back to local: {e}")
        
        # Local Ollama with fallback
        target_model = model or self.author_model
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                return self.ollama.generate(system_prompt, user_message, temperature, model=target_model)
            except Exception as e:
                last_error = e
                logger.warning(f"Model {target_model} failed (attempt {attempt + 1}/{max_retries + 1}): {e}")
                
                if attempt < max_retries:
                    if target_model == self.author_model:
                        target_model = self.fallback_author
                        logger.info(f"Switching to fallback author: {target_model}")
                    elif target_model == self.reviewer_model:
                        target_model = self.fallback_reviewer
                        logger.info(f"Switching to fallback reviewer: {target_model}")
                    else:
                        break
        
        raise last_error

    def _extract_json(self, response: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from response."""
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        pattern = r'```json\\s*(.*?)\\s*```'
        json_match = re.search(pattern, response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
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
        
        # Try OpenAI first if enabled
        reviewer_model_used = self.reviewer_model
        try:
            response = self._call_model(self.REVIEWER_SYSTEM_PROMPT, user_message, temperature=0.2, 
                                       model=self.reviewer_model, use_openai=self.prefer_openai)
            logger.info(f"Reviewer response (first 200 chars): {response[:200]}")
        except Exception as e:
            logger.error(f"All reviewer models failed: {e}")
            return {
                "approved": False,
                "error": f"All reviewer models failed: {str(e)}",
                "final_feedback": "Ошибка рецензирования: все модели недоступны"
            }
        
        review_data = self._extract_json(response)
        
        if not review_data:
            logger.error(f"Failed to parse reviewer response: {response[:500]}")
            return {
                "approved": False,
                "error": "Invalid JSON from reviewer",
                "raw": response,
                "final_feedback": "Не удалось разобрать ответ рецензента"
            }
        
        if "reviews" not in review_data:
            review_data["reviews"] = []
        if "overall_score" not in review_data:
            review_data["overall_score"] = 0.0
        if "approved" not in review_data:
            review_data["approved"] = False
        if "final_feedback" not in review_data:
            review_data["final_feedback"] = "Обратная связь не предоставлена"
        
        approved = review_data.get("approved", False)
        for r in review_data.get("reviews", []):
            if not r.get("passed", True):
                approved = False
        
        if review_data.get("overall_score", 0) < self.min_passing_score:
            approved = False
        
        review_data["approved"] = approved
        review_data["reviewer_model"] = reviewer_model_used
        
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

# 5. Update app.py to integrate OpenAI and show image generation
print("[5/5] Updating app.py with OpenAI integration and image generation...")

app_content = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI SMM Manager - Step 3: Full OpenAI Integration with DALL-E 3 and Whisper.
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
    logger.info("=== AI SMM Manager - Step 3: OpenAI Integration ===")
    
    try:
        import yaml
        from PySide6.QtWidgets import QApplication, QMainWindow, QTextEdit, QPushButton, QVBoxLayout, QWidget, QLabel, QCheckBox
        from PySide6.QtCore import Qt, Signal, QObject
        from PySide6.QtGui import QFont
        from task_state_machine import TaskStateMachine, TaskState
        from local_quality_gate import LocalQualityGate
        from ollama_client import OllamaClient
        from openai_client import OpenAIClient
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
    
    # Initialize clients
    ollama = OllamaClient()
    
    openai_config = config.get("openai", {})
    openai_api_key = openai_config.get("api_key", "")
    openai_enabled = openai_config.get("enabled", False)
    openai_client = OpenAIClient(api_key=openai_api_key, enabled=openai_enabled)
    
    if openai_client.is_available():
        logger.info("OpenAI client initialized and enabled")
    else:
        logger.info("OpenAI client disabled (using local models only)")
    
    # Initialize Quality Gate with both clients
    quality_gate = LocalQualityGate(ollama_client=ollama, openai_client=openai_client, config=config)
    
    media_router = MediaTaskRouter(config)
    
    logger.info("All components initialized. Starting GUI...")
    
    app = QApplication(sys.argv)
    app.setApplicationName("AI SMM Manager")
    
    font = QFont("Arial", 10)
    app.setFont(font)
    
    window = QMainWindow()
    window.setWindowTitle("AI SMM Manager v2.0 (Step 3 - OpenAI)")
    window.resize(800, 600)
    
    layout = QVBoxLayout()
    
    label = QLabel("Введите задачу для SMM-менеджера:")
    label.setFont(QFont("Arial", 11, QFont.Bold))
    layout.addWidget(label)
    
    text_input = QTextEdit()
    text_input.setFont(QFont("Consolas", 10))
    text_input.setPlainText("Создай короткий пост для Instagram про утренний кофе в кофейне для фрилансеров. Тон: дружелюбный. Не выдумывай цены.")
    layout.addWidget(text_input)
    
    # Checkbox for image generation
    generate_image_cb = QCheckBox("Сгенерировать изображение (DALL-E 3)")
    generate_image_cb.setChecked(False)
    layout.addWidget(generate_image_cb)
    
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
        generate_image = generate_image_cb.isChecked()
        
        msg_handler.log("\\n[СТАРТ] Отправка запроса...")
        msg_handler.log(f"[ИНФО] Автор: {quality_gate.author_model}")
        msg_handler.log(f"[ИНФО] Рецензент: {quality_gate.reviewer_model}")
        if openai_client.is_available():
            msg_handler.log("[ИНФО] OpenAI: доступен (DALL-E 3, Whisper, GPT-4o-mini)")
        else:
            msg_handler.log("[ИНФО] OpenAI: отключён (только локальные модели)")
        msg_handler.log("[ИНФО] Генерация -> Проверка...")
        
        def work_fn(task_id):
            result = quality_gate.full_quality_gate(request, {"правило": "Не выдумывай цены"})
            
            # Generate image if requested
            if generate_image and openai_client.is_available():
                msg_handler.log("[ИНФО] Генерация изображения через DALL-E 3...")
                image_prompt = f"Professional social media image for: {request}"
                image_path = str(ROOT_DIR / "media" / "images" / f"{task_id}.png")
                image_result = openai_client.generate_image(image_prompt, save_path=image_path)
                
                if image_result:
                    result["image"] = image_result
                    msg_handler.log(f"[OK] Изображение сохранено: {image_result.get('local_path', 'N/A')}")
                else:
                    msg_handler.log("[WARN] Не удалось сгенерировать изображение")
            
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
            
            if "image" in result:
                img = result["image"]
                msg_handler.log(f"\\n[ИЗОБРАЖЕНИЕ] Сгенерировано DALL-E 3")
                msg_handler.log(f"Путь: {img.get('local_path', 'N/A')}")
                msg_handler.log(f"URL: {img.get('url', 'N/A')}")
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
    logger.info("GUI is running. OpenAI integration is active.")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
'''

write_file("AI_SMM_Work_Architecture_A75/app.py", app_content)

# 6. Summary
print("\n" + "="*70)
print("=== Step 3 Summary ===")
print("="*70)
print("\nCompleted:")
print("  [OK] Installed openai package")
if api_key and api_key.startswith("sk-"):
    print("  [OK] OpenAI API key configured and enabled")
else:
    print("  [SKIP] OpenAI API key not configured (can be added later)")
print("  [OK] Updated openai_client.py with full implementation")
print("  [OK] Updated local_quality_gate.py with OpenAI support")
print("  [OK] Updated app.py with image generation checkbox")

print("\nFeatures added:")
print("  - DALL-E 3: Generate images for posts")
print("  - Whisper API: Transcribe audio/video")
print("  - GPT-4o-mini: Fast backup reviewer/author")
print("  - GUI checkbox: 'Generate image (DALL-E 3)'")

print("\nNext: Run START.bat to test with OpenAI integration.")
print("="*70 + "\n")