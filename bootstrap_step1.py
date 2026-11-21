#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI SMM Manager - Step 1: Optimize config for local models only.
Removes paid cloud models, sets deepseek-r1:8b as reviewer (reasoning model).
Run: python bootstrap_step1.py
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

print("\n=== AI SMM Manager - Step 1: Local Models Optimization ===")
print(f"Root: {ROOT_DIR}\n")

# 1. Check venv
print("[1/3] Checking virtual environment...")
venv_python = ROOT_DIR / "venv" / "Scripts" / "python.exe"
if not venv_python.exists():
    print("  ERROR: venv not found.")
    input("Press Enter to exit")
    sys.exit(1)
print("  OK: venv found\n")

# 2. Update config.yaml - remove paid cloud models, use deepseek-r1 as reviewer
print("[2/3] Updating config.yaml with optimal local models...")

config_content = """# AI SMM Manager - Configuration (Local Models Only)
# Updated: 2026-11-10
# Note: Cloud models (gpt-oss:20b-cloud, gemma4:cloud) require paid subscription.
# Using fully local setup with deepseek-r1:8b as reasoning reviewer.

hardware:
  gpu_vram_gb: 8
  cpu_cores: 24
  ram_gb: 32

ollama:
  host: "http://localhost:11434"
  timeout: 120
  
  # Model roles - ALL LOCAL (no paid cloud)
  models:
    author: "qwen3:8b"                  # Fast generation, good Russian
    reviewer: "deepseek-r1:8b"          # Reasoning model - excellent for critical review
    strategist: "deepseek-r1:8b"        # Same model for strategy (reasoning)
    hashtag_generator: "llama3.1:8b"    # Good for structured data
    
    # Fallback models (all local)
    fallback_author: "llama3.1:8b"      # If qwen3 unavailable
    fallback_reviewer: "mistral:7b"     # If deepseek-r1 unavailable
    
    # Auxiliary
    embedding: "nomic-embed-text:latest"  # Search and classification
    code_assistant: "qwen2.5-coder:7b"    # Technical tasks
    
  # All available local models
  available_local_models:
    - qwen3:8b
    - qwen2.5-coder:7b
    - llama3.1:8b
    - deepseek-r1:8b
    - mistral:7b
    - gemma3:4b
    - nomic-embed-text:latest

media_processing:
  local_sd_model: "stable-diffusion-v1-5"
  local_whisper_model: "base"
  fallback_to_cloud_if_vram_exceeded: true
  max_local_video_resolution: "1080p"

cloud_apis:
  openai:
    api_key: ""
    enabled: false
  stability_ai:
    api_key: ""
    enabled: false

storage:
  database: "data/ai_smm_manager.db"
  projects_dir: "data/projects"
  checkpoints_dir: "data/checkpoints"
  logs_dir: "data/logs"

quality:
  min_passing_score: 0.7
  max_revision_attempts: 3
  evidence_validation: true
  
  # Multi-model quality settings (all local now)
  use_different_models: true
  prefer_cloud_for_review: false          # Changed: no cloud available
  fallback_to_local_if_cloud_fails: true
"""

write_file("config/config.yaml", config_content)

# 3. Update local_quality_gate.py - better handling of model fallback
print("[3/3] Updating local_quality_gate.py with improved fallback logic...")

lqg_content = '''"""
Local Quality Gate v5 - Optimized for local models.
Uses deepseek-r1:8b (reasoning) as reviewer for better critical analysis.
"""
from typing import Dict, Any, Optional, List
import json
import hashlib
import logging
import re

logger = logging.getLogger(__name__)

class LocalQualityGate:
    AUTHOR_SYSTEM_PROMPT = """Ты — профессиональный SMM-специалист. Создай качественный контент для социальных сетей на основе запроса пользователя.
ПРАВИЛА:
1. Строго следуй требованиям пользователя (тональность, формат, длина).
2. КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО выдумывать факты, цены, услуги или статистику. Если их нет в запросе — не упоминай их.
3. Используй только информацию из контекста проекта или общие знания.
4. Отвечай СТРОГО в формате JSON:
{
  "content": "основной текст поста",
  "hashtags": ["#хэштег1", "#хэштег2"],
  "call_to_action": "призыв к действию",
  "metadata": {"platform": "instagram", "tone": "дружелюбный", "word_count": 0}
}"""

    REVIEWER_SYSTEM_PROMPT = """Ты — независимый критический редактор с аналитическим складом ума. Твоя задача — строго проверить контент по 4 критериям.

КРИТЕРИИ ПРОВЕРКИ:
1. REQUIREMENTS: Точное соответствие запросу пользователя (тональность, формат, длина).
2. COMPLETENESS: Все необходимые элементы присутствуют (текст, хэштеги, призыв к действию).
3. EVIDENCE: НЕТ ЛИ выдуманных фактов, цен, услуг или статистики? Если в запросе явно сказано "не выдумывай цены" — наличие любых цен в контенте автоматически означает ПРОВАЛ по этому критерию.
4. FORMAT_TONE: Соответствие формата и тональности целевой платформе (Instagram, VK, Telegram и т.д.).

ПРАВИЛА:
- Будь строгим, но справедливым.
- Если контент нарушает запрет на выдумывание фактов/цен — немедленно отклоняй (approved: false).
- Указывай конкретные замечания в feedback.
- Не придумывай требования, которых не было в запросе.

Отвечай СТРОГО в формате JSON:
{
  "reviews": [
    {"criterion": "REQUIREMENTS", "passed": true, "score": 0.9, "feedback": "Соответствует запросу", "suggestions": []},
    {"criterion": "COMPLETENESS", "passed": true, "score": 1.0, "feedback": "Все элементы на месте", "suggestions": []},
    {"criterion": "EVIDENCE", "passed": true, "score": 1.0, "feedback": "Факты не выдуманы", "suggestions": []},
    {"criterion": "FORMAT_TONE", "passed": true, "score": 0.95, "feedback": "Тон подходит для Instagram", "suggestions": []}
  ],
  "overall_score": 0.94,
  "approved": true,
  "final_feedback": "Контент одобрен. Все правила соблюдены."
}"""

    def __init__(self, ollama_client=None, config: Optional[Dict[str, Any]] = None):
        self.min_passing_score = 0.7
        
        if ollama_client is None:
            from ollama_client import OllamaClient
            self.ollama = OllamaClient()
        else:
            self.ollama = ollama_client
        
        # Load model configuration
        if config:
            models_config = config.get("ollama", {}).get("models", {})
            self.author_model = models_config.get("author", "qwen3:8b")
            self.reviewer_model = models_config.get("reviewer", "deepseek-r1:8b")
            self.fallback_author = models_config.get("fallback_author", "llama3.1:8b")
            self.fallback_reviewer = models_config.get("fallback_reviewer", "mistral:7b")
            self.use_different_models = config.get("quality", {}).get("use_different_models", True)
            self.prefer_cloud = config.get("quality", {}).get("prefer_cloud_for_review", False)
            self.fallback_to_local = config.get("quality", {}).get("fallback_to_local_if_cloud_fails", True)
        else:
            # Default configuration - all local
            self.author_model = "qwen3:8b"
            self.reviewer_model = "deepseek-r1:8b"
            self.fallback_author = "llama3.1:8b"
            self.fallback_reviewer = "mistral:7b"
            self.use_different_models = True
            self.prefer_cloud = False
            self.fallback_to_local = True
        
        logger.info(f"Quality Gate initialized:")
        logger.info(f"  Author model: {self.author_model}")
        logger.info(f"  Reviewer model: {self.reviewer_model} (reasoning)")
        logger.info(f"  Fallback author: {self.fallback_author}")
        logger.info(f"  Fallback reviewer: {self.fallback_reviewer}")
        logger.info(f"  Use different models: {self.use_different_models}")

    def _call_model(self, system_prompt: str, user_message: str, temperature: float = 0.7, 
                    model: Optional[str] = None, max_retries: int = 2) -> str:
        """Call model with automatic fallback on failure."""
        target_model = model or self.author_model
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                return self.ollama.generate(system_prompt, user_message, temperature, model=target_model)
            except Exception as e:
                last_error = e
                logger.warning(f"Model {target_model} failed (attempt {attempt + 1}/{max_retries + 1}): {e}")
                
                if attempt < max_retries:
                    # Try fallback
                    if target_model == self.author_model:
                        target_model = self.fallback_author
                        logger.info(f"Switching to fallback author: {target_model}")
                    elif target_model == self.reviewer_model:
                        target_model = self.fallback_reviewer
                        logger.info(f"Switching to fallback reviewer: {target_model}")
                    else:
                        break  # No more fallbacks
        
        raise last_error  # Re-raise last error if all attempts failed

    def _extract_json(self, response: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from response, handling markdown code blocks and extra text."""
        # Try direct parse first
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        # Try to extract from markdown code block
        pattern = r'```json\\s*(.*?)\\s*```'
        json_match = re.search(pattern, response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Try to find JSON object in text
        json_match = re.search(r'\\{.*?\\}', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass
        
        return None

    def generate_content(self, request_text: str, project_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        user_message = request_text
        if project_context:
            user_message += f"\\n\\nКонтекст проекта:\\n{json.dumps(project_context, ensure_ascii=False, indent=2)}"
        
        response = self._call_model(self.AUTHOR_SYSTEM_PROMPT, user_message, model=self.author_model)
        logger.info(f"Author response (first 200 chars): {response[:200]}")
        
        result = self._extract_json(response)
        if result:
            result["_request_hash"] = hashlib.sha256(request_text.encode('utf-8')).hexdigest()
            return result
        else:
            logger.error(f"Failed to parse author response: {response[:500]}")
            return {"error": "Invalid JSON from author", "raw": response}

    def review_content(self, request_text: str, content: Dict[str, Any]) -> Dict[str, Any]:
        user_message = f"Запрос:\\n{request_text}\\n\\nКонтент для проверки:\\n{json.dumps(content, ensure_ascii=False, indent=2)}"
        
        # Try reviewer model with automatic fallback
        try:
            response = self._call_model(self.REVIEWER_SYSTEM_PROMPT, user_message, temperature=0.2, model=self.reviewer_model)
            logger.info(f"Reviewer response (first 200 chars): {response[:200]}")
            reviewer_model_used = self.reviewer_model
        except Exception as e:
            logger.error(f"All reviewer models failed: {e}")
            return {
                "approved": False,
                "error": f"All reviewer models failed: {str(e)}",
                "final_feedback": "Ошибка рецензирования: все модели недоступны"
            }
        
        review_data = self._extract_json(response)
        
        if not review_data:
            logger.error(f"Failed to parse reviewer response: {response[:500]}")
            return {
                "approved": False,
                "error": "Invalid JSON from reviewer",
                "raw": response,
                "final_feedback": "Не удалось разобрать ответ рецензента"
            }
        
        # Ensure required fields exist
        if "reviews" not in review_data:
            review_data["reviews"] = []
        if "overall_score" not in review_data:
            review_data["overall_score"] = 0.0
        if "approved" not in review_data:
            review_data["approved"] = False
        if "final_feedback" not in review_data:
            review_data["final_feedback"] = "Обратная связь не предоставлена"
        
        # Check if any review failed
        approved = review_data.get("approved", False)
        for r in review_data.get("reviews", []):
            if not r.get("passed", True):
                approved = False
        
        # Check overall score
        if review_data.get("overall_score", 0) < self.min_passing_score:
            approved = False
        
        review_data["approved"] = approved
        review_data["reviewer_model"] = reviewer_model_used
        
        return review_data
    
    def full_quality_gate(self, request_text: str, project_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        logger.info("Starting full quality gate cycle...")
        
        content = self.generate_content(request_text, project_context)
        if "error" in content:
            return {"approved": False, "error": content["error"], "raw": content.get("raw", "")}
        
        review_result = self.review_content(request_text, content)
        
        return {
            "content": content,
            "review": review_result,
            "approved": review_result.get("approved", False)
        }
'''

write_file("AI_SMM_Work_Architecture_A75/local_quality_gate.py", lqg_content)

print("\n=== Step 1 completed successfully ===")
print("\nConfiguration changes:")
print("- Author: qwen3:8b (fast generation)")
print("- Reviewer: deepseek-r1:8b (reasoning model - better analysis)")
print("- Fallback author: llama3.1:8b")
print("- Fallback reviewer: mistral:7b")
print("- All models are LOCAL (no paid cloud)")
print("\nNext: Run START.bat to test with deepseek-r1 as reviewer.")