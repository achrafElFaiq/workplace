from flask import Flask, send_file, jsonify, request
from db.database import init_db
from db.queries import (
    get_events_for_month, get_events_for_range, get_upcoming_events,
    get_event, add_event, update_event, delete_event,
)
from config import CATEGORIES, CATEGORY_COLORS

app = Flask(__name__)
init_db()


@app.route("/")
def index():
    return send_file("index.html")


@app.route("/api/config")
def api_config():
    return jsonify({
        "categories": CATEGORIES,
        "colors": CATEGORY_COLORS,
    })


@app.route("/api/events/month")
def api_events_month():
    year = int(request.args.get("year"))
    month = int(request.args.get("month"))
    return jsonify(get_events_for_month(year, month))


@app.route("/api/events/range")
def api_events_range():
    return jsonify(get_events_for_range(
        request.args.get("start"),
        request.args.get("end"),
    ))


@app.route("/api/events/upcoming")
def api_events_upcoming():
    days = int(request.args.get("days", 14))
    return jsonify(get_upcoming_events(days))


@app.route("/api/events/<int:eid>")
def api_event(eid):
    e = get_event(eid)
    if not e:
        return jsonify({"error": "not found"}), 404
    return jsonify(e)


@app.route("/api/events", methods=["POST"])
def api_add_event():
    d = request.json
    eid = add_event(
        title=d["title"],
        date=d["date"],
        time=d.get("time"),
        end_time=d.get("end_time"),
        category=d.get("category", "personal"),
        description=d.get("description"),
        all_day=d.get("all_day", False),
    )
    return jsonify({"id": eid})


@app.route("/api/events/<int:eid>", methods=["PUT"])
def api_update_event(eid):
    d = request.json
    update_event(
        event_id=eid,
        title=d["title"],
        date=d["date"],
        time=d.get("time"),
        end_time=d.get("end_time"),
        category=d.get("category", "personal"),
        description=d.get("description"),
        all_day=d.get("all_day", False),
    )
    return jsonify({"ok": True})


@app.route("/api/events/<int:eid>", methods=["DELETE"])
def api_delete_event(eid):
    delete_event(eid)
    return jsonify({"ok": True})


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8501))
    app.run(host="0.0.0.0", port=port, debug=False)
