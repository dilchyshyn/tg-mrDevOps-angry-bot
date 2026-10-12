# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# mrDevOps: контекст для Claude Code

Telegram-бот у груповому чаті. Коли хтось пише про DevOps, бот відповідає грубою цитатою в reply. Текст у репозиторії і коментарях українською, назви змінних і функцій англійською.

## Стек

- Python 3.12+, aiogram 3 (long polling), pydantic-settings, PyYAML
- LLM: Gemini Flash через `google-genai` (`gemini-2.5-flash`). Класифікатор теми і генерація цитат. Anthropic тут не використовується.
- Docker (`python:3.12-slim`, non-root, read-only), docker compose на VPS
- GitHub Actions: CI (ruff, mypy, pytest, образ у GHCR) і деплой по SSH

## Команди

- `make install`: venv у `.venv` і `pip install -e ".[dev]"`
- `make check`: `lint` + `typecheck` + `test`. Запускати перед комітом, CI робить те саме.
- `make lint` (ruff check + format --check), `make format` (автовиправлення), `make typecheck` (`mypy bot config quotes`, strict)
- Один тест: `.venv/bin/pytest tests/test_quote_source.py::test_bundled_quotes_file_is_valid`, або `-k <назва>`
- `make run`: локальний запуск (потрібен `.env`, шаблон у `.env.example`)
- `make up` / `make logs` / `make down`: docker compose

Ruff: довжина рядка 100, правила `E F I B UP ASYNC`. pytest з `asyncio_mode = "auto"`, тому async-тести без декоратора.

## Архітектура

Потік повідомлення в групі (`bot/handlers.py::on_group_text`), перша гілка, що спрацювала, завершує обробку:

1. `mentions_krasovska` (`bot/triggers.py`): статична фраза з `LOVE_PHRASES` на кожне повідомлення, без cooldown. LLM про неї не викликається навіть при звертанні до бота.
2. `is_addressed` (ім'я бота за regex, `@username`, reply на бота): `Responder.answer` через Gemini, без cooldown. Без LLM або при збої відповідає `NO_ANSWER`.
3. DevOps-гілка, кожен крок може обірвати обробку мовчки:
   - `should_classify`: дешевий фільтр без LLM (довжина ≥ `MIN_TEXT_LENGTH`, є літери);
   - `Cooldown.ready`: пауза на чат, `mark` лише після успішного reply;
   - `classifier is None` → мовчимо (немає `GEMINI_API_KEY` або `LLM_ENABLED=false`);
   - `Classifier.classify` → `Verdict(devops, topic)`, будь-яка помилка дає `NEGATIVE`;
   - `QuoteSource.next_quote(topic)` залежно від `QUOTE_MODE`: `static`, `generate` або `mixed` (пул без повторів, далі генерація).

Залежності хендлерів передаються через aiogram DI: у `bot/main.py` вони кладуться в `dispatcher["<name>"]`, і хендлер отримує їх як kwargs з тим самим іменем. Новий параметр хендлера треба зареєструвати в `main.py`.

Стан (cooldown, використані id цитат) тільки в пам'яті процесу, після рестарту скидається.

Один `genai.Client` спільний для класифікатора, генерації цитат і `Responder`. Усі викликають `client.aio.models.generate_content` з `system_instruction` і `thinking_budget=0`: інакше thinking-токени 2.5 Flash з'їдають `max_output_tokens` і відповідь обрізається; у тестах мокається саме цей ланцюжок (див. фейки в `tests/test_classifier.py`).

Healthcheck: `bot/main.py::heartbeat` кожні 30 с пише файл, а `HEALTHCHECK` у `Dockerfile` перевіряє, що він свіжий (< 120 с). Шлях `/tmp/mrdevops.heartbeat` захардкожений у Dockerfile, тому `HEARTBEAT_PATH` у compose має з ним збігатися. Контейнер `read_only`, писати можна лише в `/tmp` (tmpfs).

## Деплой

- `ci.yml`: на PR і push: перевірки, збірка образу і smoke-тест (`import bot.main` + завантаження цитат у `--read-only` контейнері). На push у `main` публікує `ghcr.io/<repo lowercase>:latest` і `:<sha>`. Ім'я репо має великі літери, тому скрізь `${GITHUB_REPOSITORY,,}`.
- `deploy.yml`: `workflow_run` після успішного CI на push у `main`, або `workflow_dispatch` з `sha` для відкату. Деплоїть образ `:<sha>`, а не `:latest`. Образ мультиархітектурний (amd64 + arm64), сервер — Oracle Cloud Always Free. На VPS через `ssh vps "bash -s" < scripts/deploy.sh`: pull, `compose up --no-build`, чекання healthy (≤ 240 с, рестарт контейнера = провал), інакше відкат на попередній образ.
- Секрети (environment `production`): `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`, опційно `VPS_KNOWN_HOSTS`, `BOT_TOKEN`, `GEMINI_API_KEY`. Якщо `BOT_TOKEN` задано, `.env` на VPS (`~/mrdevops/.env`) перезаписується з секретів і `vars`. Новий параметр конфігу, який треба задавати на проді, додати і в цикл у `deploy.yml`.
- Для роботи в групах у @BotFather має бути вимкнений privacy mode (`/setprivacy` → Disable).

## Конвенції

- Збої LLM трактуються як «не DevOps», бот мовчить. Не кидати винятки з `Classifier` і `QuoteSource`, повертати `NEGATIVE` / `None`.
- Секрети тільки в `.env` (не комітиться) або в GitHub Secrets. Не вписувати токени в код і тести.
- Тести не ходять у мережу, LLM завжди мокається.
- Конфіг через змінні середовища: нові параметри додавати в `config/settings.py` і `.env.example`.

## Цитати

- Пул у `quotes/quotes.yaml`. Поля: `id` (унікальний), `text`, `lang` (`uk` або `surzhyk`), `tags`. `quotes/loader.py` падає на дублях id і невідомій мові.
- Стиль грубий, з матами. Заборонено сексуальне глузування з жінок, жарти про національності, релігії, сексуальну орієнтацію і реальних людей. Ці межі діють і в промптах (`GENERATE_PROMPT` у `bot/quote_source.py`, `ANSWER_PROMPT` у `bot/responder.py`).
- Єдиний виняток щодо реальних людей: Красовська, викладачка англійської. Про неї тільки тепло, без матів і без жодного сексуального підтексту, і тільки статичні фрази.
- Після змін у пулі запускати `make test` (`test_bundled_quotes_file_is_valid` перевіряє файл).

## Git

- Гілка `main`, CI запускається на PR і push.
- Коміти по фічах, повідомлення українською у форматі `type(scope): опис`.
- Не пушити і не створювати коміти без прохання користувача.
- Є `.pre-commit-config.yaml` (ruff, ruff-format, mypy з `.venv`).
