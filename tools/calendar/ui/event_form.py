import streamlit as st
from datetime import date
from config import CATEGORIES
from db.queries import add_event, update_event, delete_event, get_event

START_HOUR = 9
END_HOUR = 21

_SLOTS = [f"{h:02d}:{m:02d}" for h in range(START_HOUR, END_HOUR) for m in (0, 15, 30, 45)] + [f"{END_HOUR:02d}:00"]


def _end_slots(start: str) -> list[str]:
    return [s for s in _SLOTS if s > start]


def _default_end(start: str, end_opts: list[str]) -> str:
    if not start:
        return end_opts[0] if end_opts else "10:00"
    h, m = int(start[:2]), start[3:5]
    if h < 23:
        candidate = f"{h + 1:02d}:{m}"
        if candidate in end_opts:
            return candidate
    return end_opts[0] if end_opts else start


def _time_selectors(start_opts, start_key, end_key, saved_start=None, saved_end=None):
    """Render Start/End time selectboxes where End is always constrained to be after Start."""
    col_start, col_end = st.columns(2)
    with col_start:
        s_default = saved_start if saved_start in start_opts else "09:00"
        s_idx = start_opts.index(s_default) if s_default in start_opts else 0
        start = st.selectbox("Start time", start_opts, index=s_idx, key=start_key)
    with col_end:
        end_opts = _end_slots(start)
        e_default = saved_end if saved_end in end_opts else _default_end(start, end_opts)
        if end_key not in st.session_state:
            e_idx = end_opts.index(e_default) if e_default in end_opts else 0
            end = st.selectbox("End time", end_opts, index=e_idx, key=end_key)
        else:
            if st.session_state[end_key] not in end_opts:
                st.session_state[end_key] = e_default
            end = st.selectbox("End time", end_opts, key=end_key)
    return start, end


def render_add_form():
    st.markdown("#### [+] New Event")

    col_date, col_cat = st.columns(2)
    with col_date:
        event_date = st.date_input("Date *", value=date.today(), key="add_event_date")
    with col_cat:
        category = st.selectbox("Category", CATEGORIES, key="add_category")

    time_str, end_time_str = _time_selectors(_SLOTS, "add_start_time", "add_end_time")

    with st.form("add_event_form", clear_on_submit=True):
        title = st.text_input("Title *")
        description = st.text_area("Description", height=80)
        submitted = st.form_submit_button("[+] Add Event", type="primary")

    if submitted:
        if not title.strip():
            st.error("[x] Title is required.")
            return
        add_event(
            title=title.strip(),
            date=event_date.isoformat(),
            time=time_str,
            end_time=end_time_str,
            category=category,
            description=description.strip(),
            all_day=False,
        )
        st.success(f"[ok] Event '{title}' added.")
        st.rerun()


def render_edit_form(event_id: int, key_prefix: str = "edit"):
    event = get_event(event_id)
    if not event:
        st.error("[x] Event not found.")
        return

    st.markdown(f"#### [~] Edit: {event['title']}")

    col_date, col_cat = st.columns(2)
    with col_date:
        event_date = st.date_input(
            "Date *", value=date.fromisoformat(event["date"]), key=f"{key_prefix}_date_{event_id}"
        )
    with col_cat:
        cat_idx = CATEGORIES.index(event["category"]) if event["category"] in CATEGORIES else 0
        category = st.selectbox("Category", CATEGORIES, index=cat_idx, key=f"{key_prefix}_category_{event_id}")

    saved_start = event.get("time") or "09:00"
    start_opts = _SLOTS if saved_start in _SLOTS else [saved_start] + _SLOTS
    time_str, end_time_str = _time_selectors(
        start_opts,
        f"{key_prefix}_start_{event_id}",
        f"{key_prefix}_end_{event_id}",
        saved_start=saved_start,
        saved_end=event.get("end_time"),
    )

    with st.form(f"{key_prefix}_event_{event_id}"):
        title = st.text_input("Title *", value=event["title"])
        description = st.text_area("Description", value=event.get("description") or "", height=80)

        col_save, col_del = st.columns(2)
        with col_save:
            save = st.form_submit_button("[~] Save", type="primary")
        with col_del:
            delete = st.form_submit_button("[x] Delete")

    if save:
        if not title.strip():
            st.error("[x] Title is required.")
            return
        update_event(
            event_id=event_id,
            title=title.strip(),
            date=event_date.isoformat(),
            time=time_str,
            end_time=end_time_str,
            category=category,
            description=description.strip(),
            all_day=False,
        )
        st.success("[ok] Event updated.")
        st.session_state.pop("editing_event_id", None)
        st.rerun()

    if delete:
        delete_event(event_id)
        st.success("[ok] Event deleted.")
        st.session_state.pop("editing_event_id", None)
        st.rerun()
