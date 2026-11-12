# System architecture

This document describes the architecture of the stacksmith deployment kit,
the services it manages, and the data paths between them.

## High-level topology

```mermaid
flowchart TB
    client["Client / Browser"] --> nginx["nginx<br/>:80 / :443<br/>TLS · gzip · security headers"]
    nginx -->|"proxy"| app-blue["app-blue · gunicorn<br/>Django 5.2 · :8000"]
    nginx -.->|"standby"| app-green["app-green · gunicorn<br/>(blue-green)"]

    app-blue --> pg[("Postgres 17<br/>pgvector<br/>named volume")]
    app-blue --> redis[("Redis 7<br/>broker + cache")]
    app-blue --> worker["celery worker<br/>background tasks"]
    app-blue --> beat["celery beat<br/>scheduler"]

    worker --> pg
    worker --> redis
    beat --> redis

    subgraph deploy["Deployment layer"]
        deploy_sh["deploy.sh<br/>blue-green + canary"]
        rollback_sh["rollback.sh<br/>one-command revert"]
        upstream["nginx/upstreams.conf<br/>active color"]
        deploy_sh --> upstream
        rollback_sh --> upstream
    end

    subgraph backup["Backup layer"]
        backup_sh["backup-db.sh<br/>pg_dump + gzip + sha256"]
        encrypt_sh["encrypt-backups.sh<br/>age encryption"]
        sync_sh["sync-backups.sh<br/>rsync off-host"]
        restore_sh["restore-db.sh<br/>decrypt + verify + load"]
        backup_sh --> encrypt_sh --> sync_sh
        restore_sh -.->|"restore path"| pg
    end

    subgraph obs["Observability layer"]
        prom["Prometheus<br/>:9090"]
        graf["Grafana<br/>/grafana/"]
        loki["Loki<br/>:3100"]
        tempo["Tempo<br/>:4318"]
        am["Alertmanager<br/>:9093"]
        node_exp["node-exporter"]
        cadvisor["cAdvisor"]
        blackbox["blackbox"]
        promtail["promtail"]

        prom --> node_exp
        prom --> cadvisor
        prom --> blackbox
        prom --> app-blue
        prom --> am
        am -->|"Slack"| slack["Slack #ops"]
        promtail --> loki
        graf --> prom
        graf --> loki
        graf --> tempo
        app-blue -->|"OTel"| tempo
        blackbox --> nginx
    end

    subgraph supply["Supply chain"]
        ghcr["GHCR<br/>multi-arch image"]
        cosign["cosign sign<br/>+ verify"]
        sbom["syft SBOM<br/>+ grype scan"]
        codeql["CodeQL"]
        trivy["Trivy"]
        ghcr --> cosign --> sbom
        codeql -.-> app-blue
        trivy -.-> ghcr
    end

    subgraph sec["Security"]
        certbot["certbot<br/>TLS renewal loop"]
        rotate["rotate-secrets.sh<br/>zero-downtime key rotation"]
        certbot --> nginx
        rotate --> app-blue
    end
```

## Service inventory

| Service | Image | Port | Healthcheck | Purpose |
|---|---|---|---|---|
| app-blue | stacksmith/app:latest | 8000 | curl /health/live/ | Primary Django app (gunicorn) |
| app-green | stacksmith/app:latest | 8000 | curl /health/live/ | Standby for blue-green deploy |
| worker | stacksmith/app:latest | — | — | Celery worker (background tasks) |
| beat | stacksmith/app:latest | — | — | Celery beat scheduler |
| postgres | pgvector/pgvector:pg17 | 5432 | pg_isready | Database + pgvector |
| redis | redis:7-alpine | 6379 | redis-cli ping | Broker + cache |
| nginx | nginx:1.27-alpine | 80, 443 | wget /health/live/ | Reverse proxy, TLS, gzip |

## Observability inventory

| Service | Image | Port | Purpose |
|---|---|---|---|
| prometheus | prom/prometheus | 9090 | Metrics scraper + alert evaluation |
| grafana | grafana/grafana | 3000 (via nginx /grafana/) | Dashboards (5 provisioned) |
| loki | grafana/loki | 3100 | Log storage (14-day retention) |
| promtail | grafana/promtail | — | Docker log scraper → Loki |
| tempo | grafana/tempo | 4318 (OTLP) | Trace storage (7-day retention) |
| alertmanager | prom/alertmanager | 9093 | Alert routing (Slack) |
| node-exporter | prom/node-exporter | 9100 | Host metrics |
| cAdvisor | gcr.io/cadvisor | 8080 | Container metrics |
| blackbox | prom/blackbox-exporter | 9115 | HTTP probe for /health |

## CI pipeline (24 workflows)

```mermaid
flowchart LR
    push["push / PR"] --> lint["lint<br/>yamllint · shellcheck<br/>compose config"]
    push --> smoke["smoke<br/>stub + prod stack"]
    push --> deploy_drill["deploy drill<br/>blue→green→blue<br/>+ canary"]
    push --> canary_fail["canary failure<br/>break green → rollback"]
    push --> restore_drill["restore drill<br/>backup → wipe → restore"]
    push --> enc_drill["encryption drill<br/>encrypt → restore"]
    push --> integ_drill["integrity drill<br/>row count diff"]
    push --> rot_drill["rotation drill<br/>key + password"]
    push --> logs_drill["logs drill<br/>Loki ingest → query"]
    push --> alerts_drill["alerts drill<br/>alert → webhook"]
    push --> trace_drill["tracing drill<br/>Tempo → query"]
    push --> chaos_drill["chaos drill<br/>kill → recover"]
    push --> dr_drill["DR drill<br/>total loss → restore"]
    push --> k6["load test<br/>50 VUs · p95<500ms"]
    push --> codeql["CodeQL<br/>semantic analysis"]
    push --> trivy["Trivy<br/>container CVE scan"]
    push --> sbom["SBOM<br/>syft + grype"]
    push_main["push to main"] --> registry["registry build<br/>amd64 + arm64"]
    registry --> cosign_sign["cosign sign<br/>keyless"]
    cosign_sign --> cosign_verify["cosign verify<br/>signature + SBOM"]
    tag["tag v*"] --> release_notes["release notes<br/>auto-generated"]
```

## Data flow: deploy

```mermaid
sequenceDiagram
    participant op as Operator
    participant dep as deploy.sh
    participant compose as Docker Compose
    participant nginx as nginx
    participant app as app-green

    op->>dep: bash scripts/deploy.sh green
    dep->>dep: verify cosign signature (if GHCR image)
    dep->>compose: up -d --wait app-green
    compose->>app: start gunicorn + migrate
    app-->>compose: healthcheck passes
    dep->>nginx: rewrite upstreams.conf → app-green
    dep->>nginx: nginx -s reload
    dep->>dep: canary probes (5 × /health/live + /health/ready)
    alt canary passes
        dep->>compose: stop app-blue (after grace period)
        dep-->>op: deploy done — app-green is live
    else canary fails
        dep->>nginx: revert upstreams.conf → app-blue
        dep->>nginx: nginx -s reload
        dep-->>op: deploy aborted — auto-rollback
    end
```

## Data flow: backup + disaster recovery

```mermaid
sequenceDiagram
    participant cron as systemd timer
    participant backup as backup-db.sh
    participant encrypt as encrypt-backups.sh
    participant sync as sync-backups.sh
    participant pg as Postgres
    participant off as Off-host destination
    participant metric as textfile metric

    cron->>backup: nightly 03:00
    backup->>pg: pg_dump --clean --if-exists
    pg-->>backup: SQL stream
    backup->>backup: gzip + sha256
    backup->>metric: write backup.prom (timestamp, size, status)
    backup->>encrypt: age encrypt with public key
    encrypt->>sync: rsync only .age files
    sync->>off: encrypted backup delivered
```

## Firewall rules

| Port | Protocol | Source | Purpose |
|---|---|---|---|
| 22 | TCP | 0.0.0.0/0 | SSH |
| 80 | TCP | 0.0.0.0/0 | HTTP (ACME + redirect) |
| 443 | TCP | 0.0.0.0/0 | HTTPS |
| 3000 | TCP | 0.0.0.0/0 | Grafana (restrict in production) |

All other ports are closed. Internal container communication uses the
Docker bridge network (no host port exposure).
