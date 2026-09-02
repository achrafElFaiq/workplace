import sqlite3
from config import DB_PATH
from db.models import SCHEMA


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _migrate(conn):
    """CREATE TABLE IF NOT EXISTS won't add columns to an already-existing
    table — patch those in for databases created before this column existed."""
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(applications)")}
    if "process" not in columns:
        conn.execute("ALTER TABLE applications ADD COLUMN process TEXT")
    if "keywords" not in columns:
        conn.execute("ALTER TABLE applications ADD COLUMN keywords TEXT")

    contact_columns = {row["name"] for row in conn.execute("PRAGMA table_info(contacts)")}
    if "phone" not in contact_columns:
        conn.execute("ALTER TABLE contacts ADD COLUMN phone TEXT")


def init_db():
    conn = get_connection()
    conn.executescript(SCHEMA)
    _migrate(conn)
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {DB_PATH}")