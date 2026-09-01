import streamlit as st
import sys
import os
import json
import glob
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def _load_last_check() -> dict:
    from config import GMAIL_ACCOUNTS
    from db.queries import get_meta
    result = {}
    for acc in GMAIL_ACCOUNTS:
        val = get_meta(f"last_check_{acc['name']}")
        if val:
            result[acc["name"]] = val
    return result


def _load_last_sync() -> dict | None:
    sync_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "syncs")
    files = sorted(glob.glob(os.path.join(sync_dir, "sync_*.json")), reverse=True)
    if not files:
        return None
    with open(files[0]) as f:
        return json.load(f)


def render_sync():
    st.markdown("### [sync] email inbox")

    # Show last-checked status per account
    last_check = _load_last_check()
    from config import GMAIL_ACCOUNTS
    if last_check:
        lines = []
        for acc in GMAIL_ACCOUNTS:
            name = acc["name"]
            date = last_check.get(name)
            lines.append(
                f'<span style="color:#666">{acc["address"]}</span>: '
                f'<span style="color:#2d6a4f">{date if date else "never"}</span>'
            )
        status_html = " &nbsp;|&nbsp; ".join(lines)
        st.html(f'<p style="font-size:12px; font-family:JetBrains Mono,monospace; margin-bottom:12px;">last checked — {status_html}</p>')
    else:
        st.html('<p style="font-size:12px; color:#aaa; font-family:JetBrains Mono,monospace; margin-bottom:12px;">last checked — never (will fetch last 3 days)</p>')

    # Normal sync button
    col1, col2 = st.columns([3, 1])
    with col1:
        st.html('<p style="font-size:13px; color:#666; font-family:JetBrains Mono,monospace;">Fetch emails since last sync, filter noise, save what matters.</p>')
    with col2:
        run_sync = st.button("[sync] run now", type="primary", use_container_width=True)

    if run_sync:
        from sync import run_sync as _run_sync
        with st.spinner("syncing..."):
            try:
                stats = _run_sync()
                st.success(
                    f"[ok] sync complete — "
                    f"fetched: {stats['fetched']} | "
                    f"saved: {stats['saved']} | "
                    f"skipped: {stats['skipped_not_important']} not important | "
                    f"ignored: {stats['ignored_domain']} domains"
                )
                st.rerun()
            except Exception as e:
                st.error(f"[error] sync failed: {e}")

    # Force resync (manual override)
    with st.expander("[force resync] fetch further back"):
        st.html('<p style="font-size:12px; color:#888; font-family:JetBrains Mono,monospace;">Overrides last_check — use to recover missed emails.</p>')
        col_a, col_b = st.columns([2, 1])
        with col_a:
            days_back = st.selectbox(
                "days",
                options=[3, 7, 14, 30],
                format_func=lambda x: f"last {x} days",
                label_visibility="collapsed",
            )
        with col_b:
            force_run = st.button("[force]", use_container_width=True)
        if force_run:
            from sync import run_sync as _run_sync
            with st.spinner(f"resyncing last {days_back} days..."):
                try:
                    stats = _run_sync(force_days=days_back)
                    st.success(
                        f"[ok] fetched: {stats['fetched']} | saved: {stats['saved']} | "
                        f"skipped: {stats['skipped_not_important']}"
                    )
                    st.rerun()
                except Exception as e:
                    st.error(f"[error] {e}")

    st.divider()

    # Last sync summary
    st.markdown("#### last sync")
    last = _load_last_sync()
    if not last:
        st.markdown("<p style='color:#aaa; font-size:13px;'>no syncs yet</p>", unsafe_allow_html=True)
        return

    stats = last.get("stats", {})
    ts = last.get("timestamp", "")
    if ts:
        try:
            from datetime import datetime
            dt = datetime.strptime(ts, "%Y%m%d_%H%M%S")
            ts_display = dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            ts_display = ts
    else:
        ts_display = "unknown"

    st.markdown(f"<p style='font-size:12px; color:#888;'>run at {ts_display}</p>", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("fetched", stats.get("fetched", 0))
    c2.metric("saved", stats.get("saved", 0))
    c3.metric("ignored", stats.get("ignored_domain", 0))
    c4.metric("not important", stats.get("skipped_not_important", 0))

    st.divider()

    # Blocked senders management
    st.markdown("#### blocked senders")
    from blocked import list_blocked, remove_blocked_sender
    blocked = list_blocked()
    if not blocked:
        st.html('<p style="font-size:13px; color:#aaa; font-family:JetBrains Mono,monospace;">no blocked senders yet — flag emails in [inbox] to block a sender</p>')
    else:
        for entry in blocked:
            col_addr, col_date, col_unblock = st.columns([5, 3, 1])
            with col_addr:
                st.html(f'<span style="font-size:13px; font-family:JetBrains Mono,monospace; color:#1a1a1a;">{entry["address"]}</span>')
            with col_date:
                st.html(f'<span style="font-size:12px; font-family:JetBrains Mono,monospace; color:#999;">blocked {entry.get("blocked_at", "")[:10]}</span>')
            with col_unblock:
                if st.button("[unblock]", key=f"unblock_{entry['address']}"):
                    remove_blocked_sender(entry["address"])
                    st.toast(f"[ok] unblocked {entry['address']}")
                    st.rerun()
