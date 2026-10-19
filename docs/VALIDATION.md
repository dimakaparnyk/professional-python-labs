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

## Фактичний Docker та CI

18.10.2026 Inventory CI №1 пройшов у приватному репозиторії dimakaparnyk/professional-python-labs.
https://github.com/dimakaparnyk/professional-python-labs/actions/runs/39135119445

Перевірений commit: 2e3fb3d3e73f29ffa93689d631746e20beba7caf.
Quality для Python 3.11 і 3.12 — Success. Docker build, run із volume та HTTP /health — Success.
Відповідь контейнера: {"status":"ok"}. Docker job — 28 с; весь workflow — 51 с.
Створено packages-3.11 та packages-3.12. Попередження Node.js 20 і зміни ubuntu-latest не вплинули на успіх.
Локальний Docker Desktop у Windows окремо не перевірений.
Оновлення документації 19.10.2026 не змінює виконуваний код перевіреного commit.
