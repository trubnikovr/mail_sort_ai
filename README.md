# Mail Sort

AI-assisted сортировка почты. Обработка разделена на три сервиса:

- `mail-collector` получает письма и создаёт задачи классификации;
- `mail-decision` выбирает разрешённую папку с помощью AI;
- `mail-router` применяет выбранный маршрут через IMAP или EWS.

Для текущего одиночного сервера Docker Compose запускает эти три процесса в одном
контейнере `mail-app`. Supervisor перезапускает упавший процесс и публикует
состояние процессов для health-проверки.

Архитектура, установка, запуск через Docker и использование админки описаны в
[руководстве](docs/README.md). Для подробностей по Docker, логам и PRTG см.
[infra/README.md](infra/README.md).

Пошаговая установка и запуск админки отдельно: [docs/admin](docs/admin/README.md).

## Требования

- Python 3.12+;
- Node.js 22+ для локальной сборки админки;
- PostgreSQL 16+;
- доступ к почте по IMAP или on-premises EWS/NTLM.

## Установка

Установите `uv` один раз ([инструкция](https://docs.astral.sh/uv/getting-started/installation/)),
затем из корня репозитория выполните одну команду:

```bash
uv sync
```

Корневой `pyproject.toml` объявляет все workspace-пакеты, приложения и tools;
`uv sync` ставит их в `.venv` и связывает локальные пакеты редактируемо. Запускайте
команды через `uv run`, например:

```bash
uv run python -m mail_collector.main
```

Или активируйте окружение:

```bash
source .venv/bin/activate
```

Создайте `.env` из шаблона, только если его ещё нет; существующий `.env` не
перезаписывайте. Заполните настройки и выберите `MAILBOX_PROVIDER=imap` или
`MAILBOX_PROVIDER=ews`; полный список параметров и примеры находятся в
[`.env.example`](.env.example).

## Admin web

Админка — SPA на React и TypeScript: Vite собирает клиент, TanStack Router
управляет страницами, TanStack Query — запросами к API, TanStack Table — списками.
FastAPI предоставляет JSON API и OpenAPI (`/docs`); production-контейнер отдаёт
собранную статику и API с одного адреса. Первая версия позволяет смотреть
сводку, искать письма, открывать тело и историю обработки, искать сохранённые в
PostgreSQL события аудита/классификации, а также просматривать настройки папок;
данные писем и назначения доступны только для просмотра. Технические логи сервисов
сохраняются в PostgreSQL и доступны на отдельной странице админки; stdout можно
посмотреть через `docker compose logs`. На странице настроек можно приостановить и возобновить
Decision; флаг `mail_decision.enabled` хранится в таблице `app_settings`.
При распознанной ошибке оплаты AI Decision сам включит паузу, сохранит критический
алерт для PRTG и вернёт текущее письмо в очередь без расхода попытки.

Локальная разработка из корня репозитория, в двух терминалах:

```bash
uv run dashboard-api
```

```bash
npm --prefix apps/dashboard/web install
npm run dashboard
```

Откройте `http://localhost:5173`. Vite проксирует `/api` к FastAPI на `8082`.
Для локального запуска используйте уже применённые миграции и доступную базу.
Перед запуском задайте в `.env` `MAIL_ADMIN_USERNAME`, `MAIL_ADMIN_PASSWORD` и
`MAIL_ADMIN_SESSION_SECRET` длиной от 32 символов. Секрет сессии
сгенерируйте командой `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
Для Docker выполните `docker compose --env-file .env -f infra/compose.yaml up --build dashboard`;
страница будет доступна на `http://localhost:8082`. Порт привязан к loopback
интерфейсу сервера; для удалённого доступа используйте SSH-туннель. Если админка
работает за HTTPS reverse proxy, установите `MAIL_ADMIN_COOKIE_SECURE=true`.

## AI configuration

Decision uses `init_chat_model` with structured output. Set `AI_PROVIDER=openai`
(or `gemini`), `AI_MODEL` to the exact model ID, and `AI_AGENT_API_KEY` to that
provider's key. The model ID and key are required; provider defaults to OpenAI.
Both provider integrations are installed with the service.

Чтобы прогнать сохранённое письмо через те же правила и классификатор, установите
зависимости сервиса и передайте job UUID, email record UUID или provider message ID:

```bash
pip install -e apps/mail-decision
python ask_model.py EMAIL_ID
```

Скрипт использует настройки из `.env`, показывает решение и объяснение, но не
сохраняет результат, не создаёт route job и не расходует дневную квоту AI.

## Destinations

PostgreSQL `destinations` is the source of truth for folder paths, active state,
and the text instruction used by classification. The separate `sorting_rules`
table has been removed; destination-specific classification guidance is stored
in `destinations.instruction`. Destinations are managed in the dashboard.
`mail-destination-setup add` remains available to create an EWS folder and its
destination record together.

## Admin tools

Установите tools из корня репозитория командами из раздела «Установка». Доступны
следующие CLI-команды:

### `mail-destination-setup`

```text
mail-destination-setup add --id ID --name NAME --mailbox PATH [--description TEXT]
```

- `add` создаёт папку EWS и добавляет или обновляет назначение в БД. `--id`,
  `--name` и `--mailbox` обязательны; `--description` задаёт описание и
  инструкцию классификации.

Для работы нужны переменные подключения из `.env`: `DATABASE_URL`,
`MAILBOX_ACCOUNT_ID`, `EWS_ENDPOINT`, `EWS_USERNAME` и `EWS_PASSWORD`.

### `mail-database-reset`

```text
mail-database-reset
```

Команда загружает `DATABASE_URL` из окружения или корневого `.env`, показывает
целевую базу и очищаемые таблицы, затем требует ввести имя базы для подтверждения.
При совпадении удаляются данные приложения из таблиц `ai_requests`,
`job_events`, `audit_logs`, `jobs`, `email_records`,
`ai_daily_usage` и `destinations`. Схема, `alembic_version` и
содержимое почтового ящика сохраняются. Если подтверждение не совпадает, команда
завершается без изменений.

### `mail-job-inspect`

```bash
mail-job-inspect JOB_UUID
```

Печатает статус, попытки, ошибку и краткую историю аудита, обработки и AI
запросов для job и связанной job маршрутизации. Тела писем и заголовки не выводит.

## EWS destinations

To create a destination folder in EWS and register it in PostgreSQL, configure
`DATABASE_URL`, `MAILBOX_ACCOUNT_ID`, `EWS_ENDPOINT`, `EWS_USERNAME`, and
`EWS_PASSWORD` in `.env`, then run:

```bash
mail-destination-setup add \
  --id sales \
  --name "Продажи" \
  --mailbox "Mail Sort/Sales" \
  --description "Запросы и переписка по продажам"
```

The command creates missing folders in the path and upserts the destination
record. It is a standalone admin tool and is not part of `mail-router`.

## База данных

Инструкция по запуску и обслуживанию Docker Compose находится в
[infra/README.md](infra/README.md).

### Локальная база данных

Создайте базу, примените миграции и проверьте текущую ревизию:

```bash
createdb mail_sort
python -m alembic -c packages/database/alembic.ini upgrade head
python -m alembic -c packages/database/alembic.ini current
```

Для повторного прогона можно очистить данные Mail Sort, сохранив схему БД:

```bash
mail-database-reset
```

Остановите сервисы перед запуском. CLI показывает целевую базу и просит ввести
её имя для подтверждения. Он очищает jobs, снимки писем, аудит, диагностику,
счётчик AI-запросов и legacy-назначения/правила. Таблицу миграций,
схему и сами письма в почтовом ящике он не меняет.

Создавайте и редактируйте назначения в dashboard. Если нужно добавить папку EWS
вместе с записью назначения, используйте `mail-destination-setup add`, описанную
выше. Decision и Router читают назначения из PostgreSQL; инструкция для AI
хранится в поле `instruction`.

Перед AI Decision применяет детерминированные subject-фильтры. Сейчас тема,
начинающаяся с `Daily Spam Report for` без учёта регистра, сразу направляется в
`INBOX/Мусор`. Назначение `trash` доступно Router, но исключено из списка папок,
который передаётся AI. Фильтры находятся в
`apps/mail-decision/src/mail_decision/processing/steps/rules/detect_configured_filters.py`.

Если письмо не подходит или уверенность низкая, оно получает статус review
и направляется в `INBOX/Ручная проверка`. Ранее обработанные письма автоматически
не пересортировываются.

## Запуск

Collector при каждом цикле ищет непрочитанные письма только в настроенной папке
`MAILBOX_SOURCE` (по умолчанию `INBOX`). Курсор не используется: PostgreSQL
дедуплицирует задачи по account и provider message ID, поэтому повторный поиск
не создаёт повторную обработку. Письма остаются непрочитанными до применения
маршрута; collector не помечает их прочитанными.

Сначала безопасно проверьте один цикл каждого сервиса:

```bash
python -m mail_collector.main --once
python -m mail_decision.main --once
python -m mail_router.main --once
```

Для постоянной работы запустите те же модули без `--once` в отдельных
процессах.

Логи сервисов выводятся в stdout в JSON и сохраняются в PostgreSQL. Поле `service`
внутри JSON указывает на конкретный процесс Collector, Decision или Router.

## Тесты

```bash
python -m unittest discover -s apps/mail-collector/tests -v
PYTHONPATH=apps/mail-decision/src python -m unittest discover -s apps/mail-decision/tests -v
PYTHONPATH=apps/mail-router/src python -m unittest discover -s apps/mail-router/tests -v
```
