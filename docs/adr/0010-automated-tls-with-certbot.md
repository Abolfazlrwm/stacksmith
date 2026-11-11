# ADR-0010: Automated TLS with certbot and a renewal loop

- **Status:** accepted
- **Date:** 2026-11-14
- **Supersedes:** the "TLS is a template" item in `docs/known-limitations.md`

## Context

v0.1.0 shipped TLS as a commented-out template in `nginx/default.conf`.
Enabling HTTPS required manually obtaining a certificate, placing it in
`nginx/certs/`, uncommenting the `:443` server block, and reloading
nginx. There was no renewal pipeline — the operator had to remember to
renew before expiry.

The v0.2 roadmap (issue #12) lists "automated cert renewal" as a
desired improvement.

## Decision

Ship a `docker-compose.tls.yml` overlay that runs certbot in a renewal
loop (every 12h). A companion `scripts/issue-cert.sh` obtains the first
certificate via the ACME HTTP-01 challenge (served by the existing
`:80` nginx server at `/.well-known/acme-challenge/`). After the first
issuance, the renewal loop keeps the cert fresh and reloads nginx
automatically via certbot's `--deploy-hook`.

The `:443` server block in `nginx/default.conf` is now real (not a
template), but it only loads if `nginx/certs/fullchain.pem` exists. nginx
fails to start without the cert; the operator runs `issue-cert.sh` once,
then brings up the stack.

## Rationale

- **Let's Encrypt is free and automated.** There is no reason to buy a
  cert or manage renewal manually when certbot + ACME handles both.
- **The renewal loop is a container, not a cron job.** Running certbot in
  a container means it uses the same docker network as nginx, can be
  brought up and down with the rest of the stack, and does not require a
  host-level cron install.
- **`--deploy-hook` reloads nginx after renewal.** certbot runs the hook
  only on a successful renewal (not on every no-op run). The hook calls
  `docker exec <nginx-container> nginx -s reload`, so the new cert is
  picked up without downtime.
- **The first issuance is a script, not automation.** The first cert
  requires DNS to point at the host and the `:80` server to be up. This
  is a one-time manual step (`scripts/issue-cert.sh <domain> <email>`);
  automating it would hide the DNS prerequisite and make failures
  confusing.
- **Overlay, not always-on.** `docker-compose.tls.yml` is a separate
  overlay. The stack runs fine without it (HTTP-only) for development and
  CI. In production, the operator brings up the stack with
  `-f docker-compose.tls.yml` after the first issuance.

## Considered alternatives

### Manual cert renewal (v0.1.0 behavior)

Rejected. A calendar reminder is not a renewal pipeline. Cert expiry is
the most common cause of avoidable outages; automating it removes a
whole class of incidents.

### nginx-proxy + acme-companion

Rejected. nginx-proxy is a separate reverse proxy that generates nginx
config dynamically. We already have nginx config in version control
(Phase 1); adding a dynamic config generator on top is complexity
without benefit for a single-host deployment with a known set of domains.

### Caddy (automatic HTTPS built in)

Rejected. Caddy is excellent and does automatic HTTPS by default.
Switching to Caddy would mean rewriting the entire nginx config
(Phase 1) and losing the nginx-specific knowledge in the runbooks. The
certbot overlay adds renewal to the existing nginx without a rewrite.

### Cloud-managed certs (ACM, Cloudflare)

Rejected. Same reasoning as ADR-0001: no cloud lock-in. A Let's Encrypt
cert works on any VPS, with any DNS provider.

## Consequences

- `docker-compose.tls.yml` adds a `certbot` service that runs a renewal
  loop every 12h.
- `scripts/issue-cert.sh` obtains the first cert via the ACME HTTP-01
  challenge. Run it once after DNS is pointed at the host.
- `nginx/default.conf` has a real `:443` server block (not a template).
  It loads `nginx/certs/fullchain.pem` and `privkey.pem` — symlinks
  created by `issue-cert.sh` to the certbot-managed files.
- `docker-compose.prod.yml` mounts `nginx/certs` and `nginx/certbot-www`
  into the nginx container and exposes port 443.
- The renewal loop reloads nginx after each successful renewal via
  `--deploy-hook`. No downtime, no manual intervention.
- The cert files are git-ignored (`.gitignore` excludes `nginx/certs/*`
  except `.gitkeep`). They are runtime state, not source.
- This decision closes the "automated cert renewal" item from the v0.2
  roadmap (issue #12).
