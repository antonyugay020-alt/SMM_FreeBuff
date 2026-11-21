#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI SMM Manager - Sprint 10 Fix: Correct regex escaping for Python 3.12+
Run: python bootstrap_sprint10_fix.py
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

print("\n=== AI SMM Manager - Sprint 10 Fix: Regex Escaping ===")
print(f"Root: {ROOT_DIR}\n")

# 1. Check venv
print("[1/2] Checking virtual environment...")
venv_python = ROOT_DIR / "venv" / "Scripts" / "python.exe"
if not venv_python.exists():
    print("  ERROR: venv not found.")
    input("Press Enter to exit")
    sys.exit(1)
print("  OK: venv found\n")

# 2. Update local_quality_gate.py with correct regex
print("[2/2] Updating local_quality_gate.py with fixed regex...")

lqg_content = '''"""
Local Quality Gate v2 - Better JSON parsing and error handling.
"""
from typing import Dict, Any, Optional
import json
import hashlib
import logging
import re

logger = logging.getLogger(__name__)

class LocalQualityGate:
    AUTHOR_SYSTEM_PROMPT = """You are a professional SMM specialist. Create high-quality social media content based on the user request.
RULES:
1. Strictly follow user requirements (tone, format, length).
2. DO NOT invent facts, prices, services, or statistics. If unknown, state it.
3. Use only project context or general knowledge.
Respond STRICTLY in JSON format:
{
  "content": "main text",
  "hashtags": ["list", "of", "hashtags"],
  "call_to_action": "CTA text",
  "metadata": {"platform": "instagram", "tone": "friendly", "word_count": 0}
}"""

    REVIEWER_SYSTEM_PROMPT = """You are an independent critical editor. Strictly check the content against 4 criteria:
1. REQUIREMENTS: Does it match user request?
2. COMPLETENESS: Are all elements present?
3. EVIDENCE: Are there any invented facts, prices, or services?
4. FORMAT_TONE: Does it match the target platform?
RULES: Be strict. If content violates "do not invent prices" rule, reject immediately.
Respond STRICTLY in JSON format:
{
  "reviews": [{"criterion": "EVIDENCE", "passed": true, "score": 1.0, "feedback": "No invented facts", "suggestions": []}],
  "overall_score": 0.9,
  "approved": true,
  "final_feedback": "Content approved, rules followed"
}"""

    def __init__(self, ollama_client=None, model_name: str = "qwen3:8b"):
        self.model = model_name
        self.min_passing_score = 0.7
        if ollama_client is None:
            from ollama_client import OllamaClient
            self.ollama = OllamaClient(model=model_name)
        else:
            self.ollama = ollama_client

    def _call_model(self, system_prompt: str, user_message: str, temperature: float = 0.7) -> str:
        return self.ollama.generate(system_prompt, user_message, temperature)

    def _extract_json(self, response: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from response, handling markdown code blocks and extra text."""
        # Try direct parse first
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        # Try to extract from markdown code block using raw string with proper escaping
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
            user_message += f"\\n\\nProject Context:\\n{json.dumps(project_context, ensure_ascii=False, indent=2)}"
        
        response = self._call_model(self.AUTHOR_SYSTEM_PROMPT, user_message)
        logger.info(f"Author response (first 200 chars): {response[:200]}")
        
        result = self._extract_json(response)
        if result:
            result["_request_hash"] = hashlib.sha256(request_text.encode('utf-8')).hexdigest()
            return result
        else:
            logger.error(f"Failed to parse author response: {response[:500]}")
            return {"error": "Invalid JSON from author", "raw": response}

    def review_content(self, request_text: str, content: Dict[str, Any]) -> Dict[str, Any]:
        user_message = f"Request:\\n{request_text}\\n\\nContent to review:\\n{json.dumps(content, ensure_ascii=False, indent=2)}"
        
        response = self._call_model(self.REVIEWER_SYSTEM_PROMPT, user_message, temperature=0.2)
        logger.info(f"Reviewer response (first 200 chars): {response[:200]}")
        
        review_data = self._extract_json(response)
        
        if not review_data:
            logger.error(f"Failed to parse reviewer response: {response[:500]}")
            return {
                "approved": False,
                "error": "Invalid JSON from reviewer",
                "raw": response,
                "final_feedback": "Failed to parse reviewer response"
            }
        
        # Ensure required fields exist
        if "reviews" not in review_data:
            review_data["reviews"] = []
        if "overall_score" not in review_data:
            review_data["overall_score"] = 0.0
        if "approved" not in review_data:
            review_data["approved"] = False
        if "final_feedback" not in review_data:
            review_data["final_feedback"] = "No feedback provided"
        
        # Check if any review failed
        approved = review_data.get("approved", False)
        for r in review_data.get("reviews", []):
            if not r.get("passed", True):
                approved = False
        
        # Check overall score
        if review_data.get("overall_score", 0) < self.min_passing_score:
            approved = False
        
        review_data["approved"] = approved
        
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

print("\n=== Sprint 10 Fix completed successfully ===")
print("Run START.bat to test improved response handling!")
print("\nChanges:")
print("- Fixed regex escaping for Python 3.12+")
print("- Better JSON parsing (handles markdown code blocks)")
print("- Logs first 200 chars of model responses")
print("- Ensures all required fields exist in reviewer response")
print("- Shows raw response if parsing fails")