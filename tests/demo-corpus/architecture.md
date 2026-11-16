# Architecture — one VPS, eleven containers

The whole production stack runs as a single docker-compose project on one
VPS. The eleven containers are:

1. app-blue — Django + gunicorn, serves the API and the chat UI
2. app-green — the inactive half of the blue-green pair (started on deploy)
3. worker — Celery worker, runs document ingestion async
4. beat — Celery beat, schedules the backup-freshness metric and other
   periodic tasks
5. postgres — pgvector/pg17, the database and the vector store
6. redis — broker for Celery and the Django cache
7. nginx — terminates TLS, routes to the active app color, serves static
8. prometheus — scrapes metrics from app, postgres, nginx, and itself
9. loki + promtail — log aggregation
10. tempo — distributed tracing, receives OTLP from the app
11. alertmanager + grafana — alerting and dashboards

Backups are taken by `scripts/backup.sh`, which runs `pg_dump`, encrypts
the dump with age, and copies it off-host. The restore drill destroys the
Postgres volume, restores from the encrypted backup, and verifies both
data values and application health. This runs in CI on every push.
