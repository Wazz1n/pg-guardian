# pg-guardian

Lightweight command-line tool for PostgreSQL: audit your tables, create
integrity-verified backups, and generate safe synthetic test data.

> **Status:** early development (v0.1.0). See the [roadmap](#roadmap).

## Features

- `pgg inspect` lists the tables of a schema with their size, estimated row
  count and number of indexes. Tables with no index at all are shown in red.
- `pgg backup` runs `pg_dump`, compresses the output with gzip while streaming
  it, and writes a SHA-256 checksum file next to the archive.
- `pgg seed` creates a new schema filled with synthetic, reproducible test data.

## Requirements

- Python 3.10 or newer
- PostgreSQL client tools (`pg_dump` must be on your `PATH`)
- A PostgreSQL server you can connect to

## Installation

```bash
git clone https://github.com/Wazz1n/pg-guardian.git
cd pg-guardian
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Usage

Pass the connection string with the `DATABASE_URL` environment variable (or
the `--dsn` option):

```bash
export DATABASE_URL="postgresql://user@localhost:5432/mydb"
```

Avoid putting a password in the connection string on the command line: it ends
up in your shell history and in the process list. Prefer a `~/.pgpass` file, or
local peer authentication (`postgresql:///mydb`).

### Audit a schema

```bash
pgg inspect --schema public
```

```text
      PostgreSQL Schema Audit (pgg_seeded)
┏━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━┓
┃ Table     ┃    Size ┃ Est. Rows ┃ Indexes ┃
┡━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━┩
│ audit_log │ 1544 kB │     20000 │       0 │
│ orders    │  464 kB │      5000 │       2 │
│ customers │  160 kB │      1000 │       1 │
└───────────┴─────────┴───────────┴─────────┘
1 table(s) have no index at all.
```

Notes:

- Row counts are estimates from PostgreSQL statistics. They can lag behind
  right after large writes; run `ANALYZE` to refresh them.
- The Indexes column counts every index, including the primary key. A value of
  `0` therefore means the table has no primary key and no other index.

### Create a verified backup

```bash
pgg backup --out ./backups
```

This writes `backup_<UTC timestamp>.sql.gz` and a matching `.sha256` file.
Verify it with the standard tool, then restore it with `psql`:

```bash
cd backups
sha256sum -c backup_<timestamp>.sql.gz.sha256
gunzip -c backup_<timestamp>.sql.gz | psql -d target_database
```

The checksum detects accidental corruption (disk errors, truncated transfers).
It is stored next to the backup, so it does not protect against someone who
deliberately modifies both files.

### Generate test data

```bash
pgg seed --schema pgg_seeded --customers 1000 --seed 42
```

This creates three tables: `customers`, `orders` (indexed on `customer_id`) and
`audit_log` (deliberately left without an index, so that `pgg inspect` has
something to flag). The same `--seed` always produces the same data.

## Safety notes

- `inspect` uses a read-only connection.
- Passwords reach `pg_dump` through environment variables, never on its
  command line.
- `seed` only creates a new schema, inside a single transaction. It refuses to
  run if the schema already exists and never modifies existing objects.
- Generated e-mail addresses use the reserved `example.com`, `example.org` and
  `example.net` domains. No real personal data is involved.
- Backups contain your data. The `backups/` folder is git-ignored; keep it
  that way.

## Development

```bash
pytest
```

The unit tests need no running PostgreSQL: `pg_dump` is mocked and the data
generator is a pure function. The SQL parts (`inspect` and the `seed`
insertion) have been checked manually against a local PostgreSQL server;
automated integration tests are on the roadmap.

## Roadmap

- [ ] `pgg diff`: compare two schemas
- [ ] Backup rotation (keep the N most recent archives)
- [ ] S3 export for backups
- [ ] CI/CD mode (machine-readable output, exit codes based on findings)
- [ ] Optional exact row counts (`--exact`)
- [ ] Automated integration tests against a real PostgreSQL server

## License

MIT. See [LICENSE](LICENSE).
