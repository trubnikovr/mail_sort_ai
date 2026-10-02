# Mail Sort

AI-assisted сортировка почты. Система состоит из трёх независимых сервисов:

- `mail-collector` получает письма и создаёт задачи классификации;
- `mail-decision` выбирает разрешённую папку с помощью AI;
- `mail-router` применяет выбранный маршрут через IMAP или EWS.

Архитектура и гарантии доставки описаны в [docs](docs/README.md).

## Требования

- Python 3.12+;
- PostgreSQL 16+;
- доступ к почте по IMAP или on-premises EWS/NTLM.

## Установка

Из корня репозитория:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e packages/contracts
pip install -e packages/database
pip install -e packages/repositories
pip install -e tools/mail-destination-setup
pip install -e tools/mail-database-reset
pip install -e tools/mail-job-inspect
pip install -e services/mail-collector
pip install -e services/mail-decision
pip install -e services/mail-router
cp .env.example .env
```

Заполните `.env`. Выберите `MAILBOX_PROVIDER=imap` или
`MAILBOX_PROVIDER=ews`; полный список параметров и примеры находятся в
[`.env.example`](.env.example).

## AI configuration

Decision uses `init_chat_model` with structured output. Set `AI_PROVIDER=openai`
(or `gemini`), `AI_MODEL` to the exact model ID, and `AI_AGENT_API_KEY` to that
provider's key. The model ID and key are required; provider defaults to OpenAI.
Both provider integrations are installed with the service.

Чтобы прогнать сохранённое письмо через те же правила и классификатор, установите
зависимости сервиса и передайте job UUID, email record UUID или provider message ID:

```bash
pip install -e services/mail-decision
python ask_model.py EMAIL_ID
```

Скрипт использует настройки из `.env`, показывает решение и объяснение, но не
сохраняет результат, не создаёт route job и не расходует дневную квоту AI.

## Legacy destination registration

The command `mail-destination-setup add` creates an EWS folder and stores a row
in the legacy `destinations` database table. Decision and Router now use the
manual `DESTINATIONS` tuple, so this command does not add an active Mail Sort
destination. Use `mail-destination-setup sync` below for the current catalog.

## Admin tools

Установите tools из корня репозитория командами из раздела «Установка». Доступны
следующие CLI-команды:

### `mail-destination-setup`

```text
mail-destination-setup sync [--account ACCOUNT_ID]
mail-destination-setup add --id ID --name NAME --mailbox PATH [--description TEXT]
```

- `sync` создаёт отсутствующие папки для включённых назначений из каталога
  `DESTINATIONS`. `--account` переопределяет `MAILBOX_ACCOUNT_ID` только для
  выбора назначений; без флага используется значение из `.env`.
- `add` создаёт папку EWS (включая отсутствующие родительские папки) и добавляет
  или обновляет legacy-запись в таблице `destinations`. `--id`, `--name` и
  `--mailbox` обязательны; `--description` необязателен и по умолчанию пустой.
  Запись не становится активным назначением для Decision и Router.

Для работы нужны переменные подключения из `.env`: `DATABASE_URL`,
`MAILBOX_ACCOUNT_ID`, `MAILBOX_PROVIDER` и соответствующие учётные данные
провайдера. `add` предназначен для EWS; `sync` поддерживает настроенные IMAP и
EWS подключения.

### `mail-database-reset`

```text
mail-database-reset
```

Команда загружает `DATABASE_URL` из окружения или корневого `.env`, показывает
целевую базу и очищаемые таблицы, затем требует ввести имя базы для подтверждения.
При совпадении удаляются данные приложения из таблиц `ai_requests`,
`job_events`, `audit_logs`, `jobs`, `email_records`,
`ai_daily_usage`, `sorting_rules` и `destinations`. Схема, `alembic_version` и
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

Чтобы создать включённые папки каталога в подключённом ящике, настройте
`MAILBOX_PROVIDER`, `MAILBOX_ACCOUNT_ID` и учётные данные соответствующего
провайдера в `.env`, затем выполните:

```bash
mail-destination-setup sync
```

Команда создаёт отсутствующие папки, включая промежуточные каталоги, и оставляет
уже существующие. Она не изменяет БД и не переносит письма. `MAILBOX_PROVIDER=imap`
использует IMAP; `ews` — EWS.

Назначения пока задаются вручную в `DESTINATIONS`:
`packages/repositories/src/mail_sort_repositories/destinations.py`.
Это tuple записей с ID, названием, инструкцией для AI, путём папки относительно `INBOX` и enabled.
Сейчас включены «Ручная проверка», «Нет на рабочем месте», «Поставщики»,
«Запросы на туры», «Не обслуживаем», «Реклама», «Недоставка» и «Мусор».
Папки создаются на одном уровне внутри Inbox.
Decision и Router используют один каталог для `MAILBOX_ACCOUNT_ID`. Таблица
`destinations` больше не является источником назначений этих сервисов.

Перед AI Decision применяет детерминированные subject-фильтры. Сейчас тема,
начинающаяся с `Daily Spam Report for` без учёта регистра, сразу направляется в
`INBOX/Мусор`. Назначение `trash` доступно Router, но исключено из списка папок,
который передаётся AI. Фильтры находятся в
`services/mail-decision/src/mail_decision/processing/steps/rules/detect_configured_filters.py`.

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

Логи сервисов выводятся в консоль и записываются в `logs/<service>/mail-sort.log`.
Файл ротируется каждую полночь; хранятся текущий и 14 предыдущих дневных файлов.

## Тесты

```bash
python -m unittest discover -s services/mail-collector/tests -v
PYTHONPATH=services/mail-decision/src python -m unittest discover -s services/mail-decision/tests -v
PYTHONPATH=services/mail-router/src python -m unittest discover -s services/mail-router/tests -v
```
