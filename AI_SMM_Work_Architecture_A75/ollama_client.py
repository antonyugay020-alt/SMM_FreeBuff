"""
Ollama Client v2 - Multi-model support with cloud integration.
"""
import requests
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

class OllamaClient:
    def __init__(self, host: str = "http://localhost:11434", model: str = "qwen3:8b", timeout: int = 120):
        self.host = host.rstrip('/')
        self.model = model
        self.timeout = timeout
        self.session = requests.Session()
        self._available_models: Optional[List[str]] = None
        
    def is_available(self) -> bool:
        """Check if Ollama server is running."""
        try:
            response = self.session.get(f"{self.host}/api/tags", timeout=5)
            return response.status_code == 200
        except requests.exceptions.ConnectionError:
            logger.warning(f"Ollama server not available at {self.host}")
            return False
        except Exception as e:
            logger.error(f"Error checking Ollama availability: {e}")
            return False
    
    def get_available_models(self) -> List[str]:
        """Get list of available models."""
        if self._available_models is not None:
            return self._available_models
        
        if not self.is_available():
            return []
        
        try:
            response = self.session.get(f"{self.host}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                self._available_models = [m["name"] for m in models]
                logger.info(f"Available models: {self._available_models}")
                return self._available_models
        except Exception as e:
            logger.error(f"Error getting available models: {e}")
        
        return []
    
    def is_model_available(self, model_name: Optional[str] = None) -> bool:
        """Check if a specific model is available."""
        model = model_name or self.model
        available = self.get_available_models()
        return model in available
    
    def generate(self, system_prompt: str, user_message: str, temperature: float = 0.7, 
                 model: Optional[str] = None) -> str:
        """
        Generate content using Ollama API.
        
        Args:
            system_prompt: System prompt for the model
            user_message: User message
            temperature: Generation temperature (0.0-1.0)
            model: Model to use (overrides default)
        
        Returns:
            str: Generated text
        """
        target_model = model or self.model
        
        if not self.is_available():
            raise ConnectionError(f"Ollama server not available at {self.host}")
        
        if not self.is_model_available(target_model):
            raise RuntimeError(f"Model {target_model} not found. Available: {self.get_available_models()}")
        
        payload = {
            "model": target_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_ctx": 4096
            }
        }
        
        try:
            logger.info(f"Calling Ollama model {target_model} (temp={temperature})")
            start_time = datetime.now()
            
            response = self.session.post(
                f"{self.host}/api/chat",
                json=payload,
                timeout=self.timeout
            )
            
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"Ollama response received in {elapsed:.2f}s")
            
            if response.status_code != 200:
                raise RuntimeError(f"Ollama API error: {response.status_code} - {response.text}")
            
            result = response.json()
            return result["message"]["content"]
        
        except requests.exceptions.Timeout:
            raise TimeoutError(f"Ollama request timed out after {self.timeout}s")
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(f"Cannot connect to Ollama: {e}")
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            raise
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about available models."""
        return {
            "default_model": self.model,
            "host": self.host,
            "available": self.is_available(),
            "available_models": self.get_available_models()
        }
