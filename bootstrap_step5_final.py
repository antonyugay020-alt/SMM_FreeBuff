#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI SMM Manager - Step 5 Final Fix: 
1. Convert pydantic segments to plain dicts for JSON serialization
2. Add timestamps to filenames to avoid overwriting
Run: python bootstrap_step5_final.py
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

print("\n=== AI SMM Manager - Step 5 Final Fix ===\n")

# 1. Fix openai_client.py - convert pydantic to plain dicts
print("[1/2] Fixing openai_client.py - pydantic to dict conversion...")

openai_client_content = '''"""
OpenAI Client v3.6 - Pydantic to dict conversion for segments.
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

def _convert_segments_to_dicts(segments) -> List[Dict[str, Any]]:
    """Convert pydantic TranscriptionSegment objects to plain dicts."""
    if not segments:
        return []
    
    result = []
    for seg in segments:
        try:
            # Try pydantic model_dump()
            if hasattr(seg, 'model_dump'):
                result.append(seg.model_dump())
            elif hasattr(seg, 'dict'):
                result.append(seg.dict())
            elif isinstance(seg, dict):
                result.append(seg)
            else:
                # Manual extraction
                result.append({
                    "id": getattr(seg, 'id', 0),
                    "start": getattr(seg, 'start', 0.0),
                    "end": getattr(seg, 'end', 0.0),
                    "text": getattr(seg, 'text', ''),
                    "tokens": getattr(seg, 'tokens', []),
                    "temperature": getattr(seg, 'temperature', 0.0),
                    "avg_logprob": getattr(seg, 'avg_logprob', 0.0),
                    "compression_ratio": getattr(seg, 'compression_ratio', 1.0),
                    "no_speech_prob": getattr(seg, 'no_speech_prob', 0.0)
                })
        except Exception as e:
            logger.warning(f"Failed to convert segment: {e}")
    
    return result

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
        Returns dict with text, segments (as plain dicts), language.
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
            
            # Handle verbose_json response
            if response_format == "verbose_json":
                text = ""
                if hasattr(response, 'text'):
                    text = str(response.text) if response.text else ""
                elif isinstance(response, dict):
                    text = response.get('text', '')
                else:
                    text = str(response)
                
                # Convert segments to plain dicts
                raw_segments = []
                if hasattr(response, 'segments'):
                    raw_segments = response.segments if response.segments else []
                elif isinstance(response, dict):
                    raw_segments = response.get('segments', [])
                
                segments = _convert_segments_to_dicts(raw_segments)
                
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

# 2. Fix video_processor.py - convert local whisper segments too
print("[2/2] Fixing video_processor.py - timestamp filenames...")

video_processor_content = '''"""
Video Processor v2 - Whisper transcription + FFmpeg + timestamp filenames.
"""
import os
import subprocess
import json
import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import timedelta

logger = logging.getLogger(__name__)

PLATFORM_SETTINGS = {
    "instagram_reels": {"width": 1080, "height": 1920, "max_duration": 90, "fps": 30, "codec": "libx264", "preset": "medium", "crf": 23},
    "tiktok": {"width": 1080, "height": 1920, "max_duration": 180, "fps": 30, "codec": "libx264", "preset": "medium", "crf": 23},
    "youtube_shorts": {"width": 1080, "height": 1920, "max_duration": 60, "fps": 30, "codec": "libx264", "preset": "medium", "crf": 23},
    "youtube_video": {"width": 1920, "height": 1080, "max_duration": 0, "fps": 30, "codec": "libx264", "preset": "medium", "crf": 23},
    "instagram_post": {"width": 1080, "height": 1080, "max_duration": 60, "fps": 30, "codec": "libx264", "preset": "medium", "crf": 23}
}

class VideoProcessor:
    def __init__(self, whisper_model: str = "base", openai_client=None):
        self.whisper_model = whisper_model
        self.openai = openai_client
        self._whisper_model_obj = None
        self.ffmpeg_available = self._check_ffmpeg()
        
        logger.info(f"Video Processor initialized:")
        logger.info(f"  Whisper model: {whisper_model}")
        logger.info(f"  FFmpeg: {'available' if self.ffmpeg_available else 'NOT available'}")
        logger.info(f"  OpenAI: {'available' if openai_client and openai_client.is_available() else 'disabled'}")
    
    def _check_ffmpeg(self) -> bool:
        try:
            result = subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
            return result.returncode == 0
        except:
            return False
    
    def _load_whisper(self):
        if self._whisper_model_obj is not None:
            return
        try:
            import whisper
            logger.info(f"Loading Whisper model: {self.whisper_model}")
            self._whisper_model_obj = whisper.load_model(self.whisper_model)
            logger.info("Whisper model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise
    
    def transcribe(self, audio_path: str, language: Optional[str] = "ru", 
                   use_openai: bool = False) -> Optional[Dict[str, Any]]:
        if use_openai and self.openai and self.openai.is_available():
            return self._transcribe_openai(audio_path, language)
        else:
            return self._transcribe_local(audio_path, language)
    
    def _transcribe_local(self, audio_path: str, language: Optional[str]) -> Optional[Dict[str, Any]]:
        try:
            self._load_whisper()
        except Exception as e:
            logger.error(f"Cannot transcribe: {e}")
            return None
        
        try:
            logger.info(f"Transcribing: {audio_path}")
            options = {}
            if language:
                options["language"] = language
            
            result = self._whisper_model_obj.transcribe(audio_path, **options)
            
            # Convert segments to plain dicts
            segments = []
            for seg in result.get("segments", []):
                segments.append({
                    "id": seg.get("id", 0),
                    "start": seg.get("start", 0.0),
                    "end": seg.get("end", 0.0),
                    "text": seg.get("text", "")
                })
            
            return {
                "text": result["text"],
                "segments": segments,
                "language": result.get("language", "unknown")
            }
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return None
    
    def _transcribe_openai(self, audio_path: str, language: Optional[str]) -> Optional[Dict[str, Any]]:
        if not self.openai or not self.openai.is_available():
            return None
        try:
            logger.info(f"Transcribing via OpenAI Whisper: {audio_path}")
            return self.openai.transcribe_audio(audio_path, language=language)
        except Exception as e:
            logger.error(f"OpenAI transcription failed: {e}")
            return None
    
    def generate_srt(self, segments: List[Dict[str, Any]], output_path: str) -> bool:
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                for i, segment in enumerate(segments, 1):
                    start_time = self._format_srt_time(segment["start"])
                    end_time = self._format_srt_time(segment["end"])
                    text = segment["text"].strip()
                    f.write(f"{i}\\n{start_time} --> {end_time}\\n{text}\\n\\n")
            logger.info(f"SRT file saved: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to generate SRT: {e}")
            return False
    
    def _format_srt_time(self, seconds: float) -> str:
        td = timedelta(seconds=seconds)
        hours, remainder = divmod(int(td.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        milliseconds = int((seconds - int(seconds)) * 1000)
        seconds = int(seconds)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"
    
    def burn_subtitles(self, video_path: str, srt_path: str, output_path: str,
                      font_size: int = 24, font_color: str = "white") -> bool:
        if not self.ffmpeg_available:
            logger.error("FFmpeg not available")
            return False
        try:
            logger.info(f"Burning subtitles: {video_path}")
            video_path_escaped = video_path.replace("\\\\", "/").replace(":", "\\\\:").replace("'", "\\\\'")
            srt_path_escaped = srt_path.replace("\\\\", "/").replace(":", "\\\\:").replace("'", "\\\\'")
            cmd = [
                "ffmpeg", "-i", video_path,
                "-vf", f"subtitles={srt_path_escaped}:force_style='FontSize={font_size},PrimaryColour=&H00FFFFFF&'",
                "-c:a", "copy", "-y", output_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                logger.info(f"Subtitles burned: {output_path}")
                return True
            else:
                logger.error(f"FFmpeg error: {result.stderr[:500]}")
                return False
        except Exception as e:
            logger.error(f"Failed to burn subtitles: {e}")
            return False
    
    def export_for_platform(self, video_path: str, platform: str, output_path: str,
                           trim_start: float = 0, trim_end: Optional[float] = None) -> bool:
        if not self.ffmpeg_available:
            logger.error("FFmpeg not available")
            return False
        if platform not in PLATFORM_SETTINGS:
            logger.error(f"Unknown platform: {platform}")
            return False
        settings = PLATFORM_SETTINGS[platform]
        try:
            logger.info(f"Exporting for {platform}: {video_path}")
            cmd = ["ffmpeg", "-i", video_path, "-ss", str(trim_start)]
            if trim_end:
                cmd.extend(["-to", str(trim_end)])
            cmd.extend([
                "-vf", f"scale={settings['width']}:{settings['height']}:force_original_aspect_ratio=decrease,pad={settings['width']}:{settings['height']}:(ow-iw)/2:(oh-ih)/2",
                "-r", str(settings['fps']), "-c:v", settings['codec'],
                "-preset", settings['preset'], "-crf", str(settings['crf']),
                "-c:a", "aac", "-b:a", "128k", "-y", output_path
            ])
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if result.returncode == 0:
                logger.info(f"Exported for {platform}: {output_path}")
                return True
            else:
                logger.error(f"FFmpeg error: {result.stderr[:500]}")
                return False
        except Exception as e:
            logger.error(f"Failed to export: {e}")
            return False
    
    def get_video_info(self, video_path: str) -> Optional[Dict[str, Any]]:
        if not self.ffmpeg_available:
            return None
        try:
            cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", video_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                info = json.loads(result.stdout)
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
    
    def generate_unique_filename(self, prefix: str, extension: str) -> str:
        """Generate unique filename with timestamp to avoid overwriting."""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{timestamp}.{extension}"
'''

write_file("AI_SMM_Work_Architecture_A75/video_processor.py", video_processor_content)

print("\n=== Final Fix Applied ===")
print("\nChanges:")
print("  [OK] openai_client.py: Convert pydantic segments to plain dicts")
print("       - Uses model_dump() or manual extraction")
print("       - Segments now serialize correctly through JSON signals")
print("  [OK] video_processor.py: Convert local whisper segments to plain dicts")
print("  [OK] Added generate_unique_filename() for timestamp-based names")
print("\nNow run START.bat to test video processing.")
print("Subtitles should appear, and files won't overwrite each other.")