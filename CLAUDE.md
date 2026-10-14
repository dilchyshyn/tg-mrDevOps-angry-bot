# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# mrDevOps: контекст для Claude Code

Telegram-бот у груповому чаті. На DevOps-повідомлення відповідає грубою цитатою в reply, на звертання до себе відповідає через Gemini, на «Красовська» теплою фразою. Для окремих людей грубощі вимкнені (`PROTECTED_USERS`) або замінені «королівським» тоном (`QUEEN_USERS`). Текст у репозиторії і коментарях українською, назви змінних і функцій англійською.

## Стек

- Python 3.12+, aiogram 3 (long polling), pydantic-settings, PyYAML
- LLM: Gemini через `google-genai` (`gemini-3.5-flash-lite`). Тільки відповіді на звертання і, за бажанням, генерація цитат. DevOps-тема визначається ключовими словами, не LLM. Anthropic тут не використовується.
- Docker (`python:3.12-slim`, non-root, read-only), docker compose на VPS
- GitHub Actions: CI (ruff, mypy, pytest, мультиархітектурний образ у GHCR) і автодеплой по SSH на Oracle Cloud (ARM)

## Команди

- `make install`: venv у `.venv` і `pip install -e ".[dev]"`. Усі інструменти беруться з `.venv/bin/`, тож поза `make` викликати їх з цим префіксом (`.venv/bin/ruff`, `.venv/bin/mypy`, `.venv/bin/pytest`)
- `make check`: `lint` + `typecheck` + `test`. Запускати перед комітом, CI робить те саме.
- `make lint` (ruff check + format --check), `make format` (автовиправлення), `make typecheck` (`mypy bot config quotes`, strict)
- Один тест: `.venv/bin/pytest tests/test_quote_source.py::test_bundled_quotes_file_is_valid`, або `-k <назва>`
- `make run`: локальний запуск (потрібен `.env`, шаблон у `.env.example`)
- `make up` / `make logs` / `make down`: docker compose

Ruff: довжина рядка 100, правила `E F I B UP ASYNC`. pytest з `asyncio_mode = "auto"`, тому async-тести без декоратора.

## Архітектура

Потік повідомлення в групі (`bot/handlers.py::on_group_text`). Спершу рахуються прапорці автора через `ProtectedUsers` (`bot/protected.py`, username без урахування регістру або Telegram ID):

- `queen`: автор у `QUEEN_USERS`;
- `protected`: автор у `PROTECTED_USERS` **або** `queen` (королева завжди захищена);
- `tone` для `Responder`: `queen` / `polite` / `rude`.

Далі перша гілка, що спрацювала, завершує обробку:

1. `mentions_krasovska` (`bot/triggers.py`): статична фраза з `LOVE_PHRASES` будь-кому, на кожне повідомлення, без cooldown. LLM про неї не викликається навіть при звертанні до бота.
2. `is_addressed` (ім'я бота за regex, `@username`, reply на бота): `Responder.answer(text, tone=tone, history=...)` через Gemini, без cooldown. При reply на бота `history` — попередні репліки ланцюжка з `Dialogs` (`bot/dialogs.py`, до 10 реплік), щоб бот не суперечив сам собі; Telegram віддає лише одне повідомлення, на яке відповіли, тому ланцюжок зберігається в пам'яті за `parent_id`. Якщо ланцюжка немає (рестарт, reply на DevOps-цитату), береться текст самого повідомлення бота. Після відповіді обидві репліки (людини і бота, включно із запасними) записуються в `Dialogs`. У грубому тоні в `system_instruction` додаються `quotes.examples(topic)`, і Gemini закінчує відповідь власною цитатою в їхньому стилі; з шансом `DRUNK_CHANCE` (за замовчуванням 0.1) `Responder` сам додає `DRUNK_PROMPT`, і бот відповідає п'яним, теж лише в грубому тоні; захищеним і королеві прикладів не дають, бо в пулі мати. Якщо Gemini недоступний (найчастіше 429) або вимкнений, запасна відповідь залежить від автора: королеві `queen_phrase()`, захищеним `POLITE_NO_ANSWER`, решті `quotes.static_quote(topic)` (і `NO_ANSWER` лише при порожньому пулі). Захищені ніколи не отримують цитату з пулу.
3. `queen`: на DevOps-слово `queen_phrase()` (`QUEEN_PHRASES`), на інше тиша. `protected`: тиша.
4. DevOps-гілка для решти:
   - `devops_topic` (`bot/triggers.py`): regex-и за основами слів, повертає тему або `None`. LLM тут не викликається, бо безкоштовний ліміт Gemini (~20 запитів на добу на модель) згорав на перевірці кожного повідомлення. Нові слова додавати в `_DEVOPS_TOPICS` разом з тестом у `tests/test_triggers.py`, включно з негативним прикладом, щоб не ловити звичайні слова («подруга», «продукти»);
   - `Cooldown.ready`: пауза на чат, `mark` лише після успішного reply. За замовчуванням `COOLDOWN_SECONDS=0`, тобто паузи немає;
   - `QuoteSource.next_quote(topic, text)` залежно від `QUOTE_MODE`: `static` (за замовчуванням, пул по колу у випадковому порядку без повторів у межах кола; останні `len(pool) // 3` показаних не повторюються і на стику кіл), `generate` (на проді) або `mixed`. Генерація отримує текст повідомлення і `examples(topic)` (5 цитат з пулу, спершу за темою) як зразок стилю, щоб цитата була влучною саме до повідомлення. При збої LLM завжди повертає цитату з пулу, з перевагою тегів теми (`TOPIC_TAGS` у `bot/quote_source.py`: тема з `devops_topic` → теги в `quotes.yaml`; нова тема в `_DEVOPS_TOPICS` потребує запису і тут, `test_bundled_tags_cover_all_topics` це перевіряє).

Захист діє лише на повідомлення самого захищеного. Якщо хтось інший пише DevOps-фразу у відповідь захищеному, бот відповідає цьому іншому грубою цитатою. Так задумано власником.

Залежності хендлерів передаються через aiogram DI: у `bot/main.py` вони кладуться в `dispatcher["<name>"]`, і хендлер отримує їх як kwargs з тим самим іменем. Новий параметр хендлера треба зареєструвати в `main.py`.

Стан (cooldown, ланцюжки діалогів) тільки в пам'яті процесу, після рестарту скидається. Виняток — стан пулу цитат (показані в колі й останні): якщо задано `STATE_PATH`, `QuoteSource` після кожного вибору атомарно пише JSON і читає його на старті, відкидаючи id, яких уже немає в пулі. У compose це `/data/quotes-state.json` на named volume `mrdevops-data`, який переживає рестарти і деплої; локально без `STATE_PATH` усе в пам'яті.

Поза групою бот реагує лише на `/start` в особистих повідомленнях (`on_start`), решту ігнорує.

Без `GEMINI_API_KEY` клієнт не створюється, а `LLM_ENABLED=false` вимикає і `Responder` (у DI тоді лежить `None`), і генерацію цитат (`QuoteSource` отримує `client=None` і бере все з пулу).

Один `genai.Client` спільний для генерації цитат і `Responder`. Обидва ходять у Gemini лише через `bot/llm.py::generate`: він ловить збої (повертає `None`), логує час і токени (вхід, вихід, роздуми) з міткою виклику. Там же `FORBIDDEN_TOPICS` (спільні межі грубих промптів) і `format_examples`. У тестах мокається ланцюжок `client.aio.models.generate_content` через `tests/fakes.py::FakeGeminiClient`. Клієнт створюється з `HttpRetryOptions(attempts=1)`: інакше на 429 SDK ретраїть хвилинами, і бот довго не відповідає.

Вибір моделі: `gemini-3.5-flash-lite` відповідає без thinking. `thinking_config` не передається, бо 3.x відхиляє `thinking_budget=0`, а `gemini-3.8-flash` не підтримує `thinking_level=minimal` і спалює ~400 токенів на роздуми. Старі `gemini-2.0-*` повертають 404. Ліміт (~20 запитів на добу на модель) спільний для генерації цитат і відповідей: у режимі `generate` він згорає за ~20 DevOps-повідомлень, далі до опівночі за тихоокеанським часом усе йде з пулу. Безкоштовні ліміти видно тільки в AI Studio (aistudio.google.com/rate-limit), рахуються на проєкт і модель, денні скидаються опівночі за тихоокеанським часом.

Healthcheck: `bot/main.py::heartbeat` кожні 30 с пише файл, а `HEALTHCHECK` у `Dockerfile` перевіряє, що він свіжий (< 120 с). Шлях `/tmp/mrdevops.heartbeat` захардкожений у Dockerfile, тому `HEARTBEAT_PATH` у compose має з ним збігатися. Контейнер `read_only`, писати можна лише в `/tmp` (tmpfs, очищається при перезапуску) і в `/data` (volume). `/data` створюється в `Dockerfile` з власником `mrdevops`: новий named volume переймає цього власника з образу.

## Деплой

- `ci.yml`: на PR і push: перевірки, збірка образу і smoke-тест (`import bot.main` + завантаження цитат у `--read-only` контейнері). Job `image` — матриця з нативних раннерів (`ubuntu-24.04` для amd64, `ubuntu-24.04-arm` для arm64, без QEMU): кожен збирає і тестує свою архітектуру, на push у `main` пушить за digest. Job `manifest` об'єднує digest-и в `ghcr.io/<repo lowercase>:latest` і `:<sha>`. Ім'я репо має великі літери, тому скрізь `${GITHUB_REPOSITORY,,}`.
- `deploy.yml`: `workflow_run` після успішного CI на push у `main`, або `workflow_dispatch` з `sha` для відкату. Деплоїть образ `:<sha>`, а не `:latest`. Образ мультиархітектурний (amd64 + arm64), сервер — Oracle Cloud Always Free. На VPS через `ssh vps "bash -s" < scripts/deploy.sh`: pull, `compose up --no-build`, чекання healthy (≤ 240 с, рестарт контейнера = провал), інакше відкат на попередній образ. Після успіху видаляються старі образи цього репо, крім поточного і попереднього; чужі образи на сервері (`telegram-img-bot` тощо) не чіпаються.
- `.github/dependabot.yml`: щотижневі PR з оновленнями actions, pip-залежностей і базового образу.
- Секрети (environment `production`): `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`, опційно `VPS_KNOWN_HOSTS`, `BOT_TOKEN`, `GEMINI_API_KEY`. Якщо `BOT_TOKEN` задано, `.env` на VPS (`~/mrdevops/.env`) перезаписується з секретів і `vars`. Новий параметр конфігу, який треба задавати на проді, додати і в цикл у `deploy.yml`.
- Списки людей і несекретні параметри на проді — GitHub Variables того ж environment: `PROTECTED_USERS`, `QUEEN_USERS`, `QUOTE_MODE` (на проді `generate`), `COOLDOWN_SECONDS`, `LLM_MODEL`, `LLM_ENABLED`, `DRUNK_CHANCE`. Не задана змінна в `.env` не пишеться, і діє дефолт з `config/settings.py`. Змінювати через `gh variable set <NAME> --env production --body "..."`, потім `gh workflow run deploy.yml`, код чіпати не треба. Ручні правки `.env` на сервері перезапише наступний деплой. Королеву свідомо продубльовано в `PROTECTED_USERS` як запасний захист: не прибирати.
- Конкретні username людей у репозиторій (код, тести, документацію) не вписувати, вони живуть лише в GitHub Variables. У тестах вигадані імена.
- Для роботи в групах у @BotFather має бути вимкнений privacy mode (`/setprivacy` → Disable). Бот слухає токен в одному процесі: поки працює прод, локальний `make run` дасть `TelegramConflictError`.

## Конвенції

- Збої LLM не кидають винятків з `Responder` і `QuoteSource`: повертається `None`, а хендлер підставляє цитату з пулу.
- Секрети тільки в `.env` (не комітиться) або в GitHub Secrets. Не вписувати токени в код і тести.
- Тести не ходять у мережу, LLM завжди мокається.
- Конфіг через змінні середовища: нові параметри додавати в `config/settings.py` і `.env.example`. Виняток — внутрішні `QUOTES_PATH`, `HEARTBEAT_PATH` і `STATE_PATH` (задається в compose): вони мають дефолти в `settings.py` і в `.env.example` свідомо відсутні.

## Цитати

- Пул у `quotes/quotes.yaml`. Поля: `id` (унікальний), `text`, `lang` (`uk` або `surzhyk`), `tags`. `quotes/loader.py` падає на дублях id і невідомій мові.
- Стиль грубий, з матами. Заборонено сексуальне глузування з жінок, жарти про національності, релігії, сексуальну орієнтацію і реальних людей. Ці межі діють і в промптах (`GENERATE_PROMPT` у `bot/quote_source.py`, `ANSWER_PROMPT` у `bot/responder.py`). `POLITE_PROMPT` і `QUEEN_PROMPT` там само, але без матів взагалі.
- Винятки щодо реальних людей: Красовська (викладачка англійської) і користувачі з `QUEEN_USERS` (дівчина власника). Тільки тепло, без матів і без жодного сексуального підтексту. Про Красовську лише статичні фрази, до королеви — `QUEEN_PROMPT` і `QUEEN_PHRASES`.
- Після змін у пулі запускати `make test` (`test_bundled_quotes_file_is_valid` перевіряє файл).

## Git

- Гілка `main`, CI запускається на PR і push.
- Коміти по фічах, повідомлення українською у форматі `type(scope): опис`.
- Не пушити і не створювати коміти без прохання користувача.
- Є `.pre-commit-config.yaml` (ruff, ruff-format, mypy з `.venv`).
