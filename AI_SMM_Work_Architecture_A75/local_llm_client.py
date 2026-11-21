"""Client for communicating with Local LLM (LM Studio / Ollama compatible)."""
import logging
import requests
import json
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class LocalLLMClient:
    """Handles communication with a local OpenAI-compatible API server."""
    
    def __init__(self, base_url: str = "http://localhost:1235/v1", model_name: str = "auto"):
        self.base_url = base_url.rstrip('/')
        self.model_name = model_name
        self.timeout = 60  # seconds
        
        # Test connection on init
        if not self.test_connection():
            logger.warning("Could not connect to local LLM server. Using fallback mode.")
            self.available = False
        else:
            self.available = True
            # Auto-detect loaded model if 'auto' specified
            if self.model_name == "auto":
                models = self.get_available_models()
                if models:
                    self.model_name = models[0]
                    logger.info(f"Auto-detected model: {self.model_name}")
    
    def test_connection(self) -> bool:
        """Check if the server is reachable."""
        try:
            resp = requests.get(f"{self.base_url}/models", timeout=5)
            return resp.status_code == 200
        except Exception as e:
            logger.debug(f"LML Connection failed: {e}")
            return False
    
    def generate(self, prompt: str, system_prompt: str = "", temperature: float = 0.7, max_tokens: int = 2048) -> Optional[str]:
        """Send request to local LLM and get response text."""
        if not self.available:
            return None
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }
        
        try:
            logger.info(f"Sending request to {self.base_url}/chat/completions")
            resp = requests.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=self.timeout
            )
            
            if resp.status_code != 200:
                logger.error(f"LLM Error {resp.status_code}: {resp.text[:200]}")
                return None
            
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            logger.info(f"Received response length: {len(content)} chars")
            return content
            
        except requests.exceptions.Timeout:
            logger.error("LLM Request timed out")
            return None
        except Exception as e:
            logger.error(f"LLM Generation error: {e}")
            return None
    
    def get_available_models(self) -> List[str]:
        """Fetch list of loaded models from server."""
        if not self.available:
            return []
        try:
            resp = requests.get(f"{self.base_url}/models", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                return [m["id"] for m in data.get("data", [])]
        except Exception:
            pass
        return []
