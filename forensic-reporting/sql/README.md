# Optional SQL Persistence Layer

`schema.sql` defines a relational schema (`cases`, `manipulation_markers`, `custody_entries`,
`annotation_tasks`, plus a `high_confidence_synthetic_cases` view) for teams that want
forensic cases queryable/joinable at scale instead of scattered across flat files.

The toolkit's default storage remains flat files (`docs/sample-reports/`, JSON-lines
custody logs) — nothing else in this repo requires a database. This is opt-in.

## Load it (SQLite, zero setup)

```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('forensic_cases.db')
conn.executescript(open('forensic-reporting/sql/schema.sql').read())
print('Schema loaded into forensic_cases.db')
"
```

## PostgreSQL

The schema is standard SQL; on PostgreSQL swap `INTEGER PRIMARY KEY AUTOINCREMENT` for
`SERIAL PRIMARY KEY` and `TEXT` timestamp columns for `TIMESTAMPTZ` (see inline comments
in `schema.sql`).

## Example query

```sql
-- Every high-confidence synthetic case with more than 2 manipulation markers
SELECT case_id, evidence_id, overall_confidence, marker_count
FROM high_confidence_synthetic_cases
WHERE marker_count > 2;
```
