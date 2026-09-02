#!/usr/bin/env python3
"""Scan tools/*/tool.yaml and generate docker-compose.yml + nginx.conf."""
import glob
import os
import yaml

ROOT = os.path.dirname(os.path.abspath(__file__))
TOOLS_DIR = os.path.join(ROOT, "tools")


def discover():
    tools = []
    for path in sorted(glob.glob(os.path.join(TOOLS_DIR, "*", "tool.yaml"))):
        with open(path) as f:
            m = yaml.safe_load(f) or {}
        slug = m.get("slug")
        if not slug:
            continue
        tool_dir = os.path.basename(os.path.dirname(path))
        tools.append({
            "slug": slug,
            "dir": tool_dir,
            "type": m.get("type", "streamlit"),
            "volumes": m.get("volumes", []),
        })
    return tools


def gen_compose(tools):
    services = {
        "nginx": {
            "image": "nginx:alpine",
            "ports": ["8080:80"],
            "volumes": ["./nginx.conf:/etc/nginx/conf.d/default.conf:ro"],
            "depends_on": ["portal"] + [t["slug"] for t in tools],
        },
        "portal": {
            "build": ".",
            "environment": ["WORKSPACE_DOCKER=1"],
            "volumes": ["./tools:/app/tools:ro"],
        },
    }
    for t in tools:
        svc = {"build": f"./tools/{t['dir']}"}
        vols = []
        for v in t["volumes"]:
            if ":" in v:
                host, container = v.split(":", 1)
                vols.append(f"./tools/{t['dir']}/{host}:{container}")
        if vols:
            svc["volumes"] = vols
        services[t["slug"]] = svc

    doc = {"services": services}
    out = os.path.join(ROOT, "docker-compose.yml")
    with open(out, "w") as f:
        yaml.dump(doc, f, default_flow_style=False, sort_keys=False)
    print(f"  [ok] {out}")


def gen_nginx(tools):
    blocks = [
        "server {",
        "    listen 80;",
        "",
        "    # Portal",
        "    location / {",
        "        proxy_pass http://portal:8501;",
        "        proxy_set_header Host $host;",
        "        proxy_set_header X-Real-IP $remote_addr;",
        "    }",
    ]
    for t in tools:
        ws = ""
        if t["type"] == "streamlit":
            ws = (
                "\n        proxy_http_version 1.1;"
                "\n        proxy_set_header Upgrade $http_upgrade;"
                "\n        proxy_set_header Connection \"upgrade\";"
            )
        blocks += [
            "",
            f"    # {t['slug']}",
            f"    location /tools/{t['slug']}/ {{",
            f"        proxy_pass http://{t['slug']}:8501/;{ws}",
            f"        proxy_set_header Host $host;",
            f"        proxy_set_header X-Real-IP $remote_addr;",
            "    }",
        ]
    blocks += ["}", ""]

    out = os.path.join(ROOT, "nginx.conf")
    with open(out, "w") as f:
        f.write("\n".join(blocks))
    print(f"  [ok] {out}")


if __name__ == "__main__":
    tools = discover()
    print(f"  [..] Found {len(tools)} tool(s): {', '.join(t['slug'] for t in tools)}")
    gen_compose(tools)
    gen_nginx(tools)
    print(f"\n  Run: docker compose up --build")
