import streamlit as st

VERSION = "v1.0.0"

CATEGORY_COLORS = {
    "action": "#c0392b",
    "finance": "#2471a3",
    "personal": "#1e8449",
    "alert": "#b7950b",
    "update": "#7d3c98",
}

CATEGORY_LABELS = {
    "action": "[action]",
    "finance": "[finance]",
    "personal": "[personal]",
    "alert": "[alert]",
    "update": "[update]",
}


def inject_custom_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&display=swap');

        html, body, [class*="css"] {
            font-family: 'JetBrains Mono', monospace !important;
        }
        /* Material icons (e.g. expander arrows) rely on their own ligature
           font — the blanket override above breaks them into literal text
           like "keyboard_arrow_right" otherwise. */
        [data-testid="stIconMaterial"] {
            font-family: 'Material Symbols Rounded' !important;
        }

        .terminal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 16px;
            background: #f0f0e8;
            border-bottom: 1px solid #d4d4c8;
            margin: -1rem -1rem 1.5rem -1rem;
            font-size: 14px;
        }
        .terminal-header .app-name { color: #2d6a4f; font-weight: 700; }
        .terminal-header .version  { color: #888; font-size: 12px; }

        .terminal-footer {
            position: fixed;
            bottom: 0; left: 0; right: 0;
            display: flex;
            justify-content: space-between;
            padding: 4px 16px;
            background: #f0f0e8;
            border-top: 1px solid #d4d4c8;
            font-size: 12px;
            z-index: 999;
        }
        .terminal-footer .status { color: #2d6a4f; }
        .terminal-footer .ver    { color: #888; }

        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {
            gap: 0px;
            border-bottom: 1px solid #d4d4c8;
        }
        .stTabs [data-baseweb="tab"] {
            font-family: 'JetBrains Mono', monospace !important;
            font-size: 14px;
            color: #555;
            padding: 8px 20px;
            border: none;
            background: transparent;
        }
        .stTabs [aria-selected="true"] {
            color: #2d6a4f !important;
            border-bottom: 2px solid #2d6a4f !important;
            font-weight: 700;
        }

        /* Buttons */
        .stButton > button {
            font-family: 'JetBrains Mono', monospace !important;
            border: 1px solid #2d6a4f !important;
            color: #2d6a4f !important;
            background: transparent !important;
            border-radius: 4px !important;
            font-size: 13px !important;
            padding: 6px 16px !important;
            transition: all 0.15s ease;
        }
        .stButton > button:hover {
            background: #2d6a4f !important;
            color: #fafaf5 !important;
        }
        .stButton > button[kind="primary"],
        .stButton > button[data-testid="stBaseButton-primary"] {
            background: #2d6a4f !important;
            color: #fafaf5 !important;
        }

        /* Inputs */
        .stTextInput > div > div > input,
        .stTextArea > div > div > textarea,
        .stSelectbox > div > div {
            font-family: 'JetBrains Mono', monospace !important;
            font-size: 13px !important;
        }
        .stTextInput > div > div > input {
            border: 1px dashed #ccc !important;
            border-radius: 4px !important;
            background: #fafaf5 !important;
        }

        /* Metrics */
        [data-testid="stMetric"] {
            background: #f0f0e8;
            border: 1px solid #d4d4c8;
            border-radius: 4px;
            padding: 12px;
        }
        [data-testid="stMetricLabel"] { font-size: 12px !important; color: #666 !important; }
        [data-testid="stMetricValue"] { font-size: 24px !important; color: #2d6a4f !important; }

        /* Expanders */
        .streamlit-expanderHeader {
            font-family: 'JetBrains Mono', monospace !important;
            font-size: 13px !important;
            color: #555 !important;
        }

        /* Alerts */
        .stSuccess, .stWarning, .stInfo, .stError {
            font-family: 'JetBrains Mono', monospace !important;
            font-size: 13px !important;
        }

        /* Email card */
        .email-card {
            border: 1px solid #d4d4c8;
            border-radius: 6px;
            padding: 14px 16px;
            margin-bottom: 10px;
            background: #fafaf5;
            cursor: pointer;
            transition: border-color 0.15s;
        }
        .email-card:hover { border-color: #2d6a4f; }
        .email-card.unread { border-left: 3px solid #2d6a4f; }
        .email-card .card-top {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 4px;
        }
        .email-card .from-name {
            font-size: 13px;
            font-weight: 700;
            color: #1a1a1a;
        }
        .email-card .received {
            font-size: 11px;
            color: #999;
            white-space: nowrap;
        }
        .email-card .subject {
            font-size: 13px;
            color: #333;
            margin-bottom: 5px;
        }
        .email-card .summary {
            font-size: 12px;
            color: #666;
            margin-bottom: 8px;
            line-height: 1.4;
        }
        .email-card .card-footer {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .category-badge {
            display: inline-block;
            font-size: 11px;
            padding: 2px 8px;
            border-radius: 3px;
            font-weight: 500;
            color: #fafaf5;
        }
        .email-card .open-link {
            font-size: 11px;
            color: #2d6a4f;
            text-decoration: none;
            margin-left: auto;
        }
        .email-card .open-link:hover { text-decoration: underline; }

        /* Stat bar */
        .stat-bar {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
            padding: 8px 0;
            margin-bottom: 12px;
            border-bottom: 1px solid #e0e0d8;
            font-size: 12px;
        }
        .stat-item { color: #666; }
        .stat-item span { color: #2d6a4f; font-weight: 700; }

        /* Filter row */
        .filter-row { margin-bottom: 16px; }

        /* Email cards — bottom border + radius comes from the action row */
        .email-card {
            border: 1px solid #d4d4c8;
            border-bottom: none;
            border-radius: 6px 6px 0 0;
            padding: 14px 16px 10px;
            background: #fafaf5;
        }
        .email-card.unread { border-left: 3px solid #2d6a4f; }
        .email-card .card-top {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 4px;
        }
        .email-card .from-name { font-size: 13px; font-weight: 700; color: #1a1a1a; }
        .email-card .received  { font-size: 11px; color: #999; white-space: nowrap; }
        .email-card .subject   { font-size: 13px; color: #333; margin-bottom: 5px; }
        .email-card .summary   { font-size: 12px; color: #666; margin-bottom: 10px; line-height: 1.4; }
        .email-card .card-footer {
            display: flex;
            align-items: center;
            gap: 12px;
            flex-wrap: wrap;
            border-top: 1px solid #f0f0e8;
            padding-top: 8px;
            margin-top: 4px;
        }
        .cat-badge {
            display: inline-block;
            font-size: 11px;
            padding: 2px 8px;
            border-radius: 3px;
            font-weight: 500;
            color: #fafaf5;
        }
        .card-actions { margin-left: auto; display: flex; gap: 12px; align-items: center; }
        .card-link-open { font-size: 11px; color: #2d6a4f; text-decoration: none; }
        .card-link-open:hover { text-decoration: underline; }
        .card-link-read { font-size: 11px; color: #999; text-decoration: none; }
        .card-link-read:hover { color: #1a1a1a; }
        .card-link-flag { font-size: 11px; color: #c0392b; text-decoration: none; opacity: 0.6; }
        .card-link-flag:hover { opacity: 1; text-decoration: underline; }

        /* Hide Streamlit chrome */
        #MainMenu { visibility: hidden; }
        header { visibility: hidden; }
        footer { visibility: hidden; }
        .block-container { padding-bottom: 1rem !important; }

    </style>
    """, unsafe_allow_html=True)


def render_header():
    st.markdown(f"""
    <div class="terminal-header">
        <span class="app-name">$ email_reader</span>
        <span class="version">{VERSION}</span>
    </div>
    """, unsafe_allow_html=True)


def render_footer(status: str = "idle"):
    st.markdown(f"""
    <div class="terminal-footer">
        <span class="status">status: <span style="color:#2d6a4f">{status}</span></span>
        <span class="ver">{VERSION}</span>
    </div>
    """, unsafe_allow_html=True)
