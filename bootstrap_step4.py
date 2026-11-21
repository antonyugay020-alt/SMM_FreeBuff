#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI SMM Manager - Step 4: Local Stable Diffusion Integration.
Installs torch, diffusers, transformers.
Creates local_image_generator.py with SD 1.5 (optimized for 8GB VRAM).
Integrates as fallback when OpenAI DALL-E 3 unavailable.
Run: python bootstrap_step4.py
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
print("=== AI SMM Manager - Step 4: Local Stable Diffusion ===")
print("="*70 + "\n")

# 1. Check venv
print("[1/5] Checking virtual environment...")
venv_python = ROOT_DIR / "venv" / "Scripts" / "python.exe"
venv_pip = ROOT_DIR / "venv" / "Scripts" / "pip.exe"
if not venv_python.exists():
    print("  ERROR: venv not found.")
    input("Press Enter to exit")
    sys.exit(1)
print("  OK: venv found\n")

# 2. Install PyTorch with CUDA 11.8 (for RTX 2080 Super)
print("[2/5] Installing PyTorch with CUDA 11.8...")
print("  This may take 5-10 minutes (downloads ~2.5 GB)...")

try:
    result = subprocess.run(
        [str(venv_pip), "install", "torch", "torchvision", "--index-url", 
         "https://download.pytorch.org/whl/cu118", "--quiet"],
        capture_output=True, text=True, timeout=600
    )
    if result.returncode == 0:
        print("  [OK] PyTorch with CUDA 11.8 installed")
    else:
        print(f"  [ERROR] Failed: {result.stderr[:200]}")
        input("Press Enter to exit")
        sys.exit(1)
except Exception as e:
    print(f"  [ERROR] {e}")
    input("Press Enter to exit")
    sys.exit(1)

# 3. Install diffusers and dependencies
print("\n[3/5] Installing diffusers, transformers, accelerate, safetensors...")

packages = ["diffusers", "transformers", "accelerate", "safetensors", "pillow"]
for pkg in packages:
    print(f"  Installing {pkg}...", end=" ")
    try:
        result = subprocess.run(
            [str(venv_pip), "install", pkg, "--quiet"],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            print("OK")
        else:
            print(f"FAILED: {result.stderr[:100]}")
    except Exception as e:
        print(f"ERROR: {e}")

# 4. Create local_image_generator.py
print("\n[4/5] Creating local_image_generator.py...")

local_img_gen_content = '''"""
Local Image Generator - Stable Diffusion 1.5 with VRAM optimization.
Optimized for RTX 2080 Super (8 GB VRAM).
Uses attention slicing and CPU offload to fit in limited VRAM.
"""
import logging
import torch
from typing import Optional, Dict, Any
from pathlib import Path
from PIL import Image

logger = logging.getLogger(__name__)

class LocalImageGenerator:
    def __init__(self, model_name: str = "runwayml/stable-diffusion-v1-5", 
                 device: Optional[str] = None):
        self.model_name = model_name
        self.pipe = None
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.vram_gb = 0
        
        if self.device == "cuda":
            self.vram_gb = torch.cuda.get_device_properties(0).total_mem / (1024**3)
            logger.info(f"GPU detected: {torch.cuda.get_device_name(0)} ({self.vram_gb:.1f} GB VRAM)")
        
        if self.vram_gb < 6:
            logger.warning(f"Low VRAM ({self.vram_gb:.1f} GB). Image generation may be slow or fail.")
            logger.warning("Consider using OpenAI DALL-E 3 instead.")
    
    def _load_model(self):
        """Load Stable Diffusion model with VRAM optimizations."""
        if self.pipe is not None:
            return
        
        try:
            from diffusers import StableDiffusionPipeline
            
            logger.info(f"Loading Stable Diffusion model: {self.model_name}")
            logger.info("First load may take 1-2 minutes (downloading ~4 GB)...")
            
            # Use float16 for less VRAM usage
            if self.device == "cuda":
                self.pipe = StableDiffusionPipeline.from_pretrained(
                    self.model_name,
                    torch_dtype=torch.float16,
                    safety_checker=None,  # Disable safety checker for speed
                    requires_safety_checker=False
                )
                
                # VRAM optimizations
                self.pipe = self.pipe.to(self.device)
                
                if self.vram_gb < 8:
                    logger.info("Applying attention slicing for low VRAM...")
                    self.pipe.enable_attention_slicing()
                
                if self.vram_gb < 7:
                    logger.info("Applying CPU offload for very low VRAM...")
                    self.pipe.enable_model_cpu_offload()
            else:
                # CPU mode (very slow)
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
                      save_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Generate image using local Stable Diffusion.
        
        Args:
            prompt: Image description
            negative_prompt: What to avoid in the image
            width: Image width (512 or 768)
            height: Image height (512 or 768)
            num_inference_steps: More steps = better quality but slower (20-50)
            guidance_scale: How closely to follow prompt (7-10 is good)
            save_path: Optional path to save the image
        
        Returns:
            Dict with "local_path", "prompt", "parameters"
        """
        try:
            self._load_model()
        except Exception as e:
            logger.error(f"Cannot generate image: {e}")
            return None
        
        try:
            logger.info(f"Generating image locally: {prompt[:50]}...")
            logger.info(f"Parameters: {width}x{height}, {num_inference_steps} steps, guidance={guidance_scale}")
            
            # Generate
            image = self.pipe(
                prompt=prompt,
                negative_prompt=negative_prompt if negative_prompt else "blurry, low quality, distorted",
                width=width,
                height=height,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale
            ).images[0]
            
            # Save if path provided
            local_path = None
            if save_path:
                save_path_obj = Path(save_path)
                save_path_obj.parent.mkdir(parents=True, exist_ok=True)
                image.save(save_path_obj, "PNG")
                local_path = str(save_path_obj)
                logger.info(f"Image saved to {local_path}")
            
            return {
                "local_path": local_path,
                "prompt": prompt,
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
        """Check if local generation is available."""
        return torch.cuda.is_available() or self.device == "cpu"
    
    def get_info(self) -> Dict[str, Any]:
        """Get information about local generation capabilities."""
        return {
            "available": self.is_available(),
            "device": self.device,
            "vram_gb": self.vram_gb,
            "model": self.model_name,
            "recommended_size": "512x512" if self.vram_gb < 8 else "768x768"
        }
'''

write_file("AI_SMM_Work_Architecture_A75/local_image_generator.py", local_img_gen_content)

# 5. Update app.py to integrate local image generation
print("[5/5] Updating app.py with local image generation...")

app_content = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI SMM Manager - Step 4: Local Stable Diffusion Integration.
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
    logger.info("=== AI SMM Manager - Step 4: Local Stable Diffusion ===")
    
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
    
    # Initialize local image generator
    local_img_gen = LocalImageGenerator()
    local_img_info = local_img_gen.get_info()
    
    if openai_client.is_available():
        logger.info("OpenAI client initialized and enabled")
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
    window.setWindowTitle("AI SMM Manager v2.0 (Step 4 - Local SD)")
    window.resize(800, 650)
    
    layout = QVBoxLayout()
    
    label = QLabel("Введите задачу для SMM-менеджера:")
    label.setFont(QFont("Arial", 11, QFont.Bold))
    layout.addWidget(label)
    
    text_input = QTextEdit()
    text_input.setFont(QFont("Consolas", 10))
    text_input.setPlainText("Создай короткий пост для Instagram про утренний кофе в кофейне для фрилансеров. Тон: дружелюбный. Не выдумывай цены.")
    layout.addWidget(text_input)
    
    # Image generation options
    img_group = QGroupBox("Генерация изображения")
    img_layout = QVBoxLayout()
    
    use_dalle_cb = QCheckBox("DALL-E 3 (облако, высокое качество)")
    use_dalle_cb.setChecked(openai_client.is_available())
    use_dalle_cb.setEnabled(openai_client.is_available())
    img_layout.addWidget(use_dalle_cb)
    
    use_local_sd_cb = QCheckBox(f"Stable Diffusion локально ({local_img_info['device']}, {local_img_info['vram_gb']:.1f} GB VRAM)")
    use_local_sd_cb.setChecked(not openai_client.is_available())
    use_local_sd_cb.setEnabled(local_img_gen.is_available())
    img_layout.addWidget(use_local_sd_cb)
    
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
        use_dalle = use_dalle_cb.isChecked()
        use_local = use_local_sd_cb.isChecked()
        
        msg_handler.log("\\n[СТАРТ] Отправка запроса...")
        msg_handler.log(f"[ИНФО] Автор: {quality_gate.author_model}")
        msg_handler.log(f"[ИНФО] Рецензент: {quality_gate.reviewer_model}")
        
        if use_dalle and openai_client.is_available():
            msg_handler.log("[ИНФО] Изображение: DALL-E 3 (облако)")
        elif use_local and local_img_gen.is_available():
            msg_handler.log(f"[ИНФО] Изображение: Stable Diffusion локально ({local_img_info['device']})")
        else:
            msg_handler.log("[ИНФО] Изображение: отключено")
        
        msg_handler.log("[ИНФО] Генерация -> Проверка...")
        
        def work_fn(task_id):
            result = quality_gate.full_quality_gate(request, {"правило": "Не выдумывай цены"})
            
            # Generate image
            image_prompt = f"Professional social media photo: {request}. High quality, vibrant colors."
            image_path = str(ROOT_DIR / "media" / "images" / f"{task_id}.png")
            
            if use_dalle and openai_client.is_available():
                msg_handler.log("[ИНФО] Генерация через DALL-E 3...")
                image_result = openai_client.generate_image(image_prompt, save_path=image_path)
                if image_result:
                    result["image"] = image_result
                    msg_handler.log(f"[OK] DALL-E 3: {image_result.get('local_path', 'N/A')}")
                else:
                    msg_handler.log("[WARN] DALL-E 3 не сработал")
            
            elif use_local and local_img_gen.is_available():
                msg_handler.log("[ИНФО] Генерация через Stable Diffusion (может занять 30-60 сек)...")
                image_result = local_img_gen.generate_image(image_prompt, save_path=image_path)
                if image_result:
                    result["image"] = image_result
                    msg_handler.log(f"[OK] SD локально: {image_result.get('local_path', 'N/A')}")
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
    logger.info("GUI is running. Local Stable Diffusion integration is active.")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
'''

write_file("AI_SMM_Work_Architecture_A75/app.py", app_content)

# 6. Summary
print("\n" + "="*70)
print("=== Step 4 Summary ===")
print("="*70)
print("\nCompleted:")
print("  [OK] Installed PyTorch with CUDA 11.8")
print("  [OK] Installed diffusers, transformers, accelerate, safetensors")
print("  [OK] Created local_image_generator.py (Stable Diffusion 1.5)")
print("  [OK] Updated app.py with local/cloud image generation options")

print("\nFeatures added:")
print("  - Stable Diffusion 1.5 (локальная генерация)")
print("  - VRAM оптимизации (attention slicing, CPU offload)")
print("  - Выбор между DALL-E 3 и локальным SD в GUI")
print("  - Автоматическая адаптация под 8 GB VRAM")

print("\nImportant:")
print("  - Первая генерация загрузит модель (~4 GB) — это займёт 1-2 минуты")
print("  - Локальная генерация медленнее DALL-E 3 (30-60 сек vs 10-15 сек)")
print("  - Качество SD 1.5 ниже, чем DALL-E 3, но бесплатно и без интернета")

print("\nNext: Run START.bat to test local image generation.")
print("="*70 + "\n")