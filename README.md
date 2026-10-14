# mrDevOps

Telegram-бот, який у груповому чаті відповідає пацанською цитатою, коли хтось пише про девопс.

## Як це працює

Бот читає кожне текстове повідомлення в групі (privacy mode має бути вимкнений) і перевіряє по черзі:

1. **Красовська.** Якщо є слово «Красовська» у будь-якому відмінку й регістрі (також «красовская», «Krasovska»), бот відповідає теплою фразою про те, як сильно її любить. Фрази статичні, без матів, у `bot/triggers.py`. Відповідає на кожне таке повідомлення, без cooldown.
2. **Звертання до бота.** «мрдевопс», «мр девопс», «mrDevOps», «містер девопс», `@username` бота або reply на його повідомлення: Gemini відповідає по суті в стилі бота і закінчує власною цитатою в стилі пулу. Поки Gemini думає, у чаті видно «друкує…». У reply на бота Gemini бачить попередні репліки ланцюжка (до 10), щоб не суперечити собі. З шансом `DRUNK_CHANCE` (10%) бот відповідає п'яним. Cooldown тут не діє. Якщо Gemini недоступний (ліміт, збій), бот відповідає цитатою з пулу за темою повідомлення.
3. **DevOps.** Тема визначається ключовими словами (`devops_topic` у `bot/triggers.py`: докер, под, деплой, пайплайн, сервер, логи, прод тощо), без Gemini. У режимі `QUOTE_MODE=generate` (так на проді) цитату пише Gemini саме під це повідомлення, взявши кілька цитат з `quotes/quotes.yaml` за зразок стилю. У режимі `static` (за замовчуванням), а також коли Gemini недоступний, береться цитата з пулу, спершу з тегами теми повідомлення: без повторів, поки не пройде все коло, і без повтору недавніх на стику кіл. Що вже показано, зберігається на docker volume і переживає рестарти й деплої. Паузи за замовчуванням немає (`COOLDOWN_SECONDS=0`).

**Захищені люди** (`PROTECTED_USERS`: Telegram ID або @username через кому). Їм бот не кидає DevOps-цитат, а на звертання відповідає ввічливо, без матів, навіть коли Gemini недоступний. Фрази про Красовську вони отримують як усі. На сервері список задається у GitHub: Settings → Environments → `production` → Variables → `PROTECTED_USERS`, після чого треба перезапустити Deploy.

**Королеви** (`QUEEN_USERS`, той самий формат). На звертання бот відповідає як королеві («Ваша Величносте», «моя королево»), а на DevOps-повідомлення замість цитати надсилає комплімент (`QUEEN_PHRASES` у `bot/triggers.py`). На звичайні повідомлення не реагує. Королеви автоматично захищені від грубощів.

Gemini (`gemini-3.5-flash-lite`) витрачається на звертання до бота і, в режимі `generate`, на DevOps-цитати. Безкоштовний ліміт (~20 запитів на добу) спільний, тож в активному чаті він може скінчитися за день. Далі до опівночі за тихоокеанським часом бот бере цитати з пулу.

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

## Хостинг на Oracle Cloud (Always Free)

Боту не потрібні вхідні порти (long polling), тільки вихідний інтернет і SSH для деплою.

1. **Сервер.** Oracle Cloud → Compute → Instances → Create instance:
   - Image: **Ubuntu 22.04 або 24.04**;
   - Shape: `VM.Standard.A1.Flex` (ARM, Always Free) або `VM.Standard.E2.1.Micro` (AMD, Always Free). Образ збирається під обидві архітектури;
   - SSH keys: завантаж свій публічний ключ, щоб зайти на сервер.
2. **Docker на сервері:**
   ```bash
   ssh ubuntu@<публічний IP>
   curl -fsSL https://get.docker.com | sudo sh
   sudo usermod -aG docker ubuntu
   exit   # перезайти, щоб група docker застосувалась
   ```
3. **Окремий ключ для деплою** (на своєму комп'ютері):
   ```bash
   ssh-keygen -t ed25519 -f ~/.ssh/mrdevops_deploy -N ""
   ssh-copy-id -i ~/.ssh/mrdevops_deploy.pub ubuntu@<публічний IP>
   ssh-keyscan -H <публічний IP>    # вивід піде у VPS_KNOWN_HOSTS
   ```
4. **Секрети в GitHub**: Settings → Environments → `production` (таблиця нижче). `VPS_HOST` = публічний IP, `VPS_USER` = `ubuntu`, `VPS_SSH_KEY` = вміст `~/.ssh/mrdevops_deploy` (приватний).
5. **Деплой:** push у `main` або Actions → Deploy → Run workflow.

Один токен бота може слухати тільки один процес. Коли бот працює на сервері, локальний `make run` упаде з `TelegramConflictError`.

## Деплой

Повний цикл: push у `main` → CI → образ у GHCR → автоматичний деплой на VPS.

- `ci.yml`: на кожен PR і push ruff, mypy, pytest, збірка образу і smoke-тест у ньому. amd64 і arm64 збираються паралельно на нативних раннерах GitHub, тому весь CI займає ~2 хвилини. На push у `main` публікує образ `ghcr.io/<owner>/<repo>:latest` і `:<sha>`.
- `deploy.yml`: після успішного CI по `main` по SSH деплоїть образ саме того коміту (`scripts/deploy.sh`). Чекає, поки контейнер стане healthy, інакше відкочує на попередній образ і падає.
- Ручний деплой або відкат: Actions → Deploy → Run workflow, у полі `sha` вказати коміт з `main` (порожньо = останній).
- Dependabot щотижня пропонує оновлення actions, pip-залежностей і базового образу.

GitHub, environment `production`:

| Що | Тип | Обов'язково |
|---|---|---|
| `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY` | secret | так |
| `VPS_KNOWN_HOSTS` (вивід `ssh-keyscan -H <host>`) | secret | бажано, інакше ключ хоста не перевіряється |
| `BOT_TOKEN`, `GEMINI_API_KEY` | secret | ні: якщо `BOT_TOKEN` задано, `.env` на сервері генерується з секретів |
| `LLM_MODEL`, `LLM_ENABLED`, `QUOTE_MODE`, `COOLDOWN_SECONDS`, `PROTECTED_USERS`, `QUEEN_USERS` | variable | ні, порожні беруться з дефолтів |

На VPS потрібен Docker з compose, користувач `VPS_USER` у групі `docker`. Якщо `BOT_TOKEN` у секретах немає, `.env` треба покласти вручну в `~/mrdevops/.env`. Сервер логіниться в GHCR тимчасовим токеном джоба, тому образ може бути приватним.

## Структура

```
bot/      хендлери, тригери (ключові слова), відповіді Gemini, cooldown, вибір цитат, точка входу
config/   налаштування (pydantic-settings)
quotes/   пул цитат і завантажувач
tests/    unit-тести (LLM мокається)
```

## Зміна тону цитат

Редагуй `quotes/quotes.yaml`. Поля: `id`, `text`, `lang` (`uk` або `surzhyk`), `tags`.
