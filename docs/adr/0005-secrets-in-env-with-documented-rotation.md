# ADR-0005: Secrets in .env with documented rotation

- **Status:** accepted
- **Date:** 2026-11-08
- **Supersedes:** —

## Context

The stack needs secrets: `DJANGO_SECRET_KEY`, `POSTGRES_PASSWORD`,
`GRAFANA_ADMIN_PASSWORD`, and (when TLS is enabled) certificate keys.
The question is where they live, how they are rotated, and how they are
kept out of version control.

## Decision

Store secrets in `.env` on the host. `.env` is git-ignored (Phase 1);
`.env.example` is the contract of which variables exist. Rotation is a
documented manual procedure, not an automated one. No secrets are baked
into images.

## Rationale

- **Single host.** There is no cluster to distribute secrets to. The
  `.env` file on the host is the single source of truth, read by compose
  at `up` time.
- **No secret manager overhead.** Vault, SOPS, Doppler and friends are
  excellent for a fleet. For one VPS they add a service to run, a token
  to manage, and a failure mode to monitor. `.env` + file permissions is
  simpler and sufficient.
- **Git-ignored by construction.** `.gitignore` excludes `.env` and
  `.env.*` (except `.env.example`). `scripts/check-env.sh` refuses to
  proceed if `.env` is missing or the secret key is still the placeholder.
- **Images are secret-free.** The Dockerfile does not `COPY .env`. Secrets
  enter the container via `env_file: .env` in compose, at runtime. An
  image leak does not leak secrets.

## Rotation procedures

### DJANGO_SECRET_KEY

1. Generate a new key: `python -c "import secrets; print(secrets.token_urlsafe(50))"`.
2. Edit `.env`, replace the `DJANGO_SECRET_KEY` value.
3. `bash scripts/deploy.sh` — deploy the new key. All existing sessions
   are invalidated (users are logged out); no data is lost.

### POSTGRES_PASSWORD

1. `bash scripts/backup-db.sh` — take a backup before touching anything.
2. Change the password in postgres:
   `docker compose exec postgres psql -U docubot -c "ALTER USER docubot PASSWORD 'new';"`.
3. Edit `.env`, replace `POSTGRES_PASSWORD`.
4. `docker compose up -d --no-deps app-blue app-green worker beat` —
   restart the services that connect to postgres.

### GRAFANA_ADMIN_PASSWORD

1. Edit `.env`, replace `GRAFANA_ADMIN_PASSWORD`.
2. `docker compose -f docker-compose.monitoring.yml up -d --force-recreate
   grafana` — recreate grafana with the new password.

## Considered alternatives

### HashiCorp Vault

Rejected for this scale. Vault adds a service, a storage backend, a token
management lifecycle, and an unseal procedure. For a single VPS with
three secrets, `.env` + `chmod 600` is the right tool.

### SOPS / age-encrypted files in git

Rejected. SOPS is a strong pattern for a team that wants secret rotation
in version control. It adds a KMS dependency (or an age key to manage)
and a decrypt step at deploy time. For a solo deployment, `.env` on the
host is simpler and the rotation procedure is documented above.

### Docker secrets / Swarm

Rejected. We are not running Swarm. Compose does not have a first-class
secrets mechanism without Swarm.

## Consequences

- `.env` is the secret store. It must be backed up off-host (it is not in
  git). The backup of `.env` is the operator's responsibility.
- Rotation is manual. A calendar reminder is appropriate for
  time-bound rotations (e.g. quarterly key rotation).
- If the host is compromised, `.env` is exposed. This is true of any
  single-host secret strategy. Mitigation: restrict SSH access, use a
  firewall, and rotate all secrets after a suspected compromise.
- Moving to a multi-host deployment reopens this decision; at that point
  Vault or SOPS becomes worth the cost.
