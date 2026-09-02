import glob
import os
import re
import socket
import streamlit as st
import yaml

st.set_page_config(page_title="Workspace", page_icon="~", layout="wide")

DOCKER_MODE = os.environ.get("WORKSPACE_DOCKER", "") == "1"
TOOLS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools")


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _discover_tools() -> list[dict]:
    """Scan tools/*/tool.yaml manifests for auto-discovery."""
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
            "type": manifest.get("type", "streamlit"),
            "entry": manifest.get("entry", "app.py"),
        }
        if DOCKER_MODE:
            tool["url"] = f"/tools/{slug}/"
        else:
            config_path = os.path.join(os.path.dirname(manifest_path), "..", "..", "config.yaml")
            config_path = os.path.normpath(config_path)
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
                if match:
                    tool["url"] = match["url"]
                    tool["port"] = match.get("port")
                else:
                    tool["url"] = f"http://localhost:8501"
            except FileNotFoundError:
                tool["url"] = f"http://localhost:8501"
        tools.append(tool)
    return tools


@st.cache_data(ttl=8)
def _check_port(port: int) -> bool:
    s = socket.socket()
    s.settimeout(0.15)
    try:
        s.connect(("127.0.0.1", port))
        return True
    except Exception:
        return False
    finally:
        s.close()


_tools = _discover_tools()
_active_slug = st.query_params.get("tool")
_active_tool = next(
    (t for t in _tools if t["slug"] == _active_slug),
    None,
) if _active_slug else None

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&display=swap');
    html, body, [class*="css"] { font-family: 'JetBrains Mono', monospace !important; }
    /* Material icons (e.g. expander arrows) rely on their own ligature
       font — the blanket override above breaks them into literal text
       like "keyboard_arrow_right" otherwise. */
    [data-testid="stIconMaterial"] { font-family: 'Material Symbols Rounded' !important; }
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .stTabs [data-baseweb="tab-list"] { gap: 0; border-bottom: 1px solid #d4d4c8; }
    .stTabs [data-baseweb="tab"] {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 14px; color: #555; padding: 8px 20px;
        border: none; background: transparent;
    }
    .stTabs [aria-selected="true"] {
        color: #2d6a4f !important;
        border-bottom: 2px solid #2d6a4f !important;
        font-weight: 700;
    }
    .stButton > button {
        font-family: 'JetBrains Mono', monospace !important;
        border: 1px solid #2d6a4f !important; color: #2d6a4f !important;
        background: transparent !important; border-radius: 4px !important;
        font-size: 13px !important; padding: 6px 16px !important;
    }
    .stButton > button:hover { background: #2d6a4f !important; color: #fafaf5 !important; }
    .stButton > button[data-testid="stBaseButton-primary"] {
        background: #2d6a4f !important; color: #fafaf5 !important;
    }
    .stTextInput > div > div > input {
        font-family: 'JetBrains Mono', monospace !important;
        border: 1px dashed #ccc !important; border-radius: 4px !important;
        background: #fafaf5 !important; font-size: 13px !important;
    }
    .stTextInput label { font-family: 'JetBrains Mono', monospace !important; font-size: 12px !important; color: #888 !important; }
    .stSelectbox > div > div { font-family: 'JetBrains Mono', monospace !important; font-size: 13px !important; }

</style>
""", unsafe_allow_html=True)

# ── Frame ─────────────────────────────────────────────────────────────────────
# A tool is active: the workspace becomes a thin recipient shell — a back bar
# plus an iframe of the tool's own, fully independent app. The tool itself
# carries no knowledge of the workspace.
if _active_tool:
    BAR_HEIGHT = 46
    FOOTER_HEIGHT = 25
    RECIPIENT_BG = "#f0f0e8"
    IFRAME_TOP = BAR_HEIGHT
    IFRAME_BOTTOM = FOOTER_HEIGHT
    st.markdown(f"""
    <style>
        html, body {{ overflow: hidden !important; }}
        /* Hide everything Streamlit renders in the normal flow — all content
           is position:fixed so the flow layer should be invisible and zero-height. */
        div[data-testid="stMainBlockContainer"] {{
            max-width: 100% !important; padding: 0 !important; margin: 0 !important;
        }}
        /* The iframe — pin it between the two bars */
        iframe {{
            position: fixed !important;
            top: {IFRAME_TOP}px !important;
            left: 0 !important;
            right: 0 !important;
            bottom: {IFRAME_BOTTOM}px !important;
            width: 100% !important;
            height: calc(100vh - {IFRAME_TOP}px - {IFRAME_BOTTOM}px) !important;
            border: none !important;
            z-index: 1 !important;
        }}
    </style>
    """, unsafe_allow_html=True)

    st.html(f"""
    <div style="position:fixed; top:0; left:0; right:0; height:{BAR_HEIGHT}px; z-index:9999;
                box-sizing:border-box; display:flex; align-items:center; justify-content:space-between;
                padding:0 20px; border-bottom:1px solid #d4d4c8; background:{RECIPIENT_BG};">
        <a href="?" target="_self" style="font-family:'JetBrains Mono',monospace; font-size:12px;
           font-weight:700; color:#2d6a4f; text-decoration:none; white-space:nowrap;">[&lt;] workspace</a>
        <span style="font-family:'JetBrains Mono',monospace; font-size:13px; color:#555;">{_active_tool['name']}</span>
        <span aria-hidden="true" style="font-family:'JetBrains Mono',monospace; font-size:12px;
           font-weight:700; visibility:hidden; white-space:nowrap;">[&lt;] workspace</span>
    </div>
    <div style="position:fixed; bottom:0; left:0; right:0; height:{FOOTER_HEIGHT}px; z-index:9999;
                box-sizing:border-box; border-top:1px solid #d4d4c8; background:{RECIPIENT_BG};"></div>
    """)

    st.iframe(_active_tool["url"], height=800)

    st.stop()

cards_html = ""
for tool in _tools:
    slug = tool["slug"]
    cards_html += f"""
    <a href="?tool={slug}" target="_self" class="ws-card">
        <div class="ws-card-name">[&gt;] {slug}</div>
        <div class="ws-card-desc">{tool['description']}</div>
        <div class="ws-card-arrow">&rarr;</div>
    </a>
    """

cards_html += """
<div class="ws-card ws-card-add">
    <div class="ws-card-name" style="color:#2d6a4f;">[+] ajouter une app</div>
    <div class="ws-card-desc">Ajoutez vos outils personnalises</div>
    <div class="ws-card-arrow">&rarr;</div>
</div>
"""

st.html(f"""
<style>
    .ws-home {{ font-family: 'JetBrains Mono', monospace; margin: 0; padding: 32px 24px; }}
    .ws-header {{ margin-bottom: 56px; }}
    .ws-title {{ font-size: 36px; font-weight: 700; color: #1a1a1a; }}
    .ws-title span {{ color: #2d6a4f; }}
    .ws-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 32px; }}
    .ws-card {{
        display: flex; flex-direction: column; justify-content: space-between;
        border: 1px solid #d4d4c8; border-radius: 6px; padding: 20px;
        min-height: 120px; background: #fafaf5; text-decoration: none;
        cursor: pointer; transition: border-color 0.15s;
    }}
    .ws-card:hover {{ border-color: #2d6a4f; }}
    .ws-card-add {{
        border-style: dashed; cursor: default;
    }}
    .ws-card-name {{
        font-size: 15px; font-weight: 700; color: #2d6a4f; margin-bottom: 12px;
    }}
    .ws-card-desc {{
        font-size: 12px; color: #888; line-height: 1.5; flex: 1;
    }}
    .ws-card-arrow {{
        font-size: 18px; color: #2d6a4f; text-align: right; margin-top: 12px;
    }}
</style>

<div class="ws-home">
    <div class="ws-header">
        <div class="ws-title"><span>&gt;_</span> workspace</div>
    </div>
    <div class="ws-grid">
        {cards_html}
    </div>
</div>
""")
