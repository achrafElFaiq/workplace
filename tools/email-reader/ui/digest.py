import streamlit as st
import sys
import os
from datetime import datetime, timedelta, date

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from db.queries import list_emails
from ui.style import CATEGORY_COLORS, CATEGORY_LABELS


@st.cache_data(ttl=60)
def _cached_emails_week():
    return list_emails(limit=500)

WEEK_DAYS = 7


def _rel_date(received_at: str) -> str:
    try:
        dt = datetime.strptime(received_at, "%Y-%m-%d %H:%M:%S")
        today = date.today()
        if dt.date() == today:
            return f"today {dt.strftime('%H:%M')}"
        delta = (today - dt.date()).days
        if delta == 1:
            return "yesterday"
        return f"{delta}d ago"
    except Exception:
        return ""


def _urgent_card(em: dict) -> str:
    category = em.get("category", "action")
    color = CATEGORY_COLORS.get(category, "#c0392b")
    label = CATEGORY_LABELS.get(category, f"[{category}]")
    from_name = (em.get("from_name") or em.get("from_address", "")).replace("<", "&lt;")
    subject = em.get("subject", "").replace("<", "&lt;")
    summary = (em.get("summary") or "").replace("<", "&lt;")
    rel = _rel_date(em.get("received_at", ""))
    link = em.get("gmail_link", "#")
    unread_accent = "border-left:3px solid #c0392b;" if not em.get("is_read") else ""

    return f"""
<div style="border:1px solid #d4d4c8; border-radius:6px; padding:12px 16px; margin-bottom:8px;
            background:#fafaf5; font-family:'JetBrains Mono',monospace; {unread_accent}">
  <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
    <span style="font-size:13px; font-weight:700; color:#1a1a1a;">{from_name}</span>
    <span style="font-size:11px; color:#999;">{rel}</span>
  </div>
  <div style="font-size:13px; color:#333; margin-bottom:4px;">{subject}</div>
  {"<div style='font-size:12px; color:#555; margin-bottom:6px; line-height:1.4;'>" + summary + "</div>" if summary else ""}
  <div style="display:flex; align-items:center; gap:8px;">
    <span style="background:{color}; color:#fafaf5; font-size:11px; padding:2px 8px; border-radius:3px;">{label}</span>
    <a href="{link}" target="_blank"
       style="font-size:11px; color:#2d6a4f; text-decoration:none; margin-left:auto;">[open in gmail]</a>
  </div>
</div>
"""


def _bullet_row(em: dict) -> str:
    sender = (em.get("from_name") or em.get("from_address", "")).replace("<", "&lt;")
    subject = em.get("subject", "").replace("<", "&lt;")
    summary = (em.get("summary") or "").replace("<", "&lt;")
    rel = _rel_date(em.get("received_at", ""))
    link = em.get("gmail_link", "#")

    return f"""
<div style="display:flex; gap:10px; padding:7px 0; border-bottom:1px solid #f0f0e8;
            align-items:flex-start; font-family:'JetBrains Mono',monospace;">
  <span style="color:#bbb; font-size:11px; white-space:nowrap; min-width:70px; padding-top:1px;">{rel}</span>
  <div style="flex:1; min-width:0;">
    <span style="font-weight:700; font-size:12px; color:#1a1a1a;">{sender}</span>
    <span style="color:#555; font-size:12px;"> — {subject}</span>
    {"<div style='font-size:11px; color:#888; margin-top:2px; line-height:1.4;'>" + summary + "</div>" if summary else ""}
  </div>
  <a href="{link}" target="_blank"
     style="font-size:11px; color:#2d6a4f; text-decoration:none; white-space:nowrap; padding-top:1px;">[open]</a>
</div>
"""


def _section_header(label: str, color: str, count: int) -> str:
    return f"""
<div style="display:flex; align-items:center; gap:8px; margin:20px 0 8px;
            font-family:'JetBrains Mono',monospace;">
  <span style="font-size:12px; font-weight:700; color:{color};">{label}</span>
  <span style="font-size:11px; color:#bbb;">({count})</span>
</div>
"""


def render_digest():
    week_ago = (datetime.now() - timedelta(days=WEEK_DAYS)).strftime("%Y-%m-%d")
    today_str = str(date.today())

    all_emails = _cached_emails_week()
    recent = [e for e in all_emails if e.get("received_at", "") >= week_ago]

    if not recent:
        st.html("""
        <div style="padding:48px 0; text-align:center; color:#aaa;
                    font-size:13px; font-family:'JetBrains Mono',monospace;">
          no emails this week — run [sync] to fetch
        </div>
        """)
        return

    today_emails = [e for e in recent if e.get("received_at", "")[:10] == today_str]
    urgent   = [e for e in recent if e.get("category") in ("action", "alert")]
    finance  = [e for e in recent if e.get("category") == "finance"]
    personal = [e for e in recent if e.get("category") == "personal"]
    updates  = [e for e in recent if e.get("category") == "update"]

    unread_count = sum(1 for e in recent if not e.get("is_read"))

    # ── Top stats ───────────────────────────────────────────────────────────
    urgent_part = (
        f' | <span style="color:#c0392b; font-weight:700;">[!] {len(urgent)} need attention</span>'
        if urgent else
        ' | <span style="color:#2d6a4f;">[ok] nothing urgent</span>'
    )
    st.html(f"""
    <div class="stat-bar">
      <span class="stat-item">this week: <span>{len(recent)}</span></span>
      <span class="stat-item">unread: <span>{unread_count}</span></span>
      <span class="stat-item">today: <span>{len(today_emails)}</span></span>
      {urgent_part}
    </div>
    """)

    # ── Section 1: Needs attention ───────────────────────────────────────────
    if urgent:
        st.html(_section_header("[!] needs attention", "#c0392b", len(urgent)))
        st.html("".join(_urgent_card(e) for e in urgent))
    else:
        st.html("""
        <div style="font-family:'JetBrains Mono',monospace; font-size:13px;
                    color:#2d6a4f; padding:8px 0 4px;">
          [ok] inbox clear — no actions or alerts this week
        </div>
        """)

    # ── Section 2: Finance ───────────────────────────────────────────────────
    if finance:
        st.html(_section_header("[finance]", CATEGORY_COLORS["finance"], len(finance)))
        st.html(f'<div>{"".join(_bullet_row(e) for e in finance)}</div>')

    # ── Section 3: Personal ──────────────────────────────────────────────────
    if personal:
        st.html(_section_header("[personal]", CATEGORY_COLORS["personal"], len(personal)))
        st.html(f'<div>{"".join(_bullet_row(e) for e in personal)}</div>')

    # ── Section 4: Updates / newsletters ────────────────────────────────────
    if updates:
        st.html(_section_header("[updates]", CATEGORY_COLORS["update"], len(updates)))
        st.html(f'<div>{"".join(_bullet_row(e) for e in updates)}</div>')

    # ── If only non-urgent emails ────────────────────────────────────────────
    if not finance and not personal and not updates and not urgent:
        st.html("""
        <div style="font-family:'JetBrains Mono',monospace; font-size:12px;
                    color:#aaa; padding:12px 0;">
          no categorised emails this week
        </div>
        """)
