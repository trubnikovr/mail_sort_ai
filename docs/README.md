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
                           ▲
                           │ read-only admin API
                    mail-admin (React SPA)
```

## Границы сервисов

- `mail-collector` обнаруживает письма, сохраняет plain-text snapshot и
  публикует `classify_email`.
- `mail-decision` классифицирует письмо только среди активных `destinations`,
  записывает аудит и публикует `route_email`.
- `mail-router` выполняет действие через выбранный почтовый адаптер.

Приложения не импортируют друг друга. Общие transport/domain-контракты находятся в
`packages/contracts`, модели и единая история Alembic — в `packages/database`.
Начальные назначения находятся в `tools/mail-destination-setup`, а их рабочая
конфигурация хранится в PostgreSQL. Decision и Router читают назначения из БД
через собственные сервисные адаптеры.

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
