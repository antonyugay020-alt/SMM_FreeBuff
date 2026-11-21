# AI SMM Manager - Sprint 3: Ollama Integration
# Run: powershell -NoProfile -ExecutionPolicy Bypass -File .\bootstrap_sprint3.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$utf8WithBom = New-Object System.Text.UTF8Encoding $true

Write-Host ""
Write-Host "=== AI SMM Manager - Sprint 3: Ollama Integration ===" -ForegroundColor Green
Write-Host "Root: $root"
Write-Host ""

# 1. Check venv
Write-Host "[1/6] Checking virtual environment..." -ForegroundColor Cyan
$venvPython = Join-Path $root "venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "  ERROR: venv not found. Run bootstrap_sprint1.ps1 first." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "  OK: venv found" -ForegroundColor Green

# 2. Install requests (for Ollama API calls)
Write-Host "[2/6] Installing requests library..." -ForegroundColor Cyan
$venvPip = Join-Path $root "venv\Scripts\pip.exe"
& $venvPip install requests --quiet
Write-Host "  OK" -ForegroundColor Green

# 3. Helper function
Write-Host "[3/6] Preparing file writer..." -ForegroundColor Cyan

function Write-PyFile {
    param([string]$RelPath, [string]$Content)
    $fullPath = Join-Path $root $RelPath
    $dir = Split-Path $fullPath -Parent
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    [System.IO.File]::WriteAllText($fullPath, $Content, $utf8WithBom)
    Write-Host "  Created/Updated: $RelPath"
}

# 4. Generate ollama_client.py
Write-Host "[4/6] Generating ollama_client.py..." -ForegroundColor Cyan

$ollamaClientContent = @'
"""
Ollama Client - HTTP client for local Ollama API.
Handles model availability checks, generation, and error recovery.
"""
import requests
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class OllamaClient:
    def __init__(self, host: str = "http://localhost:11434", model: str = "qwen3:8b", timeout: int = 120):
        self.host = host.rstrip('/')
        self.model = model
        self.timeout = timeout
        self.session = requests.Session()
        
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
    
    def is_model_available(self) -> bool:
        """Check if the required model is downloaded."""
        if not self.is_available():
            return False
        
        try:
            response = self.session.get(f"{self.host}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m["name"] for m in models]
                return self.model in model_names
        except Exception as e:
            logger.error(f"Error checking model availability: {e}")
        
        return False
    
    def generate(self, system_prompt: str, user_message: str, temperature: float = 0.7) -> str:
        """
        Generate content using Ollama API.
        
        Args:
            system_prompt: System prompt for the model
            user_message: User message
            temperature: Generation temperature (0.0-1.0)
        
        Returns:
            str: Generated text
        """
        if not self.is_available():
            raise ConnectionError(f"Ollama server not available at {self.host}")
        
        if not self.is_model_available():
            raise RuntimeError(f"Model {self.model} not found. Run: ollama pull {self.model}")
        
        payload = {
            "model": self.model,
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
            logger.info(f"Calling Ollama model {self.model} (temp={temperature})")
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
        """Get information about the current model."""
        return {
            "model": self.model,
            "host": self.host,
            "available": self.is_available(),
            "model_downloaded": self.is_model_available()
        }
'@
Write-PyFile "AI_SMM_Work_Architecture_A75\ollama_client.py" $ollamaClientContent

# 5. Update local_quality_gate.py to use real Ollama client
Write-Host "[5/6] Updating local_quality_gate.py with Ollama integration..." -ForegroundColor Cyan

$lqgUpdatedContent = @'
"""
Local Quality Gate - Integrated with Ollama for real content generation.
Uses Sequential Role Isolation: same model, different system prompts, cleared context.
"""
from typing import Dict, Any, Optional
import json
import hashlib
import logging

logger = logging.getLogger(__name__)

class LocalQualityGate:
    AUTHOR_SYSTEM_PROMPT = """You are a professional SMM specialist. Create high-quality social media content based on the user request.
Rules:
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

    REVIEWER_SYSTEM_PROMPT = """You are an independent critical editor. Strictly check the content created by another AI author against 4 criteria:
1. REQUIREMENTS: Does it match user request?
2. COMPLETENESS: Are all elements present?
3. EVIDENCE: Are there any invented facts, prices, or services?
4. FORMAT_TONE: Does it match the target platform?
Rules: Be strict. If it fails any criterion, reject it. Provide specific feedback.
Respond STRICTLY in JSON format:
{
  "reviews": [{"criterion": "REQUIREMENTS", "passed": true, "score": 0.9, "feedback": "ok", "suggestions": []}],
  "overall_score": 0.85,
  "approved": true,
  "final_feedback": "summary"
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
        """Call Ollama model with Sequential Role Isolation."""
        logger.info(f"Calling model {self.model} with temp {temperature}")
        return self.ollama.generate(system_prompt, user_message, temperature)

    def generate_content(self, request_text: str, project_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        user_message = request_text
        if project_context:
            user_message += f"\n\nProject Context:\n{json.dumps(project_context, ensure_ascii=False, indent=2)}"
        
        response = self._call_model(self.AUTHOR_SYSTEM_PROMPT, user_message)
        
        try:
            result = json.loads(response)
            result["_request_hash"] = hashlib.sha256(request_text.encode('utf-8')).hexdigest()
            return result
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON from model: {response[:200]}")
            return {"error": "Invalid JSON from model", "raw": response}

    def review_content(self, request_text: str, content: Dict[str, Any]) -> Dict[str, Any]:
        user_message = f"Original request:\n{request_text}\n\nContent to review:\n{json.dumps(content, ensure_ascii=False, indent=2)}"
        
        response = self._call_model(self.REVIEWER_SYSTEM_PROMPT, user_message, temperature=0.3)
        
        try:
            review_data = json.loads(response)
            approved = review_data.get("approved", False)
            for r in review_data.get("reviews", []):
                if not r.get("passed", True):
                    approved = False
            return {**review_data, "approved": approved}
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON from reviewer: {response[:200]}")
            return {"approved": False, "error": "Invalid JSON from reviewer", "raw": response}
    
    def full_quality_gate(self, request_text: str, project_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Full cycle: generate + review."""
        logger.info("Starting full quality gate cycle...")
        
        content = self.generate_content(request_text, project_context)
        if "error" in content:
            return {"approved": False, "error": content["error"]}
        
        review_result = self.review_content(request_text, content)
        
        return {
            "content": content,
            "review": review_result,
            "approved": review_result.get("approved", False)
        }
'@
Write-PyFile "AI_SMM_Work_Architecture_A75\local_quality_gate.py" $lqgUpdatedContent

# 6. Update app.py to test Ollama integration
Write-Host "[6/6] Updating app.py with Ollama test..." -ForegroundColor Cyan

$appPyUpdated = @'
import sys, os, logging, sqlite3
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

logs_dir = ROOT_DIR / "data" / "logs"
logs_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler(logs_dir / "app.log", encoding='utf-8')]
)
logger = logging.getLogger(__name__)

def main():
    logger.info("=== AI SMM Manager starting ===")
    try:
        from PySide6.QtWidgets import QApplication
        import yaml
        from task_state_machine import TaskStateMachine, TaskState
        from local_quality_gate import LocalQualityGate
        from qt_worker_lifecycle import WorkerManager, PYSIDE6_AVAILABLE
        from ollama_client import OllamaClient
    except ImportError as e:
        logger.error(f"Missing dependency: {e}")
        sys.exit(1)
    
    logger.info("Dependencies OK.")
    
    db_path = ROOT_DIR / "data" / "ai_smm_manager.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    logger.info(f"Database initialized: {db_path}")
    
    project_id = "default_project"
    state_machine = TaskStateMachine(conn, project_id)
    worker_manager = WorkerManager(conn)
    
    logger.info("Core architecture v2 components initialized.")
    
    # Test Ollama integration
    logger.info("Testing Ollama integration...")
    ollama = OllamaClient()
    
    if not ollama.is_available():
        logger.error("Ollama server is not running. Start Ollama and try again.")
        logger.error("Download: https://ollama.ai/")
        sys.exit(1)
    
    if not ollama.is_model_available():
        logger.error(f"Model {ollama.model} not found. Run: ollama pull {ollama.model}")
        sys.exit(1)
    
    logger.info(f"Ollama OK: {ollama.get_model_info()}")
    
    quality_gate = LocalQualityGate(ollama_client=ollama)
    logger.info("Quality Gate initialized with real Ollama client.")
    
    app = QApplication(sys.argv)
    app.setApplicationName("AI SMM Manager")
    app.setApplicationVersion("v2.0-sprint3")
    
    logger.info("Testing TaskStateMachine...")
    auth = state_machine.create_task("test_002", "Create a post about coffee")
    state_machine.transition("test_002", TaskState.AUTHORING, "Test transition")
    logger.info(f"Task test_002 state: {state_machine.get_state('test_002')}")
    
    logger.info("GUI initialized. Ollama integration is ACTIVE and VERIFIED.")
    logger.info("Ready for real content generation!")
    sys.exit(0)

if __name__ == "__main__":
    main()
'@
Write-PyFile "AI_SMM_Work_Architecture_A75\app.py" $appPyUpdated

# 7. Final verification
Write-Host ""
Write-Host "[7/7] Final verification..." -ForegroundColor Cyan
$checks = @(
    "AI_SMM_Work_Architecture_A75\ollama_client.py",
    "AI_SMM_Work_Architecture_A75\local_quality_gate.py",
    "AI_SMM_Work_Architecture_A75\app.py"
)
$allOk = $true
foreach ($check in $checks) {
    if (Test-Path (Join-Path $root $check)) {
        Write-Host "  OK: $check" -ForegroundColor Green
    } else {
        Write-Host "  MISSING: $check" -ForegroundColor Red
        $allOk = $false
    }
}

Write-Host ""
if ($allOk) {
    Write-Host "=== Sprint 3 completed successfully ===" -ForegroundColor Green
    Write-Host "Make sure Ollama is running with qwen3:8b model." -ForegroundColor Green
    Write-Host "Run START.bat to verify Ollama integration." -ForegroundColor Green
} else {
    Write-Host "=== Sprint 3 completed with errors ===" -ForegroundColor Red
}
Write-Host ""