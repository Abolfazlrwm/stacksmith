# ADR-0007: Off-host encryption with age

- **Status:** accepted
- **Date:** 2026-11-11
- **Supersedes:** the "No off-host encryption" item in `docs/known-limitations.md`

## Context

v0.1.0 shipped `sync-backups.sh` that copies plaintext `pg_dump` output
off-host over rsync. The off-host destination therefore holds plaintext
database dumps. If the off-host is compromised (a shared backup server, a
NAS, an S3 bucket with a leaked key), the entire database is exposed.

The v0.2 roadmap (issue #12) lists "off-host encryption with age" as the
first item.

## Decision

Encrypt every backup with `age` before it leaves the host. The encryption
key is an age keypair; the public key lives in `.env`
(`BACKUP_AGE_RECIPIENT`) and encrypts; the private key lives on the
operator's machine (or a separate secrets store) and decrypts. The off-host
destination only ever sees `.age` ciphertext.

Three new scripts:

- `scripts/encrypt-backups.sh` — encrypts every `docubot-*.sql.gz` that
  does not already have a `.age` sidecar, using the public key.
- `scripts/decrypt-backup.sh` — decrypts a single `.age` file back to a
  `.sql.gz`, using the private key.
- `scripts/sync-backups.sh` — rewritten to ship only `.age` files.

`scripts/restore-db.sh` accepts both `.sql.gz` (plaintext, local) and
`.sql.gz.age` (encrypted, off-host) and decrypts in-stream when given an
`.age` file.

## Rationale

- **age is the right tool.** It is modern, audited, single-purpose, and
  has no configuration files. RSA/GPG are over-engineered for this; a
  symmetric cipher (openssl) forces key distribution to every encrypting
  host.
- **Encrypt on the host, decrypt anywhere.** The host only has the public
  key. The private key never touches the VPS in normal operation — it
  lives on the operator's laptop or in a separate secrets store, and is
  only used during a restore. A compromised VPS cannot decrypt its own
  backups.
- **Plaintext stays local.** The host keeps the plaintext `.gz` and
  `.sha256` files for the local restore drill (which needs to be fast and
  not depend on the private key). Only the `.age` files are shipped
  off-host. Local retention still prunes them via the existing 7-daily +
  4-weekly policy.
- **The restore path is tested end to end.** The `encryption-drill`
  workflow generates a throwaway keypair, encrypts a backup, drops the
  test row, restores from the `.age` file, and verifies the row is back.
  This proves the decrypt + restore path, not just the encrypt path.

## Considered alternatives

### Symmetric encryption (openssl aes-256)

Rejected. Symmetric encryption forces the encrypting host to hold the
decryption key. A compromised VPS would leak both the backups and the
key to decrypt them. age's asymmetric model keeps the private key off the
host.

### GPG / OpenPGP

Rejected. GPG is a 30-year-old tool with a sprawling configuration
surface, a keyring model that does not fit "one keypair per backup
target", and a long history of footguns. age does one thing and does it
correctly.

### Cloud KMS (AWS KMS, GCP KMS)

Rejected. The deployment target is a single VPS with no cloud lock-in
(ADR-0001). A managed KMS would either require cloud credentials on the
host (another secret to manage) or a manual encryption step off-host
(which defeats the automation).

### Encrypted rsync (rsync over SSH, with encrypted filesystem on the destination)

Rejected. SSH protects the data in transit (which rsync already does),
not at rest. An encrypted filesystem on the destination protects at rest
but ties us to a specific destination setup. age encrypts the file
itself, so the destination can be anything — a plain directory, an S3
bucket, a tape.

## Consequences

- `BACKUP_AGE_RECIPIENT` (public key) is required in `.env` before
  `encrypt-backups.sh` runs. `BACKUP_AGE_IDENTITY` (path to private key)
  is required on the restore host.
- The off-host destination only ever sees `.age` files. Plaintext `.gz`
  and `.sha256` files stay on the VPS and are pruned by the existing
  retention policy.
- The restore path now has two entry points: `.sql.gz` (local, fast) and
  `.sql.gz.age` (off-host, requires the private key). Both are tested in
  CI — the restore drill covers the plaintext path, the encryption drill
  covers the encrypted path.
- The operator must keep the age private key safe. If it is lost,
  encrypted backups cannot be restored. The key should be backed up
  somewhere other than the off-host backup destination (otherwise losing
  the destination loses both the backups and the key).
- This decision closes the "off-host encryption" item from the v0.2
  roadmap (issue #12).
