# AI SMM Manager
Автономный AI-менеджер для соцсетей: стратегия, контент-план, календарь, ТЗ, обработка медиа.

## Запуск (Windows)
1. `python -m venv venv`
2. `venv\Scripts\pip install -r AI_SMM_Work_Architecture_A75\requirements.txt`
3. `START.bat`

## Устройство
- `AI_SMM_Work_Architecture_A75/` — приложение (PySide6), точка входа `app.py`.
- `data/projects/<id>/project.db` — данные проекта в SQLite; `backups/` — копии до миграции и чистки.
- `work/PLAN.md` — текущий план, `work/DECISIONS.md` — контракт данных, `work/SESSION_LOG.md` — журнал работ.

## Статус
Разработка. Этап A: данные и каркас.
