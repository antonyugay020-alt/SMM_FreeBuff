#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI SMM Manager - Step 4.6: Unified Image Storage.
All images saved to media/images/ folder in project directory.
Run: python bootstrap_step4_6.py
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

print("\n" + "="*70)
print("=== AI SMM Manager - Step 4.6: Unified Image Storage ===")
print("="*70 + "\n")

# 1. Create media/images directory
print("[1/3] Creating unified image storage...")
media_dir = ROOT_DIR / "media" / "images"
media_dir.mkdir(parents=True, exist_ok=True)
print(f"  [OK] Created: {media_dir}")

# 2. Update local_image_generator.py with unified storage
print("\n[2/3] Updating local_image_generator.py...")

local_img_gen_content = '''"""
Local Image Generator v4 - Unified storage in media/images/.
"""
import os
import logging
import ctypes
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
                      filename: Optional[str] = None,
                      auto_translate: bool = True) -> Optional[Dict[str, Any]]:
        """
        Generate image and save to unified storage.
        
        Args:
            prompt: Image description
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
            
            # Save to unified storage
            if not filename:
                import time
                filename = f"sd_{int(time.time())}.png"
            
            save_path = self.storage_dir / filename
            save_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Use short path for SD compatibility
            safe_path = self._get_safe_path(str(save_path))
            
            image.save(safe_path, "PNG")
            
            return {
                "local_path": str(save_path),
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
'''

write_file("AI_SMM_Work_Architecture_A75/local_image_generator.py", local_img_gen_content)

# 3. Update openai_client.py with unified storage
print("[3/3] Updating openai_client.py with unified storage...")

openai_client_content = '''"""
OpenAI Client v3.2 - Unified storage in media/images/.
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
                      filename: Optional[str] = None,
                      model: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Generate image and save to unified storage.
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
            
            save_path = self.storage_dir / filename
            save_path.parent.mkdir(parents=True, exist_ok=True)
            
            result = {
                "model_used": target_model,
                "source": "openai-gpt-image",
                "filename": filename
            }
            
            # Handle base64 response
            if hasattr(image_data, 'b64_json') and image_data.b64_json:
                logger.info("Received base64 image data")
                image_bytes = base64.b64decode(image_data.b64_json)
                
                with open(save_path, 'wb') as f:
                    f.write(image_bytes)
                
                result["local_path"] = str(save_path)
                logger.info(f"Image saved to {save_path} ({len(image_bytes)} bytes)")
                return result
            
            # Handle URL response
            elif hasattr(image_data, 'url') and image_data.url:
                logger.info("Received image URL")
                result["url"] = image_data.url
                
                try:
                    img_response = requests.get(image_data.url, timeout=60)
                    img_response.raise_for_status()
                    
                    with open(save_path, 'wb') as f:
                        f.write(img_response.content)
                    
                    result["local_path"] = str(save_path)
                    logger.info(f"Image downloaded and saved to {save_path}")
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
                    return self.generate_image(prompt, size, filename, model=fallback)
            
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

print("\n" + "="*70)
print("=== Step 4.6 Summary ===")
print("="*70)
print("\nCompleted:")
print("  [OK] Created unified storage: media/images/")
print("  [OK] Updated local_image_generator.py")
print("       - Saves to media/images/ with auto-generated filename")
print("       - Uses short path for Windows compatibility")
print("  [OK] Updated openai_client.py")
print("       - Saves to media/images/ with auto-generated filename")
print("       - Same storage location as SD")

print("\nAll images now saved to:")
print(f"  {media_dir}")

print("\nNext: Run START.bat to test unified storage.")
print("="*70 + "\n")