#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI SMM Manager - Path Fix: Use ASCII-only paths for image saving.
Run: python bootstrap_path_fix.py
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

print("\n=== AI SMM Manager - Path Fix ===\n")

print("[1/2] Updating local_image_generator.py with ASCII-safe paths...")

local_img_gen_content = '''"""
Local Image Generator v3 - Fixed path handling for Cyrillic/spacing issues.
"""
import logging
import torch
from typing import Optional, Dict, Any
from pathlib import Path
from PIL import Image

logger = logging.getLogger(__name__)

class LocalImageGenerator:
    def __init__(self, model_name: str = "runwayml/stable-diffusion-v1-5", 
                 device: Optional[str] = None, ollama_client=None):
        self.model_name = model_name
        self.pipe = None
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.vram_gb = 0
        self.ollama = ollama_client
        
        if self.device == "cuda":
            props = torch.cuda.get_device_properties(0)
            self.vram_gb = props.total_memory / (1024**3)
            logger.info(f"GPU detected: {torch.cuda.get_device_name(0)} ({self.vram_gb:.1f} GB VRAM)")
        
        if self.vram_gb < 6:
            logger.warning(f"Low VRAM ({self.vram_gb:.1f} GB). Image generation may be slow.")
    
    def translate_prompt(self, prompt: str) -> str:
        if not self.ollama:
            logger.warning("No Ollama client for translation, using prompt as-is")
            return prompt
        
        if any('\\u0400' <= c <= '\\u04FF' for c in prompt):
            logger.info("Detected Russian text, translating to English for SD...")
            
            translation_prompt = f"""Translate the following text to English. Return ONLY the English translation, no explanations:

{prompt}"""
            
            try:
                translated = self.ollama.generate(
                    "You are a professional translator. Translate text to English. Return only the translation.",
                    translation_prompt,
                    temperature=0.3,
                    model="qwen3:8b"
                )
                logger.info(f"Translated prompt: {translated[:80]}...")
                return translated.strip()
            except Exception as e:
                logger.warning(f"Translation failed: {e}, using original prompt")
        
        return prompt
    
    def _load_model(self):
        if self.pipe is not None:
            return
        
        try:
            from diffusers import StableDiffusionPipeline
            
            logger.info(f"Loading Stable Diffusion model: {self.model_name}")
            logger.info("First load may take 1-2 minutes (downloading ~4 GB)...")
            
            if self.device == "cuda":
                self.pipe = StableDiffusionPipeline.from_pretrained(
                    self.model_name,
                    torch_dtype=torch.float16,
                    safety_checker=None,
                    requires_safety_checker=False
                )
                
                self.pipe = self.pipe.to(self.device)
                
                if self.vram_gb < 8:
                    logger.info("Applying attention slicing for low VRAM...")
                    self.pipe.enable_attention_slicing()
                
                if self.vram_gb < 7:
                    logger.info("Applying CPU offload for very low VRAM...")
                    self.pipe.enable_model_cpu_offload()
            else:
                self.pipe = StableDiffusionPipeline.from_pretrained(
                    self.model_name,
                    safety_checker=None,
                    requires_safety_checker=False
                )
                self.pipe = self.pipe.to(self.device)
            
            logger.info("Stable Diffusion model loaded successfully")
        
        except Exception as e:
            logger.error(f"Failed to load Stable Diffusion model: {e}")
            self.pipe = None
            raise
    
    def generate_image(self, prompt: str, negative_prompt: str = "",
                      width: int = 512, height: int = 512,
                      num_inference_steps: int = 30,
                      guidance_scale: float = 7.5,
                      save_path: Optional[str] = None,
                      auto_translate: bool = True) -> Optional[Dict[str, Any]]:
        try:
            self._load_model()
        except Exception as e:
            logger.error(f"Cannot generate image: {e}")
            return None
        
        translated_prompt = prompt
        if auto_translate:
            translated_prompt = self.translate_prompt(prompt)
        
        try:
            logger.info(f"Generating image locally: {translated_prompt[:60]}...")
            logger.info(f"Parameters: {width}x{height}, {num_inference_steps} steps, guidance={guidance_scale}")
            
            image = self.pipe(
                prompt=translated_prompt,
                negative_prompt=negative_prompt if negative_prompt else "blurry, low quality, distorted, deformed",
                width=width,
                height=height,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale
            ).images[0]
            
            local_path = None
            if save_path:
                # FIX: Use short ASCII path to avoid Cyrillic/spacing issues
                save_path_obj = Path(save_path)
                save_path_obj.parent.mkdir(parents=True, exist_ok=True)
                
                # Convert to short path name if on Windows
                if os.name == 'nt':
                    try:
                        import ctypes
                        buffer = ctypes.create_unicode_buffer(260)
                        ctypes.windll.kernel32.GetShortPathNameW(str(save_path_obj), buffer, 260)
                        short_path = buffer.value
                        if short_path:
                            save_path_obj = Path(short_path)
                            logger.info(f"Using short path: {short_path}")
                    except Exception as e:
                        logger.warning(f"Failed to get short path: {e}")
                
                image.save(str(save_path_obj), "PNG")
                local_path = str(save_path_obj)
                logger.info(f"Image saved to {local_path}")
            
            return {
                "local_path": local_path,
                "prompt": prompt,
                "translated_prompt": translated_prompt,
                "negative_prompt": negative_prompt,
                "parameters": {
                    "width": width,
                    "height": height,
                    "steps": num_inference_steps,
                    "guidance_scale": guidance_scale
                },
                "source": "local-stable-diffusion"
            }
        
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            return None
    
    def is_available(self) -> bool:
        return torch.cuda.is_available() or self.device == "cpu"
    
    def get_info(self) -> Dict[str, Any]:
        return {
            "available": self.is_available(),
            "device": self.device,
            "vram_gb": self.vram_gb,
            "model": self.model_name,
            "recommended_size": "512x512" if self.vram_gb < 8 else "768x768"
        }
'''

write_file("AI_SMM_Work_Architecture_A75/local_image_generator.py", local_img_gen_content)

# 2. Update app.py to use temp directory for image saving
print("[2/2] Updating app.py with temp directory for images...")

app_content = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI SMM Manager - Step 4.5: Fixed path handling for image generation.
"""

import sys
import os
import logging
import sqlite3
import json
import tempfile
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
    logger.info("=== AI SMM Manager - Step 4.5: Path Fix ===")
    
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
    window.setWindowTitle("AI SMM Manager v2.0 (Step 4.5 - Path Fix)")
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
            
            # FIX: Use temp directory with ASCII-only path
            temp_dir = Path(tempfile.gettempdir()) / "ai_smm_images"
            temp_dir.mkdir(parents=True, exist_ok=True)
            image_path = str(temp_dir / f"{task_id}.png")
            
            if use_openai and openai_client.is_available():
                msg_handler.log("[ИНФО] Генерация через OpenAI GPT-Image...")
                image_result = openai_client.generate_image(image_prompt, save_path=image_path)
                if image_result:
                    result["image"] = image_result
                    msg_handler.log(f"[OK] OpenAI {image_result.get('model_used')}: {image_result.get('local_path', 'N/A')}")
                else:
                    msg_handler.log("[WARN] OpenAI генерация не удалась")
            
            elif use_local and local_img_gen.is_available():
                msg_handler.log("[ИНФО] Генерация через Stable Diffusion (может занять 30-60 сек)...")
                image_result = local_img_gen.generate_image(
                    image_prompt, 
                    save_path=image_path,
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
    logger.info("GUI is running. Path fix applied.")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
'''

write_file("AI_SMM_Work_Architecture_A75/app.py", app_content)

print("\n=== Path Fix Applied ===")
print("Run START.bat to test Stable Diffusion again.")
print("\nChanges:")
print("  - Images now saved to temp directory (ASCII-only path)")
print("  - Avoids Cyrillic/spacing issues in project folder name")
print("  - Uses Windows short path names when possible")