#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI SMM Manager - Step 5 Fix 2: Handle Whisper response properly.
Run: python bootstrap_step5_fix2.py
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

print("\n=== AI SMM Manager - Step 5 Fix 2: Whisper Response Handling ===\n")

print("[1/2] Updating openai_client.py with better response handling...")

openai_client_content = '''"""
OpenAI Client v3.5 - Better Whisper response handling.
"""
import logging
import requests
import base64
import time
import json
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
                      save_path: Optional[str] = None,
                      filename: Optional[str] = None,
                      model: Optional[str] = None) -> Optional[Dict[str, Any]]:
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
            
            if not filename:
                filename = f"openai_{int(time.time())}.png"
            
            save_path_obj = self.storage_dir / filename
            save_path_obj.parent.mkdir(parents=True, exist_ok=True)
            
            result = {
                "model_used": target_model,
                "source": "openai-gpt-image",
                "filename": filename
            }
            
            if hasattr(image_data, 'b64_json') and image_data.b64_json:
                logger.info("Received base64 image data")
                image_bytes = base64.b64decode(image_data.b64_json)
                
                with open(save_path_obj, 'wb') as f:
                    f.write(image_bytes)
                
                result["local_path"] = str(save_path_obj)
                logger.info(f"Image saved to {save_path_obj} ({len(image_bytes)} bytes)")
                return result
            
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
            
            for fallback in IMAGE_MODELS_PRIORITY:
                if fallback == target_model:
                    continue
                if fallback in (self._available_models or []):
                    logger.info(f"Trying fallback model: {fallback}")
                    return self.generate_image(prompt, size, save_path, filename, model=fallback)
            
            return None
    
    def transcribe_audio(self, audio_file_path: str, language: Optional[str] = None,
                        response_format: str = "verbose_json") -> Optional[Dict[str, Any]]:
        """
        Transcribe audio using Whisper API with segments.
        Returns dict with text, segments, language.
        """
        if not self.is_available():
            logger.warning("OpenAI not available for transcription")
            return None
        
        try:
            logger.info(f"Transcribing audio: {audio_file_path}")
            logger.info(f"Response format: {response_format}")
            
            with open(audio_file_path, "rb") as audio_file:
                kwargs = {
                    "model": "whisper-1",
                    "file": audio_file,
                    "response_format": response_format
                }
                if language:
                    kwargs["language"] = language
                
                response = self._client.audio.transcriptions.create(**kwargs)
            
            # Log response type for debugging
            logger.info(f"Response type: {type(response)}")
            logger.info(f"Response attributes: {dir(response)}")
            
            # Handle different response formats
            if response_format == "verbose_json":
                # Try to get text as string
                text = ""
                if hasattr(response, 'text'):
                    text = str(response.text) if response.text else ""
                elif isinstance(response, dict):
                    text = response.get('text', '')
                else:
                    text = str(response)
                
                # Try to get segments
                segments = []
                if hasattr(response, 'segments'):
                    segments = response.segments if response.segments else []
                elif isinstance(response, dict):
                    segments = response.get('segments', [])
                
                # Try to get language
                lang = "unknown"
                if hasattr(response, 'language'):
                    lang = response.language if response.language else (language or "unknown")
                elif isinstance(response, dict):
                    lang = response.get('language', language or "unknown")
                
                logger.info(f"Transcription text length: {len(text)}")
                logger.info(f"Segments count: {len(segments)}")
                logger.info(f"Language: {lang}")
                
                return {
                    "text": text,
                    "segments": segments,
                    "language": lang
                }
            else:
                # Simple text response
                text = str(response) if response else ""
                return {
                    "text": text,
                    "segments": [],
                    "language": language or "unknown"
                }
        
        except Exception as e:
            logger.error(f"Whisper transcription failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
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

# 2. Update app.py with better error handling
print("[2/2] Updating app.py with better error handling...")

app_content = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI SMM Manager - Step 5 Fix 2: Better video processing error handling.
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
    logger.info("=== AI SMM Manager - Step 5 Fix 2 ===")
    
    try:
        import yaml
        from PySide6.QtWidgets import QApplication, QMainWindow, QTextEdit, QPushButton, QVBoxLayout, QWidget, QLabel, QCheckBox, QGroupBox, QTabWidget, QComboBox, QFileDialog
        from PySide6.QtCore import Qt, Signal, QObject
        from PySide6.QtGui import QFont
        from task_state_machine import TaskStateMachine, TaskState
        from local_quality_gate import LocalQualityGate
        from ollama_client import OllamaClient
        from openai_client import OpenAIClient
        from local_image_generator import LocalImageGenerator
        from video_processor import VideoProcessor
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
    video_processor = VideoProcessor(whisper_model="base", openai_client=openai_client)
    
    quality_gate = LocalQualityGate(ollama_client=ollama, openai_client=openai_client, config=config)
    media_router = MediaTaskRouter(config)
    
    logger.info("All components initialized. Starting GUI...")
    
    app = QApplication(sys.argv)
    app.setApplicationName("AI SMM Manager")
    
    font = QFont("Arial", 10)
    app.setFont(font)
    
    window = QMainWindow()
    window.setWindowTitle("AI SMM Manager v2.0 (Step 5 Fix 2)")
    window.resize(900, 700)
    
    tabs = QTabWidget()
    
    # === TAB 1: Text Generation ===
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
        
        text_msg_handler.log("\\n[СТАРТ] Отправка запроса...")
        text_msg_handler.log(f"[ИНФО] Автор: {quality_gate.author_model}")
        text_msg_handler.log(f"[ИНФО] Рецензент: {quality_gate.reviewer_model}")
        
        def work_fn(task_id):
            result = quality_gate.full_quality_gate(request, {"правило": "Не выдумывай цены"})
            
            image_prompt = f"Professional social media photo for Instagram: {request}. High quality, vibrant colors."
            
            if use_openai and openai_client.is_available():
                text_msg_handler.log("[ИНФО] Генерация через OpenAI GPT-Image...")
                image_result = openai_client.generate_image(image_prompt, filename=f"{task_id}.png")
                if image_result:
                    result["image"] = image_result
                    text_msg_handler.log(f"[OK] OpenAI: {image_result.get('local_path', 'N/A')}")
            
            elif use_local and local_img_gen.is_available():
                text_msg_handler.log("[ИНФО] Генерация через Stable Diffusion...")
                image_result = local_img_gen.generate_image(image_prompt, filename=f"{task_id}.png", auto_translate=auto_translate)
                if image_result:
                    result["image"] = image_result
                    text_msg_handler.log(f"[OK] SD: {image_result.get('local_path', 'N/A')}")
            
            return result
        
        worker = worker_manager.create_worker("text_task_001", "default_project", work_fn)
        worker.finished_success_json.connect(lambda tid, json_str: on_text_success(tid, json_str))
        worker.finished_error.connect(lambda tid, err: text_msg_handler.log(f"[ОШИБКА] {err}"))
    
    def on_text_success(task_id, json_result):
        try:
            result = json.loads(json_result)
        except json.JSONDecodeError as e:
            text_msg_handler.log(f"[ОШИБКА] Не удалось разобрать результат: {e}")
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
    
    text_btn = QPushButton("Сгенерировать текст и изображение")
    text_btn.setFont(QFont("Arial", 11, QFont.Bold))
    text_btn.clicked.connect(run_text_task)
    text_layout.addWidget(text_btn)
    
    text_tab.setLayout(text_layout)
    tabs.addTab(text_tab, "Текст + Изображение")
    
    # === TAB 2: Video Processing ===
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
        
        use_openai_whisper = use_openai_whisper_cb.isChecked()
        burn_subtitles = burn_subtitles_cb.isChecked()
        platform_idx = platform_combo.currentIndex()
        platforms = ["instagram_reels", "tiktok", "youtube_shorts", "youtube_video", "instagram_post"]
        platform = platforms[platform_idx]
        
        language_map = {0: "ru", 1: "en", 2: None}
        language = language_map[language_combo.currentIndex()]
        
        video_msg_handler.log(f"\\n[СТАРТ] Обработка видео: {file_path}")
        video_msg_handler.log(f"[ИНФО] Платформа: {platform}")
        video_msg_handler.log(f"[ИНФО] Язык: {language or 'авто'}")
        
        def work_fn(task_id):
            results = {}
            
            # Step 1: Transcribe
            video_msg_handler.log("[1/3] Транскрипция...")
            transcript = video_processor.transcribe(file_path, language=language, use_openai=use_openai_whisper)
            
            if not transcript:
                video_msg_handler.log("[ОШИБКА] Транскрипция не удалась")
                return {"error": "Transcription failed"}
            
            results["transcript"] = transcript
            
            # Safely get text
            text = transcript.get('text', '')
            if not isinstance(text, str):
                text = str(text) if text else ""
            
            video_msg_handler.log(f"[OK] Транскрипция завершена ({len(text)} символов)")
            
            # Show first 200 chars safely
            preview = text[:200] if len(text) > 200 else text
            video_msg_handler.log(f"Текст: {preview}...")
            
            # Step 2: Generate SRT
            segments = transcript.get('segments', [])
            video_msg_handler.log(f"[ИНФО] Сегментов: {len(segments)}")
            
            if segments:
                video_msg_handler.log("[2/3] Генерация субтитров...")
                srt_path = str(ROOT_DIR / "media" / "videos" / f"{task_id}.srt")
                Path(srt_path).parent.mkdir(parents=True, exist_ok=True)
                
                if video_processor.generate_srt(segments, srt_path):
                    results["srt_path"] = srt_path
                    video_msg_handler.log(f"[OK] SRT сохранён: {srt_path}")
                else:
                    video_msg_handler.log("[WARN] Не удалось создать SRT")
            else:
                video_msg_handler.log("[WARN] Нет сегментов для субтитров (используйте локальный Whisper для сегментов)")
            
            # Step 3: Export for platform
            video_msg_handler.log(f"[3/3] Экспорт для {platform}...")
            output_path = str(ROOT_DIR / "media" / "videos" / f"{task_id}_{platform}.mp4")
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            if burn_subtitles and results.get("srt_path"):
                temp_path = str(ROOT_DIR / "media" / "videos" / f"{task_id}_temp.mp4")
                if video_processor.burn_subtitles(file_path, results["srt_path"], temp_path):
                    if video_processor.export_for_platform(temp_path, platform, output_path):
                        results["output_path"] = output_path
                        video_msg_handler.log(f"[OK] Видео экспортировано: {output_path}")
                    else:
                        video_msg_handler.log("[ОШИБКА] Экспорт не удался")
                else:
                    video_msg_handler.log("[ОШИБКА] Наложение субтитров не удалось")
            else:
                if video_processor.export_for_platform(file_path, platform, output_path):
                    results["output_path"] = output_path
                    video_msg_handler.log(f"[OK] Видео экспортировано: {output_path}")
                else:
                    video_msg_handler.log("[ОШИБКА] Экспорт не удался")
            
            return results
        
        worker = worker_manager.create_worker("video_task_001", "default_project", work_fn)
        worker.finished_success_json.connect(lambda tid, json_str: on_video_success(tid, json_str))
        worker.finished_error.connect(lambda tid, err: video_msg_handler.log(f"[ОШИБКА] {err}"))
    
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
            video_msg_handler.log(f"\\n[ГОТОВО] Видео сохранено: {result['output_path']}")
        else:
            video_msg_handler.log("\\n[ОШИБКА] Видео не было экспортировано")
    
    video_btn = QPushButton("Обработать видео")
    video_btn.setFont(QFont("Arial", 11, QFont.Bold))
    video_btn.clicked.connect(run_video_task)
    video_layout.addWidget(video_btn)
    
    video_tab.setLayout(video_layout)
    tabs.addTab(video_tab, "Видео")
    
    main_layout = QVBoxLayout()
    main_layout.addWidget(tabs)
    
    container = QWidget()
    container.setLayout(main_layout)
    window.setCentralWidget(container)
    
    window.show()
    logger.info("GUI is running. Video pipeline fix 2 is active.")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
'''

write_file("AI_SMM_Work_Architecture_A75/app.py", app_content)

print("\n=== Fix 2 Applied ===")
print("Changes:")
print("  - Better Whisper response handling (type checking)")
print("  - Safe string slicing with type verification")
print("  - Detailed logging of response structure")
print("  - Fallback if segments not available")
print("\nRun START.bat to test video processing again.")