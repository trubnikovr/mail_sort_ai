# Архитектура Mail Sort

```text
mail provider
      │
      ▼
mail-collector ──► PostgreSQL ──► mail-decision ──► AI
                         │               │
                         │          route_email
                         │               │
                         └────────► mail-router ──► destination folder
```

## Границы сервисов

- `mail-collector` обнаруживает письма, сохраняет plain-text snapshot и
  публикует `classify_email`.
- `mail-decision` классифицирует письмо только среди активных `destinations`,
  записывает аудит и публикует `route_email`.
- `mail-router` выполняет действие через выбранный почтовый адаптер.

Сервисы не импортируют друг друга. Общие transport/domain-контракты находятся в
`packages/contracts`, модели и единая история Alembic — в `packages/database`.
Общий ручной каталог назначений (`tuple`) и репозиторий находятся в
`packages/repositories`; Decision и Router не читают назначения из БД. Decision и Router
сохраняют свои классы-адаптеры; остальные репозитории остаются внутри сервисов.

## Гарантии

- PostgreSQL — источник истины для задач; `LISTEN / NOTIFY` не заменяет очередь.
- Задачи забираются через `FOR UPDATE SKIP LOCKED` и допускают повторную доставку.
- Зависшие `processing` задачи возвращаются в очередь.
- Collector каждый цикл ищет только непрочитанные письма в настроенной папке;
  курсор не нужен, повторную постановку задачи предотвращает уникальный ключ.
- Сообщения не удаляются: допустимы только перенос/метка или review task.
- Модель видит только разрешённые направления, а не все папки почтового ящика.

Подробная последовательность: [mail-processing.mmd](mail-processing.mmd).
Команды установки и запуска: [корневой README](../README.md).
