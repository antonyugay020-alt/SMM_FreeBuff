"""
Media Task Router - Intelligent routing between local and cloud processing.
Evaluates hardware constraints (VRAM) and privacy requirements to choose the best execution path.
"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class MediaTaskRouter:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.hardware = config.get("hardware", {})
        self.media_config = config.get("media_processing", {})
        
        self.vram_gb = self.hardware.get("gpu_vram_gb", 8)
        self.fallback_to_cloud = self.media_config.get("fallback_to_cloud_if_vram_exceeded", True)
        
    def should_process_locally(self, task_type: str, estimated_vram_gb: float, is_private: bool = False) -> bool:
        """
        Determine if a media task should be processed locally.
        
        Args:
            task_type: "image_generation", "video_editing", "audio_transcription", etc.
            estimated_vram_gb: Estimated VRAM required for the task
            is_private: Whether the project requires strict privacy (no cloud)
            
        Returns:
            bool: True if local processing is recommended, False if cloud is better
        """
        if is_private:
            logger.info(f"Task '{task_type}' forced to local due to privacy requirements.")
            return True
            
        if estimated_vram_gb > self.vram_gb:
            if self.fallback_to_cloud:
                logger.warning(f"Task '{task_type}' requires {estimated_vram_gb}GB VRAM, but only {self.vram_gb}GB available. Routing to cloud.")
                return False
            else:
                logger.error(f"Task '{task_type}' requires {estimated_vram_gb}GB VRAM, but only {self.vram_gb}GB available. Cloud fallback disabled. Task may fail or be very slow.")
                return True
                
        logger.info(f"Task '{task_type}' routed to local processing (requires {estimated_vram_gb}GB / {self.vram_gb}GB available).")
        return True
        
    def get_recommended_model(self, task_type: str) -> str:
        """Get the recommended model/tool based on hardware constraints."""
        if task_type == "image_generation":
            if self.vram_gb >= 12:
                return self.media_config.get("local_sd_model_xl", "stable-diffusion-xl")
            else:
                return self.media_config.get("local_sd_model", "stable-diffusion-v1-5")
        elif task_type == "audio_transcription":
            if self.vram_gb >= 8:
                return self.media_config.get("local_whisper_model", "base")
            else:
                return "tiny"
                
        return "default"