# ADR-0003: Dump-based backups over WAL shipping

- **Status:** accepted
- **Date:** 2026-11-06
- **Supersedes:** —

## Context

The docubot database needs a backup strategy. The two mainstream options
are logical dumps (`pg_dump`) and continuous WAL shipping (`pg_basebackup`
+ `archive_command` + `restore_command`). The choice is driven by the
recovery point objective (RPO), the recovery time objective (RTO), the
operational surface, and what the CI pipeline can realistically test.

## Decision

Use nightly `pg_dump` (with gzip + sha256 + retention) as the backup
strategy. `scripts/backup-db.sh` produces a compressed dump;
`scripts/restore-db.sh` restores it; the `restore-drill` workflow proves
the restore path by backing up, dropping a test row, restoring, and
verifying the row count.

## Rationale

- **Testable.** A dump is a single file. The restore drill in CI can back
  it up, wipe a table, restore, and verify row counts in under a minute.
  WAL shipping requires a second postgres instance, a replication slot,
  and a `restore_command` — none of which fit in a CI job that also has
  to run the app stack.
- **Adequate RPO for this scale.** The docubot database is a knowledge
  base, not a transaction ledger. Losing up to 24 hours of changes (the
  worst case between nightly dumps) is acceptable. If it stops being
  acceptable, this decision is reopened.
- **Simple retention.** Keep 7 daily + 4 weekly dumps. File-based
  retention is `ls -1t | tail`. WAL retention requires managing
  `wal_keep_size`, archive volume growth, and replication slot lag.
- **Portable.** A `pg_dump` file restores into any postgres of the same
  major version. A WAL-shipped base backup is tied to the same data
  directory layout and the same major version, and requires the same
  `shared_preload_libraries`.

## Considered alternatives

### WAL shipping (continuous archiving)

Rejected for this scale. WAL shipping gives a near-zero RPO (you can
recover to the last transaction) but the cost is real: a second postgres
instance to receive the base backup and the WAL stream, a replication
slot or `archive_command` to manage, a growing archive volume to prune,
and a restore procedure (`restore_command` + `recovery.target_time`) that
is fiddly to test in CI. For a single-VPS deployment where the worst-case
data loss is 24 hours of knowledge-base edits, the complexity is not
justified.

### pgBackRest

Rejected. pgBackRest is excellent for larger deployments, but it adds a
binary, a configuration file, a repository, and its own backup/restore
CLI. The dump-based approach uses tools that are already in the postgres
image (`pg_dump`, `psql`) and the host (`gzip`, `sha256sum`). The restore
drill is simpler and more honest.

### Cloud-managed backups (RDS, CloudSQL)

Rejected. The deployment target is a single VPS, not a managed database.
A managed database would also remove the need for this repository, which
defeats the purpose.

## Consequences

- RPO is up to 24 hours (the gap between nightly dumps). If a user edits
  a document 23 hours after the last backup and the disk dies, those
  edits are lost.
- RTO is the time to `gunzip | psql` the dump — seconds to minutes
  depending on dump size.
- The backup is a single compressed file that can be copied off-host with
  `rsync` or `scp`. No WAL archive to synchronize.
- The restore drill in CI is the proof that the backup is restorable. A
  backup that has never been restored is not a backup; it is a hope.
- If the RPO requirement tightens (e.g. docubot starts handling
  transactional data), this decision is reopened and WAL shipping (or
  pgBackRest) is evaluated again.
