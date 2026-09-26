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
pip install -e services/mail-collector
pip install -e services/mail-decision
pip install -e services/mail-router
pip install -e tools/mail-destination-setup
cp .env.example .env
```

Заполните `.env`. Выберите `MAILBOX_PROVIDER=imap` или
`MAILBOX_PROVIDER=ews`; полный список параметров и примеры находятся в
[`.env.example`](.env.example).

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

Перед запуском `mail-decision` добавьте разрешённые папки для аккаунта:

```sql
INSERT INTO destinations (id, account_id, name, description, mailbox, is_active)
VALUES (
  'sales-domestic',
  'personal-gmail',
  'Продажи — внутренний туризм',
  'Запросы на туры внутри страны и переписка с туристами',
  'Продажи/Внутренний туризм',
  true
);
```

`account_id` должен совпадать с `MAILBOX_ACCOUNT_ID`, а папка из `mailbox`
должна заранее существовать у почтового провайдера.

Для писем с низкой уверенностью Decision использует destination
`needs-review` и отправляет маршрут в `Mail Sort/Needs Review`. Этот активный
destination обязателен для запуска Decision; CLI `mail-destination-setup add`
может создать его вместе с папкой.

## Запуск

Сначала безопасно проверьте один цикл каждого сервиса:

```bash
python -m mail_collector.main --once
python -m mail_decision.main --once
python -m mail_router.main --once
```

Для постоянной работы запустите те же модули без `--once` в отдельных
процессах.

## Тесты

```bash
python -m unittest discover -s services/mail-collector/tests -v
PYTHONPATH=services/mail-decision/src python -m unittest discover -s services/mail-decision/tests -v
PYTHONPATH=services/mail-router/src python -m unittest discover -s services/mail-router/tests -v
```
