# mrDevOps

Telegram-бот, який у груповому чаті відповідає пацанською цитатою, коли хтось пише про девопс.

## Як це працює

1. Бот отримує повідомлення в групі (privacy mode вимкнений).
2. Короткі повідомлення і без літер відсіюються без виклику LLM.
3. Gemini Flash класифікує, чи це DevOps-тема.
4. Якщо так і чат не в cooldown, бот відповідає цитатою в reply.
5. Цитата береться з `quotes/quotes.yaml` або генерується LLM (режим `QUOTE_MODE`).

## Налаштування

1. У @BotFather створити бота, отримати токен, вимкнути privacy mode командою `/setprivacy` → Disable.
2. Отримати ключ Gemini API в Google AI Studio (aistudio.google.com → Get API key).
3. `cp .env.example .env` і заповнити значення.

## Локальний запуск

```bash
make install
make run
```

## Тести і перевірки

```bash
make check
```

## Docker

```bash
make up      # збірка і запуск
make logs    # логи
make down
```

## Деплой

Повний цикл: push у `main` → CI → образ у GHCR → автоматичний деплой на VPS.

- `ci.yml`: на кожен PR і push ruff, mypy, pytest, збірка образу і smoke-тест у ньому. На push у `main` публікує образ `ghcr.io/<owner>/<repo>:latest` і `:<sha>`.
- `deploy.yml`: після успішного CI по `main` по SSH деплоїть образ саме того коміту (`scripts/deploy.sh`). Чекає, поки контейнер стане healthy, інакше відкочує на попередній образ і падає.
- Ручний деплой або відкат: Actions → Deploy → Run workflow, у полі `sha` вказати коміт з `main` (порожньо = останній).
- Dependabot щотижня пропонує оновлення actions, pip-залежностей і базового образу.

GitHub, environment `production`:

| Що | Тип | Обов'язково |
|---|---|---|
| `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY` | secret | так |
| `VPS_KNOWN_HOSTS` (вивід `ssh-keyscan -H <host>`) | secret | бажано, інакше ключ хоста не перевіряється |
| `BOT_TOKEN`, `GEMINI_API_KEY` | secret | ні: якщо `BOT_TOKEN` задано, `.env` на сервері генерується з секретів |
| `LLM_MODEL`, `LLM_ENABLED`, `QUOTE_MODE`, `COOLDOWN_SECONDS`, `MIN_TEXT_LENGTH` | variable | ні, порожні беруться з дефолтів |

На VPS потрібен Docker з compose, користувач `VPS_USER` у групі `docker`. Якщо `BOT_TOKEN` у секретах немає, `.env` треба покласти вручну в `~/mrdevops/.env`. Сервер логіниться в GHCR тимчасовим токеном джоба, тому образ може бути приватним.

## Структура

```
bot/      хендлери, класифікатор, cooldown, вибір цитат, точка входу
config/   налаштування (pydantic-settings)
quotes/   пул цитат і завантажувач
tests/    unit-тести (LLM мокається)
```

## Зміна тону цитат

Редагуй `quotes/quotes.yaml`. Поля: `id`, `text`, `lang` (`uk` або `surzhyk`), `tags`.
