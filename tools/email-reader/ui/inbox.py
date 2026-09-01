import streamlit as st
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from db.queries import (
    list_emails, mark_read, mark_all_read, get_stats,
    delete_email, delete_emails_by_sender, get_email_by_id,
)
from blocked import add_blocked_sender
from config import GMAIL_ACCOUNTS
from ui.style import CATEGORY_COLORS, CATEGORY_LABELS


@st.cache_data(ttl=30)
def _cached_emails(category=None, account=None, unread_only=False):
    return list_emails(category=category, account=account, unread_only=unread_only)


@st.cache_data(ttl=30)
def _cached_stats():
    return get_stats()


def _format_date(received_at: str) -> str:
    try:
        from datetime import datetime, date
        dt = datetime.strptime(received_at, "%Y-%m-%d %H:%M:%S")
        today = date.today()
        if dt.date() == today:
            return dt.strftime("%H:%M")
        elif dt.year == today.year:
            return dt.strftime("%b %d")
        else:
            return dt.strftime("%Y-%m-%d")
    except Exception:
        return received_at[:10] if received_at else ""


def _email_card_html(em: dict) -> str:
    """Card body — [open in gmail] is a real link (opens externally, correct).
    [read] and [flag] are native st.button below — no new-tab issue."""
    category = em.get("category", "update")
    color = CATEGORY_COLORS.get(category, "#888")
    label = CATEGORY_LABELS.get(category, f"[{category}]")
    unread_class = "" if em.get("is_read") else " unread"
    subject = em.get("subject", "").replace("<", "&lt;").replace(">", "&gt;")
    summary = (em.get("summary") or "").replace("<", "&lt;").replace(">", "&gt;")
    from_name = (em.get("from_name") or em.get("from_address", "")).replace("<", "&lt;")
    received = _format_date(em.get("received_at", ""))
    gmail_link = em.get("gmail_link", "#")

    return f"""
<div class="email-card{unread_class}">
  <div class="card-top">
    <span class="from-name">{from_name}</span>
    <span class="received">{received}</span>
  </div>
  <div class="subject">{subject}</div>
  {"<div class='summary'>" + summary + "</div>" if summary else ""}
  <div class="card-footer">
    <span class="cat-badge" style="background:{color}">{label}</span>
    <a class="card-link-open" href="{gmail_link}" target="_blank">[open in gmail]</a>
  </div>
</div>
"""


def _flag_sender(from_address: str):
    add_blocked_sender(from_address)
    delete_emails_by_sender(from_address)


def render_inbox():
    stats = _cached_stats()

    # CSS to pull action buttons flush against the card above them
    st.markdown("""
    <style>
    /* Card + action row look like one unit */
    div[data-testid="stHtml"] + div[data-testid="stHorizontalBlock"] {
        margin-top: -14px !important;
        padding-bottom: 4px;
        border-left: 1px solid #d4d4c8;
        border-right: 1px solid #d4d4c8;
        border-bottom: 1px solid #d4d4c8;
        border-radius: 0 0 6px 6px;
        padding: 6px 14px 8px;
        background: #fafaf5;
    }
    /* Override button style inside action rows to look like inline links */
    div[data-testid="stHtml"] + div[data-testid="stHorizontalBlock"] .stButton > button {
        border: none !important;
        background: transparent !important;
        padding: 0 !important;
        font-size: 11px !important;
        min-height: unset !important;
        height: auto !important;
        line-height: 1 !important;
    }
    div[data-testid="stHtml"] + div[data-testid="stHorizontalBlock"] .stButton:nth-child(1) > button {
        color: #999 !important;
    }
    div[data-testid="stHtml"] + div[data-testid="stHorizontalBlock"] .stButton:nth-child(1) > button:hover {
        color: #1a1a1a !important;
    }
    div[data-testid="stHtml"] + div[data-testid="stHorizontalBlock"] .stButton:nth-child(2) > button {
        color: #c0392b !important;
        opacity: 0.65;
    }
    div[data-testid="stHtml"] + div[data-testid="stHorizontalBlock"] .stButton:nth-child(2) > button:hover {
        opacity: 1 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # Stats bar
    by_cat = stats.get("by_category", {})
    cat_parts = " | ".join(
        f'<span class="stat-item">{CATEGORY_LABELS.get(k, k)}: <span>{v}</span></span>'
        for k, v in by_cat.items()
    )
    st.html(f"""
    <div class="stat-bar">
      <span class="stat-item">total: <span>{stats['total']}</span></span>
      <span class="stat-item">unread: <span>{stats['unread']}</span></span>
      <span class="stat-item">today: <span>{stats['today']}</span></span>
      {"<span style='color:#d4d4c8'>|</span>" + cat_parts if cat_parts else ""}
    </div>
    """)

    # Filters
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        category_options = ["all"] + list(CATEGORY_LABELS.keys())
        category_labels_map = {"all": "[all categories]"} | CATEGORY_LABELS
        category = st.selectbox(
            "category",
            options=category_options,
            format_func=lambda x: category_labels_map.get(x, x),
            label_visibility="collapsed",
        )
    with col2:
        account_options = ["all"] + [acc["name"] for acc in GMAIL_ACCOUNTS]
        account_labels = {"all": "[all accounts]"} | {acc["name"]: acc["address"] for acc in GMAIL_ACCOUNTS}
        account = st.selectbox(
            "account",
            options=account_options,
            format_func=lambda x: account_labels.get(x, x),
            label_visibility="collapsed",
        )
    with col3:
        unread_only = st.checkbox("unread only", value=False)

    if stats["unread"] > 0:
        if st.button(f"[mark all read] ({stats['unread']})", key="mark_all"):
            mark_all_read()
            st.cache_data.clear()
            st.rerun()

    emails = _cached_emails(
        category=category if category != "all" else None,
        account=account if account != "all" else None,
        unread_only=unread_only,
    )

    if not emails:
        st.html("""
        <div style="padding:32px 0; text-align:center; color:#aaa;
                    font-size:13px; font-family:'JetBrains Mono',monospace;">
          inbox empty — run [sync] to fetch emails
        </div>
        """)
        return

    for em in emails:
        eid = em["id"]
        sender = em.get("from_address", "")

        # Card body (top + sides border, no bottom border — action row closes it)
        st.html(_email_card_html(em))

        # Action row: attaches visually to the card via CSS above
        col_read, col_flag, _ = st.columns([1, 1, 10])
        with col_read:
            with st.container(key=f"linkbtn_read_{eid}"):
                if st.button("[read]", key=f"read_{eid}"):
                    delete_email(eid)
                    st.cache_data.clear()
                    st.rerun()
        with col_flag:
            with st.container(key=f"linkbtn_flag_{eid}"):
                if st.button("[flag]", key=f"flag_{eid}"):
                    _flag_sender(sender)
                    st.cache_data.clear()
                    st.rerun()

        # Full body expander
        body = em.get("body_preview", "").strip()
        if body:
            with st.expander("[body]"):
                st.text(body)

    # Mark visible emails as read after first visit
    unread_ids = [em["id"] for em in emails if not em.get("is_read")]
    if unread_ids and st.session_state.get("inbox_visited"):
        for eid in unread_ids:
            mark_read(eid)
    st.session_state["inbox_visited"] = True
