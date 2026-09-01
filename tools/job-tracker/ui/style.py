import streamlit as st

VERSION = "v1.0.0"

def inject_custom_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&display=swap');

        /* Global */
        html, body, [class*="css"] {
            font-family: 'JetBrains Mono', monospace !important;
        }
        /* Material icons (e.g. expander arrows) rely on their own ligature
           font — the blanket override above breaks them into literal text
           like "keyboard_arrow_right" otherwise. */
        [data-testid="stIconMaterial"] {
            font-family: 'Material Symbols Rounded' !important;
        }

        /* Header bar */
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
        .terminal-header .app-name {
            color: #2d6a4f;
            font-weight: 700;
        }
        .terminal-header .version {
            color: #888;
            font-size: 12px;
        }

        /* Footer */
        .terminal-footer {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            display: flex;
            justify-content: space-between;
            padding: 4px 16px;
            background: #f0f0e8;
            border-top: 1px solid #d4d4c8;
            font-size: 12px;
            z-index: 999;
        }
        .terminal-footer .status {
            color: #2d6a4f;
        }
        .terminal-footer .ver {
            color: #888;
        }

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
        .stButton > button[kind="primary"]:hover,
        .stButton > button[data-testid="stBaseButton-primary"]:hover {
            background: #1b4332 !important;
        }

        /* Inputs */
        .stTextInput > div > div > input,
        .stTextArea > div > div > textarea {
            font-family: 'JetBrains Mono', monospace !important;
            border: 1px dashed #ccc !important;
            border-radius: 4px !important;
            background: #fafaf5 !important;
            font-size: 13px !important;
        }
        .stTextInput > div > div > input:focus,
        .stTextArea > div > div > textarea:focus {
            border-color: #2d6a4f !important;
            box-shadow: none !important;
        }

        /* Select boxes */
        .stSelectbox > div > div {
            font-family: 'JetBrains Mono', monospace !important;
            font-size: 13px !important;
        }

        /* Metrics */
        [data-testid="stMetric"] {
            background: #f0f0e8;
            border: 1px solid #d4d4c8;
            border-radius: 4px;
            padding: 12px;
        }
        [data-testid="stMetricLabel"] {
            font-size: 12px !important;
            color: #666 !important;
        }
        [data-testid="stMetricValue"] {
            font-size: 24px !important;
            color: #2d6a4f !important;
        }

        /* Expanders */
        .streamlit-expanderHeader {
            font-family: 'JetBrains Mono', monospace !important;
            font-size: 13px !important;
            color: #555 !important;
        }

        /* Success/Warning/Info boxes */
        .stSuccess, .stWarning, .stInfo {
            font-family: 'JetBrains Mono', monospace !important;
            font-size: 13px !important;
        }

        /* Download button */
        .stDownloadButton > button {
            font-family: 'JetBrains Mono', monospace !important;
            border: 1px solid #2d6a4f !important;
            color: #2d6a4f !important;
            background: transparent !important;
            font-size: 13px !important;
        }

        /* Hide default Streamlit elements */
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}

        /* Add padding at bottom for fixed footer */
        .block-container {
            padding-bottom: 3rem !important;
        }

    </style>
    """, unsafe_allow_html=True)


def render_header():
    st.markdown("""
    <div class="terminal-header">
        <span class="app-name">$ job_tracker</span>
        <span class="version">""" + VERSION + """</span>
    </div>
    """, unsafe_allow_html=True)


def render_footer():
    st.markdown("""
    <div class="terminal-footer">
        <span class="status">status: <span style="color: #2d6a4f">idle</span></span>
        <span class="ver">""" + VERSION + """</span>
    </div>
    """, unsafe_allow_html=True)