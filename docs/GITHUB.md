# Як завантажити проєкт на GitHub

## 1. Підготовка

Увійдіть у свій GitHub. Створіть новий репозиторій `computer-inventory`.
Оберіть видимість за вимогами викладача. Не додавайте README, .gitignore
або license під час створення: ці файли вже є локально.

У ZIP є папка `.git` і готова історія з трьох логічних комітів.
Розпакуйте весь ZIP, включно з прихованою `.git`. Відкрийте PowerShell
у папці, де знаходиться `pyproject.toml`. Середовище `.venv` треба створити
за README; в архів воно не входить.

## 2. Вкажіть автора майбутніх комітів

Замініть ПІБ та адресу власними даними; можна використати адресу noreply
з GitHub → Settings → Emails. Параметри діють лише в цьому репозиторії.

```powershell
git config user.name "ВАШЕ ПІБ"
git config user.email "ВАША АДРЕСА EMAIL"
git status
git log --oneline
```

Три підготовлені коміти мають службового автора `Lab Preparation`
(`lab-preparation@example.invalid`). Зміна config змінює автора лише
майбутніх комітів. Не видавайте службову історію за власні етапи роботи;
для демонстрації своїх етапів повторіть їх самостійно в окремій папці.

## 3. Підключіть віддалений репозиторій

Замініть YOUR_USERNAME на свій логін GitHub, а назву — якщо обрали іншу.

```powershell
git remote add origin https://github.com/YOUR_USERNAME/computer-inventory.git
git remote -v
git push -u origin main
```

Під час першого push Git Credential Manager може відкрити браузер.
Завершіть вхід самостійно. Пароль облікового запису не використовується
як пароль Git через HTTPS; не вставляйте токен у файли проєкту.

Якщо origin уже існує, спочатку перевірте `git remote -v`, а потім за потреби:

```powershell
git remote set-url origin https://github.com/YOUR_USERNAME/computer-inventory.git
```

Оновіть сторінку репозиторію: мають бути README, src, tests, pyproject.toml
і три коміти. `.venv` та кеші не повинні з’являтися.

## 4. Наступні зміни

```powershell
git add src tests README.md
git commit -m "Improve inventory functionality"
git push
```

Звіт можна додати окремо в каталог reports і закомітити окремим етапом.

## Якщо .git не збереглася після розпакування

У новій папці без історії виконайте `git init -b main`, вкажіть автора,
а потім три коміти за логічними групами файлів:

```powershell
git add .gitignore pyproject.toml src/computer_inventory/__init__.py
git commit -m "Create project structure and packaging configuration"
git add src/computer_inventory/models.py src/computer_inventory/services.py
git commit -m "Add device model and inventory business logic"
git add src/computer_inventory/main.py tests README.md docs
git commit -m "Add console interface tests and documentation"
```

Далі підключіть origin і виконайте push, як у пункті 3.

Офіційна інструкція:
https://docs.github.com/en/migrations/importing-source-code/using-the-command-line-to-import-source-code/adding-locally-hosted-code-to-github
