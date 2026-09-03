import glob
import inspect
import json
import os
import re

import yaml
import httpx
from mcp.server import MCPServer

TOOLS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools")


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _discover() -> dict[str, dict]:
    registry = {}
    for manifest_path in sorted(glob.glob(os.path.join(TOOLS_DIR, "*", "tool.yaml"))):
        with open(manifest_path) as f:
            manifest = yaml.safe_load(f) or {}
        slug = manifest.get("slug") or _slugify(manifest.get("name", ""))
        if not slug:
            continue
        actions = manifest.get("mcp", {}).get("actions", [])
        if not actions:
            continue
        registry[slug] = {
            "name": manifest.get("name", slug),
            "slug": slug,
            "description": manifest.get("description", ""),
            "actions": actions,
        }
    return registry


def _resolve_path(path_template: str, arguments: dict) -> tuple[str, dict]:
    resolved = path_template
    body_args = dict(arguments)
    for match in re.finditer(r"\{(\w+)\}", path_template):
        param_name = match.group(1)
        if param_name in body_args:
            resolved = resolved.replace(f"{{{param_name}}}", str(body_args.pop(param_name)))
    return resolved, body_args


def _call_api(slug: str, action: dict, arguments: dict) -> str:
    method = action.get("method", "GET").upper()
    path, remaining = _resolve_path(action["path"], arguments)
    url = f"http://{slug}:8501{path}"

    with httpx.Client(timeout=30) as client:
        if method == "GET":
            query = {k: str(v) for k, v in remaining.items() if v is not None}
            resp = client.get(url, params=query)
        elif method == "DELETE":
            resp = client.request("DELETE", url, json=remaining if remaining else None)
        else:
            resp = client.request(method, url, json=remaining)

    if resp.headers.get("content-type", "").startswith("application/json"):
        return json.dumps(resp.json(), indent=2)
    return resp.text


def _make_handler(slug: str, action: dict):
    params = action.get("params", [])
    sig_params = []
    annotations = {"return": str}
    for p in params:
        py_type = {"string": str, "integer": int, "number": float, "boolean": bool}.get(
            p.get("type", "string"), str
        )
        default = inspect.Parameter.empty if p.get("required") else None
        sig_params.append(inspect.Parameter(
            p["name"], inspect.Parameter.KEYWORD_ONLY, default=default, annotation=py_type,
        ))
        annotations[p["name"]] = py_type

    def handler(**kwargs) -> str:
        return _call_api(slug, action, kwargs)

    handler.__signature__ = inspect.Signature(sig_params)
    handler.__annotations__ = annotations
    handler.__doc__ = action.get("description", "")
    return handler


def create_mcp_server() -> MCPServer:
    server = MCPServer("workspace")
    registry = _discover()
    loaded_slugs: set[str] = set()

    def _sync_tools():
        current = {t.name for t in server._tool_manager.list_tools()}
        keep = {"list_available_tools", "load_tools", "unload_tools"}
        for name in current - keep:
            server.remove_tool(name)
        for slug in loaded_slugs:
            tool_info = registry.get(slug)
            if not tool_info:
                continue
            for action in tool_info["actions"]:
                full_name = f"{slug}__{action['name']}"
                if full_name not in current:
                    desc = f"[{tool_info['name']}] {action['description']}"
                    if not action.get("read", True):
                        desc += " (write)"
                    handler = _make_handler(slug, action)
                    server.add_tool(handler, name=full_name, description=desc)

    def list_available_tools() -> str:
        """List all available workspace tools. Call this first to see what tools are available, then use load_tools to activate the ones you need."""
        result = []
        for slug, info in registry.items():
            read_count = sum(1 for a in info["actions"] if a.get("read", True))
            write_count = len(info["actions"]) - read_count
            result.append({
                "slug": info["slug"],
                "name": info["name"],
                "description": info["description"],
                "actions": len(info["actions"]),
                "read_actions": read_count,
                "write_actions": write_count,
                "loaded": slug in loaded_slugs,
                "action_names": [a["name"] for a in info["actions"]],
            })
        return json.dumps(result, indent=2)

    def load_tools(*, tools: str) -> str:
        """Load one or more tools by slug (comma-separated). Their actions become available as callable tools. Example: load_tools(tools="calendar,todolist")"""
        slugs = [s.strip() for s in tools.split(",") if s.strip()]
        added = []
        not_found = []
        for slug in slugs:
            if slug in registry:
                loaded_slugs.add(slug)
                added.append(slug)
            else:
                not_found.append(slug)
        _sync_tools()
        msg = {"loaded": added, "total_actions": sum(len(registry[s]["actions"]) for s in loaded_slugs)}
        if not_found:
            msg["not_found"] = not_found
            msg["available"] = list(registry.keys())
        return json.dumps(msg, indent=2)

    def unload_tools(*, tools: str) -> str:
        """Unload one or more tools by slug (comma-separated). Their actions are removed. Example: unload_tools(tools="calendar")"""
        slugs = [s.strip() for s in tools.split(",") if s.strip()]
        removed = []
        for slug in slugs:
            if slug in loaded_slugs:
                loaded_slugs.discard(slug)
                removed.append(slug)
        _sync_tools()
        return json.dumps({"unloaded": removed, "still_loaded": list(loaded_slugs)}, indent=2)

    server.add_tool(list_available_tools)
    server.add_tool(load_tools)
    server.add_tool(unload_tools)

    return server


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("MCP_PORT", 8510))
    server = create_mcp_server()
    app = server.sse_app(host="0.0.0.0")
    uvicorn.run(app, host="0.0.0.0", port=port)
