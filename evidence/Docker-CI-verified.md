# Перевірка Docker та GitHub Actions

Дата: 18.10.2026
Репозиторій: https://github.com/dimakaparnyk/professional-python-labs
Запуск: https://github.com/dimakaparnyk/professional-python-labs/actions/runs/39135119445
Commit: 2e3fb3d3e73f29ffa93689d631746e20beba7caf

Результат: Success. Загальна тривалість: 51 с.
- quality (Python 3.11): успіх.
- quality (Python 3.12): успіх.
- docker: успіх, 28 с; образ побудовано, контейнер запущено.
- HTTP /health у контейнері: {"status":"ok"}. Початкові спроби під час запуску повторювалися; остаточний запит успішний.
- Створено два артефакти пакетів packages-3.11 і packages-3.12.

GitHub показав попередження про застарілий Node.js 20 у версіях actions та повідомлення про майбутню зміну ubuntu-latest. Вони не спричинили помилок цього запуску.

Ця перевірка підтверджує Docker на GitHub-hosted runner. Локальне встановлення Docker Desktop у Windows ще не підтверджено.
Цей запис уточнює попередні звіти, де запуск Docker/CI був позначений як невиконаний. Звіт ЛР10 оновлено цими результатами 19.10.2026.
