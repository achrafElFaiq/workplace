import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, request, jsonify, send_file
from db.database import init_db
from db.queries import (
    get_setting, set_setting,
    list_periods, get_period, create_period, delete_period, copy_planned_from,
    list_budget_items, add_budget_item, update_budget_item, delete_budget_item,
    list_patrimoine_items, add_patrimoine_item, update_patrimoine_item, delete_patrimoine_item,
)

app = Flask(__name__)
init_db()


@app.route("/")
def index():
    return send_file("index.html")


# ── Settings ──

@app.route("/api/settings")
def api_get_settings():
    cycle_day = get_setting("cycle_start_day", "1")
    return jsonify({"cycle_start_day": int(cycle_day)})


@app.route("/api/settings", methods=["POST"])
def api_save_settings():
    data = request.get_json()
    if "cycle_start_day" in data:
        set_setting("cycle_start_day", data["cycle_start_day"])
    return jsonify({"ok": True})


# ── Periods ──

@app.route("/api/periods")
def api_list_periods():
    return jsonify(list_periods())


@app.route("/api/periods", methods=["POST"])
def api_create_period():
    data = request.get_json()
    pid = create_period(data["label"], data["start_date"], data["end_date"])
    if data.get("copy_from"):
        copy_planned_from(data["copy_from"], pid)
    return jsonify({"ok": True, "id": pid})


@app.route("/api/periods/<int:pid>")
def api_get_period(pid):
    p = get_period(pid)
    return jsonify(p) if p else ("", 404)


@app.route("/api/periods/<int:pid>", methods=["DELETE"])
def api_delete_period(pid):
    delete_period(pid)
    return jsonify({"ok": True})


# ── Budget Items ──

@app.route("/api/periods/<int:pid>/budget")
def api_budget_items(pid):
    return jsonify(list_budget_items(pid))


@app.route("/api/periods/<int:pid>/budget", methods=["POST"])
def api_add_budget_item(pid):
    data = request.get_json()
    item_id = add_budget_item(pid, data["family"], data["label"])
    return jsonify({"ok": True, "id": item_id})


@app.route("/api/budget/<int:item_id>", methods=["PUT"])
def api_update_budget_item(item_id):
    data = request.get_json()
    update_budget_item(
        item_id,
        planned=data.get("planned"),
        actual=data.get("actual"),
        label=data.get("label"),
    )
    return jsonify({"ok": True})


@app.route("/api/budget/<int:item_id>", methods=["DELETE"])
def api_delete_budget_item(item_id):
    delete_budget_item(item_id)
    return jsonify({"ok": True})


# ── Patrimoine Items ──

@app.route("/api/periods/<int:pid>/patrimoine")
def api_patrimoine_items(pid):
    return jsonify(list_patrimoine_items(pid))


@app.route("/api/periods/<int:pid>/patrimoine", methods=["POST"])
def api_add_patrimoine_item(pid):
    data = request.get_json()
    item_id = add_patrimoine_item(pid, data["family"], data["label"])
    return jsonify({"ok": True, "id": item_id})


@app.route("/api/patrimoine/<int:item_id>", methods=["PUT"])
def api_update_patrimoine_item(item_id):
    data = request.get_json()
    update_patrimoine_item(
        item_id,
        planned=data.get("planned"),
        actual=data.get("actual"),
        label=data.get("label"),
    )
    return jsonify({"ok": True})


@app.route("/api/patrimoine/<int:item_id>", methods=["DELETE"])
def api_delete_patrimoine_item(item_id):
    delete_patrimoine_item(item_id)
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8501, debug=False)
