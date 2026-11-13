# ADR-0023: cosign verify gate — closing the supply-chain loop

- **Status:** accepted
- **Date:** 2026-12-01
- **Supersedes:** —

## Context

ADR-0020 ships cosign keyless signing. The image is signed, but nothing
verifies the signature before a deploy. A consumer (the VPS, a CI deploy
job, a human) has no automated gate that says "this image is signed by
this repo's CI — safe to deploy".

The supply chain is:

1. **Build** (registry-build) → image in GHCR
2. **Sign** (cosign-sign) → cosign signature + SBOM attestation
3. **Verify** (cosign-verify) → confirm the signature is valid ← MISSING

Without step 3, the signature exists but is never checked. An attacker
who replaces the image in GHCR (via a compromised token) leaves the
signature invalid, but nobody notices.

## Decision

Add a `cosign-verify.yml` workflow that:

1. Installs cosign.
2. Logs in to GHCR (read-only).
3. Verifies the signature on `ghcr.io/.../app:latest` using the
   keyless identity (GitHub OIDC issuer + repo identity regex).
4. Verifies the SBOM attestation (`cosign verify-attestation --type
   spdxjson`).

The workflow runs on every push (so a PR that breaks the signature is
caught), daily at 06:00 UTC (so a registry compromise is detected within
24h), and on manual dispatch.

Also fix the cosign-sign timing: change its trigger from `push` to
`workflow_run` on `registry-build` completed. This ensures the image
exists in GHCR before cosign tries to sign it.

## Rationale

- **Verify, don't just sign.** A signature that is never verified is
  theatre. The verify workflow is the proof that the signature is valid
  and that the image has not been tampered with since signing.

- **Both signature and SBOM attestation.** The image has two cosign
  artifacts: the signature (proves who built it) and the SBOM attestation
  (proves what is in it). Both are verified. A consumer that checks only
  the signature knows who built the image but not what is in it.

- **Daily schedule.** A push-triggered verify catches regressions (a PR
  that breaks signing). A daily schedule catches registry compromise
  (someone replaces the image without a code change). Both are real
  attack vectors.

- **`workflow_run` for sign.** The sign workflow previously triggered on
  `push` alongside `registry-build`. If sign ran before build pushed the
  image, cosign had nothing to sign. `workflow_run` on
  `registry-build: completed` guarantees the image exists.

## Considered alternatives

### Verify in the deploy script (not CI)

Not rejected, but not the only gate. The deploy script (`deploy.sh`)
could call `cosign verify` before switching the upstream. This is a good
defense-in-depth measure and is on the v0.7 roadmap. The CI verify is
the baseline; the deploy-time verify is the belt-and-suspenders.

### Sigstore Policy Controller

Rejected for now. The Sigstore Policy Controller is a Kubernetes
admission controller that verifies cosign signatures at deploy time.
For a compose-based deployment, it does not apply. If the kit moves to
Kubernetes (ADR-0001 reopens), the Policy Controller is the right tool.

### No verify (trust the registry)

Rejected. A registry is not a trust anchor. GHCR is operated by GitHub;
a compromised GitHub token can push a malicious image. The cosign
signature is independent of the registry — it is tied to the OIDC
identity, not to the registry's auth.

## Consequences

- `cosign-verify.yml` runs on every push, daily, and on dispatch.
- The workflow verifies both the image signature and the SBOM attestation.
- `cosign-sign.yml` now triggers on `workflow_run: registry-build:
  completed` instead of `push`. This adds ~2 min to the sign cycle (the
  build must complete first).
- A failed verify blocks the PR (the signature is invalid or the image
  was tampered with).
- The daily run catches a registry compromise within 24h.

---

# ADR-0024: Disaster recovery drill — total VPS loss simulation

- **Status:** accepted
- **Date:** 2026-12-02
- **Supersedes:** —

## Context

Every previous drill tests a single failure mode:

- restore-drill: backup → wipe one row → restore → verify (Phase 3)
- encryption-drill: encrypt → wipe → restore from encrypted → verify (Phase 6.2)
- integrity-drill: backup → verify row counts match (Phase 7.2)
- chaos-drill: kill worker + stop nginx → verify recovery (Phase 9.4)

None tests the scenario that actually keeps operators awake: **the VPS is
gone**. The disk failed, the cloud provider terminated the instance, the
datacenter burned down. The only thing that survives is an encrypted
backup on an off-host destination and the age private key.

## Decision

Add a `disaster-recovery-drill.yml` workflow that simulates a total VPS
loss in six phases:

1. **Seed** — bring up the stack, create a `_dr_canary` table with known
   data.
2. **Backup** — take a backup and encrypt it with age.
3. **Destroy** — tear down the entire stack with `--volumes`. Remove
   plaintext backups. Only the `.age` file survives.
4. **Provision** — bring up a fresh stack from scratch (empty database).
   Verify the `_dr_canary` table does NOT exist.
5. **Restore** — restore from the encrypted `.age` backup.
6. **Verify** — confirm the `_dr_canary` table has the expected rows
   with the expected values. Confirm the app is serving `/health/live/`.

## Rationale

- **Total loss, not partial.** Every other drill keeps the volumes and
  the postgres container running. This drill destroys everything. If the
  backup can survive a total loss and restore into a fresh stack, it can
  survive anything.

- **Encrypted backup, not plaintext.** The drill uses the `.age` file,
  not the `.sql.gz`. This proves the encryption path (ADR-0007) works
  end to end — the operator only needs the encrypted file and the age
  key to recover.

- **Verify data, not just row count.** The drill checks the actual
  values (`label = 'critical-data'`), not just the count. A restore that
  produces the right number of rows with wrong values is silent
  corruption.

- **Verify the app serves.** Data recovery is not enough; the app must
  be serving traffic after the restore. The drill hits `/health/live/`
  after the restore to confirm the stack is operational.

- **Six numbered phases.** The drill is structured as six explicit
  phases so an operator reading the logs can follow exactly what
  happened and where it failed. A drill that is a single 200-line script
  is harder to debug than six named phases.

## Considered alternatives

### Restore to a second VPS (true off-host)

Not rejected, but not the default. A true off-host restore requires a
second VPS, which the kit does not provision (Terraform provisions one).
The drill restores to a fresh stack on the same CI runner, which proves
the backup → restore → verify path. The off-host restore is the same
path with a different SSH target.

### Snapshot-based recovery

Rejected. The kit does not use volume snapshots (ADR-0003 chose
dump-based backups). A snapshot-based DR drill would test a different
backup strategy than the one the kit ships.

### No DR drill (rely on the restore drill)

Rejected. The restore drill (Phase 3) keeps the volumes and the postgres
container. It proves the dump can be restored. It does NOT prove the
stack can be rebuilt from scratch with only an encrypted backup. The DR
drill is the "house burned down" test — the restore drill is the "spilled
coffee on the keyboard" test.

## Consequences

- `disaster-recovery-drill.yml` runs on every push.
- The drill takes ~8-10 minutes (two full stack up/down cycles + backup +
  encrypt + restore).
- The drill uses an age keypair generated in CI (thrown away after the
  run). In production, the operator's age key is on their laptop.
- The drill proves: encrypted backup survives total loss, fresh stack
  accepts the restore, data is verified, app is serving.
- This is the strongest claim the kit can make: "we tested recovery from
  a total VPS loss, and it works."
