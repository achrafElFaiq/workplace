import streamlit as st
from db.database import get_connection


@st.cache_data(ttl=60)
def get_events_for_month(year: int, month: int) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM events WHERE strftime('%Y', date) = ? AND strftime('%m', date) = ? ORDER BY date, time",
        (str(year), f"{month:02d}"),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@st.cache_data(ttl=60)
def get_events_for_range(start: str, end: str) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM events WHERE date >= ? AND date <= ? ORDER BY date, time",
        (start, end),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@st.cache_data(ttl=60)
def get_upcoming_events(days: int = 14) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM events WHERE date >= date('now') AND date <= date('now', ?) ORDER BY date, time",
        (f"+{days} days",),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_event(event_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def add_event(title, date, time, end_time, category, description, all_day) -> int:
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO events (title, date, time, end_time, category, description, all_day) VALUES (?,?,?,?,?,?,?)",
        (title, date, time or None, end_time or None, category, description or None, int(all_day)),
    )
    conn.commit()
    event_id = cur.lastrowid
    conn.close()
    st.cache_data.clear()
    return event_id


def update_event(event_id: int, title, date, time, end_time, category, description, all_day):
    conn = get_connection()
    conn.execute(
        """UPDATE events SET title=?, date=?, time=?, end_time=?, category=?, description=?, all_day=?,
           updated_at=datetime('now') WHERE id=?""",
        (title, date, time or None, end_time or None, category, description or None, int(all_day), event_id),
    )
    conn.commit()
    conn.close()
    st.cache_data.clear()


def delete_event(event_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM events WHERE id = ?", (event_id,))
    conn.commit()
    conn.close()
    st.cache_data.clear()
