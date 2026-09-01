import re
import socket
import streamlit as st
import yaml

st.set_page_config(page_title="Workspace", page_icon="~", layout="wide")


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


CONFIG_PATH = "config.yaml"


def _load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f) or {}



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


_config = _load_config()
_active_slug = st.query_params.get("tool")
_active_tool = next(
    (t for t in _config.get("tools", []) if _slugify(t["name"]) == _active_slug),
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

st.title("workspace")

config = _load_config()
cols = st.columns(3)
for i, tool in enumerate(config.get("tools", [])):
    port = tool.get("port")
    is_up = _check_port(port) if port else False
    status_label = "[ok]" if is_up else "[--]"
    status_color = "#2d6a4f" if is_up else "#c0392b"
    slug = _slugify(tool["name"])

    with cols[i % 3]:
        st.html(f"""
        <a href="?tool={slug}" target="_self" style="text-decoration:none;">
            <div style="border:1px solid #d4d4c8; border-radius:6px; padding:24px;
                        margin-bottom:16px; background:#fafaf5; cursor:pointer;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                    <span style="font-family:'JetBrains Mono',monospace; font-size:16px;
                                 font-weight:700; color:#2d6a4f;">[>] {tool['name']}</span>
                    <span style="font-family:'JetBrains Mono',monospace; font-size:11px;
                                 color:{status_color};">{status_label}</span>
                </div>
                <div style="font-family:'JetBrains Mono',monospace; font-size:12px;
                            color:#888; margin-bottom:6px;">{tool['description']}</div>
                <div style="font-family:'JetBrains Mono',monospace; font-size:11px;
                            color:#aaa;">{tool['url']}</div>
            </div>
        </a>
        """)
