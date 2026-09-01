SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT    NOT NULL,
    date        DATE    NOT NULL,
    time        TEXT,
    end_time    TEXT,
    category    TEXT    DEFAULT 'personal',
    description TEXT,
    all_day     INTEGER DEFAULT 1,
    source      TEXT    DEFAULT 'manual',
    source_id   INTEGER,
    created_at  DATETIME DEFAULT (datetime('now')),
    updated_at  DATETIME DEFAULT (datetime('now'))
);
"""
