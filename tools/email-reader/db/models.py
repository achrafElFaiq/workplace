SCHEMA = """
CREATE TABLE IF NOT EXISTS emails (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gmail_id TEXT UNIQUE NOT NULL,
    gmail_account TEXT,
    from_name TEXT,
    from_address TEXT,
    subject TEXT,
    body_preview TEXT,
    summary TEXT,
    category TEXT,
    received_at DATETIME,
    synced_at DATETIME DEFAULT (datetime('now')),
    is_read INTEGER DEFAULT 0,
    gmail_link TEXT
);

CREATE INDEX IF NOT EXISTS idx_emails_received ON emails(received_at DESC);
CREATE INDEX IF NOT EXISTS idx_emails_category ON emails(category);
CREATE INDEX IF NOT EXISTS idx_emails_account ON emails(gmail_account);

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""
