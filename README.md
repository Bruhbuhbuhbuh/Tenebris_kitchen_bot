# Скрытие API-ключей и чувствительных данных

Коротко: никогда не храните реальные API-ключи в репозитории. Используйте переменные окружения, `.env` (локально) и GitHub Secrets (в CI).

Шаги, которые мы уже сделали:
- Убраны значения по умолчанию из `main.py` — теперь ключи берутся только из окружения.
- Добавлен `.gitignore`, чтобы игнорировать `.env`.
- Добавлен `.env.example` с плейсхолдерами.

Как использовать локально
1. Скопируйте `.env.example` в `.env` и заполните значения.

```
cp .env.example .env
# отредактируйте .env
```

2. Установите `python-dotenv`, если хотите автоматически загружать `.env` при запуске:

```
pip install python-dotenv
```

Как убрать уже закоммиченные ключи из истории
(ВНИМАНИЕ: переписывает историю — делайте это только если понимаете последствия и у вас есть права на репозиторий.)

Вариант A — самый простой (удалит файл, но не очистит старые коммиты):

```
git rm --cached .env
git commit -m "Remove .env from repo"
git push
```

Вариант B — использовать BFG (удобно для удаления конкретных строк/ключей):

1. Скачайте BFG: https://rtyley.github.io/bfg-repo-cleaner/
2. Сделайте зеркальную копию репозитория:

```
git clone --mirror git@github.com:YOURUSER/YOURREPO.git
java -jar bfg.jar --replace-text replacements.txt YOURREPO.git
cd YOURREPO.git
git push
```

`replacements.txt` — простой файл с заменами, например:

```
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==>REDACTED-GROQ
8854521444:AAFyU6NX_RoD5CK9JHXSUlYkNTqU5LSyB-M==>REDACTED-TELEGRAM
```

Вариант C — `git filter-repo` (рекомендуется, более гибкий):

```
# Установите git-filter-repo
pip install git-filter-repo

git clone --mirror git@github.com:YOURUSER/YOURREPO.git
cd YOURREPO.git
git filter-repo --replace-text replacements.txt
git push --force
```

После очистки истории — ПОВТОРНО СОЗДАЙТЕ/РОТОЙТЕ все скомпрометированные ключи в провайдерах (GitHub, Groq, Telegram и т.д.).

Рекомендации
- Никогда не храните реальные ключи в коде.
- Используйте GitHub Secrets для CI/Actions.
- Ротируйте ключи, если они попали в репозиторий.
