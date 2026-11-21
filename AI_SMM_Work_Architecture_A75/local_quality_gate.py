"""
Local Quality Gate v6 - Hybrid: Local Ollama + OpenAI fallback.
Uses local models by default, OpenAI as optional alternative.
"""
from typing import Dict, Any, Optional
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

    def __init__(self, ollama_client=None, openai_client=None, config: Optional[Dict[str, Any]] = None):
        self.min_passing_score = 0.7
        
        if ollama_client is None:
            from ollama_client import OllamaClient
            self.ollama = OllamaClient()
        else:
            self.ollama = ollama_client
        
        self.openai = openai_client
        
        # Load model configuration
        if config:
            models_config = config.get("ollama", {}).get("models", {})
            self.author_model = models_config.get("author", "qwen3:8b")
            self.reviewer_model = models_config.get("reviewer", "deepseek-r1:8b")
            self.fallback_author = models_config.get("fallback_author", "llama3.1:8b")
            self.fallback_reviewer = models_config.get("fallback_reviewer", "mistral:7b")
            self.use_different_models = config.get("quality", {}).get("use_different_models", True)
            self.prefer_openai = config.get("openai", {}).get("enabled", False)
        else:
            self.author_model = "qwen3:8b"
            self.reviewer_model = "deepseek-r1:8b"
            self.fallback_author = "llama3.1:8b"
            self.fallback_reviewer = "mistral:7b"
            self.use_different_models = True
            self.prefer_openai = False
        
        logger.info(f"Quality Gate initialized:")
        logger.info(f"  Author model: {self.author_model}")
        logger.info(f"  Reviewer model: {self.reviewer_model} (reasoning)")
        logger.info(f"  OpenAI enabled: {self.prefer_openai and self.openai is not None}")

    def _call_model(self, system_prompt: str, user_message: str, temperature: float = 0.7, 
                    model: Optional[str] = None, max_retries: int = 2, use_openai: bool = False) -> str:
        """Call model with automatic fallback."""
        
        # Try OpenAI first if enabled and requested
        if use_openai and self.openai and self.openai.is_available():
            try:
                logger.info("Using OpenAI GPT-4o-mini")
                response = self.openai.chat(system_prompt, user_message, model="gpt-4o-mini", temperature=temperature)
                if response:
                    return response
            except Exception as e:
                logger.warning(f"OpenAI failed, falling back to local: {e}")
        
        # Local Ollama with fallback
        target_model = model or self.author_model
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                return self.ollama.generate(system_prompt, user_message, temperature, model=target_model)
            except Exception as e:
                last_error = e
                logger.warning(f"Model {target_model} failed (attempt {attempt + 1}/{max_retries + 1}): {e}")
                
                if attempt < max_retries:
                    if target_model == self.author_model:
                        target_model = self.fallback_author
                        logger.info(f"Switching to fallback author: {target_model}")
                    elif target_model == self.reviewer_model:
                        target_model = self.fallback_reviewer
                        logger.info(f"Switching to fallback reviewer: {target_model}")
                    else:
                        break
        
        raise last_error

    def _extract_json(self, response: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from response."""
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        pattern = r'```json\s*(.*?)\s*```'
        json_match = re.search(pattern, response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        json_match = re.search(r'\{.*?\}', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass
        
        return None

    def generate_content(self, request_text: str, project_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        user_message = request_text
        if project_context:
            user_message += f"\n\nКонтекст проекта:\n{json.dumps(project_context, ensure_ascii=False, indent=2)}"
        
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
        user_message = f"Запрос:\n{request_text}\n\nКонтент для проверки:\n{json.dumps(content, ensure_ascii=False, indent=2)}"
        
        # Try OpenAI first if enabled
        reviewer_model_used = self.reviewer_model
        try:
            response = self._call_model(self.REVIEWER_SYSTEM_PROMPT, user_message, temperature=0.2, 
                                       model=self.reviewer_model, use_openai=self.prefer_openai)
            logger.info(f"Reviewer response (first 200 chars): {response[:200]}")
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
        
        if "reviews" not in review_data:
            review_data["reviews"] = []
        if "overall_score" not in review_data:
            review_data["overall_score"] = 0.0
        if "approved" not in review_data:
            review_data["approved"] = False
        if "final_feedback" not in review_data:
            review_data["final_feedback"] = "Обратная связь не предоставлена"
        
        approved = review_data.get("approved", False)
        for r in review_data.get("reviews", []):
            if not r.get("passed", True):
                approved = False
        
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
