# ADR-0001: docker compose is the deployment unit

- Status: accepted
- Date: 2026-11-03
- Deciders: the maintainer (single-operator project)

## Context

docubot is a Django 5.2 application with three application processes
(gunicorn, Celery worker, Celery beat) backed by PostgreSQL with pgvector,
Redis, and nginx in front. The deployment target is one VPS operated by one
person. The deployment unit has to run the whole stack, keep it healthy, and
leave room for zero-downtime releases and a real restore story without
hiring a platform team of one.

## Decision

docker compose is the deployment unit. Every service - app, worker, beat,
postgres, redis, nginx - is defined in compose files, wired with
healthchecks, and driven by the Makefile and the scripts in `scripts/`. The
same files that run the stack locally are the files CI brings up in the
smoke and drill jobs.

## Alternatives considered

1. Kubernetes (k3s on a single node, or a small managed cluster). Rejected:
   the stack does not need multi-node scheduling, and the operational cost -
   manifests, ingress controllers, storage classes, upgrades - is paid every
   week while solving problems this stack does not have. A one-operator
   project that cannot debug its own scheduler is a liability, not a
   platform.
2. A cloud container service (ECS, Cloud Run, App Runner). Rejected: it ties
   the kit to one vendor's primitives and pricing, and the point of the kit
   is that it runs on a VPS you can ssh into. Egress and managed-postgres
   costs are also wrong for a hobby-grade budget.
3. Bare systemd units with `docker run`. Rejected: the service graph, health
   gating and per-release networking would be re-implemented by hand in unit
   files, while CI would still test a different environment than production.
4. Nomad. Rejected for the same reason as Kubernetes: a second scheduler to
   learn and operate, for a single machine.

## Consequences

- The ceiling is one host. Scaling is vertical; there is no built-in HA. If
  docubot outgrows a VPS, that is a new decision and a new ADR - not a slow
  drift into half-adopted Kubernetes.
- Compose has no native rollout primitive. Zero-downtime deploys are built
  on top of compose project slots (blue/green) - see ADR-0002.
- Everything CI asserts about the stack (healthchecks, env contract, backup
  and restore) is asserted against the same compose files production uses.
- Postgres and Redis run as containers with named volumes. That is a
  deliberate trade: simpler lifecycle, at the cost of respecting the backup
  discipline introduced in phase 3.
