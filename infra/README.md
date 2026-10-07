# Mail Sort: Docker Compose

Compose запускает PostgreSQL, `mail-app` с процессами Collector, Decision и
Router, `mail-admin`, `mail-health` и `mail-alerts` для критических событий PRTG.
Supervisor перезапускает упавший процесс внутри `mail-app` и отдаёт его состояние
для health-проверки. После готовности PostgreSQL `mail-admin` применяет миграции;
остальные backend-сервисы ждут его healthcheck.

## Подготовка

Из корня проекта создайте `.env` из шаблона и заполните настройки почты, AI и
админки. Для `MAIL_ADMIN_SESSION_SECRET` задайте случайное значение длиной не
менее 32 символов; его можно сгенерировать `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
Если `.env` уже настроен, не перезаписывайте его: добавьте новые переменные
`MAIL_ADMIN_*` из `.env.example`. Для временного входа в админку заданы
`admin` / `admin`; перед внешним доступом смените пароль. `MAIL_ADMIN_SESSION_SECRET`
обязательно сгенерируйте случайно.

В PowerShell:

```powershell
Copy-Item .env.example .env
```

В macOS/Linux:

```sh
cp .env.example .env
```

## Запуск

Команды ниже одинаковы в PowerShell, macOS и Linux. Выполняйте их из корня
репозитория:

```text
docker compose --env-file .env -f infra/compose.yaml up --build --remove-orphans -d
docker compose --env-file .env -f infra/compose.yaml ps
docker compose --env-file .env -f infra/compose.yaml logs -f mail-app
```

На Windows нужен Docker Desktop с Compose v2; отдельный Windows compose-файл не
нужен. Пути к `.env` и контексту сборки заданы относительно `infra/compose.yaml`,
поэтому Compose запускается из корня репозитория.

Остановка без удаления данных базы:

```text
docker compose --env-file .env -f infra/compose.yaml down
```

Удаление контейнеров и volume PostgreSQL:

```text
docker compose --env-file .env -f infra/compose.yaml down -v
```

## Логи и журнал обработки

В админке на странице **Журнал** ищите события аудита, этапы классификации и
AI-запросы по теме письма, provider message ID или ID задачи (`audit_logs`,
`job_events`, `ai_requests`). Технические логи приложений открываются отдельно,
на странице **Логи**; они хранятся в таблице `system_logs` 30 дней по умолчанию.
Срок хранения можно изменить через `SYSTEM_LOG_RETENTION_DAYS`.

Контейнеры также пишут технические JSON-логи в stdout. Их можно смотреть в
терминале:

```text
docker compose --env-file .env -f infra/compose.yaml logs -f mail-app mail-alerts mail-health mail-admin
```

`docker compose logs` читает stdout контейнеров напрямую. Старая конфигурация
Grafana/Loki/Alloy перемещена в `infra/old/observability` и не участвует в основном
Compose.

## Синхронизация папок

Отдельного Compose-сервиса для настройки destinations нет. После запуска
`mail-app` синхронизируйте каталог и создайте отсутствующие папки в почтовом ящике:

```text
docker compose --env-file .env -f infra/compose.yaml exec mail-app mail-destination-setup sync
```

## Admin web

`mail-admin` объединяет FastAPI JSON API и собранный Vite frontend в одном
контейнере. Frontend использует React, TanStack Router, Query и Table. Страница
**Журнал** показывает события обработки, а **Логи** — технические логи сервисов
из PostgreSQL с поиском по сообщению, сервису и logger. Веб-панель доступна на
`http://127.0.0.1:${MAIL_ADMIN_PORT:-8082}`;
привязка к loopback
оставляет её закрытой для прямого внешнего доступа. Для удалённой работы используйте
SSH port forwarding, например `ssh -L 8082:127.0.0.1:8082 <server>`.

На странице **Настройки** можно приостановить и возобновить Decision. Состояние
хранится в `app_settings` под ключом `mail_decision.enabled`; миграция создаёт его
со значением `true`. При паузе Decision завершает текущую задачу и прекращает
брать новые примерно в течение одного интервала опроса очереди. Collector и
Router продолжают работать.

Если AI API возвращает распознанную ошибку оплаты/исчерпанного баланса, Decision
в одной транзакции выключает этот параметр, возвращает текущую задачу в очередь
без расхода попытки и добавляет критический alert в PostgreSQL outbox. `mail-alerts`
доставляет его в PRTG. После пополнения баланса нажмите **Возобновить Decision**;
задачи снова начнут обрабатываться. Обычные временные rate limit сами по себе не
ставят Decision на паузу.

Для входа нужны `MAIL_ADMIN_USERNAME` и `MAIL_ADMIN_PASSWORD`; сессия подписана
`MAIL_ADMIN_SESSION_SECRET`, действует заданное время и использует HttpOnly,
SameSite=Lax cookie. После пяти неудачных попыток с одного адреса вход блокируется
на 15 минут. При TLS reverse proxy включите `MAIL_ADMIN_COOKIE_SECURE=true`.

Для локальной frontend-разработки из корня репозитория установите backend-
зависимости командой `uv sync`, запустите API командой `uv run mail-admin-api`,
затем во втором терминале выполните `npm --prefix apps/mail-admin/web install`
(один раз) и `npm run admin`. Vite доступен на `http://localhost:5173` и
проксирует API-запросы на локальный порт 8082. OpenAPI UI FastAPI доступен по
`http://localhost:8082/docs`. Требуются доступная PostgreSQL и применённые
миграции. Полная инструкция находится в [docs/README.md](../docs/README.md).

## Health checks и PRTG

`mail-health` публикует `GET /health/live` и `GET /health/ready` на порту
`${HEALTH_PORT:-8080}`. Первый проверяет процесс health-сервиса. Второй проверяет
PostgreSQL и доступность настроенного AI API/model ID. Сейчас поддерживаются
OpenAI и Gemini; проверка AI подтверждает API-доступ и наличие модели, но не
делает платный inference-запрос. Если настроены `AWS_REGION` и AWS credentials,
health также проверяет AWS credentials и доступность STS; без `AWS_REGION` AWS
показывается как `not_configured` и не ухудшает readiness. Ограничьте доступ к
порту health-сервиса сетевым правилом до PRTG.

Сам `mail-app` проверяет три процесса по PID через внутренний
`GET /health/services` на порту 8081. `mail-health` опрашивает этот endpoint и
включает статусы каждого процесса в ответ `/health/ready`. Падение процесса
вызывает его перезапуск supervisor-ом с увеличивающейся задержкой; пока процесс
не восстановлен, endpoint readiness возвращает HTTP 503. Если завершится сам
контейнер, `restart: unless-stopped` перезапустит его.

В PRTG добавьте HTTP sensor, опрашивающий
`http://<mail-sort-host>:8080/health/ready` (или настроенный `HEALTH_PORT`), и
настройте уведомление на HTTP 503.

Для доставки событий из приложения создайте PRTG **HTTP Push Data Advanced**
sensor, выберите POST и задайте URL сенсора в `PRTG_PUSH_URL` в `.env`, например
`http://<prtg-probe>:5050/<sensor-token>`. Откройте PRTG probe port для Mail Sort.
Настройте у сенсора limit/notification trigger для канала **Critical alerts**
при значении больше нуля. `mail-alerts` читает outbox из PostgreSQL и повторяет
отправку при сбоях; окончательное исчерпание попыток классификации или маршрута
создаёт critical alert в той же транзакции, что и статус `failed`. Сенсор
показывает последнее событие; канал уведомления (email, push и т. п.) задаётся
в самом PRTG.
