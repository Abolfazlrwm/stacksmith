# Getting started

This guide takes you from a fresh clone to a running, monitored
docubot stack on your local machine in about 10 minutes. It mirrors the
production path (`docker-compose.prod.yml`) but uses a stub app and
self-signed certs so you do not need a domain.

For the full production deploy to a real VPS, see the
[deploy runbook](runbooks/deploy.md) and the
[architecture overview](architecture.md).

## Prerequisites

| Tool          | Min version | Why                              |
| ------------- | ----------- | -------------------------------- |
| Docker        | 24.0        | compose v2.20+, healthcheck `--wait` |
| `make`        | any         | the `Makefile` wraps common ops  |
| `curl`        | any          | smoke test, canary probe         |
| `git`         | 2.30        | hooks in `.githooks/`            |

No Node, no Go, no Terraform needed for the local stack.

## 1. Clone and configure

```bash
git clone https://github.com/Abolfazlrwm/stacksmith.git
cd stacksmith
cp .env.example .env
```

Open `.env` and fill in the values. For a local run the defaults work;
for production you must set the secrets marked `# required` in the file.

## 2. Install the local git hooks (optional, recommended)

```bash
git config core.hooksPath .githooks
```

This runs commitlint on every commit message and refuses to push
branches with leftover `fixup!` commits. See
[ADR-0032](adr/0032-enforce-conventional-commits.md).

## 3. Check the host

```bash
make doctor
```

`doctor` verifies Docker is new enough, the compose plugin is present,
the `.env` has no empty required vars, and the ports 8080, 5432, 6379
are free. Fix anything it reports before continuing.

## 4. Bring the stack up

```bash
make up
```

This runs `docker compose -f docker-compose.prod.yml up -d --wait`,
which starts nginx, app-blue, postgres, redis, worker, beat, prometheus,
grafana, loki, tempo, and alertmanager, then waits for every
healthcheck to pass.

When the prompt returns, the stack is live:

```bash
curl http://127.0.0.1:8080/health/live/
# {"status":"live"}
```

## 5. Run the smoke test

```bash
make smoke
```

This hits the live and ready endpoints through nginx, then through the
app directly, and checks that the database responds to a trivial
query. If it passes, your local stack is wired correctly.

## 6. Look at the dashboards

| Service     | URL                                   | Login           |
| ----------- | ------------------------------------- | --------------- |
| Grafana     | <http://127.0.0.1:3001>               | admin / admin   |
| Prometheus  | <http://127.0.0.1:9091>               | (none)          |
| Alertmanager | <http://127.0.0.1:9094>              | (none)          |

Grafana ships with five dashboards:

- **Services** — per-container CPU, memory, restart count
- **Business** — request rate, error rate, latency
- **Logs** — Loki log stream with filters
- **Cost** — monthly cost estimate, per-service breakdown
- **Capacity** — 7-day trends, disk exhaustion prediction
- **SLO** — availability %, error budget, latency percentiles

## 7. Deploy a change (blue-green)

Edit the app (or just bump a version label), then:

```bash
bash scripts/deploy.sh
```

`deploy.sh` starts the *inactive* color (green if blue is live), probes
it with canary checks through nginx, switches the upstream, and reloads.
If the canary fails, it rolls back automatically. See the
[deploy runbook](runbooks/deploy.md).

## 8. Back up and restore

```bash
make backup    # takes an encrypted dump to backups/
make restore   # wipes the DB and restores from the latest backup
```

The restore drill is also a CI job — every PR proves the backup can be
restored. See [ADR-0007](adr/0007-off-host-encryption-with-age.md) and
[ADR-0012](adr/0012-backup-integrity-verification.md).

## 9. Stop and clean up

```bash
make down      # stop all containers, keep volumes
make nuke      # stop and delete volumes (loses the database)
```

## Where to go next

- [Architecture overview](architecture.md) — the five Mermaid diagrams
- [ADR index](adr/INDEX.md) — every architectural decision
- [Runbooks](runbooks/) — deploy, backup, failure playbook
- [Known limitations](known-limitations.md) — what does not work yet
- [Contributing](../CONTRIBUTING.md) — how to add a feature

## Troubleshooting

### `make up` hangs on the healthcheck

The app healthcheck waits for postgres and redis. Check:

```bash
docker compose -f docker-compose.prod.yml logs app-blue
docker compose -f docker-compose.prod.yml logs postgres
```

The most common cause is a missing `DJANGO_SECRET_KEY` or a wrong
`DATABASE_URL` in `.env`.

### Grafana shows no data

Prometheus needs a few scrape intervals (15s each) before panels fill.
Wait 1 minute, then refresh. If still empty, check that the
`prometheus` target is up:

```bash
curl http://127.0.0.1:9091/-/healthy
```

### `deploy.sh` says "cosign verification failed"

You are running deploy-time cosign verify (ADR-0025) against a local
image that has no signature. Set `APP_IMAGE=` (empty) in your env, or
remove cosign from your PATH for local deploys. Production pulls a
signed image from GHCR, so this check is real there.
