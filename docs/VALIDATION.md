# Фактично виконані перевірки

Локальне середовище: Windows, Python 3.12.14. Варіант 13.

- Ruff check: успіх.
- Ruff format --check: успіх.
- Mypy: 16 source-файлів, помилок немає.
- Pytest: 84 passed, 9 subtests passed, 1 deprecation warning залежності.
- Сукупне statement/branch coverage: 96.45%; поріг 80% виконано.
- Wheel і sdist побудовано через python -m build --no-isolation.
- Wheel установлено в новий venv із залежностями; demo та імпорт API успішні.
- API з установленого wheel: /health повернув 200 і {"status":"ok"}.
- Живий Uvicorn: чотири POST /devices → 201; health, list, statistics → 200.
- SQLite: CRUD, UNIQUE, FOREIGN KEY та rollback перевірено тестами.
- Експерименти ЛР2, ЛР3, ЛР5, ЛР6, ЛР9 виконано; журнали в docs/results.

## Що потребує окремого фактичного запуску

Docker у середовищі не знайдено. Dockerfile, Compose і healthcheck підготовлені,
але image build та container run локально не підтверджено.

GitHub Actions підготовлено. Workflow не запускався в зовнішньому репозиторії,
тому green CI, Docker build у CI та знімки цих станів ще не підтверджено.

Потрібно виконати команди з README на машині з Docker, завантажити репозиторій
за docs/GITHUB.md та перевірити фактичні jobs у Actions.
