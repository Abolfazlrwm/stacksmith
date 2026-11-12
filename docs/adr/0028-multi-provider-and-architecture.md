# ADR-0028: Multi-provider Terraform — Hetzner + DigitalOcean

- **Status:** accepted
- **Date:** 2026-12-09
- **Supersedes:** the Hetzner-only Terraform from ADR-0021

## Context

ADR-0021 ships Terraform provisioning for Hetzner Cloud only. An operator
who uses DigitalOcean (or wants to compare providers) has to rewrite the
module.

## Decision

Rewrite `terraform/main.tf` to support both Hetzner Cloud and DigitalOcean
via a `provider` variable. The module uses `count` conditionals to
activate only the selected provider's resources. Both providers get:
- Firewall (SSH 22, HTTP 80, HTTPS 443, monitoring 3000)
- VPS with cloud-init (Docker + repo clone)
- Unified outputs (server_ip, ssh_command)
- Generated deploy-to-vps.sh

## Rationale

- **`count` over separate modules.** Using `count = var.provider == "hcloud" ? 1 : 0` keeps everything in one file. Separate modules per provider would duplicate the firewall and cloud-init logic.

- **Provider-specific defaults.** Hetzner defaults to `cx22` (2 vCPU/4GB) in `nbg1`. DigitalOcean defaults to `s-2vcpu-4gb` in `fra1`. Both are ~$6-8/month.

- **Same cloud-init.** Both providers support `user_data` for cloud-init. The same `cloud-init.yml` installs Docker and clones the repo on either provider.

## Consequences

- `terraform/main.tf` gains `digitalocean` provider and resources.
- `terraform/deploy-to-vps.sh.tpl` is a template (was a static file).
- The operator selects the provider at `terraform apply` time.
- Adding a third provider (AWS, Vultr) follows the same pattern.

---

# ADR-0029: Architecture documentation and OpenAPI spec

- **Status:** accepted
- **Date:** 2026-12-10
- **Supersedes**: —

## Context

The README has a Mermaid stack diagram, but there is no detailed
architecture document. The health endpoints have no formal API
specification — an integrator has to read the Django view code.

## Decision

1. **`docs/architecture.md`** — a comprehensive architecture document
   with five Mermaid diagrams: high-level topology, CI pipeline, deploy
   sequence, backup/DR sequence, and firewall rules. Plus a service
   inventory table and an observability inventory table.

2. **`docs/api/health-openapi.json`** — an OpenAPI 3.0 specification for
   the two health endpoints (`/health/live/` and `/health/ready/`), with
   schemas for the liveness and readiness responses.

## Rationale

- **Diagrams answer "how does this work?" without reading code.** An
  operator onboarding at 3am during an incident needs to understand the
  system in 30 seconds, not 30 minutes. The deploy sequence diagram
  shows exactly what happens when `deploy.sh` runs.

- **OpenAPI answers "what does the API return?" without curling.** An
  integrator building a monitoring dashboard needs the exact response
  schema. The OpenAPI spec is machine-readable — it can generate client
  code, Postman collections, or Swagger UI.

- **Five diagrams, not one.** The README diagram is a 10,000-foot view.
  The architecture doc adds the CI pipeline (which workflow runs when),
  the deploy sequence (step-by-step timing), the backup flow (data
  path), and the firewall rules (network surface). Each answers a
  different question.

## Consequences

- `docs/architecture.md` is the canonical architecture reference.
- `docs/api/health-openapi.json` is the canonical API spec.
- The README links to both.
- The diagrams are maintained as Mermaid in version control, not as
  exported images.
