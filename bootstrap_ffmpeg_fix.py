#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI SMM Manager - FFmpeg Fix: Check returncode instead of stderr.
Also adds unique timestamps to filenames.
Run: python bootstrap_ffmpeg_fix.py
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

print("\n=== AI SMM Manager - FFmpeg Fix ===\n")

print("[1/1] Fixing video_processor.py...")

video_processor_content = '''"""
Video Processor v3 - FFmpeg returncode check + unique filenames.
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
    
    def _run_ffmpeg(self, cmd: List[str], timeout: int = 300) -> bool:
        """
        Run FFmpeg command and check returncode (not stderr).
        FFmpeg always outputs version info to stderr, even on success.
        """
        try:
            logger.info(f"Running FFmpeg: {' '.join(cmd[:5])}...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            
            # Check returncode, NOT stderr
            if result.returncode == 0:
                logger.info("FFmpeg completed successfully")
                return True
            else:
                # Show first 300 chars of stderr for debugging
                error_preview = result.stderr[:300] if result.stderr else "No error message"
                logger.error(f"FFmpeg failed (returncode={result.returncode}): {error_preview}")
                return False
        
        except subprocess.TimeoutExpired:
            logger.error(f"FFmpeg timeout after {timeout}s")
            return False
        except Exception as e:
            logger.error(f"FFmpeg execution failed: {e}")
            return False
    
    def burn_subtitles(self, video_path: str, srt_path: str, output_path: str,
                      font_size: int = 24, font_color: str = "white") -> bool:
        if not self.ffmpeg_available:
            logger.error("FFmpeg not available")
            return False
        try:
            logger.info(f"Burning subtitles: {video_path}")
            logger.info(f"Output: {output_path}")
            
            video_path_escaped = video_path.replace("\\\\", "/").replace(":", "\\\\:").replace("'", "\\\\'")
            srt_path_escaped = srt_path.replace("\\\\", "/").replace(":", "\\\\:").replace("'", "\\\\'")
            
            cmd = [
                "ffmpeg", "-i", video_path,
                "-vf", f"subtitles={srt_path_escaped}:force_style='FontSize={font_size},PrimaryColour=&H00FFFFFF&'",
                "-c:a", "copy", "-y", output_path
            ]
            
            return self._run_ffmpeg(cmd, timeout=300)
        
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
            logger.info(f"Resolution: {settings['width']}x{settings['height']}")
            
            cmd = ["ffmpeg", "-i", video_path, "-ss", str(trim_start)]
            if trim_end:
                cmd.extend(["-to", str(trim_end)])
            cmd.extend([
                "-vf", f"scale={settings['width']}:{settings['height']}:force_original_aspect_ratio=decrease,pad={settings['width']}:{settings['height']}:(ow-iw)/2:(oh-ih)/2",
                "-r", str(settings['fps']), "-c:v", settings['codec'],
                "-preset", settings['preset'], "-crf", str(settings['crf']),
                "-c:a", "aac", "-b:a", "128k", "-y", output_path
            ])
            
            return self._run_ffmpeg(cmd, timeout=600)
        
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
        """Generate unique filename with timestamp."""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{timestamp}.{extension}"
'''

write_file("AI_SMM_Work_Architecture_A75/video_processor.py", video_processor_content)

print("\n=== FFmpeg Fix Applied ===")
print("\nChanges:")
print("  [OK] Added _run_ffmpeg() helper method")
print("       - Checks returncode (0 = success)")
print("       - Ignores stderr (FFmpeg always outputs version info there)")
print("       - Shows error preview only on actual failure")
print("  [OK] burn_subtitles() now uses _run_ffmpeg()")
print("  [OK] export_for_platform() now uses _run_ffmpeg()")
print("  [OK] Added generate_unique_filename() for timestamp-based names")
print("\nNow run START.bat to test video processing.")
print("Subtitles should burn correctly, and export should work.")