#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI SMM Manager - Final Fix: Add save_path parameter to openai_client.py
and update app.py to use consistent interface.
Run: python bootstrap_final_fix.py
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

print("\n=== AI SMM Manager - Final Fix: Unified Interface ===\n")

# 1. Update openai_client.py with save_path parameter
print("[1/2] Updating openai_client.py with save_path parameter...")

openai_client_content = '''"""
OpenAI Client v3.3 - Unified interface with save_path parameter.
"""
import logging
import requests
import base64
import time
from typing import Optional, Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)

IMAGE_MODELS_PRIORITY = [
    "gpt-image-2.5-sunburst",
    "gpt-image-2.5-flare",
    "gpt-image-2",
    "gpt-image-1.5",
]

class OpenAIClient:
    def __init__(self, api_key: str = "", enabled: bool = False, 
                 storage_dir: Optional[str] = None):
        self.api_key = api_key
        self.enabled = enabled and bool(api_key)
        self._client = None
        self._available_models: Optional[List[str]] = None
        self._image_model: Optional[str] = None
        
        # Unified storage directory
        if storage_dir:
            self.storage_dir = Path(storage_dir)
        else:
            self.storage_dir = Path(__file__).resolve().parent.parent / "media" / "images"
        
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"OpenAI image storage: {self.storage_dir}")
        
        if self.enabled:
            try:
                import openai
                self._client = openai.OpenAI(api_key=api_key)
                logger.info("OpenAI client initialized successfully")
                self._discover_models()
            except ImportError:
                logger.error("openai package not installed. Run: pip install openai")
                self.enabled = False
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                self.enabled = False
        else:
            logger.info("OpenAI client disabled (no API key or enabled=false)")
    
    def _discover_models(self):
        if not self._client:
            return
        
        try:
            models_response = self._client.models.list()
            self._available_models = [m.id for m in models_response.data]
            logger.info(f"Found {len(self._available_models)} OpenAI models")
            
            for model in IMAGE_MODELS_PRIORITY:
                if model in self._available_models:
                    self._image_model = model
                    logger.info(f"Selected image model: {model}")
                    break
            
            if not self._image_model:
                logger.warning("No GPT-Image models available in your account")
        
        except Exception as e:
            logger.error(f"Failed to discover models: {e}")
    
    def is_available(self) -> bool:
        return self.enabled and self._client is not None
    
    def get_image_model(self) -> Optional[str]:
        return self._image_model
    
    def generate_image(self, prompt: str, size: str = "1024x1024",
                      save_path: Optional[str] = None,  # Backward compatibility
                      filename: Optional[str] = None,
                      model: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Generate image and save to unified storage.
        
        Args:
            prompt: Image description
            save_path: Legacy parameter (ignored, uses filename instead)
            filename: Optional filename (auto-generated if None)
            model: Override model (uses best available if None)
        """
        if not self.is_available():
            logger.warning("OpenAI not available for image generation")
            return None
        
        target_model = model or self._image_model
        if not target_model:
            logger.error("No image model available")
            return None
        
        try:
            logger.info(f"Generating image with {target_model}: {prompt[:60]}...")
            
            response = self._client.images.generate(
                model=target_model,
                prompt=prompt,
                size=size,
                n=1
            )
            
            image_data = response.data[0]
            
            # Generate filename if not provided
            if not filename:
                filename = f"openai_{int(time.time())}.png"
            
            save_path_obj = self.storage_dir / filename
            save_path_obj.parent.mkdir(parents=True, exist_ok=True)
            
            result = {
                "model_used": target_model,
                "source": "openai-gpt-image",
                "filename": filename
            }
            
            # Handle base64 response
            if hasattr(image_data, 'b64_json') and image_data.b64_json:
                logger.info("Received base64 image data")
                image_bytes = base64.b64decode(image_data.b64_json)
                
                with open(save_path_obj, 'wb') as f:
                    f.write(image_bytes)
                
                result["local_path"] = str(save_path_obj)
                logger.info(f"Image saved to {save_path_obj} ({len(image_bytes)} bytes)")
                return result
            
            # Handle URL response
            elif hasattr(image_data, 'url') and image_data.url:
                logger.info("Received image URL")
                result["url"] = image_data.url
                
                try:
                    img_response = requests.get(image_data.url, timeout=60)
                    img_response.raise_for_status()
                    
                    with open(save_path_obj, 'wb') as f:
                        f.write(img_response.content)
                    
                    result["local_path"] = str(save_path_obj)
                    logger.info(f"Image downloaded and saved to {save_path_obj}")
                    return result
                except Exception as e:
                    logger.error(f"Failed to download image: {e}")
                    return None
            
            else:
                logger.error("Unknown image response format")
                return None
        
        except Exception as e:
            logger.error(f"Image generation with {target_model} failed: {e}")
            
            # Try fallback models
            for fallback in IMAGE_MODELS_PRIORITY:
                if fallback == target_model:
                    continue
                if fallback in (self._available_models or []):
                    logger.info(f"Trying fallback model: {fallback}")
                    return self.generate_image(prompt, size, save_path, filename, model=fallback)
            
            return None
    
    def transcribe_audio(self, audio_file_path: str, language: Optional[str] = None,
                        response_format: str = "text") -> Optional[str]:
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
            
            return response if response_format == "text" else (response.text if hasattr(response, 'text') else str(response))
        
        except Exception as e:
            logger.error(f"Whisper transcription failed: {e}")
            return None
    
    def chat(self, system_prompt: str, user_message: str, 
             model: str = "gpt-4o-mini", temperature: float = 0.7) -> Optional[str]:
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
'''

write_file("AI_SMM_Work_Architecture_A75/openai_client.py", openai_client_content)

# 2. Update app.py to use consistent interface (no save_path, only filename)
print("[2/2] Updating app.py with consistent interface...")

app_content = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI SMM Manager - Final: Consistent interface for image generation.
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
    logger.info("=== AI SMM Manager - Final: Consistent Interface ===")
    
    try:
        import yaml
        from PySide6.QtWidgets import QApplication, QMainWindow, QTextEdit, QPushButton, QVBoxLayout, QWidget, QLabel, QCheckBox, QGroupBox
        from PySide6.QtCore import Qt, Signal, QObject
        from PySide6.QtGui import QFont
        from task_state_machine import TaskStateMachine, TaskState
        from local_quality_gate import LocalQualityGate
        from ollama_client import OllamaClient
        from openai_client import OpenAIClient
        from local_image_generator import LocalImageGenerator
        from qt_worker_lifecycle import WorkerManager
        from media_task_router import MediaTaskRouter
    except ImportError as e:
        logger.error(f"Missing dependency: {e}")
        sys.exit(1)
    
    conn = sqlite3.connect(str(ROOT_DIR / "data" / "ai_smm_manager.db"))
    conn.execute("PRAGMA journal_mode=WAL")
    
    state_machine = TaskStateMachine(conn, "default_project")
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
    local_img_info = local_img_gen.get_info()
    
    if openai_client.is_available():
        img_model = openai_client.get_image_model()
        logger.info(f"OpenAI client initialized. Image model: {img_model}")
    else:
        logger.info("OpenAI client disabled (using local models only)")
    
    logger.info(f"Local image generator: {local_img_info}")
    
    quality_gate = LocalQualityGate(ollama_client=ollama, openai_client=openai_client, config=config)
    media_router = MediaTaskRouter(config)
    
    logger.info("All components initialized. Starting GUI...")
    
    app = QApplication(sys.argv)
    app.setApplicationName("AI SMM Manager")
    
    font = QFont("Arial", 10)
    app.setFont(font)
    
    window = QMainWindow()
    window.setWindowTitle("AI SMM Manager v2.0 (Final)")
    window.resize(800, 650)
    
    layout = QVBoxLayout()
    
    label = QLabel("Введите задачу для SMM-менеджера:")
    label.setFont(QFont("Arial", 11, QFont.Bold))
    layout.addWidget(label)
    
    text_input = QTextEdit()
    text_input.setFont(QFont("Consolas", 10))
    text_input.setPlainText("Создай короткий пост для Instagram про утренний кофе в кофейне для фрилансеров. Тон: дружелюбный. Не выдумывай цены.")
    layout.addWidget(text_input)
    
    img_group = QGroupBox("Генерация изображения")
    img_layout = QVBoxLayout()
    
    use_openai_cb = QCheckBox(f"OpenAI GPT-Image ({openai_client.get_image_model() or 'недоступно'})")
    use_openai_cb.setChecked(openai_client.is_available())
    use_openai_cb.setEnabled(openai_client.is_available())
    img_layout.addWidget(use_openai_cb)
    
    use_local_sd_cb = QCheckBox(f"Stable Diffusion локально ({local_img_info['device']}, {local_img_info['vram_gb']:.1f} GB VRAM)")
    use_local_sd_cb.setChecked(not openai_client.is_available())
    use_local_sd_cb.setEnabled(local_img_gen.is_available())
    img_layout.addWidget(use_local_sd_cb)
    
    auto_translate_cb = QCheckBox("Автоперевод промпта RU -> EN (для SD)")
    auto_translate_cb.setChecked(True)
    img_layout.addWidget(auto_translate_cb)
    
    img_group.setLayout(img_layout)
    layout.addWidget(img_group)
    
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
        use_openai = use_openai_cb.isChecked()
        use_local = use_local_sd_cb.isChecked()
        auto_translate = auto_translate_cb.isChecked()
        
        msg_handler.log("\\n[СТАРТ] Отправка запроса...")
        msg_handler.log(f"[ИНФО] Автор: {quality_gate.author_model}")
        msg_handler.log(f"[ИНФО] Рецензент: {quality_gate.reviewer_model}")
        
        if use_openai and openai_client.is_available():
            msg_handler.log(f"[ИНФО] Изображение: {openai_client.get_image_model()} (облако)")
        elif use_local and local_img_gen.is_available():
            msg_handler.log(f"[ИНФО] Изображение: Stable Diffusion локально ({local_img_info['device']})")
            if auto_translate:
                msg_handler.log("[ИНФО] Автоперевод промпта: включён")
        else:
            msg_handler.log("[ИНФО] Изображение: отключено")
        
        msg_handler.log("[ИНФО] Генерация -> Проверка...")
        
        def work_fn(task_id):
            result = quality_gate.full_quality_gate(request, {"правило": "Не выдумывай цены"})
            
            image_prompt = f"Professional social media photo for Instagram: {request}. High quality, vibrant colors, good lighting."
            
            if use_openai and openai_client.is_available():
                msg_handler.log("[ИНФО] Генерация через OpenAI GPT-Image...")
                # Use filename parameter instead of save_path
                image_result = openai_client.generate_image(image_prompt, filename=f"{task_id}.png")
                if image_result:
                    result["image"] = image_result
                    msg_handler.log(f"[OK] OpenAI {image_result.get('model_used')}: {image_result.get('local_path', 'N/A')}")
                else:
                    msg_handler.log("[WARN] OpenAI генерация не удалась")
            
            elif use_local and local_img_gen.is_available():
                msg_handler.log("[ИНФО] Генерация через Stable Diffusion (может занять 30-60 сек)...")
                # Use filename parameter instead of save_path
                image_result = local_img_gen.generate_image(
                    image_prompt, 
                    filename=f"{task_id}.png",
                    auto_translate=auto_translate
                )
                if image_result:
                    result["image"] = image_result
                    msg_handler.log(f"[OK] SD локально: {image_result.get('local_path', 'N/A')}")
                    if image_result.get('translated_prompt'):
                        msg_handler.log(f"[ИНФО] Переведённый промпт: {image_result['translated_prompt'][:80]}...")
                else:
                    msg_handler.log("[WARN] Stable Diffusion не сработал")
            
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
                source = img.get('source', 'unknown')
                msg_handler.log(f"\\n[ИЗОБРАЖЕНИЕ] Источник: {source}")
                msg_handler.log(f"Путь: {img.get('local_path', 'N/A')}")
                if 'url' in img:
                    msg_handler.log(f"URL: {img['url']}")
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
    logger.info("GUI is running. Final interface applied.")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
'''

write_file("AI_SMM_Work_Architecture_A75/app.py", app_content)

print("\n" + "="*70)
print("=== Final Fix Applied ===")
print("="*70)
print("\nChanges:")
print("  [OK] openai_client.py: Added save_path parameter (backward compatibility)")
print("  [OK] app.py: Uses filename parameter instead of save_path")
print("  [OK] Both generators now use consistent interface")

print("\nAll images saved to:")
print(f"  {ROOT_DIR / 'media' / 'images'}")

print("\nNext: Run START.bat to test both image generators.")
print("="*70 + "\n")