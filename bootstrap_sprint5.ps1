# AI SMM Manager - Sprint 5: Encoding Fix, Prompt Refinement & Basic GUI
# Run: powershell -NoProfile -ExecutionPolicy Bypass -File .\bootstrap_sprint5.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$utf8WithBom = New-Object System.Text.UTF8Encoding $true

Write-Host ""
Write-Host "=== AI SMM Manager - Sprint 5: Encoding, Prompts & GUI ===" -ForegroundColor Green
Write-Host "Root: $root"
Write-Host ""

# 1. Check venv
Write-Host "[1/3] Checking virtual environment..." -ForegroundColor Cyan
$venvPython = Join-Path $root "venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "  ERROR: venv not found." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# 2. Helper function
function Write-PyFile {
    param([string]$RelPath, [string]$Content)
    $fullPath = Join-Path $root $RelPath
    $dir = Split-Path $fullPath -Parent
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    [System.IO.File]::WriteAllText($fullPath, $Content, $utf8WithBom)
    Write-Host "  Created/Updated: $RelPath"
}

# 3. Update local_quality_gate.py with improved Russian prompts and strict negative constraints
Write-Host "[2/3] Updating local_quality_gate.py (Improved Prompts)..." -ForegroundColor Cyan

$lqgUpdated = @'
"""
Local Quality Gate - Integrated with Ollama.
Uses Sequential Role Isolation with strict negative constraint handling.
"""
from typing import Dict, Any, Optional
import json
import hashlib
import logging

logger = logging.getLogger(__name__)

class LocalQualityGate:
    AUTHOR_SYSTEM_PROMPT = """Ты — профессиональный SMM-специалист. Создай качественный контент для соцсетей на основе запроса.
ПРАВИЛА:
1. Строго следуй требованиям (тон, формат, длина).
2. КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО выдумывать факты, цены, услуги или статистику. Если их нет в запросе — не упоминай их.
3. Отвечай СТРОГО в формате JSON:
{
  "content": "основной текст поста",
  "hashtags": ["#хэштег1", "#хэштег2"],
  "call_to_action": "призыв к действию",
  "metadata": {"platform": "instagram", "tone": "дружелюбный", "word_count": 0}
}"""

    REVIEWER_SYSTEM_PROMPT = """Ты — независимый критический редактор. Строго проверь контент по 4 критериям:
1. REQUIREMENTS: Точное соответствие запросу.
2. COMPLETENESS: Все элементы на месте.
3. EVIDENCE: НЕТ ЛИ выдуманных фактов, цен или услуг? (Если в запросе сказано "не выдумывай цены", наличие цен в контенте — это ПРОВАЛ, а не требование!).
4. FORMAT_TONE: Соответствие платформе.
ПРАВИЛА: Будь строгим. Если контент нарушает запрет на выдумывание фактов/цен — немедленно отклоняй (approved: false).
Отвечай СТРОГО в формате JSON:
{
  "reviews": [{"criterion": "EVIDENCE", "passed": true, "score": 1.0, "feedback": "Факты не выдуманы", "suggestions": []}],
  "overall_score": 0.9,
  "approved": true,
  "final_feedback": "Контент одобрен, правила соблюдены"
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

    def generate_content(self, request_text: str, project_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        user_message = request_text
        if project_context:
            user_message += f"\n\nКонтекст проекта:\n{json.dumps(project_context, ensure_ascii=False, indent=2)}"
        response = self._call_model(self.AUTHOR_SYSTEM_PROMPT, user_message)
        try:
            result = json.loads(response)
            result["_request_hash"] = hashlib.sha256(request_text.encode('utf-8')).hexdigest()
            return result
        except json.JSONDecodeError:
            return {"error": "Invalid JSON", "raw": response}

    def review_content(self, request_text: str, content: Dict[str, Any]) -> Dict[str, Any]:
        user_message = f"Запрос:\n{request_text}\n\nКонтент:\n{json.dumps(content, ensure_ascii=False, indent=2)}"
        response = self._call_model(self.REVIEWER_SYSTEM_PROMPT, user_message, temperature=0.2)
        try:
            review_data = json.loads(response)
            approved = review_data.get("approved", False)
            for r in review_data.get("reviews", []):
                if not r.get("passed", True):
                    approved = False
            return {**review_data, "approved": approved}
        except json.JSONDecodeError:
            return {"approved": False, "error": "Invalid JSON from reviewer", "raw": response}
    
    def full_quality_gate(self, request_text: str, project_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        content = self.generate_content(request_text, project_context)
        if "error" in content:
            return {"approved": False, "error": content["error"]}
        review_result = self.review_content(request_text, content)
        return {"content": content, "review": review_result, "approved": review_result.get("approved", False)}
'@
Write-PyFile "AI_SMM_Work_Architecture_A75\local_quality_gate.py" $lqgUpdated

# 4. Update app.py with Encoding Fix and Basic PySide6 GUI
Write-Host "[3/3] Updating app.py with Basic GUI and Encoding Fix..." -ForegroundColor Cyan

$appPyGui = @'
import sys, os, logging, sqlite3, json
from pathlib import Path

# FIX WINDOWS CONSOLE ENCODING
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

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
    logger.info("=== AI SMM Manager - Sprint 5: GUI Initialization ===")
    
    try:
        import yaml
        from PySide6.QtWidgets import QApplication, QMainWindow, QTextEdit, QPushButton, QVBoxLayout, QWidget, QLabel
        from PySide6.QtCore import Qt
        from task_state_machine import TaskStateMachine, TaskState
        from local_quality_gate import LocalQualityGate
        from ollama_client import OllamaClient
        from qt_worker_lifecycle import WorkerManager
        from media_task_router import MediaTaskRouter
    except ImportError as e:
        logger.error(f"Missing dependency: {e}")
        sys.exit(1)
    
    # Init DB & Components
    conn = sqlite3.connect(str(ROOT_DIR / "data" / "ai_smm_manager.db"))
    conn.execute("PRAGMA journal_mode=WAL")
    
    state_machine = TaskStateMachine(conn, "default_project")
    worker_manager = WorkerManager(conn)
    ollama = OllamaClient()
    quality_gate = LocalQualityGate(ollama_client=ollama)
    
    # Load config for router
    config_path = ROOT_DIR / "config" / "config.yaml"
    config = yaml.safe_load(open(config_path, 'r', encoding='utf-8')) if config_path.exists() else {}
    media_router = MediaTaskRouter(config)
    
    logger.info("All components initialized. Starting GUI...")
    
    # --- BASIC GUI ---
    app = QApplication(sys.argv)
    app.setApplicationName("AI SMM Manager")
    
    window = QMainWindow()
    window.setWindowTitle("AI SMM Manager v2.0 (Sprint 5)")
    window.resize(600, 400)
    
    layout = QVBoxLayout()
    
    label = QLabel("Введите задачу для SMM-менеджера:")
    layout.addWidget(label)
    
    text_input = QTextEdit()
    text_input.setPlainText("Создай короткий пост для Instagram про утренний кофе в кофейне для фрилансеров. Тон: дружелюбный. Не выдумывай цены.")
    layout.addWidget(text_input)
    
    output_log = QTextEdit()
    output_log.setReadOnly(True)
    layout.addWidget(output_log)
    
    def log_msg(msg):
        output_log.append(msg)
        
    def run_task():
        request = text_input.toPlainText()
        log_msg(f"\n[START] Отправка запроса в Ollama (qwen3:8b)...")
        log_msg("[INFO] Генерация -> Независимая проверка...")
        
        # Run in background thread using our WorkerManager!
        def work_fn(task_id):
            result = quality_gate.full_quality_gate(request, {"rule": "Не выдумывай цены"})
            return result
            
        worker = worker_manager.create_worker("gui_task_001", "default_project", work_fn)
        worker.finished_success.connect(lambda tid, res: on_success(res))
        worker.finished_error.connect(lambda tid, err: log_msg(f"[ERROR] {err}"))
        
    def on_success(result):
        if result.get("approved"):
            log_msg("\n✅ КОНТЕНТ ОДОБРЕН РЕЦЕНЗЕНТОМ!")
            c = result.get("content", {})
            log_msg(f"📝 Текст:\n{c.get('content')}")
            log_msg(f"🏷️ Хэштеги: {', '.join(c.get('hashtags', []))}")
        else:
            log_msg(f"\n❌ КОНТЕНТ ОТКЛОНЕН: {result.get('review', {}).get('final_feedback')}")
            
    btn = QPushButton("Сгенерировать и проверить")
    btn.clicked.connect(run_task)
    layout.addWidget(btn)
    
    container = QWidget()
    container.setLayout(layout)
    window.setCentralWidget(container)
    
    window.show()
    logger.info("GUI is running. Architecture v2 is fully operational.")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
'@
Write-PyFile "AI_SMM_Work_Architecture_A75\app.py" $appPyGui

Write-Host ""
Write-Host "=== Sprint 5 completed successfully ===" -ForegroundColor Green
Write-Host "Run START.bat to launch the new GUI window!" -ForegroundColor Green