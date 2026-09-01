import streamlit as st
import os
import sys

# Ensure the app directory is in path when running via Streamlit
sys.path.insert(0, os.path.dirname(__file__))

from db.database import init_db
from ui.style import inject_custom_css
from ui.inbox import render_inbox
from ui.sync_tab import render_sync
from ui.digest import render_digest
from ui.config_tab import render_config

st.set_page_config(
    page_title="Email Reader",
    page_icon="[mail]",
    layout="wide",
)

init_db()

inject_custom_css()

tab_digest, tab_inbox, tab_sync, tab_config = st.tabs(["[digest]", "[inbox]", "[sync]", "[config]"])

with tab_digest:
    render_digest()

with tab_inbox:
    render_inbox()

with tab_sync:
    render_sync()

with tab_config:
    render_config()
