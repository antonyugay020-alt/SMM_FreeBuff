#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Step 1 (Correct Order): Connect Real Local AI via LM Studio API.
Creates local_llm_client.py + patches gui_ai_panel.py to use it.
Run: python fix_local_ai_integration.py
"""

from pathlib import Path
import json

ROOT_DIR = Path(__file__).resolve().parent
BASE = ROOT_DIR / "AI_SMM_Work_Architecture_A75"

def write(rel, content):
    p = BASE / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding='utf-8', newline='\n')
    print(f"  [OK] {rel}")

print("\n=== Step 1: Real Local AI Integration ===\n")

# 1. Create local_llm_client.py
print("[1/2] Creating local_llm_client.py...")

llm_client_code = r'''"""Client for communicating with Local LLM (LM Studio / Ollama compatible)."""
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
'''

write("local_llm_client.py", llm_client_code)

# 2. Patch gui_ai_panel.py to use real client instead of mock
print("[2/2] Integrating Local LLM into gui_ai_panel.py...")

panel_path = BASE / "gui_ai_panel.py"
ap_content = panel_path.read_text(encoding='utf-8')

# Add import at top
if 'from local_llm_client import' not in ap_content:
    ap_content = ap_content.replace(
        'from ai_task_router import AITaskRouter',
        'from ai_task_router import AITaskRouter\nfrom local_llm_client import LocalLLMClient'
    )

# Initialize client in __init__
old_init = '''    def __init__(self, app_state: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.state = app_state
        self.proposal_engine = ProposalEngine()
        self.task_router = AITaskRouter()
        self.ai_client = None'''

new_init = '''    def __init__(self, app_state: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.state = app_state
        self.proposal_engine = ProposalEngine()
        self.task_router = AITaskRouter()
        # Try connecting to local LLM (LM Studio default port 1235)
        self.local_llm = LocalLLMClient(base_url="http://localhost:1235/v1")
        if self.local_llm.available:
            logger.info("Connected to Local LLM successfully!")
        else:
            logger.warning("Local LLM unavailable. Falling back to simulation.")
        self.ai_client = None'''

ap_content = ap_content.replace(old_init, new_init)

# Replace _simulate_response logic with REAL call when possible
start_marker = "    def _simulate_response(self, user_input: str):"
end_marker_search_idx = ap_content.find(start_marker)
if end_marker_search_idx != -1:
    next_def_idx = ap_content.find("    def ", end_marker_search_idx + len(start_marker))
    if next_def_idx == -1: next_def_idx = len(ap_content)
    
    current_block = ap_content[end_marker_search_idx:next_def_idx]
    
    new_block = '''    def _simulate_response(self, user_input: str):
        """Generate response using Local LLM or fallback to mock."""
        lower_input = user_input.lower()
        
        # ATTEMPT REAL GENERATION VIA LOCAL LLM FIRST
        if hasattr(self, 'local_llm') and getattr(self.local_llm, 'available', False):
            sys_prompt = ("Ты опытный SMM менеджер и стратег. Помогай пользователю создавать кампании, "
                          "стратегии и контент-планы на русском языке. Будь лаконичен, но информативен.")
            
            try:
                # Blocking call acceptable for short queries; consider threading for long ones later
                real_resp = self.local_llm.generate(user_input, system_prompt=sys_prompt)
                
                if real_resp and len(real_resp.strip()) > 10:
                    self._add_bubble("assistant", real_resp)
                    
                    # Parse potential proposals automatically
                    prop_cat = self._detect_category(user_input)
                    proposal = self.proposal_engine.create_from_ai_response(real_resp, context=user_input, category=prop_cat)
                    if proposal:
                        self._show_proposal_card(proposal)
                        
                    logger.info("Used REAL Local LLM response.")
                    return  # Exit early – no need for mocks
                    
            except Exception as ex:
                logger.warning(f"Local LLM attempt failed gracefully falling back: {ex}")
        
        # ORIGINAL MOCK LOGIC BELOW (unchanged behavior when offline/error)
        if "вариант" in lower_input or "идея" in lower_input or "стратегия" in lower_input:
            response = f"""Я проанализировал ваш запрос «{user_input}». Вот несколько вариантов решения:

Вариант 1: Агрессивный маркетинг
Описание: Фокус на быстрых результатах и скидках.
Плюсы: Быстрый рост базы клиентов.
Минусы: Низкая лояльность, демпинг цен.

Вариант 2: Премиум позиционирование
Описание: Акцент на эксклюзивности и качестве сервиса.
Плюсы: Высокий средний чек, лояльная аудитория.
Минусы: Долгий цикл продаж.

Вариант 3: Гибридный подход
Описание: Баланс между доступностью и качеством.
Плюсы: Универсальность.
Минусы: Размытое позиционирование."""
            
            self._add_bubble("assistant", response)
            
            proposal = self.proposal_engine.create_from_ai_response(response, context=user_input, category="strategy")
            if proposal:
                self._show_proposal_card(proposal)
                
        else:
            response = f"AI получил сообщение: «{user_input}». Это тестовый режим."
            self._add_bubble("assistant", response)

'''
    
    ap_content = ap_content[:end_marker_search_idx] + new_block + ap_content[next_def_idx:]
else:
    print("[!] Could not locate _simulate_response boundary exactly.")

panel_path.write_text(ap_content, encoding='utf-8', newline='\n')
print("  [OK] Updated GUI Panel Logic")

print("\n=== Setup Instructions ===")
print("Make sure your LM Studio Server is RUNNING on PORT 1235:")
print("   Settings -> Server Tab -> Start Server")
print("Model should be loaded (e.g., qwen2.5-coder)")
print("\nRun START.bat now!")