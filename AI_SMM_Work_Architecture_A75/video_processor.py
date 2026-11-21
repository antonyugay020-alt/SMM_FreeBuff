"""
Video Processor v6 - UTF-8 BOM for SRT + proper filter escaping.
"""
import os
import subprocess
import json
import logging
import time
import shutil
import tempfile
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
        self.ffmpeg_temp_dir = Path(tempfile.gettempdir()) / "ai_smm_ffmpeg"
        self.ffmpeg_temp_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Video Processor initialized:")
        logger.info(f"  Whisper model: {whisper_model}")
        logger.info(f"  FFmpeg: {'available' if self.ffmpeg_available else 'NOT available'}")
        logger.info(f"  FFmpeg temp dir: {self.ffmpeg_temp_dir}")
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
        """Generate SRT file with UTF-8 BOM (required by FFmpeg for Cyrillic)."""
        try:
            with open(output_path, 'w', encoding='utf-8-sig', newline='\n') as f:
                for i, segment in enumerate(segments, 1):
                    start_time = self._format_srt_time(segment["start"])
                    end_time = self._format_srt_time(segment["end"])
                    text = segment["text"].strip()
                    f.write(f"{i}\n{start_time} --> {end_time}\n{text}\n\n")
            logger.info(f"SRT file saved (UTF-8 BOM): {output_path}")
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

    @staticmethod
    def _escape_srt_path_for_filter(path: str) -> str:
        """
        Escape SRT path for FFmpeg subtitles filter.
        Rules:
        1. Use forward slashes
        2. Escape colon after drive letter: C: -> C\\:
        3. Wrap in single quotes
        """
        path = path.replace("\\", "/")
        if len(path) >= 2 and path[1] == ':':
            path = path[0] + '\\:' + path[2:]
        return f"'{path}'"

    def _prepare_ffmpeg_paths(self, video_path: str, srt_path: Optional[str] = None) -> Dict[str, str]:
        """Copy files to temp directory with ASCII-only names for FFmpeg."""
        timestamp = int(time.time())
        video_ext = Path(video_path).suffix or '.mp4'
        temp_video = self.ffmpeg_temp_dir / f"input_{timestamp}{video_ext}"
        shutil.copy2(video_path, temp_video)
        result = {
            "video": str(temp_video).replace("\\", "/"),
            "temp_video": temp_video
        }
        if srt_path and Path(srt_path).exists():
            temp_srt = self.ffmpeg_temp_dir / f"subs_{timestamp}.srt"
            shutil.copy2(srt_path, temp_srt)
            result["srt"] = str(temp_srt).replace("\\", "/")
            result["srt_escaped"] = self._escape_srt_path_for_filter(str(temp_srt))
            result["temp_srt"] = temp_srt
        return result

    def _run_ffmpeg(self, cmd: List[str], timeout: int = 300) -> bool:
        """Run FFmpeg command and check returncode."""
        try:
            logger.info(f"Running FFmpeg: {' '.join(cmd[:6])}...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            if result.returncode == 0:
                logger.info("FFmpeg completed successfully")
                return True
            else:
                error_preview = result.stderr[:500] if result.stderr else "No error message"
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
            paths = self._prepare_ffmpeg_paths(video_path, srt_path)
            temp_video = paths["video"]
            srt_escaped = paths.get("srt_escaped", paths["srt"])
            temp_output = str(self.ffmpeg_temp_dir / "output_temp.mp4").replace("\\", "/")
            filter_str = f"subtitles={srt_escaped}:force_style='FontSize={font_size},PrimaryColour=&H00FFFFFF&'"
            cmd = [
                "ffmpeg", "-i", temp_video,
                "-vf", filter_str,
                "-c:a", "copy", "-y", temp_output
            ]
            logger.info(f"FFmpeg command: {' '.join(cmd)}")
            success = self._run_ffmpeg(cmd, timeout=300)
            if success:
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(self.ffmpeg_temp_dir / "output_temp.mp4", output_path)
                logger.info(f"Subtitles burned and saved to: {output_path}")
            try:
                paths["temp_video"].unlink(missing_ok=True)
                if "temp_srt" in paths:
                    paths["temp_srt"].unlink(missing_ok=True)
                (self.ffmpeg_temp_dir / "output_temp.mp4").unlink(missing_ok=True)
            except Exception as e:
                logger.warning(f"Failed to cleanup temp files: {e}")
            return success
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
            paths = self._prepare_ffmpeg_paths(video_path)
            temp_video = paths["video"]
            temp_output = str(self.ffmpeg_temp_dir / "output_export.mp4").replace("\\", "/")
            cmd = ["ffmpeg", "-i", temp_video, "-ss", str(trim_start)]
            if trim_end:
                cmd.extend(["-to", str(trim_end)])
            cmd.extend([
                "-vf", f"scale={settings['width']}:{settings['height']}:force_original_aspect_ratio=decrease,pad={settings['width']}:{settings['height']}:(ow-iw)/2:(oh-ih)/2",
                "-r", str(settings['fps']), "-c:v", settings['codec'],
                "-preset", settings['preset'], "-crf", str(settings['crf']),
                "-c:a", "aac", "-b:a", "128k", "-y", temp_output
            ])
            success = self._run_ffmpeg(cmd, timeout=600)
            if success:
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(self.ffmpeg_temp_dir / "output_export.mp4", output_path)
                logger.info(f"Exported for {platform}: {output_path}")
            try:
                paths["temp_video"].unlink(missing_ok=True)
                (self.ffmpeg_temp_dir / "output_export.mp4").unlink(missing_ok=True)
            except Exception as e:
                logger.warning(f"Failed to cleanup temp files: {e}")
            return success
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
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{timestamp}.{extension}"
