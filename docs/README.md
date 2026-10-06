# Mail Sort: установка и использование

Mail Sort получает письма по IMAP или EWS, классифицирует их с помощью AI и
перемещает в разрешённые папки. Для повседневного запуска проще всего использовать
Docker Compose: он запускает PostgreSQL, миграции, обработчики писем, админку,
проверку состояния и сбор логов.

## Что понадобится

- Docker Desktop с Docker Compose v2 (Windows/macOS) или Docker Engine с Compose
  plugin (Linux).
- Учётная запись почты с доступом по IMAP либо on-premises EWS/NTLM.
- API key и ID модели для OpenAI или Gemini.

Для разработки без Docker понадобятся Python 3.12+, `uv`, Node.js 22+ и PostgreSQL
16+. Установка `uv` описана в [официальном руководстве](https://docs.astral.sh/uv/getting-started/installation/).

## Настройка

Откройте терминал в корне репозитория. Создайте `.env`, если его ещё нет:

```sh
cp .env.example .env
```

В Windows PowerShell используйте `Copy-Item .env.example .env`. Если `.env` уже
существует, сохраните его и внесите нужные изменения вручную.

Откройте `.env` и задайте как минимум:

- `MAILBOX_PROVIDER` и параметры подключения к почте;
- `AI_PROVIDER`, `AI_MODEL` и `AI_AGENT_API_KEY`;
- `POSTGRES_PASSWORD` для базы данных;
- `MAIL_ADMIN_USERNAME`, `MAIL_ADMIN_PASSWORD` и
  `MAIL_ADMIN_SESSION_SECRET` для входа в админку;
- `GRAFANA_ADMIN_PASSWORD` для Grafana.

Случайный секрет сессии можно получить так:

```sh
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Вставьте результат в `MAIL_ADMIN_SESSION_SECRET`. Замените демонстрационные
пароли из `.env.example` до запуска на сервере. Описание остальных параметров и
примеров находится в [`.env.example`](../.env.example).

## Запуск через Docker

Из корня проекта запустите все сервисы в фоне:

```sh
docker compose --env-file .env -f infra/compose.yaml up --build -d
```

Compose поднимет PostgreSQL, применит миграции и запустит обработчики, админку и
health endpoint. Grafana/Loki можно включить отдельно; их отсутствие не мешает
работе основной системы. При первом запуске Docker соберёт образы,
поэтому команда может занять несколько минут.

Проверьте состояние контейнеров:

```sh
docker compose --env-file .env -f infra/compose.yaml ps
```

Основные адреса на компьютере, где работает Docker:

- Админка: `http://localhost:8082`
- Проверка готовности: `http://localhost:8080/health/ready`
- Grafana (если включён профиль `observability`): `http://localhost:3000`

Войдите в админку с `MAIL_ADMIN_USERNAME` и `MAIL_ADMIN_PASSWORD`. Для Grafana
сначала задайте `GRAFANA_ADMIN_USER` и `GRAFANA_ADMIN_PASSWORD` в `.env`, затем
включите профиль наблюдения:

```sh
docker compose --env-file .env -f infra/compose.yaml --profile observability up --build -d
```

Grafana привязана к loopback интерфейсу сервера; для удалённого доступа используйте
SSH-туннель.

Для просмотра логов:

```sh
docker compose --env-file .env -f infra/compose.yaml logs -f mail-app
```

Остановите сервисы, сохранив данные PostgreSQL:

```sh
docker compose --env-file .env -f infra/compose.yaml down
```

Чтобы также удалить базу и сохранённые данные, используйте `down -v`. Это удалит
volume PostgreSQL вместе с данными писем и аудита.

Больше команд для логов, PRTG и удалённого доступа приведено в
[руководстве по Docker](../infra/README.md).

Отдельная инструкция по установке и запуску админки находится в
[docs/admin](admin/README.md).

## Админка

В Docker админка запускается вместе с остальными сервисами и доступна на
`http://localhost:8082`. Она позволяет искать обработанные письма и события,
просматривать историю классификации, назначения и состояние Decision. На странице
настроек можно приостановить или возобновить Decision.

Docker публикует порт админки только на loopback интерфейс сервера. Для доступа с
другого компьютера создайте SSH-туннель:

```sh
ssh -L 8082:127.0.0.1:8082 <user>@<server>
```

После подключения откройте `http://localhost:8082` локально.

### Локальный запуск админки для разработки

Подготовьте Python окружение из корня репозитория (один раз):

```sh
uv sync
```

В первом терминале запустите API:

```sh
uv run mail-admin-api
```

Во втором терминале из корня установите frontend-зависимости (один раз) и
запустите Vite:

```sh
npm --prefix apps/mail-admin/web install
npm run admin
```

Откройте `http://localhost:5173`. Vite перенаправляет `/api` запросы к API на
`localhost:8082`. Нужны настроенные `.env`, доступная PostgreSQL и уже применённые
миграции. Для просмотра схемы API откройте `http://localhost:8082/docs`.

## Архитектура

```text
почтовый сервер
      │
      ▼
mail-collector ──► PostgreSQL ──► mail-decision ──► AI
                         │               │
                         └────────► mail-router ──► папка назначения
                           ▲
                           │ read-only admin API
                    mail-admin (React SPA)
```

- `mail-collector` обнаруживает сообщения и создаёт задачи классификации.
- `mail-decision` выбирает активное назначение, записывает аудит и публикует
  задачу маршрутизации.
- `mail-router` применяет маршрут через адаптер почты.
- `mail-admin` показывает операционные данные и управляет паузой Decision.

PostgreSQL является источником истины для очереди и аудита. Повторная доставка
задачи безопасна, а письма не удаляются. Подробнее — в
[спецификации обработки](mail-processing.mmd) и [описании первой версии](phase-1-spec.md).
