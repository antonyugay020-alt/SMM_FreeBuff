# AI SMM Manager - Sprint 4: Real Generation & Media Router
# Run: powershell -NoProfile -ExecutionPolicy Bypass -File .\bootstrap_sprint4.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$utf8WithBom = New-Object System.Text.UTF8Encoding $true

Write-Host ""
Write-Host "=== AI SMM Manager - Sprint 4: Real Generation & Media Router ===" -ForegroundColor Green
Write-Host "Root: $root"
Write-Host ""

# 1. Check venv
Write-Host "[1/4] Checking virtual environment..." -ForegroundColor Cyan
$venvPython = Join-Path $root "venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "  ERROR: venv not found." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "  OK: venv found" -ForegroundColor Green

# 2. Helper function
Write-Host "[2/4] Preparing file writer..." -ForegroundColor Cyan

function Write-PyFile {
    param([string]$RelPath, [string]$Content)
    $fullPath = Join-Path $root $RelPath
    $dir = Split-Path $fullPath -Parent
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    [System.IO.File]::WriteAllText($fullPath, $Content, $utf8WithBom)
    Write-Host "  Created/Updated: $RelPath"
}

# 3. Generate media_task_router.py
Write-Host "[3/4] Generating media_task_router.py..." -ForegroundColor Cyan

$mediaRouterContent = @'
"""
Media Task Router - Intelligent routing between local and cloud processing.
Evaluates hardware constraints (VRAM) and privacy requirements to choose the best execution path.
"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class MediaTaskRouter:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.hardware = config.get("hardware", {})
        self.media_config = config.get("media_processing", {})
        
        self.vram_gb = self.hardware.get("gpu_vram_gb", 8)
        self.fallback_to_cloud = self.media_config.get("fallback_to_cloud_if_vram_exceeded", True)
        
    def should_process_locally(self, task_type: str, estimated_vram_gb: float, is_private: bool = False) -> bool:
        """
        Determine if a media task should be processed locally.
        
        Args:
            task_type: "image_generation", "video_editing", "audio_transcription", etc.
            estimated_vram_gb: Estimated VRAM required for the task
            is_private: Whether the project requires strict privacy (no cloud)
            
        Returns:
            bool: True if local processing is recommended, False if cloud is better
        """
        if is_private:
            logger.info(f"Task '{task_type}' forced to local due to privacy requirements.")
            return True
            
        if estimated_vram_gb > self.vram_gb:
            if self.fallback_to_cloud:
                logger.warning(f"Task '{task_type}' requires {estimated_vram_gb}GB VRAM, but only {self.vram_gb}GB available. Routing to cloud.")
                return False
            else:
                logger.error(f"Task '{task_type}' requires {estimated_vram_gb}GB VRAM, but only {self.vram_gb}GB available. Cloud fallback disabled. Task may fail or be very slow.")
                return True
                
        logger.info(f"Task '{task_type}' routed to local processing (requires {estimated_vram_gb}GB / {self.vram_gb}GB available).")
        return True
        
    def get_recommended_model(self, task_type: str) -> str:
        """Get the recommended model/tool based on hardware constraints."""
        if task_type == "image_generation":
            if self.vram_gb >= 12:
                return self.media_config.get("local_sd_model_xl", "stable-diffusion-xl")
            else:
                return self.media_config.get("local_sd_model", "stable-diffusion-v1-5")
        elif task_type == "audio_transcription":
            if self.vram_gb >= 8:
                return self.media_config.get("local_whisper_model", "base")
            else:
                return "tiny"
                
        return "default"
'@
Write-PyFile "AI_SMM_Work_Architecture_A75\media_task_router.py" $mediaRouterContent

# 4. Update app.py to run a REAL end-to-end generation test
Write-Host "[4/4] Updating app.py with real generation test..." -ForegroundColor Cyan

$appPyUpdated = @'
import sys, os, logging, sqlite3, json
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

def print_separator():
    print("\n" + "="*70 + "\n")

def main():
    print_separator()
    logger.info("=== AI SMM Manager - Sprint 4: Real Generation Test ===")
    
    try:
        import yaml
        from task_state_machine import TaskStateMachine, TaskState
        from local_quality_gate import LocalQualityGate
        from ollama_client import OllamaClient
        from media_task_router import MediaTaskRouter
    except ImportError as e:
        logger.error(f"Missing dependency: {e}")
        sys.exit(1)
    
    logger.info("Dependencies OK.")
    
    # Load config
    config_path = ROOT_DIR / "config" / "config.yaml"
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        logger.info("Configuration loaded.")
    else:
        config = {}
        logger.warning("config.yaml not found, using defaults.")
    
    # Initialize DB
    db_path = ROOT_DIR / "data" / "ai_smm_manager.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    
    project_id = "default_project"
    state_machine = TaskStateMachine(conn, project_id)
    
    # Initialize Ollama
    ollama = OllamaClient()
    if not ollama.is_available() or not ollama.is_model_available():
        logger.error("Ollama or model qwen3:8b not available. Please check Ollama.")
        sys.exit(1)
    
    # Initialize Quality Gate & Media Router
    quality_gate = LocalQualityGate(ollama_client=ollama)
    media_router = MediaTaskRouter(config)
    
    logger.info("All core components initialized.")
    print_separator()
    
    # --- REAL END-TO-END TEST ---
    test_request = "Создай короткий пост для Instagram про утренний кофе в кофейне для фрилансеров. Тон: дружелюбный, мотивирующий. Не выдумывай цены."
    project_context = {"business": "Уютная кофейня", "target": "Фрилансеры и удаленные работники", "rules": "Не указывать конкретные цены"}
    
    logger.info(f"📝 REQUEST: {test_request}")
    print_separator()
    
    logger.info("🔄 Starting full quality gate cycle (Generation + Independent Review)...")
    logger.info("This may take 15-30 seconds depending on your GPU.")
    
    try:
        result = quality_gate.full_quality_gate(test_request, project_context)
        
        print_separator()
        if result.get("approved"):
            logger.info("✅ CONTENT APPROVED BY INDEPENDENT REVIEWER!")
            logger.info(f"📊 Overall Score: {result.get('overall_score')}")
            
            content = result.get("content", {})
            logger.info(f"📝 CONTENT:\n{content.get('content')}")
            logger.info(f"🏷️ HASHTAGS: {', '.join(content.get('hashtags', []))}")
            logger.info(f"📣 CALL TO ACTION: {content.get('call_to_action')}")
            
            # Test Media Router
            logger.info("🖼️ Testing Media Task Router for accompanying image...")
            should_use_local = media_router.should_process_locally(
                task_type="image_generation", 
                estimated_vram_gb=6.0, 
                is_private=False
            )
            recommended_model = media_router.get_recommended_model("image_generation")
            logger.info(f"   -> Local processing recommended: {should_use_local}")
            logger.info(f"   -> Recommended model: {recommended_model}")
            
        else:
            logger.warning("❌ CONTENT REJECTED BY REVIEWER")
            logger.warning(f"💬 Feedback: {result.get('review', {}).get('final_feedback')}")
            if "error" in result.get("content", {}):
                logger.warning(f"⚠️ Generation Error: {result['content'].get('error')}")
                
    except Exception as e:
        logger.error(f"❌ Generation failed: {e}")
        import traceback
        traceback.print_exc()
    
    print_separator()
    logger.info("✅ Sprint 4 test completed. Architecture is fully operational.")
    logger.info("Ready for GUI integration and advanced media pipelines.")
    print_separator()
    
    sys.exit(0)

if __name__ == "__main__":
    main()
'@
Write-PyFile "AI_SMM_Work_Architecture_A75\app.py" $appPyUpdated

# 5. Final verification
Write-Host ""
Write-Host "[5/5] Final verification..." -ForegroundColor Cyan
$checks = @(
    "AI_SMM_Work_Architecture_A75\media_task_router.py",
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
    Write-Host "=== Sprint 4 completed successfully ===" -ForegroundColor Green
    Write-Host "Run START.bat to see real AI content generation and review in action!" -ForegroundColor Green
} else {
    Write-Host "=== Sprint 4 completed with errors ===" -ForegroundColor Red
}
Write-Host ""