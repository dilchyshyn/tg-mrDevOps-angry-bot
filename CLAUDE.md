# mrDevOps: контекст для Claude Code

Telegram-бот у груповому чаті. Коли хтось пише про DevOps, бот відповідає грубою цитатою в reply. Текст у репозиторії і коментарях українською, назви змінних і функцій англійською.

## Стек

- Python 3.12+, aiogram 3 (long polling), pydantic-settings, PyYAML
- LLM: Gemini Flash через `google-genai` (`gemini-2.5-flash`). Класифікатор теми і генерація цитат. Anthropic тут не використовується.
- Docker (`python:3.12-slim`, non-root, read-only), docker compose на VPS
- GitHub Actions: CI (ruff, mypy, pytest, образ у GHCR) і деплой по SSH

## Структура

```
bot/      main.py (точка входу, dispatcher, heartbeat), handlers.py (групи, /start),
          classifier.py (JSON-вердикт від LLM), cooldown.py, quote_source.py
config/   settings.py (Settings з .env)
quotes/   quotes.yaml (пул цитат), loader.py (Quote, load_quotes)
tests/    unit-тести, LLM завжди мокається
```

## Команди

- `make install`: venv у `.venv` і `pip install -e ".[dev]"`
- `make check`: ruff, mypy, pytest. Запускати перед комітом.
- `make run`: локальний запуск (потрібен `.env`)
- `make up` / `make logs` / `make down`: docker compose

## Конвенції

- Поведінка за замовчуванням: LLM-класифікатор обирає DevOps-тему, cooldown 60 с на чат. Збої LLM трактуються як «не DevOps», бот мовчить.
- Без `GEMINI_API_KEY` класифікатор вимкнений, і бот у групах мовчить.
- Секрети тільки в `.env` (не комітиться) або в GitHub Secrets. Не вписувати токени в код і тести.
- Тести не ходять у мережу. Gemini-клієнт мокається через `aio.models.generate_content`.
- Конфіг через змінні середовища: нові параметри додавати в `config/settings.py` і `.env.example`.

## Цитати

- Пул у `quotes/quotes.yaml`. Поля: `id`, `text`, `lang` (`uk` або `surzhyk`), `tags`.
- Стиль грубий, з матами. Заборонено сексуальне глузування з жінок, жарти про національності, релігії, сексуальну орієнтацію і реальних людей. Ці межі діють і в промпті генерації (`GENERATE_PROMPT` у `bot/quote_source.py`).
- Після змін у пулі запускати `make test`, там перевіряється валідність файлу.

## Git

- Гілка `main`, CI запускається на PR і push.
- Коміти по фічах, повідомлення українською у форматі `type(scope): опис`.
- Не пушити і не створювати коміти без прохання користувача.
