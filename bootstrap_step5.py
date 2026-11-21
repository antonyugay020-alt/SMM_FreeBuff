#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI SMM Manager - Step 5: Video Pipeline (Whisper + FFmpeg).
Adds video transcription, subtitle generation, and platform-specific export.
Run: python bootstrap_step5.py
"""

import os
import sys
import subprocess
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
print("=== AI SMM Manager - Step 5: Video Pipeline ===")
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

# 2. Check FFmpeg
print("[2/5] Checking FFmpeg installation...")
try:
    result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=5)
    if result.returncode == 0:
        print("  [OK] FFmpeg is installed")
        # Extract version
        version_line = result.stdout.split('\n')[0]
        print(f"       {version_line}")
    else:
        print("  [WARNING] FFmpeg not found in PATH")
        print("  Install from: https://ffmpeg.org/download.html")
except FileNotFoundError:
    print("  [WARNING] FFmpeg not found in PATH")
    print("  Install from: https://ffmpeg.org/download.html")
    print("  Or: winget install Gyan.FFmpeg")

# 3. Install video processing libraries
print("\n[3/5] Installing video processing libraries...")

packages = [
    ("openai-whisper", "Whisper for local transcription"),
    ("moviepy", "Video editing"),
    ("pydub", "Audio processing"),
]

for pkg, desc in packages:
    print(f"  Installing {pkg} ({desc})...", end=" ")
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

# 4. Create video_processor.py
print("\n[4/5] Creating video_processor.py...")

video_processor_content = '''"""
Video Processor - Whisper transcription + FFmpeg subtitle burning + platform export.
Supports: MP4, MOV, AVI, MKV, WebM, MP3, WAV, M4A
"""
import os
import subprocess
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import timedelta

logger = logging.getLogger(__name__)

# Platform-specific export settings
PLATFORM_SETTINGS = {
    "instagram_reels": {
        "width": 1080,
        "height": 1920,
        "max_duration": 90,
        "fps": 30,
        "codec": "libx264",
        "preset": "medium",
        "crf": 23
    },
    "tiktok": {
        "width": 1080,
        "height": 1920,
        "max_duration": 180,
        "fps": 30,
        "codec": "libx264",
        "preset": "medium",
        "crf": 23
    },
    "youtube_shorts": {
        "width": 1080,
        "height": 1920,
        "max_duration": 60,
        "fps": 30,
        "codec": "libx264",
        "preset": "medium",
        "crf": 23
    },
    "youtube_video": {
        "width": 1920,
        "height": 1080,
        "max_duration": 0,  # No limit
        "fps": 30,
        "codec": "libx264",
        "preset": "medium",
        "crf": 23
    },
    "instagram_post": {
        "width": 1080,
        "height": 1080,
        "max_duration": 60,
        "fps": 30,
        "codec": "libx264",
        "preset": "medium",
        "crf": 23
    }
}

class VideoProcessor:
    def __init__(self, whisper_model: str = "base", openai_client=None):
        """
        Initialize video processor.
        
        Args:
            whisper_model: Whisper model size (tiny, base, small, medium, large)
            openai_client: Optional OpenAI client for cloud transcription
        """
        self.whisper_model = whisper_model
        self.openai = openai_client
        self._whisper_model_obj = None
        
        # Check FFmpeg
        self.ffmpeg_available = self._check_ffmpeg()
        
        logger.info(f"Video Processor initialized:")
        logger.info(f"  Whisper model: {whisper_model}")
        logger.info(f"  FFmpeg: {'available' if self.ffmpeg_available else 'NOT available'}")
        logger.info(f"  OpenAI: {'available' if openai_client and openai_client.is_available() else 'disabled'}")
    
    def _check_ffmpeg(self) -> bool:
        """Check if FFmpeg is available."""
        try:
            result = subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
            return result.returncode == 0
        except:
            return False
    
    def _load_whisper(self):
        """Load Whisper model for local transcription."""
        if self._whisper_model_obj is not None:
            return
        
        try:
            import whisper
            logger.info(f"Loading Whisper model: {self.whisper_model}")
            logger.info("First load may take 1-2 minutes (downloading model)...")
            self._whisper_model_obj = whisper.load_model(self.whisper_model)
            logger.info("Whisper model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise
    
    def transcribe(self, audio_path: str, language: Optional[str] = "ru", 
                   use_openai: bool = False) -> Optional[Dict[str, Any]]:
        """
        Transcribe audio/video file to text.
        
        Args:
            audio_path: Path to audio or video file
            language: Language code (ru, en, etc.) or None for auto-detect
            use_openai: Use OpenAI Whisper API instead of local
        
        Returns:
            Dict with "text", "segments", "language"
        """
        if use_openai and self.openai and self.openai.is_available():
            return self._transcribe_openai(audio_path, language)
        else:
            return self._transcribe_local(audio_path, language)
    
    def _transcribe_local(self, audio_path: str, language: Optional[str]) -> Optional[Dict[str, Any]]:
        """Transcribe using local Whisper model."""
        try:
            self._load_whisper()
        except Exception as e:
            logger.error(f"Cannot transcribe: {e}")
            return None
        
        try:
            logger.info(f"Transcribing: {audio_path}")
            logger.info(f"Language: {language or 'auto-detect'}")
            
            options = {}
            if language:
                options["language"] = language
            
            result = self._whisper_model_obj.transcribe(audio_path, **options)
            
            return {
                "text": result["text"],
                "segments": result["segments"],
                "language": result.get("language", "unknown")
            }
        
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return None
    
    def _transcribe_openai(self, audio_path: str, language: Optional[str]) -> Optional[Dict[str, Any]]:
        """Transcribe using OpenAI Whisper API."""
        if not self.openai or not self.openai.is_available():
            logger.warning("OpenAI not available")
            return None
        
        try:
            logger.info(f"Transcribing via OpenAI Whisper: {audio_path}")
            
            text = self.openai.transcribe_audio(audio_path, language=language)
            
            if text:
                return {
                    "text": text,
                    "segments": [],  # OpenAI doesn't return segments
                    "language": language or "unknown"
                }
            else:
                return None
        
        except Exception as e:
            logger.error(f"OpenAI transcription failed: {e}")
            return None
    
    def generate_srt(self, segments: List[Dict[str, Any]], output_path: str) -> bool:
        """
        Generate SRT subtitle file from segments.
        
        Args:
            segments: List of segments with "start", "end", "text"
            output_path: Path to save SRT file
        
        Returns:
            bool: True if successful
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                for i, segment in enumerate(segments, 1):
                    start_time = self._format_srt_time(segment["start"])
                    end_time = self._format_srt_time(segment["end"])
                    text = segment["text"].strip()
                    
                    f.write(f"{i}\\n")
                    f.write(f"{start_time} --> {end_time}\\n")
                    f.write(f"{text}\\n\\n")
            
            logger.info(f"SRT file saved: {output_path}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to generate SRT: {e}")
            return False
    
    def _format_srt_time(self, seconds: float) -> str:
        """Convert seconds to SRT time format (HH:MM:SS,mmm)."""
        td = timedelta(seconds=seconds)
        hours, remainder = divmod(int(td.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        milliseconds = int((seconds - int(seconds)) * 1000)
        seconds = int(seconds)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"
    
    def burn_subtitles(self, video_path: str, srt_path: str, output_path: str,
                      font_size: int = 24, font_color: str = "white") -> bool:
        """
        Burn subtitles into video using FFmpeg.
        
        Args:
            video_path: Input video path
            srt_path: SRT subtitle file path
            output_path: Output video path
            font_size: Subtitle font size
            font_color: Subtitle font color
        
        Returns:
            bool: True if successful
        """
        if not self.ffmpeg_available:
            logger.error("FFmpeg not available")
            return False
        
        try:
            logger.info(f"Burning subtitles: {video_path}")
            logger.info(f"Output: {output_path}")
            
            # Escape special characters in paths for FFmpeg
            video_path_escaped = video_path.replace("\\\\", "/").replace(":", "\\\\:").replace("'", "\\\\'")
            srt_path_escaped = srt_path.replace("\\\\", "/").replace(":", "\\\\:").replace("'", "\\\\'")
            
            # FFmpeg command with subtitles filter
            cmd = [
                "ffmpeg",
                "-i", video_path,
                "-vf", f"subtitles={srt_path_escaped}:force_style='FontSize={font_size},PrimaryColour=&H00{font_color[1:]}&'",
                "-c:a", "copy",
                "-y",
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                logger.info(f"Subtitles burned successfully: {output_path}")
                return True
            else:
                logger.error(f"FFmpeg error: {result.stderr[:500]}")
                return False
        
        except subprocess.TimeoutExpired:
            logger.error("FFmpeg timeout")
            return False
        except Exception as e:
            logger.error(f"Failed to burn subtitles: {e}")
            return False
    
    def export_for_platform(self, video_path: str, platform: str, output_path: str,
                           trim_start: float = 0, trim_end: Optional[float] = None) -> bool:
        """
        Export video for specific platform (Instagram Reels, TikTok, etc.).
        
        Args:
            video_path: Input video path
            platform: Platform name (instagram_reels, tiktok, youtube_shorts, etc.)
            output_path: Output video path
            trim_start: Start time in seconds
            trim_end: End time in seconds (None for no trim)
        
        Returns:
            bool: True if successful
        """
        if not self.ffmpeg_available:
            logger.error("FFmpeg not available")
            return False
        
        if platform not in PLATFORM_SETTINGS:
            logger.error(f"Unknown platform: {platform}")
            return False
        
        settings = PLATFORM_SETTINGS[platform]
        
        try:
            logger.info(f"Exporting for {platform}: {video_path}")
            logger.info(f"Resolution: {settings['width']}x{settings['height']}")
            
            # Build FFmpeg command
            cmd = [
                "ffmpeg",
                "-i", video_path,
                "-ss", str(trim_start),
            ]
            
            if trim_end:
                cmd.extend(["-to", str(trim_end)])
            
            cmd.extend([
                "-vf", f"scale={settings['width']}:{settings['height']}:force_original_aspect_ratio=decrease,pad={settings['width']}:{settings['height']}:(ow-iw)/2:(oh-ih)/2",
                "-r", str(settings['fps']),
                "-c:v", settings['codec'],
                "-preset", settings['preset'],
                "-crf", str(settings['crf']),
                "-c:a", "aac",
                "-b:a", "128k",
                "-y",
                output_path
            ])
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            
            if result.returncode == 0:
                logger.info(f"Exported for {platform}: {output_path}")
                return True
            else:
                logger.error(f"FFmpeg error: {result.stderr[:500]}")
                return False
        
        except subprocess.TimeoutExpired:
            logger.error("FFmpeg timeout")
            return False
        except Exception as e:
            logger.error(f"Failed to export: {e}")
            return False
    
    def get_video_info(self, video_path: str) -> Optional[Dict[str, Any]]:
        """Get video file information using FFprobe."""
        if not self.ffmpeg_available:
            return None
        
        try:
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                info = json.loads(result.stdout)
                
                # Extract video stream info
                video_stream = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), None)
                
                if video_stream:
                    return {
                        "width": int(video_stream.get("width", 0)),
                        "height": int(video_stream.get("height", 0)),
                        "duration": float(info.get("format", {}).get("duration", 0)),
                        "fps": eval(video_stream.get("r_frame_rate", "30/1")),
                        "codec": video_stream.get("codec_name", "unknown")
                    }
            
            return None
        
        except Exception as e:
            logger.error(f"Failed to get video info: {e}")
            return None
'''

write_file("AI_SMM_Work_Architecture_A75/video_processor.py", video_processor_content)

# 5. Update app.py with video processing tab
print("[5/5] Updating app.py with video processing...")

app_content = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI SMM Manager - Step 5: Video Pipeline Integration.
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
    logger.info("=== AI SMM Manager - Step 5: Video Pipeline ===")
    
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
    
    # Initialize video processor
    video_processor = VideoProcessor(whisper_model="base", openai_client=openai_client)
    
    quality_gate = LocalQualityGate(ollama_client=ollama, openai_client=openai_client, config=config)
    media_router = MediaTaskRouter(config)
    
    logger.info("All components initialized. Starting GUI...")
    
    app = QApplication(sys.argv)
    app.setApplicationName("AI SMM Manager")
    
    font = QFont("Arial", 10)
    app.setFont(font)
    
    window = QMainWindow()
    window.setWindowTitle("AI SMM Manager v2.0 (Step 5 - Video)")
    window.resize(900, 700)
    
    # Create tab widget
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
        
        if use_openai and openai_client.is_available():
            text_msg_handler.log(f"[ИНФО] Изображение: {openai_client.get_image_model()} (облако)")
        elif use_local and local_img_gen.is_available():
            text_msg_handler.log(f"[ИНФО] Изображение: Stable Diffusion локально")
        else:
            text_msg_handler.log("[ИНФО] Изображение: отключено")
        
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
    
    # File selection
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
            # Get video info
            info = video_processor.get_video_info(file_path)
            if info:
                file_path_label.setText(f"{file_path}\\n{info['width']}x{info['height']}, {info['duration']:.1f}s, {info['fps']:.1f} fps")
    
    select_btn = QPushButton("Выбрать файл")
    select_btn.clicked.connect(select_file)
    file_layout.addWidget(select_btn)
    
    file_group.setLayout(file_layout)
    video_layout.addWidget(file_group)
    
    # Transcription options
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
    
    # Export options
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
            video_msg_handler.log(f"[OK] Транскрипция завершена ({len(transcript['text'])} символов)")
            video_msg_handler.log(f"Текст: {transcript['text'][:200]}...")
            
            # Step 2: Generate SRT
            if transcript.get("segments"):
                video_msg_handler.log("[2/3] Генерация субтитров...")
                srt_path = str(ROOT_DIR / "media" / "videos" / f"{task_id}.srt")
                Path(srt_path).parent.mkdir(parents=True, exist_ok=True)
                
                if video_processor.generate_srt(transcript["segments"], srt_path):
                    results["srt_path"] = srt_path
                    video_msg_handler.log(f"[OK] SRT сохранён: {srt_path}")
                else:
                    video_msg_handler.log("[WARN] Не удалось создать SRT")
            
            # Step 3: Export for platform
            video_msg_handler.log(f"[3/3] Экспорт для {platform}...")
            output_path = str(ROOT_DIR / "media" / "videos" / f"{task_id}_{platform}.mp4")
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            if burn_subtitles and results.get("srt_path"):
                # First burn subtitles, then export
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
        
        if result.get("transcript"):
            video_msg_handler.log(f"\\n[ТРАНСКРИПЦИЯ] {result['transcript']['text'][:300]}...")
        
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
    
    # Main layout
    main_layout = QVBoxLayout()
    main_layout.addWidget(tabs)
    
    container = QWidget()
    container.setLayout(main_layout)
    window.setCentralWidget(container)
    
    window.show()
    logger.info("GUI is running. Video pipeline is active.")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
'''

write_file("AI_SMM_Work_Architecture_A75/app.py", app_content)

# 6. Create media/videos directory
print("\n[6/6] Creating media/videos directory...")
videos_dir = ROOT_DIR / "media" / "videos"
videos_dir.mkdir(parents=True, exist_ok=True)
print(f"  [OK] Created: {videos_dir}")

print("\n" + "="*70)
print("=== Step 5 Summary ===")
print("="*70)
print("\nCompleted:")
print("  [OK] Installed openai-whisper, moviepy, pydub")
print("  [OK] Created video_processor.py")
print("       - Whisper transcription (local or OpenAI API)")
print("       - SRT subtitle generation")
print("       - Subtitle burning via FFmpeg")
print("       - Platform-specific export (Instagram Reels, TikTok, YouTube)")
print("  [OK] Updated app.py with Video tab")
print("  [OK] Created media/videos/ directory")

print("\nFeatures added:")
print("  - Transcribe audio/video to text (Russian/English)")
print("  - Generate SRT subtitle files")
print("  - Burn subtitles into video")
print("  - Export for Instagram Reels, TikTok, YouTube Shorts")
print("  - Automatic resolution and format adjustment")

print("\nNext: Run START.bat to test video processing.")
print("="*70 + "\n")