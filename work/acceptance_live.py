"""Приёмка цепочки на настоящей локальной модели (Ollama).

Запуск на вашем компьютере, где работает Ollama с моделью из настроек:

    python work/acceptance_live.py
    python work/acceptance_live.py --model qwen2.5:7b-instruct

Скрипт ничего не публикует и не трогает ваш проект: создаёт временный каталог.
Печатает реальные тексты ответов модели и время до 10 готовых постов.
Без доступной Ollama честно завершается с кодом 2 и подсказкой.
"""
from __future__ import annotations

import argparse
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "AI_SMM_Work_Architecture_A75"
if not (ROOT / "ai_core.py").is_file():
    print(f"Не нашёл код приложения: {ROOT}")
    print("Скрипт должен лежать в папке work рядом с AI_SMM_Work_Architecture_A75.")
    print("Запуск из папки проекта: .\\AI_SMM_Work_Architecture_A75\\.venv\\Scripts\\python.exe .\\work\\acceptance_live.py")
    raise SystemExit(2)
sys.path.insert(0, str(ROOT))

from ai_core import AICore, OllamaProvider  # noqa: E402
from data_manager import DataManager  # noqa: E402


def _installed(host: str) -> list:
    """Имена моделей из /api/tags; при любой ошибке — пустой список."""
    try:
        import json
        import urllib.request

        with urllib.request.urlopen(f"{host}/api/tags", timeout=3) as response:
            data = json.loads(response.read().decode("utf-8"))
        return [str(item.get("name") or "") for item in data.get("models") or []]
    except Exception:
        return []


def main() -> int:
    parser = argparse.ArgumentParser(description="Приёмка цепочки на локальной модели")
    parser.add_argument("--model", default="qwen3:8b",
                       help="имя модели в Ollama (по умолчанию qwen3:8b)")
    parser.add_argument("--host", default="http://localhost:11434", help="адрес Ollama API")
    parser.add_argument("--keep", action="store_true", help="оставить временный проект на диске")
    args = parser.parse_args()

    local = OllamaProvider(host=args.host, model=args.model)
    if not local.available():
        print(f"Ollama недоступна: {args.host}, модель {args.model}.")
        print("Запустите `ollama serve` и `ollama pull <модель>`, затем повторите.")
        print("Установленные модели:", ", ".join(_installed(args.host)) or "список не получен")
        return 2
    installed = _installed(args.host)
    if installed and not any(name.split(":")[0] == args.model.split(":")[0] for name in installed):
        print(f"Модели {args.model} нет в Ollama. Установленные: {', '.join(installed)}")
        print("Выберите модель аргументом --model.")
        return 2

    tmp = Path(tempfile.mkdtemp(prefix="accept_live_"))
    dm = DataManager("accept_live", str(tmp / "client"))
    dm.save_brand_profile({"client_name": "Кофейня «Пар»", "niche": "кофейня", "city": "Алматы",
                           "audience": "жители района 25–40", "positioning": "своя обжарка",
                           "tone_of_voice": "тёплый", "languages": "ru"})
    core = AICore(dm, {"monthly_budget_usd": 0}, providers=(local, None))
    started = time.time()
    marks: list[tuple[str, float]] = []

    def say(title: str, text: str, seconds: float) -> None:
        marks.append((title, seconds))
        print(f"\n=== {title} — {seconds:.1f} с ===")
        print(text.strip()[:1200])

    def run(title: str, fn):
        step = time.time()
        value = fn()
        seconds = time.time() - step
        if isinstance(value, dict):
            text = str(value.get("summary") or "")
        else:
            text = getattr(value, "text", "") or str(value)
        say(title, text, seconds)
        return value

    run("стратегия", lambda: core.handle("сделай стратегию для кофейни у дома"))
    for section in (dm.get_strategy().get("sections") or [])[:5]:
        print(f"· {section.get('title')}: {str(section.get('content') or '')[:300]}")
    run("контент-план на 10 постов", lambda: core.handle("создай контент-план на 10 постов"))
    plan = dm.get_content_plan()
    if not plan:
        print("\nЦепочка оборвалась: модель не собрала стратегию, план не создан.")
        return 1
    say("календарь", str(core.tools.sync_plan_events().get("summary")), 0.0)

    caption_started = time.time()
    for item in plan[:2]:
        run(f"подпись: {item.get('topic')}", lambda item=item: core.tools.write_captions(item["id"]))
        print("—", (dm.get_content_plan_item(item["id"]) or {}).get("caption", ""))
    for item in plan[2:]:
        core.tools.write_captions(item["id"])
    captions_seconds = time.time() - caption_started
    lengths = [len(str(i.get("caption") or "")) for i in dm.get_content_plan()]
    print(f"\nдлина подписей: мин {min(lengths)}, макс {max(lengths)} символов")

    for item in plan:
        core.handle("создай ТЗ")

    ready = [i for i in dm.get_content_plan() if i.get("date") and i.get("caption")]
    total = time.time() - started
    print("\n=== итог ===")
    print(f"постов в плане: {len(plan)}, с подписью: {len(ready)}, "
          f"ТЗ: {len(dm.get_shooting_tasks())}, событий: {len(dm.get_calendar_events())}")
    print(f"подписи на 10 позиций: {captions_seconds:.1f} с")
    print(f"время до 10 постов с подписями: {total:.1f} с ({total / 60:.1f} мин)")
    print(f"проверка плана: {core.tools.validate_plan().get('summary', '').splitlines()[0]}")
    for title, seconds in marks:
        print(f"  {seconds:7.1f} с — {title}")

    dm2 = DataManager("accept_live", str(tmp / "client"))
    print(f"после перезапуска: план {len(dm2.get_content_plan())}, "
          f"ТЗ {len(dm2.get_shooting_tasks())}, профиль {bool(dm2.get_brand_profile().get('client_name'))}")
    if not args.keep:
        print(f"временный проект: {tmp} (удалить можно вручную)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
