import json
import os
import sqlite3
from datetime import datetime

from flask import Flask, send_file, jsonify, request

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "tasks.db")


def _get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""CREATE TABLE IF NOT EXISTS projects (
        id TEXT PRIMARY KEY, name TEXT NOT NULL, emoji TEXT DEFAULT '>_',
        color TEXT DEFAULT '#2d6a4f', deadline TEXT, archived INTEGER DEFAULT 0,
        createdAt TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY, project_id TEXT NOT NULL, title TEXT NOT NULL,
        done INTEGER DEFAULT 0, dueDate TEXT, priority TEXT, doneAt TEXT,
        createdAt TEXT,
        FOREIGN KEY (project_id) REFERENCES projects(id))""")
    conn.commit()
    return conn


@app.route("/")
def index():
    return send_file("dashboard.html")


@app.route("/api/data")
def get_data():
    conn = _get_db()
    projects = []
    for p in conn.execute("SELECT * FROM projects").fetchall():
        proj = dict(p)
        proj["archived"] = bool(proj["archived"])
        rows = conn.execute(
            "SELECT id, title, done, dueDate, priority, doneAt, createdAt FROM tasks WHERE project_id = ?",
            (p["id"],),
        ).fetchall()
        proj["tasks"] = [{**dict(t), "done": bool(t["done"])} for t in rows]
        projects.append(proj)
    conn.close()
    return jsonify({"projects": projects})


@app.route("/api/data", methods=["POST"])
def save_data():
    data = request.get_json(force=True)
    projects = data.get("projects", [])
    conn = _get_db()
    conn.execute("DELETE FROM tasks")
    conn.execute("DELETE FROM projects")
    for p in projects:
        conn.execute(
            "INSERT INTO projects (id,name,emoji,color,deadline,archived,createdAt) VALUES (?,?,?,?,?,?,?)",
            (p["id"], p["name"], p.get("emoji", ">_"), p.get("color", "#2d6a4f"),
             p.get("deadline"), int(bool(p.get("archived", False))),
             p.get("createdAt", datetime.now().isoformat())),
        )
        for t in p.get("tasks", []):
            conn.execute(
                "INSERT INTO tasks (id,project_id,title,done,dueDate,priority,doneAt,createdAt) VALUES (?,?,?,?,?,?,?,?)",
                (t["id"], p["id"], t["title"], int(bool(t.get("done", False))),
                 t.get("dueDate"), t.get("priority"), t.get("doneAt"),
                 t.get("createdAt", datetime.now().isoformat())),
            )
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


def _gen_id():
    import random, string
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))


@app.route("/api/projects", methods=["POST"])
def add_project():
    data = request.get_json(force=True)
    conn = _get_db()
    pid = _gen_id()
    conn.execute(
        "INSERT INTO projects (id,name,emoji,color,deadline,archived,createdAt) VALUES (?,?,?,?,?,0,?)",
        (pid, data["name"], data.get("emoji", ">_"), data.get("color", "#2d6a4f"),
         data.get("deadline"), datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "id": pid})


@app.route("/api/projects/<project_id>/tasks", methods=["POST"])
def add_task(project_id):
    data = request.get_json(force=True)
    conn = _get_db()
    p = conn.execute("SELECT id FROM projects WHERE id=?", (project_id,)).fetchone()
    if not p:
        conn.close()
        return jsonify({"error": "project not found"}), 404
    tid = _gen_id()
    conn.execute(
        "INSERT INTO tasks (id,project_id,title,done,dueDate,priority,doneAt,createdAt) VALUES (?,?,?,0,?,?,NULL,?)",
        (tid, project_id, data["title"], data.get("dueDate"), data.get("priority"),
         datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "id": tid})


@app.route("/api/tasks/<task_id>/toggle", methods=["POST"])
def toggle_task(task_id):
    conn = _get_db()
    t = conn.execute("SELECT done FROM tasks WHERE id=?", (task_id,)).fetchone()
    if not t:
        conn.close()
        return jsonify({"error": "task not found"}), 404
    new_done = 0 if t["done"] else 1
    done_at = datetime.now().isoformat() if new_done else None
    conn.execute("UPDATE tasks SET done=?, doneAt=? WHERE id=?", (new_done, done_at, task_id))
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "done": bool(new_done)})


@app.route("/api/tasks/<task_id>", methods=["DELETE"])
def delete_task(task_id):
    conn = _get_db()
    conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.route("/api/projects/<project_id>/archive", methods=["POST"])
def archive_project(project_id):
    conn = _get_db()
    p = conn.execute("SELECT archived FROM projects WHERE id=?", (project_id,)).fetchone()
    if not p:
        conn.close()
        return jsonify({"error": "project not found"}), 404
    new_val = 0 if p["archived"] else 1
    conn.execute("UPDATE projects SET archived=? WHERE id=?", (new_val, project_id))
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "archived": bool(new_val)})


@app.route("/api/projects/<project_id>", methods=["DELETE"])
def delete_project(project_id):
    conn = _get_db()
    conn.execute("DELETE FROM tasks WHERE project_id=?", (project_id,))
    conn.execute("DELETE FROM projects WHERE id=?", (project_id,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8502))
    app.run(host="0.0.0.0", port=port, debug=False)
