import glob
import os
import re
from flask import Flask, send_file, jsonify, request
import yaml

app = Flask(__name__)
TOOLS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools")
DOCKER_MODE = os.environ.get("WORKSPACE_DOCKER", "") == "1"
DOCKER_NETWORK = os.environ.get("DOCKER_NETWORK", "workspace_default")
COMPOSE_PROJECT = os.environ.get("COMPOSE_PROJECT", "workspace")

if DOCKER_MODE:
    import docker
    docker_client = docker.from_env()


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _read_manifests() -> list[dict]:
    tools = []
    for manifest_path in sorted(glob.glob(os.path.join(TOOLS_DIR, "*", "tool.yaml"))):
        with open(manifest_path) as f:
            manifest = yaml.safe_load(f) or {}
        slug = manifest.get("slug") or _slugify(manifest.get("name", ""))
        if not slug:
            continue
        tools.append({
            "name": manifest.get("name", slug),
            "slug": slug,
            "description": manifest.get("description", ""),
            "type": manifest.get("type", "streamlit"),
            "default": manifest.get("default", False),
            "dir": os.path.basename(os.path.dirname(manifest_path)),
            "volumes": manifest.get("volumes", []),
            "mcp": manifest.get("mcp", {}),
        })
    return tools


def _container_name(slug: str) -> str:
    return f"{COMPOSE_PROJECT}-{slug}-1"


def _is_running(slug: str) -> bool:
    if not DOCKER_MODE:
        return False
    try:
        c = docker_client.containers.get(_container_name(slug))
        return c.status == "running"
    except docker.errors.NotFound:
        return False


def _tool_url(slug: str, manifest_path: str = "") -> str:
    if DOCKER_MODE:
        return f"/tools/{slug}/"
    config_path = os.path.normpath(
        os.path.join(TOOLS_DIR, "..", "config.yaml")
    )
    try:
        with open(config_path) as f:
            cfg = yaml.safe_load(f) or {}
        match = next(
            (t for t in cfg.get("tools", [])
             if _slugify(t["name"]) == slug),
            None,
        )
        return match["url"] if match else "http://localhost:8501"
    except FileNotFoundError:
        return "http://localhost:8501"


@app.route("/")
def index():
    return send_file("index.html")


@app.route("/api/mcp")
def api_mcp():
    tools = []
    for t in _read_manifests():
        actions = t.get("mcp", {}).get("actions", [])
        for action in actions:
            tools.append({
                "name": f"{t['slug']}__{action['name']}",
                "tool": t["name"],
                "description": action.get("description", ""),
                "read": action.get("read", True),
            })
    return jsonify({
        "sse_url": "/mcp/sse",
        "tools_count": len(tools),
        "tools": tools,
    })


@app.route("/api/tools")
def api_tools():
    result = []
    for t in _read_manifests():
        if _is_running(t["slug"]):
            result.append({
                "name": t["name"],
                "slug": t["slug"],
                "description": t["description"],
                "url": _tool_url(t["slug"]),
            })
    return jsonify(result)


@app.route("/api/marketplace")
def api_marketplace():
    result = []
    for t in _read_manifests():
        result.append({
            "name": t["name"],
            "slug": t["slug"],
            "description": t["description"],
            "installed": _is_running(t["slug"]),
        })
    return jsonify(result)


@app.route("/api/install/<slug>", methods=["POST"])
def install_tool(slug):
    if not DOCKER_MODE:
        return jsonify({"error": "install only available in Docker mode"}), 400

    manifests = {t["slug"]: t for t in _read_manifests()}
    tool = manifests.get(slug)
    if not tool:
        return jsonify({"error": "tool not found"}), 404

    container_name = _container_name(slug)

    try:
        existing = docker_client.containers.get(container_name)
        if existing.status == "running":
            return jsonify({"status": "already_running"})
        existing.start()
        return jsonify({"status": "started"})
    except docker.errors.NotFound:
        pass

    image_name = f"{COMPOSE_PROJECT}-{slug}"
    try:
        docker_client.images.get(image_name)
    except docker.errors.ImageNotFound:
        build_path = os.path.join(TOOLS_DIR, tool["dir"])
        try:
            docker_client.images.build(path=build_path, tag=image_name, rm=True)
        except Exception as e:
            return jsonify({"error": f"build failed: {e}"}), 500

    container = docker_client.containers.run(
        image_name,
        name=container_name,
        detach=True,
        restart_policy={"Name": "unless-stopped"},
    )

    network = docker_client.networks.get(DOCKER_NETWORK)
    network.connect(container, aliases=[slug])

    return jsonify({"status": "installed"})


@app.route("/api/uninstall/<slug>", methods=["POST"])
def uninstall_tool(slug):
    if not DOCKER_MODE:
        return jsonify({"error": "uninstall only available in Docker mode"}), 400

    manifests = {t["slug"]: t for t in _read_manifests()}
    tool = manifests.get(slug)
    if not tool:
        return jsonify({"error": "tool not found"}), 404

    container_name = _container_name(slug)
    try:
        container = docker_client.containers.get(container_name)
        container.stop(timeout=5)
        container.remove()
        return jsonify({"status": "uninstalled"})
    except docker.errors.NotFound:
        return jsonify({"status": "not_installed"})


# ── Agent ─────────────────────────────────────

from agent import get_or_create_session, process_message, confirm_action


def _agent_config() -> dict:
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agent_config.yaml")
    try:
        with open(config_path) as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}


@app.route("/api/agent/chat", methods=["POST"])
def api_agent_chat():
    data = request.get_json()
    message = data.get("message", "")
    session_id = data.get("session_id")
    if not message:
        return jsonify({"error": "no message"}), 400
    config = _agent_config()
    if not config.get("api_key"):
        return jsonify({"error": "agent not configured — add api_key to agent_config.yaml"}), 400
    result = process_message(session_id, message, config)
    return jsonify(result)


@app.route("/api/agent/confirm", methods=["POST"])
def api_agent_confirm():
    data = request.get_json()
    session_id = data.get("session_id")
    approved = data.get("approved", False)
    if not session_id:
        return jsonify({"error": "no session_id"}), 400
    config = _agent_config()
    result = confirm_action(session_id, approved, config)
    return jsonify(result)


@app.route("/api/agent/config")
def api_agent_get_config():
    cfg = _agent_config()
    return jsonify({
        "has_api_key": bool(cfg.get("api_key")),
        "model": cfg.get("model", "deepseek/deepseek-chat-v3"),
        "base_url": cfg.get("base_url", "https://openrouter.ai/api/v1"),
    })


@app.route("/api/agent/config", methods=["POST"])
def api_agent_save_config():
    data = request.get_json()
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agent_config.yaml")
    try:
        with open(config_path) as f:
            cfg = yaml.safe_load(f) or {}
    except FileNotFoundError:
        cfg = {}
    if "api_key" in data:
        cfg["api_key"] = data["api_key"]
    if "model" in data:
        cfg["model"] = data["model"]
    if "base_url" in data:
        cfg["base_url"] = data["base_url"]
    with open(config_path, "w") as f:
        yaml.dump(cfg, f, default_flow_style=False)
    return jsonify({"ok": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8500))
    app.run(host="0.0.0.0", port=port, debug=False)
