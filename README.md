# Inventory Service — облік комп’ютерної техніки

Наскрізний проєкт курсу «Професійний Python», лабораторні №1–10,
**варіант 13**. Автор: **Капарник Дмитро Андрійович, ФЕП-32**.

Пристрій має інвентарний номер, тип, виробника, модель і вартість.
Система підтримує пошук, фільтр виробника, середню/загальну вартість,
найдорожчий пристрій; у наступних етапах — імпорт, БД та REST API.

## Вимоги й установлення

Python 3.11+, Git; для контейнерного запуску — окремо Docker.
Команди нижче виконуються з каталогу, де знаходиться pyproject.toml.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[test,dev]"
```

Активація необов’язкова: `.\.venv\Scripts\Activate.ps1`. Якщо PowerShell
блокує активацію, використовуйте прямі шляхи до команд середовища, як нижче.
Середовище `.venv` не переноситься в ZIP і створюється заново після розпакування.

## Консольні режими

```powershell
.\.venv\Scripts\python.exe -m inventory_service.main
.\.venv\Scripts\python.exe -m inventory_service.main --demo
.\.venv\Scripts\python.exe -m inventory_service.main --analytics
.\.venv\Scripts\python.exe -m inventory_service.main --oop-demo
.\.venv\Scripts\python.exe -m inventory_service.main --import-config config.yaml
```

Без аргументів відкривається меню з порожнім списком. Воно працює з даними
в пам’яті до виходу. REST API зберігає дані у SQLite між перезапусками.
Старий запуск `python -m computer_inventory.main` теж підтримується.

Демо містить чотири пристрої: сума **92700.00 грн**, середнє **23175.00 грн**,
найдорожчий — **INV-003, Dell Latitude 5440, 45000.00 грн**.
Суми обчислюються Decimal або цілими копійками; середнє округлюється
ROUND_HALF_UP. Для порожнього набору суми й середнє — 0, максимум відсутній.
Інвентарні номери унікальні без урахування регістру. За однакової найбільшої
ціни обирається перший пристрій (у БД — з найменшим id).

## Конфігурація й API

`.env.example` документує параметри. Застосунок читає змінні **середовища**;
сам файл `.env` автоматично не завантажується. Для Docker його можна
передати через `--env-file`. У прикладі немає реальних секретів.

```powershell
$env:DATABASE_URL = "sqlite:///inventory.db"
$env:APP_ENV = "development"
$env:LOG_LEVEL = "INFO"
.\.venv\Scripts\uvicorn.exe inventory_service.api:create_app --factory --host 127.0.0.1 --port 8000
```

Swagger: http://127.0.0.1:8000/docs. OpenAPI: /openapi.json.

| Метод | Шлях | Призначення |
|---|---|---|
| GET | /health | Перевірка доступності та з’єднання з БД |
| GET | /devices | Список, пошук і фільтрація |
| POST | /devices | Реєстрація пристрою |
| GET | /devices/{id} | Отримання пристрою |
| PATCH | /devices/{id} | Зміна вартості |
| DELETE | /devices/{id} | Видалення |
| GET | /manufacturers | Список виробників |
| POST | /manufacturers | Додавання виробника |
| GET | /manufacturers/{id}/devices | Обладнання виробника |
| GET | /devices/statistics або /statistics | Кількість, сума, середнє, максимум |
| GET | /manufacturers/details?names=Dell | Асинхронний запит до провайдера |

Параметри /devices: manufacturer, inventory_number, offset, limit (1–100).
У /manufacturers/details URL провайдера задається PROVIDER_URL (типово
http://127.0.0.1:8001); провайдер має відповідати на /manufacturers/{name}.
HTTPX-клієнт виконує Task/gather, обмежує одночасність Semaphore, застосовує
timeout і повторює тимчасові помилки з backoff. Тести використовують
MockTransport, тому не залежать від інтернету.

Приклад POST /devices:

```json
{"inventory_number":"INV-001","type":"Computer","manufacturer":"Dell","model":"Latitude","value":"45000.00","location":"Lab 13"}
```

Успіх: 201. Повторний номер: 409. Некоректна ціна: 422. Відсутній id: 404.
Грошові значення в JSON передаються рядками, щоб зберегти точність.

## Лабораторні та Git

| Робота | Можливості | Запуск експерименту |
|---|---|---|
| 1 | src-layout, пакет, меню, Git | python -m computer_inventory.main --demo |
| 2 | list/tuple/set/dict, Counter, індекс, closure, decorator | python scripts/lab02.py |
| 3 | generators, CSV pipeline, batches, 10k/100k/500k | python scripts/lab03.py --output work/datasets |
| 4 | Computer/Printer, Protocol, ABC, Generic, DI | python scripts/lab04.py |
| 5 | YAML, validation, strict/tolerant, atomic JSON | python scripts/lab05.py work/io-experiment |
| 6 | pytest, fixtures, Mock/AsyncMock, coverage | python -m pytest --cov=computer_inventory --cov-branch |
| 7 | SQLite, ORM, DB-API, migration, rollback | python scripts/lab07.py work/database/inventory.db |
| 8 | REST API, HTTPX, retry, timeout, Semaphore | uvicorn inventory_service.api:create_app --factory |
| 9 | Threads/Processes/NumPy, profiling, cache | python scripts/lab09.py work/performance |
| 10 | package, environment, Docker, CI | python -m build |

У таблиці скорочені команди: після активації середовища вони виконуються
без префікса .venv\Scripts. В архіві збережено `.git` і теги `lab-01` … `lab-10`.
`lab-01` … `lab-09` фіксують початкові етапи; фінальні виправлення, узгодження
округлення та форматування містяться в `lab-10` і версії `v1.0.0`.
Службовий автор підготовлених комітів — Lab Preparation. Власні зміни
підписуйте своїм ім’ям через локальні git config (див. docs/GITHUB.md).

Для перегляду раннього етапу без зміни фінального дерева:

```powershell
git worktree add ../inventory-lab01 lab-01
```

Кожен такий каталог потребує власного середовища. Усі роботи зберігають
одну предметну область варіанта 13. `value` у CSV ЛР5 відповідає `cost`
у моделі ЛР1 та CSV ЛР3; імпортер приймає обидві назви.

## Структура

- src/computer_inventory/models.py, services.py, main.py — основа ЛР1.
- analytics.py — індекс, групування, comprehensions, декоратор і closure.
- streaming.py — лінивий конвеєр і генерація відтворюваних наборів.
- domain.py — типізована модель, repository, registry, maintenance service.
- fileio.py — YAML, помилки, журналювання, CSV і атомарний JSON.
- database.py — ORM, репозиторії, SQL і версійована міграція SQLite.
- api.py, async_client.py — HTTP-контракт і асинхронний провайдер.
- performance.py — порівнювані реалізації й кеш з інвалідацією.
- src/inventory_service — фінальна точка входу та конфігурація середовища.
- tests — unit, integration, API, boundary та failure-path перевірки.
- scripts — відтворювані демонстрації й вимірювання.
- experiments — ізольовані навмисні помилки для навчальних досліджень.
- migrations — SQL-схема та додавання location.

У БД вартість зберігається цілими копійками. Foreign keys увімкнені.
Транзакція register_batch підтверджує всю групу або відкачує її цілком.
Міграції застосовуються функцією migrate, версія — PRAGMA user_version.

## Перевірки й збірка

```powershell
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\ruff.exe format --check .
.\.venv\Scripts\mypy.exe src
.\.venv\Scripts\python.exe -m pytest --cov=computer_inventory --cov=inventory_service --cov-branch --cov-fail-under=80 --cov-report=term-missing --cov-report=html
.\.venv\Scripts\python.exe -m build
```

Навмисно помилковий приклад типізації збережено як experiments/type_errors.txt:
копіюйте його в тимчасовий .py, виконуйте mypy й не додавайте до production.
Експеримент якості тестів: python experiments/testing_quality.py work/testing.
Усі експериментальні результати слід вимірювати заново на своїй машині.
Час процесів включає запуск і передавання даних; tracemalloc не вимірює
повний RSS і пам’ять усіх дочірніх процесів.

## Docker

```powershell
docker build -t inventory-service:1.0.0 .
docker run --name inventory -p 8000:8000 -v inventory-data:/data -e APP_ENV=production -e DATABASE_URL=sqlite:////data/inventory.db inventory-service:1.0.0
```

Або `docker compose up --build`. Образ використовує non-root user,
healthcheck та окремий етап збірки. Volume зберігає SQLite після видалення
контейнера. API доступне на http://127.0.0.1:8000/docs.

## CI/CD і завантаження на GitHub

Покрокова інструкція — **docs/GITHUB.md**. Після створення порожнього
репозиторію й підключення origin виконайте `git push -u origin main`,
а для тегів — `git push origin --tags`. Workflow запускає lint, format,
mypy, pytest з branch coverage, package build і Docker build/run/health.
Матриця якості перевіряє Python 3.11 та 3.12. Пакети зберігаються як artifacts.

Локальні перевірки та вміст workflow — різні докази: статус GitHub Actions
підтверджується лише реальним запуском у вашому репозиторії. Локально Docker
не перевірено, оскільки виконуваний файл Docker у середовищі не знайдено.

## Сценарій захисту

1. Показати структуру, моделі й історію git log --oneline.
2. Запустити --demo, --analytics та --oop-demo.
3. Показати YAML, імпорт і збереження попереднього JSON після помилки.
4. Запустити pytest і переглянути htmlcov/index.html.
5. Показати БД, parameterized query, міграцію location і rollback.
6. Запустити API й створити, знайти, змінити та видалити пристрій у /docs.
7. Показати benchmark.csv, profile.txt та інвалідацію кешу.
8. Зібрати wheel/sdist, запустити Docker і показати /health.
9. Показати фактичний результат workflow у вкладці Actions.

## Підтверджений результат CI від 18.10.2026

[Inventory CI №1](https://github.com/dimakaparnyk/professional-python-labs/actions/runs/39135119445) завершився успішно: Python 3.11, Python 3.12, Docker build/run та HTTP /health. Перевірено commit 2e3fb3d. Це оновлення уточнює попередні згадки про ще не запущений workflow; локальний Docker у Windows залишається неперевіреним.
