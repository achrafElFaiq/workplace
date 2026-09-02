SCHEMA = """
CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company TEXT NOT NULL,
    position TEXT NOT NULL,
    location TEXT,
    contract_type TEXT,
    salary TEXT,
    missions TEXT,        -- JSON array
    stack TEXT,           -- JSON array
    requirements TEXT,    -- JSON array
    process TEXT,         -- JSON array, etapes du processus de recrutement
    keywords TEXT,        -- JSON array, mots-clés pertinents pour l'offre
    sector TEXT,
    company_size TEXT,
    contact TEXT,
    seniority TEXT,
    url TEXT,
    raw_text TEXT,
    source TEXT,
    applied_via_email TEXT,
    status TEXT DEFAULT 'applied',
    notes TEXT,
    applied_at DATE DEFAULT (date('now')),
    created_at DATETIME DEFAULT (datetime('now')),
    updated_at DATETIME DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS emails (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id INTEGER NOT NULL,
    gmail_id TEXT UNIQUE NOT NULL,
    gmail_account TEXT,
    from_address TEXT,
    subject TEXT,
    snippet TEXT,
    classification TEXT,
    gmail_link TEXT,
    received_at DATETIME,
    FOREIGN KEY (application_id) REFERENCES applications(id)
);

CREATE TABLE IF NOT EXISTS status_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id INTEGER NOT NULL,
    old_status TEXT,
    new_status TEXT NOT NULL,
    trigger TEXT DEFAULT 'manual',
    changed_at DATETIME DEFAULT (datetime('now')),
    FOREIGN KEY (application_id) REFERENCES applications(id)
);

CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id INTEGER NOT NULL,
    filename TEXT NOT NULL,
    filepath TEXT NOT NULL,
    doc_type TEXT,
    uploaded_at DATETIME DEFAULT (datetime('now')),
    FOREIGN KEY (application_id) REFERENCES applications(id)
);

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT,
    last_name TEXT,
    function TEXT,
    company TEXT,
    email TEXT,
    phone TEXT,
    notes TEXT,
    created_at DATETIME DEFAULT (datetime('now')),
    updated_at DATETIME DEFAULT (datetime('now'))
);
"""