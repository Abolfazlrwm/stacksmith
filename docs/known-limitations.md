# Known limitations

What works today is proven in CI. What does not is listed here, honestly.

## Not implemented

- **Single host.** Everything runs on one VPS. There is no HA, no
  multi-host failover, no horizontal scaling. ADR-0001 documents this as
  a deliberate choice; ADR-0015 documents what multi-host would require.
- **No automated secret rotation schedule.** `scripts/rotate-secrets.sh`
  exists and is tested in CI (ADR-0013), but scheduling it (e.g.
  quarterly via cron) is a manual operator decision.
- **cosign verify at deploy time.** The cosign signature is verified in
  CI (ADR-0023), but `deploy.sh` does not call `cosign verify` before
  switching the upstream. A deploy-time verify is on the v0.7 roadmap.
- **Business-endpoint load tests.** The k6 load test covers
  `/health/live/` only. Testing the real docubot API (RAG queries,
  streaming) requires the docubot app, which is not part of this kit.
- **Terraform is provider-specific.** The module ships for Hetzner Cloud
  only. Swapping to DigitalOcean or AWS requires changing the provider
  block (ADR-0021).

## Tested but not in production

- The backup and restore scripts are tested in CI against a fresh
  database. They have not been run against a large production database.
  The restore time for a multi-GB dump is unknown.
- The blue-green deploy is tested in CI with a health probe. It has not
  been tested under real traffic with long-lived connections (websockets,
  streaming uploads). The `GRACE_PERIOD` may need tuning.
- The disaster recovery drill destroys and rebuilds the stack on a CI
  runner. A real VPS loss may differ (DNS propagation, SSH access, cloud
  provider quirks).

## Recently closed

- **Disaster recovery** (closed 2026-12-02, ADR-0024). Total VPS loss
  simulation: destroy everything, restore from encrypted backup, verify
  data values and app health.
- **cosign verify gate** (closed 2026-12-01, ADR-0023). CI workflow
  verifies image signature and SBOM attestation on every push and daily.
- **Automated TLS** (closed 2026-11-14, ADR-0010). certbot renewal loop.
- **Log aggregation** (closed 2026-11-13, ADR-0009). Loki + promtail.
- **Canary checks** (closed 2026-11-12, ADR-0008). Post-switch probes
  with auto-rollback.
- **Off-host encryption** (closed 2026-11-11, ADR-0007). age encryption.
- **Backup freshness metric** (closed 2026-11-10, ADR-0006). textfile
  metric + BackupStale/BackupFailed alerts.
