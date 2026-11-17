# ADR-0012: Backup integrity verification against a throwaway database

- **Status:** accepted
- **Date:** 2026-11-17
- **Supersedes:** the "tested in CI against a fresh database" caveat in known-limitations

## Context

The restore drill (Phase 3) proves a backup can be restored: it seeds one
row, backs up, drops the row, restores, and verifies the row count is 1.
This catches gross failures (the dump is corrupt, the restore fails) but
not silent corruption:

- A table was dropped between the dump starting and completing.
- `pg_dump` ran mid-transaction and captured an inconsistent snapshot.
- A migration changed the schema after the dump but before the restore.
- A large table is silently missing rows due to a storage-level error.

The v0.3 roadmap (issue #20) lists "Backup integrity verification" as the
second item.

## Decision

`scripts/verify-backup.sh` restores a backup into a throwaway database
(created alongside the production one), then diffs the row counts of every
user table between the source and the restored copy. If any table's row
count differs, the script exits non-zero.

The `integrity-drill` workflow runs this end to end: seed multiple tables
with known row counts, take a backup, verify integrity, and confirm the
row counts match.

## Rationale

- **Row count is a cheap, strong signal.** A backup that has the wrong
  number of rows in any table is corrupt. Row counts do not catch value
  corruption (a byte flipped in a text field), but they catch the failure
  modes that actually happen: missing tables, truncated dumps, mid-write
  snapshots.
- **Throwaway database, not a separate container.** Creating a second
  database inside the same postgres instance is free — no extra container,
  no extra port, no extra volume. The throwaway is dropped on exit.
- **`pg_stat_user_tables` is fast.** The `n_live_tup` column is maintained
  by the planner and does not require `COUNT(*)` on every table. For a
  multi-GB database, this is seconds, not minutes.
- **Works on encrypted backups.** `verify-backup.sh` accepts `.age` files
  and decrypts in-stream, so off-host backups can be verified without
  leaving a plaintext copy on disk.

## Considered alternatives

### Full checksum of every row

Rejected for performance. `md5(string_agg(row::text))` on every table is
correct but requires a full table scan on both databases. For a
knowledge-base database this is fine; for a large transactional database
it is too slow to run nightly. Row count is 95% of the signal at 1% of
the cost. If row counts ever pass but corruption is suspected, the
operator can run a one-off full checksum manually.

### pgbackrest verify

Rejected. pgbackrest is not in the stack (ADR-0003 chose pg_dump). The
integrity check must work on the dump-based backups we actually produce.

### Periodic restore into a staging host

Not rejected, but not the default. The throwaway-database approach runs on
the production host and verifies the backup against the live database. A
staging restore verifies against a copy of the database (which itself
might be stale). The throwaway approach is more honest: it compares
backup-against-source at the moment of verification.

## Consequences

- `scripts/verify-backup.sh` creates and drops a throwaway database
  inside the production postgres. The throwaway name includes the PID so
  concurrent runs do not collide.
- The script works on both `.sql.gz` and `.sql.gz.age` files.
- The `integrity-drill` workflow seeds two tables with known row counts,
  takes a backup, and verifies the counts match after restore.
- This does not replace the restore drill (which tests the restore path
  end to end); it adds an integrity layer on top of it.
- This decision closes the "Backup integrity verification" item from the
  v0.3 roadmap (issue #20).
