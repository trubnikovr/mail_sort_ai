# Админка Mail Sort

Админка состоит из двух частей: FastAPI предоставляет API, а React/Vite — веб-
интерфейс. В рабочем Docker запуске API и собранный интерфейс работают в одном
контейнере. Для локальной разработки API и frontend запускаются отдельно.

## Требования

Для Docker способа нужны Docker Engine/Desktop и Compose v2. Для локальной
разработки дополнительно нужны Python 3.12+, `uv`, Node.js 22+ и npm. Локальному
API требуется PostgreSQL с применёнными миграциями.

## Настройка доступа

Из корня репозитория создайте `.env`, если его ещё нет:

```sh
cp .env.example .env
```

Не перезаписывайте существующий `.env`. Установите значения:

```dotenv
MAIL_ADMIN_USERNAME=admin
MAIL_ADMIN_PASSWORD=ваш-длинный-пароль
MAIL_ADMIN_SESSION_SECRET=случайный-секрет-не-короче-32-символов
MAIL_ADMIN_PORT=8082
```

Секрет сессии можно сгенерировать командой:

```sh
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Для постоянного сервера замените демонстрационные логин и пароль. Если админка
работает за HTTPS reverse proxy, задайте `MAIL_ADMIN_COOKIE_SECURE=true`.

## Запуск через Docker

Админка использует общую PostgreSQL и миграции проекта. Запустите только нужные
контейнеры из корня репозитория:

```sh
docker compose --env-file .env -f infra/compose.yaml up --build -d postgres dashboard
```

При старте `dashboard` сам проверит и применит ожидающие миграции до запуска API.
Отдельный контейнер `migrate` не создаётся.

После запуска откройте `http://localhost:8082` и войдите с данными из `.env`.
Проверить состояние контейнера можно командой:

```sh
docker compose --env-file .env -f infra/compose.yaml ps
```

Посмотреть логи админки:

```sh
docker compose --env-file .env -f infra/compose.yaml logs -f dashboard
```

Остановить эти контейнеры, сохранив данные базы:

```sh
docker compose --env-file .env -f infra/compose.yaml stop dashboard postgres
```

Compose привязывает порт админки к loopback сервера. Для доступа к серверу
удалённо откройте SSH-туннель на своём компьютере:

```sh
ssh -L 8082:127.0.0.1:8082 <user>@<server>
```

Затем посетите `http://localhost:8082` на своём компьютере.

Чтобы запустить всю систему, включая обработчики почты и health checks,
выполните обычный полный запуск из [руководства по Docker](../../infra/README.md).

## Локальная установка и запуск для разработки

### 1. Установите backend-зависимости

В корне репозитория:

```sh
uv sync
```

Если `uv` ещё не установлен, установите его по
[официальному руководству](https://docs.astral.sh/uv/getting-started/installation/).

### 2. Подготовьте базу и переменные окружения

Задайте в `.env` `DATABASE_URL` и параметры входа, описанные выше. PostgreSQL
должна быть запущена, а миграции применены. Например, если база запускается через
Compose, выполните:

```sh
docker compose --env-file .env -f infra/compose.yaml up -d postgres
uv run python -m alembic -c packages/database/alembic.ini upgrade head
```

Эта команда подготовит базу, не запуская контейнер API админки.

### 3. Установите frontend-зависимости

Из корня репозитория выполните один раз:

```sh
npm --prefix apps/dashboard/web install
```

### 4. Запустите API и frontend

Оставьте API работающим в первом терминале:

```sh
uv run dashboard-api
```

Из корня репозитория запустите frontend во втором терминале:

```sh
npm run dashboard
```

Перейдите на `http://localhost:5173`. Vite перенаправляет `/api` запросы к API на
`http://localhost:8082`. API документация доступна на `http://localhost:8082/docs`.

Остановка — `Ctrl+C` в каждом терминале. Если команда `uv` не найдена, установите
`uv` и повторите `uv sync`.

## Что доступно в админке

- Сводка и поиск по письмам.
- Просмотр тела письма, статуса обработки и истории задач.
- Журнал событий аудита, классификации и AI-запросов.
- Отдельная страница технических логов сервисов из PostgreSQL. Срок хранения —
  30 дней по умолчанию.
- Просмотр настроек назначений.
- Пауза и возобновление `mail-decision` на странице настроек.

Админка не изменяет письма и назначения. Для назначения папок используйте
инструмент `mail-destination-setup`; детали потоков обработки описаны в
[документации проекта](../README.md).
