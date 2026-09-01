import streamlit as st
from db.database import init_db
from ui.style import inject_custom_css
from ui.calendar_view import render_calendar
from ui.event_form import render_add_form, render_edit_form
from ui.agenda import render_agenda

st.set_page_config(page_title="Calendar", page_icon="[~]", layout="wide")

init_db()
inject_custom_css()

tab_cal, tab_add, tab_agenda = st.tabs(["[~] Calendar", "[+] Add Event", "[=] Agenda"])

with tab_cal:
    render_calendar()

with tab_add:
    if "editing_event_id" in st.session_state:
        render_edit_form(st.session_state["editing_event_id"], key_prefix="add_edit")
        st.divider()
        if st.button("[x] Cancel edit", key="cancel_add"):
            st.session_state.pop("editing_event_id", None)
            st.rerun()
    else:
        render_add_form()

with tab_agenda:
    if "editing_event_id" in st.session_state:
        render_edit_form(st.session_state["editing_event_id"], key_prefix="agenda_edit")
        st.divider()
        if st.button("[x] Cancel edit", key="cancel_agenda"):
            st.session_state.pop("editing_event_id", None)
            st.rerun()
    else:
        render_agenda()
