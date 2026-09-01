import streamlit as st
from datetime import date
from config import CATEGORY_COLORS
from db.queries import get_upcoming_events, delete_event


def render_agenda():
    st.markdown("#### [=] Upcoming — next 14 days")

    events = get_upcoming_events(days=14)

    if not events:
        st.html('<p style="font-family:JetBrains Mono,monospace; color:#888; font-size:13px;">No upcoming events.</p>')
        return

    current_date = None
    for e in events:
        event_date = date.fromisoformat(e["date"])
        bg, fg = CATEGORY_COLORS.get(e["category"], ("#e0e0e0", "#555"))

        if event_date != current_date:
            current_date = event_date
            is_today = event_date == date.today()
            label = "today" if is_today else event_date.strftime("%A, %d %B %Y")
            color = "#2d6a4f" if is_today else "#555"
            st.html(
                f'<p style="font-family:JetBrains Mono,monospace; font-size:13px; '
                f'color:{color}; font-weight:700; margin-top:16px; margin-bottom:4px;">'
                f'-- {label} --</p>'
            )

        time_str = ""
        if not e["all_day"] and e.get("time"):
            end = f" → {e['end_time'][:5]}" if e.get("end_time") else ""
            time_str = f" [{e['time'][:5]}{end}]"

        desc_html = (
            f'<br><span style="font-family:JetBrains Mono,monospace; font-size:11px; color:#888;">'
            f'{e["description"]}</span>'
            if e.get("description") else ""
        )
        col_event, col_edit, col_del = st.columns([8, 2, 2])
        with col_event:
            st.html(
                f'<div style="display:flex; align-items:center; gap:8px; margin-bottom:6px;">'
                f'<span style="background:{bg}; color:{fg}; font-size:11px; padding:2px 6px; '
                f'border-radius:3px; font-family:JetBrains Mono,monospace;">{e["category"]}</span>'
                f'<span style="font-family:JetBrains Mono,monospace; font-size:13px; color:#333;">'
                f'{e["title"]}{time_str}</span>'
                f'{desc_html}'
                f'</div>'
            )
        with col_edit:
            with st.container(key=f"linkbtn_edit_{e['id']}"):
                if st.button("[edit]", key=f"edit_{e['id']}", help="Edit"):
                    st.session_state["editing_event_id"] = e["id"]
                    st.rerun()
        with col_del:
            with st.container(key=f"linkbtn_del_{e['id']}"):
                if st.button("[delete]", key=f"del_{e['id']}", help="Delete"):
                    delete_event(e["id"])
                    st.success(f"[ok] Event '{e['title']}' deleted.")
                    st.rerun()
