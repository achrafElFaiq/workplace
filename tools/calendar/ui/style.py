import streamlit as st

VERSION = "v1.0.0"


def inject_custom_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&display=swap');

        html, body, [class*="css"] { font-family: 'JetBrains Mono', monospace !important; }
        /* Material icons (e.g. expander arrows) rely on their own ligature
           font — the blanket override above breaks them into literal text
           like "keyboard_arrow_right" otherwise. */
        [data-testid="stIconMaterial"] { font-family: 'Material Symbols Rounded' !important; }

        .stTabs [data-baseweb="tab-list"] { gap: 0px; border-bottom: 1px solid #d4d4c8; }
        .stTabs [data-baseweb="tab"] {
            font-family: 'JetBrains Mono', monospace !important;
            font-size: 13px; color: #888; padding: 8px 20px;
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
            transition: all 0.15s ease;
        }
        .stButton > button:hover { background: #2d6a4f !important; color: #fafaf5 !important; }
        .stButton > button[data-testid="stBaseButton-primary"] {
            background: #2d6a4f !important; color: #fafaf5 !important;
        }
        .stButton > button[data-testid="stBaseButton-primary"]:hover {
            background: #1b4332 !important; color: #fafaf5 !important;
        }

        .stTextInput > div > div > input,
        .stTextArea > div > div > textarea,
        .stNumberInput > div > div > input,
        .stDateInput > div > div > input {
            font-family: 'JetBrains Mono', monospace !important;
            border: 1px dashed #ccc !important; border-radius: 4px !important;
            background: #fafaf5 !important; font-size: 13px !important;
        }
        .stTextInput > div > div > input:focus,
        .stTextArea > div > div > textarea:focus,
        .stNumberInput > div > div > input:focus,
        .stDateInput > div > div > input:focus {
            border-color: #2d6a4f !important; box-shadow: none !important;
        }

        .stTextInput label, .stTextArea label, .stDateInput label,
        .stSelectbox label, .stNumberInput label, .stCheckbox label,
        .stRadio label, .stTimeInput label {
            font-family: 'JetBrains Mono', monospace !important;
            font-size: 12px !important; color: #888 !important;
        }

        .stSelectbox > div > div,
        .stMultiSelect > div > div {
            font-family: 'JetBrains Mono', monospace !important; font-size: 13px !important;
        }

        .stCheckbox > label, .stRadio > div label {
            font-family: 'JetBrains Mono', monospace !important;
            font-size: 13px !important; color: #1a1a1a !important;
        }

        details summary {
            font-family: 'JetBrains Mono', monospace !important;
            font-size: 13px !important; color: #888 !important;
        }

        .stAlert, .stAlert p {
            font-family: 'JetBrains Mono', monospace !important;
            font-size: 13px !important; border-radius: 4px !important;
        }

        [class*="st-key-daysel_"], [class*="st-key-eventsel_"],
        [class*="st-key-cal_day_proxies"], [class*="st-key-cal_event_proxies"] {
            display: none !important;
        }

        [class*="st-key-linkbtn_"],
        [class*="st-key-linkbtn_"] > div,
        [class*="st-key-linkbtn_"] [data-testid="stButton"] {
            display: flex !important; justify-content: flex-end !important;
            width: 100% !important;
        }
        [class*="st-key-linkbtn_"] button,
        [class*="st-key-linkbtn_"] button:hover,
        [class*="st-key-linkbtn_"] button:active,
        [class*="st-key-linkbtn_"] button:focus {
            font-family: 'JetBrains Mono', monospace !important;
            border: none !important; background: transparent !important;
            box-shadow: none !important; outline: none !important;
            color: #2d6a4f !important; padding: 0 !important;
            font-size: 12px !important; border-radius: 0 !important;
            width: auto !important; min-width: 0 !important;
        }

        hr { border-color: #d4d4c8 !important; }

        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        .block-container { padding-top: 1.5rem !important; padding-bottom: 1.5rem !important; }

    </style>
    """, unsafe_allow_html=True)


