import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from db.database import get_connection


def save_email(em: dict) -> bool:
    """Insert email, skip if gmail_id already exists. Returns True if inserted."""
    conn = get_connection()
    try:
        cursor = conn.execute("""
            INSERT OR IGNORE INTO emails
                (gmail_id, gmail_account, from_name, from_address, subject,
                 body_preview, summary, category, received_at, gmail_link)
            VALUES
                (:gmail_id, :gmail_account, :from_name, :from_address, :subject,
                 :body_preview, :summary, :category, :received_at, :gmail_link)
        """, em)
        inserted = cursor.rowcount > 0
        conn.commit()
        return inserted
    finally:
        conn.close()


def list_emails(
    category: str = None,
    account: str = None,
    unread_only: bool = False,
    limit: int = 200,
) -> list[dict]:
    conn = get_connection()
    try:
        conditions = []
        params = []
        if category and category != "all":
            conditions.append("category = ?")
            params.append(category)
        if account and account != "all":
            conditions.append("gmail_account = ?")
            params.append(account)
        if unread_only:
            conditions.append("is_read = 0")

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        rows = conn.execute(
            f"SELECT * FROM emails {where} ORDER BY received_at DESC LIMIT ?",
            params + [limit]
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def mark_read(email_id: int):
    conn = get_connection()
    try:
        conn.execute("UPDATE emails SET is_read = 1 WHERE id = ?", (email_id,))
        conn.commit()
    finally:
        conn.close()


def mark_all_read():
    conn = get_connection()
    try:
        conn.execute("UPDATE emails SET is_read = 1")
        conn.commit()
    finally:
        conn.close()


def get_stats() -> dict:
    conn = get_connection()
    try:
        total = conn.execute("SELECT COUNT(*) FROM emails").fetchone()[0]
        unread = conn.execute("SELECT COUNT(*) FROM emails WHERE is_read = 0").fetchone()[0]
        today = conn.execute(
            "SELECT COUNT(*) FROM emails WHERE date(received_at) = date('now')"
        ).fetchone()[0]
        by_category = conn.execute(
            "SELECT category, COUNT(*) as cnt FROM emails GROUP BY category ORDER BY cnt DESC"
        ).fetchall()
        return {
            "total": total,
            "unread": unread,
            "today": today,
            "by_category": {r["category"]: r["cnt"] for r in by_category},
        }
    finally:
        conn.close()


def get_email_by_id(email_id: int) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM emails WHERE id = ?", (email_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def delete_email(email_id: int):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM emails WHERE id = ?", (email_id,))
        conn.commit()
    finally:
        conn.close()


def delete_emails_by_sender(from_address: str):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM emails WHERE from_address = ?", (from_address.lower().strip(),))
        conn.commit()
    finally:
        conn.close()


def email_exists(gmail_id: str) -> bool:
    conn = get_connection()
    try:
        row = conn.execute("SELECT 1 FROM emails WHERE gmail_id = ?", (gmail_id,)).fetchone()
        return row is not None
    finally:
        conn.close()


def get_known_gmail_ids() -> set:
    conn = get_connection()
    try:
        rows = conn.execute("SELECT gmail_id FROM emails").fetchall()
        return {r["gmail_id"] for r in rows}
    finally:
        conn.close()


# ── Meta ──

def get_meta(key: str) -> str | None:
    conn = get_connection()
    try:
        row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else None
    finally:
        conn.close()


def set_meta(key: str, value: str):
    conn = get_connection()
    try:
        conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", (key, value))
        conn.commit()
    finally:
        conn.close()
