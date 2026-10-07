# Archived observability stack

Grafana, Loki, Alloy, and their configuration are archived here and are not part
of the main Mail Sort Compose file. The PostgreSQL-backed technical log page and
`docker compose logs` are the current ways to inspect logs.

To run this stack manually, provide `GRAFANA_ADMIN_USER`, `GRAFANA_ADMIN_PASSWORD`,
and optionally `GRAFANA_PORT`, then use:

```sh
docker compose --env-file .env -f infra/old/observability/compose.yaml up -d
```
