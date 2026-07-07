-- schema.sql
-- -----------
-- Optional relational persistence layer for forensic cases, manipulation
-- markers, and chain-of-custody entries.
--
-- The toolkit's default storage is flat files (Markdown/JSON/PDF reports in
-- docs/sample-reports/, JSON-lines custody logs) so every module works with
-- zero infrastructure. This schema is for teams that outgrow flat files and
-- want cases queryable/joinable at scale (e.g. "show me every case with a
-- checkerboard_score marker above 0.7 in the last 30 days").
--
-- Written in standard SQL (tested against SQLite in this repo's CI-equivalent
-- checks; also valid on PostgreSQL with minor type substitutions noted below
-- as comments).
--
-- Load into SQLite:
--   sqlite3 forensic_cases.db < forensic-reporting/sql/schema.sql

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS cases (
    case_id             TEXT PRIMARY KEY,
    evidence_id         TEXT NOT NULL,
    analyst             TEXT NOT NULL,
    evidence_description TEXT,
    overall_verdict     TEXT NOT NULL CHECK (overall_verdict IN ('LIKELY_SYNTHETIC', 'LIKELY_AUTHENTIC', 'INCONCLUSIVE')),
    overall_confidence  REAL NOT NULL CHECK (overall_confidence >= 0.0 AND overall_confidence <= 1.0),
    generated_at        TEXT NOT NULL  -- ISO-8601 UTC timestamp; TIMESTAMPTZ on PostgreSQL
);

CREATE TABLE IF NOT EXISTS manipulation_markers (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,  -- SERIAL on PostgreSQL
    case_id      TEXT NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    marker_type  TEXT NOT NULL,
    confidence   REAL NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    detail       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS custody_entries (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,  -- SERIAL on PostgreSQL
    case_id          TEXT NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    timestamp        TEXT NOT NULL,
    actor            TEXT NOT NULL,
    action           TEXT NOT NULL,
    evidence_hash    TEXT NOT NULL,
    notes            TEXT,
    prev_entry_hash  TEXT NOT NULL,
    entry_hash       TEXT NOT NULL UNIQUE  -- enforces the hash chain can't be duplicated/replayed
);

CREATE TABLE IF NOT EXISTS annotation_tasks (
    task_id                    TEXT PRIMARY KEY,
    filename                   TEXT NOT NULL,
    ground_truth_label         TEXT CHECK (ground_truth_label IN ('real', 'synthetic')),
    adjudicated_label          TEXT CHECK (adjudicated_label IN ('real', 'synthetic', 'uncertain')),
    fleiss_kappa_at_adjudication REAL
);

-- Convenience view: cases with at least one high-confidence marker, most
-- recent first -- the kind of query a triage dashboard would run.
CREATE VIEW IF NOT EXISTS high_confidence_synthetic_cases AS
SELECT
    c.case_id,
    c.evidence_id,
    c.analyst,
    c.overall_confidence,
    c.generated_at,
    COUNT(m.id) AS marker_count
FROM cases c
JOIN manipulation_markers m ON m.case_id = c.case_id
WHERE c.overall_verdict = 'LIKELY_SYNTHETIC'
  AND c.overall_confidence >= 0.75
GROUP BY c.case_id
ORDER BY c.generated_at DESC;

CREATE INDEX IF NOT EXISTS idx_markers_case_id ON manipulation_markers(case_id);
CREATE INDEX IF NOT EXISTS idx_custody_case_id ON custody_entries(case_id);
