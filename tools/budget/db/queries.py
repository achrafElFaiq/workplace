from db.database import get_connection

BUDGET_FAMILIES = ["income", "fixed", "variable", "other", "savings"]
PATRIMOINE_FAMILIES = ["assets", "liabilities"]


# ── Settings ──

def get_setting(key, default=None):
    conn = get_connection()
    try:
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default
    finally:
        conn.close()


def set_setting(key, value):
    conn = get_connection()
    try:
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
        conn.commit()
    finally:
        conn.close()


# ── Periods ──

def list_periods():
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM periods ORDER BY start_date DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_period(period_id):
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM periods WHERE id = ?", (period_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def create_period(label, start_date, end_date):
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO periods (label, start_date, end_date) VALUES (?, ?, ?)",
            (label, start_date, end_date),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def delete_period(period_id):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM periods WHERE id = ?", (period_id,))
        conn.commit()
    finally:
        conn.close()


def copy_planned_from(source_period_id, target_period_id):
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT family, label, planned, sort_order FROM budget_items WHERE period_id = ? ORDER BY sort_order",
            (source_period_id,),
        ).fetchall()
        for r in rows:
            conn.execute(
                "INSERT INTO budget_items (period_id, family, label, planned, actual, sort_order) VALUES (?, ?, ?, ?, 0, ?)",
                (target_period_id, r["family"], r["label"], r["planned"], r["sort_order"]),
            )
        pat_rows = conn.execute(
            "SELECT family, label, planned, sort_order FROM patrimoine_items WHERE period_id = ? ORDER BY sort_order",
            (source_period_id,),
        ).fetchall()
        for r in pat_rows:
            conn.execute(
                "INSERT INTO patrimoine_items (period_id, family, label, planned, actual, sort_order) VALUES (?, ?, ?, ?, 0, ?)",
                (target_period_id, r["family"], r["label"], r["planned"], r["sort_order"]),
            )
        conn.commit()
    finally:
        conn.close()


# ── Budget Items ──

def list_budget_items(period_id):
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM budget_items WHERE period_id = ? ORDER BY family, sort_order, id",
            (period_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def add_budget_item(period_id, family, label):
    conn = get_connection()
    try:
        max_order = conn.execute(
            "SELECT COALESCE(MAX(sort_order), -1) FROM budget_items WHERE period_id = ? AND family = ?",
            (period_id, family),
        ).fetchone()[0]
        cursor = conn.execute(
            "INSERT INTO budget_items (period_id, family, label, planned, actual, sort_order) VALUES (?, ?, ?, 0, 0, ?)",
            (period_id, family, label, max_order + 1),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def update_budget_item(item_id, planned=None, actual=None, label=None):
    conn = get_connection()
    try:
        if planned is not None:
            conn.execute("UPDATE budget_items SET planned = ? WHERE id = ?", (planned, item_id))
        if actual is not None:
            conn.execute("UPDATE budget_items SET actual = ? WHERE id = ?", (actual, item_id))
        if label is not None:
            conn.execute("UPDATE budget_items SET label = ? WHERE id = ?", (label, item_id))
        conn.commit()
    finally:
        conn.close()


def delete_budget_item(item_id):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM budget_items WHERE id = ?", (item_id,))
        conn.commit()
    finally:
        conn.close()


# ── Patrimoine Items ──

def list_patrimoine_items(period_id):
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM patrimoine_items WHERE period_id = ? ORDER BY family, sort_order, id",
            (period_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def add_patrimoine_item(period_id, family, label):
    conn = get_connection()
    try:
        max_order = conn.execute(
            "SELECT COALESCE(MAX(sort_order), -1) FROM patrimoine_items WHERE period_id = ? AND family = ?",
            (period_id, family),
        ).fetchone()[0]
        cursor = conn.execute(
            "INSERT INTO patrimoine_items (period_id, family, label, planned, actual, sort_order) VALUES (?, ?, ?, 0, 0, ?)",
            (period_id, family, label, max_order + 1),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def update_patrimoine_item(item_id, planned=None, actual=None, label=None):
    conn = get_connection()
    try:
        if planned is not None:
            conn.execute("UPDATE patrimoine_items SET planned = ? WHERE id = ?", (planned, item_id))
        if actual is not None:
            conn.execute("UPDATE patrimoine_items SET actual = ? WHERE id = ?", (actual, item_id))
        if label is not None:
            conn.execute("UPDATE patrimoine_items SET label = ? WHERE id = ?", (label, item_id))
        conn.commit()
    finally:
        conn.close()


def delete_patrimoine_item(item_id):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM patrimoine_items WHERE id = ?", (item_id,))
        conn.commit()
    finally:
        conn.close()
