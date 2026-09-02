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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8500))
    app.run(host="0.0.0.0", port=port, debug=False)
