import glob
import json
import os
import re
import uuid
from datetime import datetime, timezone

import yaml
import httpx

TOOLS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools")

sessions: dict[str, dict] = {}


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _load_registry() -> dict[str, dict]:
    registry = {}
    for path in sorted(glob.glob(os.path.join(TOOLS_DIR, "*", "tool.yaml"))):
        with open(path) as f:
            m = yaml.safe_load(f) or {}
        slug = m.get("slug") or _slugify(m.get("name", ""))
        if not slug:
            continue
        actions = m.get("mcp", {}).get("actions", [])
        if not actions:
            continue
        registry[slug] = {
            "name": m.get("name", slug),
            "slug": slug,
            "description": m.get("description", ""),
            "actions": {a["name"]: a for a in actions},
        }
    return registry


REGISTRY = _load_registry()

SYSTEM_PROMPT = """You are a workspace assistant. You help the user manage their tools: calendar, emails, tasks, job applications, and budget.

Current date and time: {now}

Available tools you can discover:
{tool_list}

Start by calling list_available_tools to see what's available, then load_tools to activate what you need.

Rules:
- Be concise and helpful
- When you read data, present it clearly
- Before any write action, briefly say what you're about to change (e.g. "I'll add 'Visit grandma' to Voyage Italie"). The user sees a confirmation card with the action — keep the intent clear
- Use the tools to answer questions, don't guess
- Always use the current date/time above as reference, never guess the date"""


def _build_tool_list() -> str:
    lines = []
    for slug, info in REGISTRY.items():
        lines.append(f"- {info['name']} ({slug}): {info['description']} — {len(info['actions'])} actions")
    return "\n".join(lines)


def _meta_tools_schema() -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": "list_available_tools",
                "description": "List all available workspace tools and their actions. Call this first.",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "load_tools",
                "description": "Load tools by slug (comma-separated) to make their actions available. Example: load_tools(tools='calendar,todolist')",
                "parameters": {
                    "type": "object",
                    "properties": {"tools": {"type": "string", "description": "Comma-separated tool slugs"}},
                    "required": ["tools"],
                },
            },
        },
    ]


def _action_to_schema(slug: str, action: dict) -> dict:
    props = {}
    required = []
    for p in action.get("params", []):
        props[p["name"]] = {
            "type": p.get("type", "string"),
            "description": p.get("description", ""),
        }
        if p.get("required"):
            required.append(p["name"])

    full_name = f"{slug}__{action['name']}"
    desc = action["description"]
    if not action.get("read", True):
        desc += " [WRITE — requires user confirmation]"

    return {
        "type": "function",
        "function": {
            "name": full_name,
            "description": desc,
            "parameters": {"type": "object", "properties": props, "required": required},
        },
    }


def _get_tool_schemas(loaded_slugs: set[str]) -> list[dict]:
    schemas = list(_meta_tools_schema())
    for slug in loaded_slugs:
        info = REGISTRY.get(slug)
        if not info:
            continue
        for action in info["actions"].values():
            schemas.append(_action_to_schema(slug, action))
    return schemas


def _resolve_path(template: str, args: dict) -> tuple[str, dict]:
    resolved = template
    remaining = dict(args)
    for match in re.finditer(r"\{(\w+)\}", template):
        name = match.group(1)
        if name in remaining:
            resolved = resolved.replace(f"{{{name}}}", str(remaining.pop(name)))
    return resolved, remaining


def _exec_api(slug: str, action: dict, arguments: dict) -> str:
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


def _exec_meta_tool(name: str, args: dict, session: dict) -> str:
    if name == "list_available_tools":
        result = []
        for slug, info in REGISTRY.items():
            result.append({
                "slug": slug,
                "name": info["name"],
                "description": info["description"],
                "actions": len(info["actions"]),
                "loaded": slug in session["loaded"],
                "action_names": list(info["actions"].keys()),
            })
        return json.dumps(result, indent=2)

    if name == "load_tools":
        slugs = [s.strip() for s in args.get("tools", "").split(",") if s.strip()]
        loaded = []
        for s in slugs:
            if s in REGISTRY:
                session["loaded"].add(s)
                loaded.append(s)
        return json.dumps({"loaded": loaded, "available_actions": sum(
            len(REGISTRY[s]["actions"]) for s in session["loaded"]
        )})

    return json.dumps({"error": f"unknown meta tool: {name}"})


def _call_llm(messages: list[dict], tools: list[dict], config: dict) -> dict:
    api_key = config.get("api_key", "")
    model = config.get("model", "deepseek/deepseek-chat-v3")
    base_url = config.get("base_url", "https://openrouter.ai/api/v1")

    with httpx.Client(timeout=60) as client:
        resp = client.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": messages,
                "tools": tools if tools else None,
                "tool_choice": "auto",
            },
        )
    return resp.json()


def get_or_create_session(session_id: str = None) -> tuple[str, dict]:
    if session_id and session_id in sessions:
        return session_id, sessions[session_id]
    sid = session_id or str(uuid.uuid4())[:8]
    now = datetime.now().strftime("%A, %B %d, %Y at %H:%M")
    sessions[sid] = {
        "messages": [{"role": "system", "content": SYSTEM_PROMPT.format(
            tool_list=_build_tool_list(), now=now,
        )}],
        "loaded": set(),
        "pending_confirm": None,
    }
    return sid, sessions[sid]


def process_message(session_id: str, user_message: str, config: dict) -> dict:
    sid, session = get_or_create_session(session_id)

    session["messages"].append({"role": "user", "content": user_message})

    max_iterations = 15
    for _ in range(max_iterations):
        tools_schema = _get_tool_schemas(session["loaded"])
        llm_resp = _call_llm(session["messages"], tools_schema, config)

        if "error" in llm_resp:
            return {"session_id": sid, "type": "error", "content": str(llm_resp["error"])}

        choice = llm_resp["choices"][0]
        msg = choice["message"]
        session["messages"].append(msg)

        if not msg.get("tool_calls"):
            return {"session_id": sid, "type": "text", "content": msg.get("content", "")}

        for tc in msg["tool_calls"]:
            fn_name = tc["function"]["name"]
            fn_args = json.loads(tc["function"]["arguments"]) if tc["function"].get("arguments") else {}

            if fn_name in ("list_available_tools", "load_tools"):
                result = _exec_meta_tool(fn_name, fn_args, session)
                session["messages"].append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result,
                })
                continue

            parts = fn_name.split("__", 1)
            if len(parts) != 2:
                session["messages"].append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": json.dumps({"error": f"unknown tool: {fn_name}"}),
                })
                continue

            slug, action_name = parts
            info = REGISTRY.get(slug)
            if not info or action_name not in info["actions"]:
                session["messages"].append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": json.dumps({"error": f"tool not found: {fn_name}"}),
                })
                continue

            action = info["actions"][action_name]

            if action.get("read", True):
                result = _exec_api(slug, action, fn_args)
                session["messages"].append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result,
                })
            else:
                session["pending_confirm"] = {
                    "tool_call_id": tc["id"],
                    "tool_call": tc,
                    "slug": slug,
                    "action_name": action_name,
                    "action": action,
                    "args": fn_args,
                    "description": action["description"],
                    "tool_name": info["name"],
                }
                return {
                    "session_id": sid,
                    "type": "confirm",
                    "tool": info["name"],
                    "action": action_name,
                    "description": action["description"],
                    "args": fn_args,
                }

    return {"session_id": sid, "type": "error", "content": "too many tool calls, stopping"}


def confirm_action(session_id: str, approved: bool, config: dict) -> dict:
    session = sessions.get(session_id)
    if not session or not session["pending_confirm"]:
        return {"session_id": session_id, "type": "error", "content": "nothing to confirm"}

    pending = session["pending_confirm"]
    session["pending_confirm"] = None

    if approved:
        result = _exec_api(pending["slug"], pending["action"], pending["args"])
        session["messages"].append({
            "role": "tool",
            "tool_call_id": pending["tool_call_id"],
            "content": result,
        })
    else:
        session["messages"].append({
            "role": "tool",
            "tool_call_id": pending["tool_call_id"],
            "content": json.dumps({"error": "user denied this action"}),
        })

    tools_schema = _get_tool_schemas(session["loaded"])
    llm_resp = _call_llm(session["messages"], tools_schema, config)

    if "error" in llm_resp:
        return {"session_id": session_id, "type": "error", "content": str(llm_resp["error"])}

    choice = llm_resp["choices"][0]
    msg = choice["message"]
    session["messages"].append(msg)

    if msg.get("tool_calls"):
        return process_message.__wrapped__(session_id, None, config) if hasattr(process_message, '__wrapped__') else {
            "session_id": session_id, "type": "text", "content": msg.get("content", "")
        }

    return {"session_id": session_id, "type": "text", "content": msg.get("content", "")}
