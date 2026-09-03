import os
import sys
import json
import glob

sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, request, jsonify, send_file
from db.database import init_db
from db.queries import (
    list_emails, mark_read, mark_all_read, get_stats,
    delete_email, delete_emails_by_sender, get_email_by_id, get_meta,
)
from blocked import add_blocked_sender, list_blocked, remove_blocked_sender
from config import GMAIL_ACCOUNTS, CONFIG_PATH

app = Flask(__name__)
init_db()


@app.route("/")
def index():
    return send_file("index.html")


# ── Emails ──

@app.route("/api/stats")
def api_stats():
    return jsonify(get_stats())


@app.route("/api/emails")
def api_emails():
    category = request.args.get("category")
    account = request.args.get("account")
    unread_only = request.args.get("unread_only") == "1"
    limit = int(request.args.get("limit", 200))
    emails = list_emails(
        category=category if category and category != "all" else None,
        account=account if account and account != "all" else None,
        unread_only=unread_only,
        limit=limit,
    )
    return jsonify(emails)


@app.route("/api/emails/<int:eid>")
def api_email(eid):
    em = get_email_by_id(eid)
    return jsonify(em) if em else ("", 404)


@app.route("/api/emails/<int:eid>/read", methods=["POST"])
def api_mark_read(eid):
    mark_read(eid)
    return jsonify({"ok": True})


@app.route("/api/emails/read-all", methods=["POST"])
def api_mark_all_read():
    mark_all_read()
    return jsonify({"ok": True})


@app.route("/api/emails/<int:eid>", methods=["DELETE"])
def api_delete_email(eid):
    delete_email(eid)
    return jsonify({"ok": True})


@app.route("/api/emails/flag-sender", methods=["POST"])
def api_flag_sender():
    data = request.get_json()
    address = data.get("address", "")
    if address:
        add_blocked_sender(address)
        delete_emails_by_sender(address)
    return jsonify({"ok": True})


# ── Sync ──

@app.route("/api/sync", methods=["POST"])
def api_sync():
    from sync import run_sync
    force_days = request.get_json().get("force_days") if request.is_json else None
    try:
        stats = run_sync(force_days=force_days)
        return jsonify({"ok": True, "stats": stats})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/sync/status")
def api_sync_status():
    result = {}
    for acc in GMAIL_ACCOUNTS:
        val = get_meta(f"last_check_{acc['name']}")
        result[acc["name"]] = {"address": acc["address"], "last_check": val}
    return jsonify(result)


@app.route("/api/sync/last")
def api_sync_last():
    sync_dir = os.path.join(os.path.dirname(__file__), "data", "syncs")
    files = sorted(glob.glob(os.path.join(sync_dir, "sync_*.json")), reverse=True)
    if not files:
        return jsonify(None)
    with open(files[0]) as f:
        return jsonify(json.load(f))


# ── Blocked ──

@app.route("/api/blocked")
def api_blocked():
    return jsonify(list_blocked())


@app.route("/api/blocked", methods=["DELETE"])
def api_unblock():
    data = request.get_json()
    remove_blocked_sender(data.get("address", ""))
    return jsonify({"ok": True})


# ── Accounts ──

@app.route("/api/accounts")
def api_accounts():
    return jsonify([{"name": a["name"], "address": a["address"]} for a in GMAIL_ACCOUNTS])


# ── Config ──

@app.route("/api/config")
def api_get_config():
    import yaml
    try:
        with open(CONFIG_PATH) as f:
            cfg = yaml.safe_load(f) or {}
    except FileNotFoundError:
        cfg = {}
    safe = {
        "openrouter_model": cfg.get("openrouter_model", "google/gemini-2.5-flash"),
        "has_api_key": bool(cfg.get("openrouter_api_key")),
        "gmail_accounts": [
            {"address": a.get("address", ""), "has_password": bool(a.get("app_password"))}
            for a in (cfg.get("gmail_accounts") or [])
        ],
    }
    return jsonify(safe)


@app.route("/api/config", methods=["POST"])
def api_save_config():
    import yaml
    data = request.get_json()
    try:
        with open(CONFIG_PATH) as f:
            cfg = yaml.safe_load(f) or {}
    except FileNotFoundError:
        cfg = {}

    if "openrouter_api_key" in data:
        cfg["openrouter_api_key"] = data["openrouter_api_key"]
    if "openrouter_model" in data:
        cfg["openrouter_model"] = data["openrouter_model"]
    if "gmail_accounts" in data:
        cfg["gmail_accounts"] = data["gmail_accounts"]

    with open(CONFIG_PATH, "w") as f:
        yaml.dump(cfg, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8501, debug=False)
