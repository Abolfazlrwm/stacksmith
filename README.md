# StackSmith

[![lint](https://github.com/Abolfazlrwm/stacksmith/actions/workflows/lint.yml/badge.svg)](https://github.com/Abolfazlrwm/stacksmith/actions/workflows/lint.yml)
[![smoke](https://github.com/Abolfazlrwm/stacksmith/actions/workflows/smoke.yml/badge.svg)](https://github.com/Abolfazlrwm/stacksmith/actions/workflows/smoke.yml)
[![Release](https://img.shields.io/github/v/release/Abolfazlrwm/stacksmith?sort=semver)](https://github.com/Abolfazlrwm/stacksmith/releases/latest)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**deploys this ← [docubot](https://github.com/Abolfazlrwm/docubot)**

Production-grade deployment kit for the docubot stack: docker compose,
zero-downtime deploys, backups, observability. One VPS, no Kubernetes, no
cloud lock-in — everything here runs on a single machine you can ssh into.

## Why this exists

docubot is a real backend — Django 5.2 + DRF + Celery + Postgres/pgvector +
Redis. It deserves a real production path where the boring parts (deploy,
rollback, backup, monitor) are engineered as deliberately as the application
code. StackSmith is that path, and it holds itself to one rule:

> a claim in this README must be proven by a CI job; everything untested is
> written down as a known limitation instead.

## The plan

The kit is built in six phases, each merged as one pull request:

| Phase | What lands | Status |
|---|---|---|
| 0 | skeleton, lint + smoke CI, conventions, ADR-0001 | this PR |
| 1 | production compose stack: app, worker, beat, postgres, redis, nginx | planned |
| 2 | blue-green deploys and one-command rollback | planned |
| 3 | encrypted backups with a tested restore path | planned |
| 4 | observability: prometheus, alert rules, grafana, uptime probe | planned |
| 5 | runbooks, failure playbook, v0.1.0 | planned |

## Docs

- [Engineering conventions](docs/conventions.md) — how this repo is built
- [ADR-0001: compose as the deployment unit](docs/adr/0001-use-compose-as-the-deployment-unit.md)

## License

[MIT](LICENSE)
