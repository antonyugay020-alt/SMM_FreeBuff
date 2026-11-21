# AI SMM Manager - Sprint 1 Bootstrap
# Run: powershell -NoProfile -ExecutionPolicy Bypass -File .\bootstrap_sprint1.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

Write-Host ""
Write-Host "=== AI SMM Manager - Sprint 1 Bootstrap ===" -ForegroundColor Green
Write-Host "Root: $root"
Write-Host ""

# 1. Check Python
Write-Host "[1/7] Checking Python..." -ForegroundColor Cyan
$pythonCmd = $null
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $ver = & $cmd --version 2>&1
        if ($ver -like "Python 3.*") {
            $pythonCmd = $cmd
            Write-Host "  OK: $ver" -ForegroundColor Green
            break
        }
    } catch {}
}

if (-not $pythonCmd) {
    Write-Host "  ERROR: Python 3.10+ not found" -ForegroundColor Red
    Write-Host "  Download from https://www.python.org/downloads/" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# 2. Create directories
Write-Host "[2/7] Creating directories..." -ForegroundColor Cyan
$dirs = @(
    "AI_SMM_Work_Architecture_A75",
    "AI_SMM_Developer_A75\tests",
    "data\projects",
    "data\checkpoints",
    "data\logs",
    "data\exports",
    "media\images",
    "media\videos",
    "media\audio",
    "config",
    "bootstrap"
)
foreach ($d in $dirs) {
    $path = Join-Path $root $d
    if (-not (Test-Path $path)) {
        New-Item -ItemType Directory -Path $path -Force | Out-Null
        Write-Host "  Created: $d"
    } else {
        Write-Host "  Exists:  $d" -ForegroundColor DarkGray
    }
}

# 3. Virtual Environment
Write-Host "[3/7] Creating virtual environment..." -ForegroundColor Cyan
$venvPath = Join-Path $root "venv"
if (-not (Test-Path (Join-Path $venvPath "Scripts\python.exe"))) {
    Write-Host "  Creating venv..."
    & $pythonCmd -m venv $venvPath
    Write-Host "  OK: venv created" -ForegroundColor Green
} else {
    Write-Host "  OK: venv exists" -ForegroundColor Green
}
$venvPip = Join-Path $venvPath "Scripts\pip.exe"

# 4. Install dependencies
Write-Host "[4/7] Installing dependencies..." -ForegroundColor Cyan
Write-Host "  Upgrading pip..."
& $venvPip install --upgrade pip --quiet
Write-Host "  Installing PySide6, requests, pillow, numpy, PyYAML..."
& $venvPip install PySide6 requests pillow numpy PyYAML --quiet
Write-Host "  OK" -ForegroundColor Green

# 5. Generate project files
Write-Host "[5/7] Generating project files..." -ForegroundColor Cyan

function Write-ProjectFile {
    param([string]$RelPath, [string]$Content)
    $fullPath = Join-Path $root $RelPath
    $dir = Split-Path $fullPath -Parent
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    [System.IO.File]::WriteAllText($fullPath, $Content, [System.Text.UTF8Encoding]::new($true))
    Write-Host "  Created: $RelPath"
}

$reqContent = "PySide6>=6.5.0`nrequests>=2.31.0`npillow>=10.0.0`nnumpy>=1.24.0`nPyYAML>=6.0"
Write-ProjectFile "AI_SMM_Work_Architecture_A75\requirements.txt" $reqContent

$configContent = @"
# AI SMM Manager - Configuration
hardware:
  gpu_vram_gb: 8
  cpu_cores: 12
  ram_gb: 32
ollama:
  model: "qwen3:8b"
  host: "http://localhost:11434"
  timeout: 120
media_processing:
  local_sd_model: "stable-diffusion-v1-5"
  fallback_to_cloud_if_vram_exceeded: true
storage:
  database: "data/ai_smm_manager.db"
  projects_dir: "data/projects"
  logs_dir: "data/logs"
quality:
  min_passing_score: 0.7
  evidence_validation: true
"@
Write-ProjectFile "config\config.yaml" $configContent

$gitignoreContent = "__pycache__/`n*.py[cod]`nvenv/`n*.db`ndata/logs/*.log`nconfig/config.yaml"
Write-ProjectFile ".gitignore" $gitignoreContent

$readmeContent = @"
# AI SMM Manager
Autonomous AI manager for social media.
## Quick Start
1. Run bootstrap_sprint1.ps1
2. Edit config\config.yaml
3. Run START.bat
## Status: NOT RELEASE
"@
Write-ProjectFile "README.md" $readmeContent

# 6. Generate Python modules
Write-Host "[6/7] Generating Python modules..." -ForegroundColor Cyan

$appPy = @"
import sys, os, logging, sqlite3
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

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
    except ImportError as e:
        logger.error(f"Missing dependency: {e}")
        sys.exit(1)
    
    logger.info("Dependencies OK. GUI initialized (stub).")
    logger.info("Full integration with TaskStateMachine, LocalQualityGate - next sprint.")
    sys.exit(0)

if __name__ == "__main__":
    main()
"@
Write-ProjectFile "AI_SMM_Work_Architecture_A75\app.py" $appPy

$startBat = @"
@echo off
chcp 65001 >nul
title AI SMM Manager
cd /d "%~dp0"
if not exist "venv\Scripts\python.exe" (
    echo [ERROR] venv not found. Run bootstrap_sprint1.ps1
    pause
    exit /b 1
)
echo Starting AI SMM Manager...
venv\Scripts\python.exe AI_SMM_Work_Architecture_A75\app.py
if errorlevel 1 (
    echo [ERROR] Exit code: %errorlevel%
    pause
)
"@
Write-ProjectFile "START.bat" $startBat

# 7. Final verification
Write-Host "[7/7] Final verification..." -ForegroundColor Cyan
$checks = @("venv\Scripts\python.exe", "AI_SMM_Work_Architecture_A75\app.py", "config\config.yaml", "START.bat")
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
    Write-Host "=== Bootstrap completed successfully ===" -ForegroundColor Green
    Write-Host "Next step: double-click START.bat" -ForegroundColor Green
} else {
    Write-Host "=== Bootstrap completed with errors ===" -ForegroundColor Red
}
Write-Host ""