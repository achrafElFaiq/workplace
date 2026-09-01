import streamlit as st
from db.database import init_db
from ui.quick_add import render_quick_add
from ui.dashboard import render_dashboard
from ui.contacts import render_contacts
from ui.style import inject_custom_css
from ui.config_tab import render_config

st.set_page_config(page_title="Job Tracker", page_icon="[+]", layout="wide")

init_db()
inject_custom_css()


tab_add, tab_dashboard, tab_contacts, tab_config = st.tabs(["[+] Ajouter", "[=] Dashboard", "[c] Contacts", "[config]"])

with tab_add:
    render_quick_add()

with tab_dashboard:
    render_dashboard()

with tab_contacts:
    render_contacts()

with tab_config:
    render_config()

