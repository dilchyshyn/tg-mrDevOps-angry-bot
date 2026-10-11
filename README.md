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

- `ci.yml`: ruff, mypy, pytest на кожен PR і push. На push в `main` збирає образ і публікує його в GHCR.
- `deploy.yml`: після успішного CI по `main` підключається по SSH до VPS і оновлює контейнер через `docker compose`.

Секрети в GitHub (environment `production`): `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`.
На VPS має бути встановлений Docker з compose, а `.env` з `BOT_TOKEN` і `GEMINI_API_KEY` лежить у `~/mrdevops/.env`.

## Структура

```
bot/      хендлери, класифікатор, cooldown, вибір цитат, точка входу
config/   налаштування (pydantic-settings)
quotes/   пул цитат і завантажувач
tests/    unit-тести (LLM мокається)
```

## Зміна тону цитат

Редагуй `quotes/quotes.yaml`. Поля: `id`, `text`, `lang` (`uk` або `surzhyk`), `tags`.
