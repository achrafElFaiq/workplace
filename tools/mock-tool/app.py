import os
from flask import Flask, send_file

app = Flask(__name__)


@app.route("/")
def index():
    return send_file("index.html")


@app.route("/api/ping")
def ping():
    return {"status": "ok", "tool": "mock-tool"}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8501))
    app.run(host="0.0.0.0", port=port, debug=False)
