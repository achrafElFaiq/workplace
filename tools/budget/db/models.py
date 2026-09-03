SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS periods (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    label      TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date   TEXT NOT NULL,
    created_at DATETIME DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS budget_items (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    period_id  INTEGER NOT NULL REFERENCES periods(id) ON DELETE CASCADE,
    family     TEXT NOT NULL,
    label      TEXT NOT NULL,
    planned    REAL DEFAULT 0,
    actual     REAL DEFAULT 0,
    sort_order INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS patrimoine_items (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    period_id  INTEGER NOT NULL REFERENCES periods(id) ON DELETE CASCADE,
    family     TEXT NOT NULL,
    label      TEXT NOT NULL,
    planned    REAL DEFAULT 0,
    actual     REAL DEFAULT 0,
    sort_order INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_budget_period ON budget_items(period_id);
CREATE INDEX IF NOT EXISTS idx_patrimoine_period ON patrimoine_items(period_id);
"""
