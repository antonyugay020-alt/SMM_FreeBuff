# AI SMM Manager - Sprint 7: Aggressive Qt Encoding Fix
# Run: powershell -NoProfile -ExecutionPolicy Bypass -File .\bootstrap_sprint7.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$utf8WithBom = New-Object System.Text.UTF8Encoding $true

Write-Host ""
Write-Host "=== AI SMM Manager - Sprint 7: Aggressive Qt Encoding Fix ===" -ForegroundColor Green
Write-Host "Root: $root"
Write-Host ""

# 1. Check venv
Write-Host "[1/2] Checking virtual environment..." -ForegroundColor Cyan
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

# 3. Update app.py with aggressive encoding fixes
Write-Host "[2/2] Updating app.py with aggressive encoding fixes..." -ForegroundColor Cyan

$appPyFixed = @'
import sys, os, logging, sqlite3, json
from pathlib import Path

# AGGRESSIVE ENCODING FIX - Must be before ANY other imports
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PYTHONUTF8'] = '1'

# Force UTF-8 for stdout/stderr
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
    logger.info("=== AI SMM Manager - Sprint 7: Aggressive Encoding Fix ===")
    
    try:
        import yaml
        from PySide6.QtWidgets import QApplication, QMainWindow, QTextEdit, QPushButton, QVBoxLayout, QWidget, QLabel
        from PySide6.QtCore import Qt, Signal, QObject, QCoreApplication
        from PySide6.QtGui import QFont, QTextCodec
        from task_state_machine import TaskStateMachine, TaskState
        from local_quality_gate import LocalQualityGate
        from ollama_client import OllamaClient
        from qt_worker_lifecycle import WorkerManager
        from media_task_router import MediaTaskRouter
    except ImportError as e:
        logger.error(f"Missing dependency: {e}")
        sys.exit(1)
    
    # Force Qt to use UTF-8
    QCoreApplication.setAttribute(Qt.AA_PluginApplication, True)
    
    # Init DB & Components
    conn = sqlite3.connect(str(ROOT_DIR / "data" / "ai_smm_manager.db"))
    conn.execute("PRAGMA journal_mode=WAL")
    
    state_machine = TaskStateMachine(conn, "default_project")
    worker_manager = WorkerManager(conn)
    ollama = OllamaClient()
    quality_gate = LocalQualityGate(ollama_client=ollama)
    
    config_path = ROOT_DIR / "config" / "config.yaml"
    config = yaml.safe_load(open(config_path, 'r', encoding='utf-8')) if config_path.exists() else {}
    media_router = MediaTaskRouter(config)
    
    logger.info("All components initialized. Starting GUI...")
    
    # --- GUI WITH AGGRESSIVE ENCODING ---
    app = QApplication(sys.argv)
    app.setApplicationName("AI SMM Manager")
    
    # Force UTF-8 codec for Qt
    QTextCodec.setCodecForLocale(QTextCodec.codecForName("UTF-8"))
    
    # Use font that definitely supports Cyrillic
    font = QFont("Arial", 10)
    app.setFont(font)
    
    window = QMainWindow()
    window.setWindowTitle("AI SMM Manager v2.0 (Sprint 7)")
    window.resize(700, 500)
    
    layout = QVBoxLayout()
    
    label = QLabel("Введите задачу для SMM-менеджера:")
    label.setFont(QFont("Arial", 11, QFont.Bold))
    layout.addWidget(label)
    
    text_input = QTextEdit()
    text_input.setFont(QFont("Consolas", 10))
    text_input.setPlainText("Создай короткий пост для Instagram про утренний кофе в кофейне для фрилансеров. Тон: дружелюбный. Не выдумывай цены.")
    layout.addWidget(text_input)
    
    output_log = QTextEdit()
    output_log.setFont(QFont("Consolas", 10))
    output_log.setReadOnly(True)
    layout.addWidget(output_log)
    
    # Thread-safe message handler with explicit encoding
    class MessageHandler(QObject):
        log_signal = Signal(str)
        
        def __init__(self, text_edit):
            super().__init__()
            self.text_edit = text_edit
            self.log_signal.connect(self.append_log)
        
        def append_log(self, msg):
            # Ensure msg is properly decoded
            if isinstance(msg, bytes):
                msg = msg.decode('utf-8', errors='replace')
            self.text_edit.append(msg)
        
        def log(self, msg):
            # Ensure msg is string, not bytes
            if isinstance(msg, bytes):
                msg = msg.decode('utf-8', errors='replace')
            self.log_signal.emit(str(msg))
    
    msg_handler = MessageHandler(output_log)
    
    def run_task():
        request = text_input.toPlainText()
        msg_handler.log("\n[START] Отправка запроса в Ollama (qwen3:8b)...")
        msg_handler.log("[INFO] Генерация -> Независимая проверка...")
        
        def work_fn(task_id):
            result = quality_gate.full_quality_gate(request, {"rule": "Не выдумывай цены"})
            return result
        
        worker = worker_manager.create_worker("gui_task_001", "default_project", work_fn)
        worker.finished_success.connect(lambda tid, res: on_success(res))
        worker.finished_error.connect(lambda tid, err: msg_handler.log(f"[ERROR] {err}"))
    
    def on_success(result):
        if result.get("approved"):
            msg_handler.log("\n[OK] КОНТЕНТ ОДОБРЕН РЕЦЕНЗЕНТОМ!")
            c = result.get("content", {})
            msg_handler.log(f"Текст:\n{c.get('content')}")
            msg_handler.log(f"Хэштеги: {', '.join(c.get('hashtags', []))}")
            msg_handler.log(f"Призыв: {c.get('call_to_action')}")
        else:
            feedback = result.get('review', {}).get('final_feedback', 'Неизвестная причина')
            msg_handler.log(f"\n[FAIL] КОНТЕНТ ОТКЛОНЕН: {feedback}")
    
    btn = QPushButton("Сгенерировать и проверить")
    btn.setFont(QFont("Arial", 11, QFont.Bold))
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
Write-PyFile "AI_SMM_Work_Architecture_A75\app.py" $appPyFixed

Write-Host ""
Write-Host "=== Sprint 7 completed successfully ===" -ForegroundColor Green
Write-Host "Run START.bat to launch the fixed GUI!" -ForegroundColor Green