import os
import random
import string
import sqlite3
from datetime import datetime

from flask import Flask, send_file, jsonify, request

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "notes.db")


def _gen_id():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))


def _get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""CREATE TABLE IF NOT EXISTS projects (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        createdAt TEXT NOT NULL
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS notes (
        id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL,
        title TEXT NOT NULL,
        content TEXT DEFAULT '',
        createdAt TEXT NOT NULL,
        updatedAt TEXT NOT NULL,
        FOREIGN KEY (project_id) REFERENCES projects(id)
    )""")
    conn.commit()
    return conn


# ── Pages ──

@app.route("/")
def index():
    return send_file("index.html")


# ── Projects API ──

@app.route("/api/projects")
def list_projects():
    conn = _get_db()
    rows = conn.execute(
        "SELECT p.*, COUNT(n.id) as note_count FROM projects p "
        "LEFT JOIN notes n ON n.project_id = p.id "
        "GROUP BY p.id ORDER BY p.createdAt DESC"
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/projects", methods=["POST"])
def create_project():
    data = request.get_json(force=True)
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "name required"}), 400
    conn = _get_db()
    pid = _gen_id()
    now = datetime.now().isoformat()
    conn.execute("INSERT INTO projects (id, name, createdAt) VALUES (?, ?, ?)", (pid, name, now))
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "id": pid})


@app.route("/api/projects/<pid>", methods=["PUT"])
def rename_project(pid):
    data = request.get_json(force=True)
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "name required"}), 400
    conn = _get_db()
    conn.execute("UPDATE projects SET name = ? WHERE id = ?", (name, pid))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.route("/api/projects/<pid>", methods=["DELETE"])
def delete_project(pid):
    conn = _get_db()
    conn.execute("DELETE FROM notes WHERE project_id = ?", (pid,))
    conn.execute("DELETE FROM projects WHERE id = ?", (pid,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


# ── Notes API ──

@app.route("/api/projects/<pid>/notes")
def list_notes(pid):
    conn = _get_db()
    rows = conn.execute(
        "SELECT id, project_id, title, createdAt, updatedAt, LENGTH(content) as content_length "
        "FROM notes WHERE project_id = ? ORDER BY updatedAt DESC", (pid,)
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/notes/<nid>")
def get_note(nid):
    conn = _get_db()
    row = conn.execute("SELECT * FROM notes WHERE id = ?", (nid,)).fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "not found"}), 404
    return jsonify(dict(row))


@app.route("/api/projects/<pid>/notes", methods=["POST"])
def create_note(pid):
    data = request.get_json(force=True)
    title = data.get("title", "").strip()
    if not title:
        return jsonify({"error": "title required"}), 400
    content = data.get("content", "")
    conn = _get_db()
    proj = conn.execute("SELECT id FROM projects WHERE id = ?", (pid,)).fetchone()
    if not proj:
        conn.close()
        return jsonify({"error": "project not found"}), 404
    nid = _gen_id()
    now = datetime.now().isoformat()
    conn.execute(
        "INSERT INTO notes (id, project_id, title, content, createdAt, updatedAt) VALUES (?, ?, ?, ?, ?, ?)",
        (nid, pid, title, content, now, now),
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "id": nid})


@app.route("/api/notes/<nid>", methods=["PUT"])
def update_note(nid):
    data = request.get_json(force=True)
    conn = _get_db()
    row = conn.execute("SELECT * FROM notes WHERE id = ?", (nid,)).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "not found"}), 404
    title = data.get("title", row["title"])
    content = data.get("content", row["content"])
    now = datetime.now().isoformat()
    conn.execute("UPDATE notes SET title = ?, content = ?, updatedAt = ? WHERE id = ?", (title, content, now, nid))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.route("/api/notes/<nid>", methods=["DELETE"])
def delete_note(nid):
    conn = _get_db()
    conn.execute("DELETE FROM notes WHERE id = ?", (nid,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8501))
    app.run(host="0.0.0.0", port=port, debug=False)
