import os
import random
import string
import sqlite3
from datetime import datetime

from flask import Flask, send_file, jsonify, request

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "kanban.db")

STATUSES = ["todo", "in_progress", "review", "done"]


def _gen_id():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))


def _ticket_id():
    num = random.randint(1, 9999)
    return f"TK-{num:04d}"


def _get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""CREATE TABLE IF NOT EXISTS boards (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        createdAt TEXT NOT NULL
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS tickets (
        id TEXT PRIMARY KEY,
        board_id TEXT NOT NULL,
        ticket_id TEXT NOT NULL UNIQUE,
        title TEXT NOT NULL,
        description TEXT DEFAULT '',
        status TEXT NOT NULL DEFAULT 'todo',
        priority TEXT DEFAULT 'medium',
        assignee TEXT DEFAULT '',
        tags TEXT DEFAULT '',
        position INTEGER DEFAULT 0,
        createdAt TEXT NOT NULL,
        updatedAt TEXT NOT NULL,
        FOREIGN KEY (board_id) REFERENCES boards(id)
    )""")
    conn.commit()
    return conn


# ── Pages ──

@app.route("/")
def index():
    return send_file("index.html")


# ── Boards API ──

@app.route("/api/boards")
def list_boards():
    conn = _get_db()
    rows = conn.execute(
        "SELECT b.*, COUNT(t.id) as ticket_count FROM boards b "
        "LEFT JOIN tickets t ON t.board_id = b.id "
        "GROUP BY b.id ORDER BY b.createdAt DESC"
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/boards", methods=["POST"])
def create_board():
    data = request.get_json(force=True)
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "name required"}), 400
    conn = _get_db()
    bid = _gen_id()
    now = datetime.now().isoformat()
    conn.execute("INSERT INTO boards (id, name, createdAt) VALUES (?, ?, ?)", (bid, name, now))
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "id": bid})


@app.route("/api/boards/<bid>", methods=["PUT"])
def rename_board(bid):
    data = request.get_json(force=True)
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "name required"}), 400
    conn = _get_db()
    conn.execute("UPDATE boards SET name = ? WHERE id = ?", (name, bid))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.route("/api/boards/<bid>", methods=["DELETE"])
def delete_board(bid):
    conn = _get_db()
    conn.execute("DELETE FROM tickets WHERE board_id = ?", (bid,))
    conn.execute("DELETE FROM boards WHERE id = ?", (bid,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


# ── Tickets API ──

@app.route("/api/boards/<bid>/tickets")
def list_tickets(bid):
    status = request.args.get("status")
    conn = _get_db()
    if status and status in STATUSES:
        rows = conn.execute(
            "SELECT * FROM tickets WHERE board_id = ? AND status = ? ORDER BY position ASC, updatedAt DESC",
            (bid, status)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM tickets WHERE board_id = ? ORDER BY status, position ASC, updatedAt DESC",
            (bid,)
        ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/boards/<bid>/tickets", methods=["POST"])
def create_ticket(bid):
    data = request.get_json(force=True)
    title = data.get("title", "").strip()
    if not title:
        return jsonify({"error": "title required"}), 400

    conn = _get_db()

    board = conn.execute("SELECT id FROM boards WHERE id = ?", (bid,)).fetchone()
    if not board:
        conn.close()
        return jsonify({"error": "board not found"}), 404

    for _ in range(10):
        tid = _ticket_id()
        existing = conn.execute("SELECT id FROM tickets WHERE ticket_id = ?", (tid,)).fetchone()
        if not existing:
            break
    else:
        tid = f"TK-{_gen_id()}"

    max_pos = conn.execute(
        "SELECT COALESCE(MAX(position), -1) FROM tickets WHERE board_id = ? AND status = ?",
        (bid, data.get("status", "todo"))
    ).fetchone()[0]

    now = datetime.now().isoformat()
    row_id = _gen_id()
    conn.execute(
        "INSERT INTO tickets (id, board_id, ticket_id, title, description, status, priority, assignee, tags, position, createdAt, updatedAt) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            row_id, bid, tid, title,
            data.get("description", ""),
            data.get("status", "todo"),
            data.get("priority", "medium"),
            data.get("assignee", ""),
            data.get("tags", ""),
            max_pos + 1,
            now, now,
        ),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM tickets WHERE id = ?", (row_id,)).fetchone()
    conn.close()
    return jsonify(dict(row))


@app.route("/api/tickets/<tid>")
def get_ticket(tid):
    conn = _get_db()
    row = conn.execute(
        "SELECT * FROM tickets WHERE id = ? OR ticket_id = ?", (tid, tid)
    ).fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "not found"}), 404
    return jsonify(dict(row))


@app.route("/api/tickets/<tid>", methods=["PUT"])
def update_ticket(tid):
    data = request.get_json(force=True)
    conn = _get_db()
    row = conn.execute(
        "SELECT * FROM tickets WHERE id = ? OR ticket_id = ?", (tid, tid)
    ).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "not found"}), 404

    title = data.get("title", row["title"])
    description = data.get("description", row["description"])
    status = data.get("status", row["status"])
    priority = data.get("priority", row["priority"])
    assignee = data.get("assignee", row["assignee"])
    tags = data.get("tags", row["tags"])
    position = data.get("position", row["position"])
    now = datetime.now().isoformat()

    if status not in STATUSES:
        conn.close()
        return jsonify({"error": f"invalid status, must be one of: {', '.join(STATUSES)}"}), 400

    conn.execute(
        "UPDATE tickets SET title=?, description=?, status=?, priority=?, assignee=?, tags=?, position=?, updatedAt=? WHERE id=?",
        (title, description, status, priority, assignee, tags, position, now, row["id"]),
    )
    conn.commit()
    updated = conn.execute("SELECT * FROM tickets WHERE id = ?", (row["id"],)).fetchone()
    conn.close()
    return jsonify(dict(updated))


@app.route("/api/tickets/<tid>/move", methods=["POST"])
def move_ticket(tid):
    data = request.get_json(force=True)
    new_status = data.get("status", "").strip()
    if new_status not in STATUSES:
        return jsonify({"error": f"invalid status, must be one of: {', '.join(STATUSES)}"}), 400

    conn = _get_db()
    row = conn.execute(
        "SELECT * FROM tickets WHERE id = ? OR ticket_id = ?", (tid, tid)
    ).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "not found"}), 404

    new_pos = data.get("position")
    if new_pos is None:
        max_pos = conn.execute(
            "SELECT COALESCE(MAX(position), -1) FROM tickets WHERE board_id = ? AND status = ?",
            (row["board_id"], new_status)
        ).fetchone()[0]
        new_pos = max_pos + 1

    now = datetime.now().isoformat()
    conn.execute(
        "UPDATE tickets SET status=?, position=?, updatedAt=? WHERE id=?",
        (new_status, new_pos, now, row["id"]),
    )
    conn.commit()
    updated = conn.execute("SELECT * FROM tickets WHERE id = ?", (row["id"],)).fetchone()
    conn.close()
    return jsonify(dict(updated))


@app.route("/api/tickets/<tid>", methods=["DELETE"])
def delete_ticket(tid):
    conn = _get_db()
    conn.execute("DELETE FROM tickets WHERE id = ? OR ticket_id = ?", (tid, tid))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8501))
    app.run(host="0.0.0.0", port=port, debug=False)
