# Mail Sort — working agreement

## Tests

- Do not add or modify tests unless the user explicitly requests it. This preference avoids spending the user's token budget on unsolicited test work.

## Structure

- Use screaming architecture: top-level names express a business capability, not a technical pattern. For example, `mail-collector` says what the service does; a name such as `ingest` does not.
- `services/mail-collector`, `services/mail-decision`, and `services/mail-router` are independent deployable services.
- A service must not import code from another service.
- `packages/contracts` is the shared transport/domain contract package. It contains transport and domain contracts only: types, validation schemas, and constants. It contains no database, provider, AI, or framework implementation.
- `packages/database` is the shared persistence package. It contains SQLAlchemy models, session helpers, and the single Alembic migration history. It contains no service use cases.
- `packages/repositories` contains the shared, manually maintained destination tuple and its repository only. Decision and Router retain their own adapters and interfaces; other repositories remain service-local.
- PostgreSQL is the source of truth for jobs and audit data. `LISTEN` / `NOTIFY` wakes workers up but must never be treated as durable delivery.

## Queue rules

- Claim jobs atomically with `FOR UPDATE SKIP LOCKED`.
- Jobs must be idempotent: the same provider message may be delivered more than once.
- Recover stale `processing` jobs after a worker crash.
- Do not delete or permanently modify messages. The processor may only apply a label/folder or create a review task.

## Database migrations

- Use SQLAlchemy 2.x for PostgreSQL persistence and Alembic for every schema change.
- Never call `Base.metadata.create_all()` in a service. Apply migrations once with `alembic upgrade head` before starting service replicas.
- Migration scripts live only in `packages/database/migrations`; services may import models and session helpers, but never own separate migration histories.

## Boundaries

- Mail collector owns discovering messages and enqueuing jobs.
- Decision owns classification, route publication, and classification audit records.
- Router owns mailbox action execution and action retries. It may apply a route through IMAP, EWS, or a future provider adapter.
- Keep provider OAuth tokens encrypted at rest and never log email bodies or secrets.
- Define interfaces as abstract base classes (`ABC` / `@abstractmethod`) and have implementations inherit them; do not use `typing.Protocol`.

## Collector patterns

- `MailboxCollector` is the provider Strategy; IMAP is the initial adapter implementing it.
- `MailboxCollectorRegistry` resolves the strategy by account provider. Do not use `if provider` branches inside synchronization logic.
- `MailboxSynchronizationService` coordinates adapters, job publishing, and cursors. It must advance a cursor only after every discovered message has a durable, idempotent job.

## AI boundary

- The processor's classification use case depends on its own `StructuredAgent` port, never on LangChain or a vendor SDK.
- `AiAgent` selects the configured model and only communicates with it. LangChain and provider SDK imports live only in `mail_decision.infrastructure.ai_agent`.
- Adding another provider means adding one model-creation branch in `AiAgent`; it must not change classification, queue, or mailbox-action code.
