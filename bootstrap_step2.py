#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI SMM Manager - Step 2: Cleanup unused models + prepare OpenAI integration.
Frees ~7.8 GB by removing mistral:7b and gemma3:4b.
Adds OpenAI API configuration.
Run: python bootstrap_step2.py
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
print("=== AI SMM Manager - Step 2: Cleanup + OpenAI Prep ===")
print("="*70 + "\n")

# 1. Show current models and sizes
print("[1/4] Current models inventory:")
print("-" * 70)

try:
    result = subprocess.run(
        ["ollama", "list"],
        capture_output=True, text=True, timeout=10
    )
    if result.returncode == 0:
        print(result.stdout)
    else:
        print("  Could not get model list. Is Ollama running?")
except Exception as e:
    print(f"  Error: {e}")

# 2. Ask user which models to remove
print("\n[2/4] Models recommended for removal (not used in SMM workflow):")
print("  - mistral:7b   (~4.4 GB) - outdated version")
print("  - gemma3:4b    (~3.4 GB) - too small for quality tasks")
print("  Total to free: ~7.8 GB\n")

models_to_remove = ["mistral:7b", "gemma3:4b"]

user_input = input("Remove these models? (y/n): ").strip().lower()

if user_input == 'y':
    print("\nRemoving models...")
    for model in models_to_remove:
        print(f"  Removing {model}...", end=" ")
        try:
            result = subprocess.run(
                ["ollama", "rm", model],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                print("OK")
            else:
                print(f"FAILED: {result.stderr.strip()}")
        except Exception as e:
            print(f"ERROR: {e}")
else:
    print("\nSkipping removal. Models kept.")

# 3. Update config.yaml with OpenAI API section
print("\n[3/4] Updating config.yaml with OpenAI API configuration...")

config_content = """# AI SMM Manager - Configuration
# Updated: 2026-11-10 (Step 2)

hardware:
  gpu_vram_gb: 8
  cpu_cores: 24
  ram_gb: 32

ollama:
  host: "http://localhost:11434"
  timeout: 120
  
  # Model roles - LOCAL ONLY (no paid Ollama cloud)
  models:
    author: "qwen3:8b"                  # Fast generation, good Russian
    reviewer: "deepseek-r1:8b"          # Reasoning model - excellent critical review
    strategist: "deepseek-r1:8b"        # Strategy and analysis
    hashtag_generator: "llama3.1:8b"    # Structured data (hashtags, SEO)
    
    # Fallback models
    fallback_author: "llama3.1:8b"
    fallback_reviewer: "mistral:7b"
    
    # Auxiliary
    embedding: "nomic-embed-text:latest"
    code_assistant: "qwen2.5-coder:7b"

# OpenAI API - for DALL-E 3, Whisper, GPT-4o-mini
openai:
  api_key: ""                           # <-- INSERT YOUR KEY HERE
  enabled: false                        # Set to true after adding key
  
  # Model roles (when enabled)
  models:
    image_generator: "dall-e-3"         # High-quality image generation
    transcriber: "whisper-1"            # Audio/video transcription
    backup_reviewer: "gpt-4o-mini"      # Fast, cheap reviewer alternative
    backup_author: "gpt-4o-mini"        # Fast generation alternative
  
  # Limits
  monthly_budget_usd: 10                # Safety limit
  max_image_size: "1024x1024"
  max_audio_minutes: 30

media_processing:
  # Local fallback when OpenAI unavailable
  local_image_model: "stable-diffusion-v1-5"
  local_whisper_model: "base"
  fallback_to_cloud_if_vram_exceeded: true
  max_local_video_resolution: "1080p"

storage:
  database: "data/ai_smm_manager.db"
  projects_dir: "data/projects"
  checkpoints_dir: "data/checkpoints"
  logs_dir: "data/logs"
  media_dir: "media"

quality:
  min_passing_score: 0.7
  max_revision_attempts: 3
  evidence_validation: true
  use_different_models: true
  prefer_cloud_for_review: false
  fallback_to_local_if_cloud_fails: true
"""

write_file("config/config.yaml", config_content)

# 4. Create openai_client.py stub
print("[4/4] Creating openai_client.py (stub for Step 3)...")

openai_client_content = '''"""
OpenAI Client - Integration with OpenAI API (DALL-E 3, Whisper, GPT-4o-mini).
Stub version - will be fully implemented in Step 3.
"""
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class OpenAIClient:
    def __init__(self, api_key: str = "", enabled: bool = False):
        self.api_key = api_key
        self.enabled = enabled and bool(api_key)
        self._client = None
        
        if self.enabled:
            try:
                import openai
                self._client = openai.OpenAI(api_key=api_key)
                logger.info("OpenAI client initialized successfully")
            except ImportError:
                logger.error("openai package not installed. Run: pip install openai")
                self.enabled = False
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                self.enabled = False
        else:
            logger.info("OpenAI client disabled (no API key or enabled=false)")
    
    def is_available(self) -> bool:
        return self.enabled and self._client is not None
    
    def generate_image(self, prompt: str, size: str = "1024x1024", quality: str = "hd") -> Optional[str]:
        """
        Generate image using DALL-E 3.
        Returns URL of generated image.
        """
        if not self.is_available():
            logger.warning("OpenAI not available for image generation")
            return None
        
        try:
            response = self._client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size=size,
                quality=quality,
                n=1
            )
            return response.data[0].url
        except Exception as e:
            logger.error(f"DALL-E 3 generation failed: {e}")
            return None
    
    def transcribe_audio(self, audio_file_path: str, language: Optional[str] = None) -> Optional[str]:
        """
        Transcribe audio using Whisper API.
        Returns transcription text.
        """
        if not self.is_available():
            logger.warning("OpenAI not available for transcription")
            return None
        
        try:
            with open(audio_file_path, "rb") as audio_file:
                kwargs = {"model": "whisper-1", "file": audio_file}
                if language:
                    kwargs["language"] = language
                response = self._client.audio.transcriptions.create(**kwargs)
            return response.text
        except Exception as e:
            logger.error(f"Whisper transcription failed: {e}")
            return None
    
    def chat(self, system_prompt: str, user_message: str, model: str = "gpt-4o-mini") -> Optional[str]:
        """
        Chat completion using GPT-4o-mini (fast and cheap).
        Returns response text.
        """
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
                temperature=0.7,
                max_tokens=1000
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI chat failed: {e}")
            return None
'''

write_file("AI_SMM_Work_Architecture_A75/openai_client.py", openai_client_content)

# 5. Summary
print("\n" + "="*70)
print("=== Step 2 Summary ===")
print("="*70)
print("\nCompleted:")
if user_input == 'y':
    print("  [OK] Removed unused models (freed ~7.8 GB)")
else:
    print("  [SKIP] Models removal skipped")
print("  [OK] Updated config.yaml with OpenAI section")
print("  [OK] Created openai_client.py stub")

print("\nNext steps:")
print("  1. Open config/config.yaml and add your OpenAI API key:")
print('     openai:')
print('       api_key: "sk-..."')
print('       enabled: true')
print("  2. Install openai package:")
print("     venv\\Scripts\\pip.exe install openai")
print("  3. Run START.bat to verify")

print("\nIn Step 3 we will fully integrate DALL-E 3 and Whisper.")
print("="*70 + "\n")