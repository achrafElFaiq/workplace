import glob
import os
import re
import json
from flask import Flask, send_file, jsonify
import yaml

app = Flask(__name__)
TOOLS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools")
DOCKER_MODE = os.environ.get("WORKSPACE_DOCKER", "") == "1"


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _discover_tools() -> list[dict]:
    tools = []
    for manifest_path in sorted(glob.glob(os.path.join(TOOLS_DIR, "*", "tool.yaml"))):
        with open(manifest_path) as f:
            manifest = yaml.safe_load(f) or {}
        slug = manifest.get("slug") or _slugify(manifest.get("name", ""))
        if not slug:
            continue
        tool = {
            "name": manifest.get("name", slug),
            "slug": slug,
            "description": manifest.get("description", ""),
        }
        if DOCKER_MODE:
            tool["url"] = f"/tools/{slug}/"
        else:
            config_path = os.path.normpath(
                os.path.join(os.path.dirname(manifest_path), "..", "..", "config.yaml")
            )
            try:
                with open(config_path) as f:
                    cfg = yaml.safe_load(f) or {}
                tool_dir = os.path.basename(os.path.dirname(manifest_path))
                match = next(
                    (t for t in cfg.get("tools", [])
                     if _slugify(t["name"]) == slug
                     or t.get("path", "").rstrip("/").endswith(f"/{tool_dir}")),
                    None,
                )
                tool["url"] = match["url"] if match else "http://localhost:8501"
            except FileNotFoundError:
                tool["url"] = "http://localhost:8501"
        tools.append(tool)
    return tools


@app.route("/")
def index():
    return send_file("index.html")


@app.route("/api/tools")
def api_tools():
    return jsonify(_discover_tools())


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8500))
    app.run(host="0.0.0.0", port=port, debug=False)
