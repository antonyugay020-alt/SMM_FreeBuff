#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI SMM Manager - Step 4.5 Fix: Handle base64 image response from gpt-image-2.5-sunburst.
Run: python bootstrap_step4_5_fix.py
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

print("\n=== AI SMM Manager - Step 4.5 Fix: Base64 Image Handling ===\n")

print("[1/1] Updating openai_client.py to handle base64 images...")

openai_client_content = '''"""
OpenAI Client v3.1 - Fixed base64 image handling for gpt-image-2.5-sunburst.
"""
import logging
import requests
import base64
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
    def __init__(self, api_key: str = "", enabled: bool = False):
        self.api_key = api_key
        self.enabled = enabled and bool(api_key)
        self._client = None
        self._available_models: Optional[List[str]] = None
        self._image_model: Optional[str] = None
        
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
                      model: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Generate image using GPT-Image models.
        Handles both URL and base64 responses.
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
            
            result = {
                "model_used": target_model,
                "source": "openai-gpt-image"
            }
            
            # Handle base64 response (gpt-image-2.5-sunburst returns b64_json)
            if hasattr(image_data, 'b64_json') and image_data.b64_json:
                logger.info("Received base64 image data")
                image_bytes = base64.b64decode(image_data.b64_json)
                
                if save_path:
                    save_path_obj = Path(save_path)
                    save_path_obj.parent.mkdir(parents=True, exist_ok=True)
                    
                    with open(save_path_obj, 'wb') as f:
                        f.write(image_bytes)
                    
                    result["local_path"] = str(save_path_obj)
                    logger.info(f"Image saved to {save_path_obj} ({len(image_bytes)} bytes)")
                
                result["format"] = "base64"
                return result
            
            # Handle URL response (older models)
            elif hasattr(image_data, 'url') and image_data.url:
                logger.info("Received image URL")
                result["url"] = image_data.url
                
                if save_path:
                    try:
                        img_response = requests.get(image_data.url, timeout=60)
                        img_response.raise_for_status()
                        
                        save_path_obj = Path(save_path)
                        save_path_obj.parent.mkdir(parents=True, exist_ok=True)
                        
                        with open(save_path_obj, 'wb') as f:
                            f.write(img_response.content)
                        
                        result["local_path"] = str(save_path_obj)
                        logger.info(f"Image downloaded and saved to {save_path_obj}")
                    except Exception as e:
                        logger.error(f"Failed to download image: {e}")
                
                result["format"] = "url"
                return result
            
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
                    return self.generate_image(prompt, size, save_path, model=fallback)
            
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
    
    def translate_to_english(self, text: str) -> str:
        if not self.is_available():
            return text
        
        system_prompt = """You are a professional translator. Translate the following text to English.
Return ONLY the English translation, no explanations, no quotes.
Preserve all details and descriptive elements."""
        
        result = self.chat(system_prompt, text, model="gpt-4o-mini", temperature=0.3)
        return result.strip() if result else text
'''

write_file("AI_SMM_Work_Architecture_A75/openai_client.py", openai_client_content)

print("\n=== Fix applied ===")
print("Run START.bat to test image generation again.")
print("\nChanges:")
print("  - Added base64 image handling for gpt-image-2.5-sunburst")
print("  - Supports both URL and base64 response formats")
print("  - Logs image size when saving")