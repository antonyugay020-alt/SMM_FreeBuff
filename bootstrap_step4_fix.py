#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI SMM Manager - Step 4 Fix: Correct torch attribute name.
Run: python bootstrap_step4_fix.py
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

print("\n=== AI SMM Manager - Step 4 Fix: torch attribute ===\n")

# Fix local_image_generator.py - replace total_mem with total_memory
print("[1/1] Fixing local_image_generator.py...")

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
            props = torch.cuda.get_device_properties(0)
            self.vram_gb = props.total_memory / (1024**3)
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
                    safety_checker=None,
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

print("\n=== Fix applied ===")
print("Run START.bat to test.")