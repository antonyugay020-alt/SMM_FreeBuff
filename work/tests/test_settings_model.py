"""Настройки: поле модели — список моделей Ollama и не откатывает автоподмену."""
import json, os, sys, tempfile
from pathlib import Path

APP = Path(__file__).resolve().parents[2] / "AI_SMM_Work_Architecture_A75"
sys.path.insert(0, str(APP))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import QApplication

app = QApplication([])

from gui_settings import Settings
from gui_sections.settings_section import SettingsSection


def ok(name, cond, extra=""):
    print(("SET_OK " if cond else "SET_FAIL ") + name + ("" if cond else f" :: {extra}"))
    if not cond:
        raise SystemExit(1)


INSTALLED = ["gemma3:4b", "qwen3:8b", "nomic-embed-text:latest", "qwen2.5-coder:7b",
             "llama3.1:8b"]
SettingsSection.installed_models = lambda self: list(INSTALLED)

path = Path(tempfile.mkdtemp(prefix="settings_model_")) / "settings.json"
settings = Settings(path)
settings.set("local_model", "qwen3:8b")
settings.save()

section = SettingsSection({"settings": settings})
ok("поле стало списком", section.local_model.count() >= len(INSTALLED),
   section.local_model.count())
ok("показана сохранённая модель", section.current_model() == "qwen3:8b",
   section.current_model())
names = [section.local_model.itemText(row) for row in range(section.local_model.count())]
ok("в списке установленные модели",
   "qwen3:8b" in names and "gemma3:4b" in names and "llama3.1:8b" in names, names)

# --- автоподмена записала другое значение: поле обязано его подхватить ---
settings.set("local_model", "gemma3:4b")
settings.save()
section.showEvent(QShowEvent())
ok("поле подхватило новую модель", section.current_model() == "gemma3:4b",
   section.current_model())
section._on_save()
ok("сохранение не откатывает модель", settings.get("local_model") == "gemma3:4b",
   settings.get("local_model"))
ok("на диске та же модель",
   json.loads(path.read_text(encoding="utf-8"))["local_model"] == "gemma3:4b")
ok("статус подтвердил", "Сохранено" in section.status.text(), section.status.text())

# --- модели нет в Ollama: остаётся выбранной и помечена ---
settings.set("local_model", "custom:1b")
settings.save()
section.showEvent(QShowEvent())
ok("незнакомая модель выбрана", section.current_model() == "custom:1b", section.current_model())
texts = [section.local_model.itemText(row) for row in range(section.local_model.count())]
ok("помечена как не установленная",
   any("custom:1b" in text and "не установлена" in text for text in texts), texts)
section._on_save()
ok("незнакомая модель не теряется", settings.get("local_model") == "custom:1b",
   settings.get("local_model"))

# --- Ollama не отвечает: список не пустеет, модель остаётся ---
SettingsSection.installed_models = lambda self: []
offline = SettingsSection({"settings": settings})
ok("без Ollama модель на месте", offline.current_model() == "custom:1b",
   offline.current_model())
offline._on_save()
ok("без Ollama сохранение не портит", settings.get("local_model") == "custom:1b",
   settings.get("local_model"))

print("SETTINGS_MODEL_OK")
