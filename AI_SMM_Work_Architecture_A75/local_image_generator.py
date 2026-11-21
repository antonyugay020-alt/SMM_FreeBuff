"""
Local Image Generator v4.1 - Backward compatible with save_path parameter.
"""
import os
import logging
import ctypes
import time
import torch
from typing import Optional, Dict, Any
from pathlib import Path
from PIL import Image

logger = logging.getLogger(__name__)

class LocalImageGenerator:
    def __init__(self, model_name: str = "runwayml/stable-diffusion-v1-5", 
                 device: Optional[str] = None, ollama_client=None, 
                 storage_dir: Optional[str] = None):
        self.model_name = model_name
        self.pipe = None
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.vram_gb = 0
        self.ollama = ollama_client
        
        # Unified storage directory
        if storage_dir:
            self.storage_dir = Path(storage_dir)
        else:
            self.storage_dir = Path(__file__).resolve().parent.parent / "media" / "images"
        
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Image storage: {self.storage_dir}")
        
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
        
        if any('\u0400' <= c <= '\u04FF' for c in prompt):
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
    
    def _get_safe_path(self, path_str: str) -> str:
        """Convert path to short path on Windows to avoid issues with spaces/Cyrillic."""
        if os.name != 'nt':
            return path_str
        
        try:
            buffer = ctypes.create_unicode_buffer(260)
            result = ctypes.windll.kernel32.GetShortPathNameW(path_str, buffer, 260)
            if result > 0:
                return buffer.value
        except Exception as e:
            logger.warning(f"Failed to get short path: {e}")
        
        return path_str
    
    def generate_image(self, prompt: str, negative_prompt: str = "",
                      width: int = 512, height: int = 512,
                      num_inference_steps: int = 30,
                      guidance_scale: float = 7.5,
                      save_path: Optional[str] = None,  # Backward compatibility
                      filename: Optional[str] = None,
                      auto_translate: bool = True) -> Optional[Dict[str, Any]]:
        """
        Generate image and save to unified storage.
        
        Args:
            prompt: Image description
            save_path: Legacy parameter (ignored, use filename instead)
            filename: Optional filename (auto-generated if None)
        """
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
            
            # Generate filename if not provided
            if not filename:
                filename = f"sd_{int(time.time())}.png"
            
            save_path_obj = self.storage_dir / filename
            save_path_obj.parent.mkdir(parents=True, exist_ok=True)
            
            # Use short path for SD compatibility
            safe_path = self._get_safe_path(str(save_path_obj))
            
            image.save(safe_path, "PNG")
            
            return {
                "local_path": str(save_path_obj),
                "filename": filename,
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
            "storage": str(self.storage_dir),
            "recommended_size": "512x512" if self.vram_gb < 8 else "768x768"
        }
