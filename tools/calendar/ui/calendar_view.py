import streamlit as st
import calendar as cal_module
from datetime import date, timedelta
from config import CATEGORY_COLORS
from db.queries import get_events_for_month, get_events_for_range, get_event, delete_event

MONTH_NAMES = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]
DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

START_HOUR = 9
END_HOUR = 21
PX_PER_HOUR = 36
TIMELINE_HEIGHT = (END_HOUR - START_HOUR) * PX_PER_HOUR
HEADER_ROW_HEIGHT = 26
ALLDAY_ROW_HEIGHT = 24


def _time_to_px(time_str: str) -> int:
    h, m = int(time_str[:2]), int(time_str[3:5])
    h = max(START_HOUR, min(END_HOUR, h))
    return (h - START_HOUR) * PX_PER_HOUR + int(m * PX_PER_HOUR / 60)


def _duration_px(start: str, end: str) -> int:
    s = _time_to_px(start)
    e = _time_to_px(end)
    return max(24, e - s)


def _to_minutes(time_str: str) -> int:
    return int(time_str[:2]) * 60 + int(time_str[3:5])


def _layout_overlaps(events: list[dict]) -> list[tuple[dict, int, int]]:
    """Assign each timed event a (column, total_columns) pair so overlapping
    events render side by side instead of stacking on top of each other."""
    items = []
    for e in events:
        start = _to_minutes(e["time"])
        end = _to_minutes(e["end_time"]) if e.get("end_time") else start + 30
        items.append({"event": e, "start": start, "end": max(end, start + 15)})
    items.sort(key=lambda it: (it["start"], it["end"]))

    clusters: list[list[dict]] = []
    cluster: list[dict] = []
    cluster_end = None
    for it in items:
        if cluster and it["start"] < cluster_end:
            cluster.append(it)
            cluster_end = max(cluster_end, it["end"])
        else:
            if cluster:
                clusters.append(cluster)
            cluster = [it]
            cluster_end = it["end"]
    if cluster:
        clusters.append(cluster)

    result: list[tuple[dict, int, int]] = []
    for clu in clusters:
        col_ends: list[int] = []
        assignment: list[int] = []
        for it in clu:
            placed = False
            for idx, col_end in enumerate(col_ends):
                if it["start"] >= col_end:
                    col_ends[idx] = it["end"]
                    assignment.append(idx)
                    placed = True
                    break
            if not placed:
                col_ends.append(it["end"])
                assignment.append(len(col_ends) - 1)
        total = len(col_ends)
        for it, col in zip(clu, assignment):
            result.append((it["event"], col, total))
    return result


def _proxy_click_script(selector_attr: str, key_prefix: str) -> str:
    """Bridges a click on an HTML element to a hidden native Streamlit button,
    so Streamlit performs its normal in-place rerun instead of a page navigation."""
    return f"""
<script>
document.querySelectorAll('[{selector_attr}]').forEach(function (el) {{
  el.addEventListener('click', function (evt) {{
    evt.stopPropagation();
    var id = CSS.escape(el.getAttribute('{selector_attr}'));
    var btn = document.querySelector('.st-key-{key_prefix}' + id + ' button');
    if (btn) btn.click();
  }});
}});
</script>
"""


def _render_proxy_button(key: str, on_click):
    with st.container(key=key):
        if st.button(key, key=f"btn_{key}"):
            on_click()
            st.rerun()


def _init_state(today: date):
    st.session_state.setdefault("cal_year", today.year)
    st.session_state.setdefault("cal_month", today.month)
    st.session_state.setdefault("cal_view", "month")
    st.session_state.setdefault("selected_date", today)


def _render_nav(year: int, month: int, view: str, today: date):
    nav_container = st.container(key="cal_nav")
    with nav_container:
        col_views, col_prev, col_title, col_next, col_today = st.columns([3, 1, 5, 1, 1])

    with col_views:
        v_col1, v_col2 = st.columns(2)
        with v_col1:
            if st.button("[week]", key="view_week",
                         type="primary" if view == "week" else "secondary"):
                st.session_state["cal_view"] = "week"
                st.rerun()
        with v_col2:
            if st.button("[month]", key="view_month",
                         type="primary" if view == "month" else "secondary"):
                st.session_state["cal_view"] = "month"
                st.rerun()

    selected = st.session_state.get("selected_date", today)

    if view == "week":
        monday = selected - timedelta(days=selected.weekday())
        sunday = monday + timedelta(days=6)
        title = f"{monday.strftime('%d %b')} – {sunday.strftime('%d %b %Y')}"
    else:
        title = f"{MONTH_NAMES[month]} {year}"

    with col_prev:
        if st.button("[<]", key="nav_prev"):
            _nav_prev(view, year, month, selected, today)
    with col_title:
        st.html(
            f"<p style='text-align:center; font-family:JetBrains Mono,monospace; "
            f"color:#2d6a4f; font-weight:700; font-size:15px; margin:6px 0;'>{title}</p>"
        )
    with col_next:
        if st.button("[>]", key="nav_next"):
            _nav_next(view, year, month, selected, today)
    with col_today:
        if st.button("today", key="nav_today"):
            st.session_state["cal_year"] = today.year
            st.session_state["cal_month"] = today.month
            st.session_state["selected_date"] = today
            st.rerun()


def _nav_prev(view, year, month, selected, today):
    if view == "month":
        if month == 1:
            st.session_state["cal_month"] = 12
            st.session_state["cal_year"] = year - 1
        else:
            st.session_state["cal_month"] = month - 1
    elif view == "week":
        nd = selected - timedelta(days=7)
        st.session_state["selected_date"] = nd
        st.session_state["cal_year"] = nd.year
        st.session_state["cal_month"] = nd.month
    st.rerun()


def _nav_next(view, year, month, selected, today):
    if view == "month":
        if month == 12:
            st.session_state["cal_month"] = 1
            st.session_state["cal_year"] = year + 1
        else:
            st.session_state["cal_month"] = month + 1
    elif view == "week":
        nd = selected + timedelta(days=7)
        st.session_state["selected_date"] = nd
        st.session_state["cal_year"] = nd.year
        st.session_state["cal_month"] = nd.month
    st.rerun()


# ── Month view ────────────────────────────────────────────────────────────────

def _build_month_html(year: int, month: int, events_by_date: dict, selected: date) -> str:
    today = date.today()
    weeks = cal_module.monthcalendar(year, month)

    th = ("background:#f0f0e8; color:#888; font-size:12px; padding:8px 4px; "
          "border:1px solid #d4d4c8; text-align:center; font-family:'JetBrains Mono',monospace;")
    headers = "".join(f'<th style="{th}">{d}</th>' for d in DAY_NAMES)

    rows_html = ""
    for week in weeks:
        row = ""
        for day in week:
            if day == 0:
                row += '<td style="background:#f5f5f0; border:1px solid #d4d4c8; height:84px;"></td>'
                continue
            d = date(year, month, day)
            is_today = d == today
            is_sel = d == selected
            border = "2px solid #2d6a4f" if is_today else "1px solid #d4d4c8"
            bg = "#e8f5e9" if is_sel and not is_today else "#fafaf5"
            num_color = "#2d6a4f" if is_today else "#555"
            num_weight = "700" if is_today else "400"

            events = events_by_date.get(d, [])
            pills = ""
            for e in events[:3]:
                ec, fg = CATEGORY_COLORS.get(e["category"], ("#e0e0e0", "#555"))
                label = e["title"][:16] + "…" if len(e["title"]) > 16 else e["title"]
                t = f"{e['time'][:5]} " if e.get("time") and not e["all_day"] else ""
                pills += (
                    f'<div style="font-size:10px;padding:1px 4px;border-radius:3px;'
                    f'margin-bottom:2px;background:{ec};color:{fg};overflow:hidden;'
                    f'white-space:nowrap;text-overflow:ellipsis;">{t}{label}</div>'
                )
            if len(events) > 3:
                pills += f'<div style="font-size:10px;color:#aaa;">+{len(events)-3} more</div>'

            date_str = d.isoformat()
            row += (
                f'<td data-date="{date_str}" '
                f'style="border:{border};padding:6px;vertical-align:top;height:84px;'
                f'background:{bg};width:14.28%;cursor:pointer;" '
                f'onmouseover="this.style.background=\'#f0f0e8\'" '
                f'onmouseout="this.style.background=\'{bg}\'">'
                f'<span style="font-size:13px;color:{num_color};font-weight:{num_weight};'
                f'font-family:JetBrains Mono,monospace;display:block;margin-bottom:4px;">{day}</span>'
                f'{pills}</td>'
            )
        rows_html += f"<tr>{row}</tr>"

    js = _proxy_click_script("data-date", "daysel_")
    return (
        f'<div style="font-family:JetBrains Mono,monospace;overflow-x:auto;">'
        f'<table style="width:100%;border-collapse:collapse;">'
        f"<thead><tr>{headers}</tr></thead>"
        f"<tbody>{rows_html}</tbody>"
        f"</table></div>{js}"
    )


def _select_day(d: date):
    st.session_state["selected_date"] = d
    st.session_state["cal_year"] = d.year
    st.session_state["cal_month"] = d.month


def _render_month(year: int, month: int, events_by_date: dict):
    selected = st.session_state.get("selected_date", date.today())
    html = _build_month_html(year, month, events_by_date, selected)
    st.html(html, unsafe_allow_javascript=True)

    with st.container(key="cal_day_proxies"):
        for week in cal_module.monthcalendar(year, month):
            for day in week:
                if day == 0:
                    continue
                d = date(year, month, day)
                _render_proxy_button(f"daysel_{d.isoformat()}", lambda d=d: _select_day(d))

    _render_legend()


def _render_legend():
    parts = []
    for cat, (bg, fg) in CATEGORY_COLORS.items():
        parts.append(
            f'<span style="display:inline-block;padding:2px 8px;border-radius:3px;'
            f'background:{bg};color:{fg};font-size:11px;margin-right:6px;">{cat}</span>'
        )
    st.html(f'<div style="margin-top:12px;font-family:JetBrains Mono,monospace;">{"".join(parts)}</div>')


# ── Week view ─────────────────────────────────────────────────────────────────

def _build_week_html(days: list[date], events_by_date: dict) -> str:
    today = date.today()
    hours = list(range(START_HOUR, END_HOUR))
    total_h = TIMELINE_HEIGHT

    # Time axis — top spacer matches the day-column header + all-day rows
    spacer_h = HEADER_ROW_HEIGHT + ALLDAY_ROW_HEIGHT
    time_col = (
        f'<div style="width:48px;flex-shrink:0;">'
        f'<div style="height:{spacer_h}px;border-right:1px solid #d4d4c8;'
        f'box-sizing:border-box;"></div>'
        f'<div style="position:relative;height:{total_h}px;border-right:1px solid #d4d4c8;">'
    )
    for h in hours + [END_HOUR]:
        top = (h - START_HOUR) * PX_PER_HOUR
        offset = "-100%" if h == END_HOUR else "-6px"
        time_col += (
            f'<div style="position:absolute;top:{top}px;left:0;right:0;'
            f'font-size:10px;color:#888;font-family:JetBrains Mono,monospace;'
            f'padding-right:4px;text-align:right;transform:translateY({offset});">'
            f'{h:02d}:00</div>'
        )
    time_col += '</div></div>'

    # Day columns
    day_cols = ""
    for d in days:
        is_today = d == today
        hdr_color = "#2d6a4f" if is_today else "#555"
        hdr_weight = "700" if is_today else "400"
        hdr_bg = "#e8f5e9" if is_today else "#f0f0e8"
        label = d.strftime("%a %d")

        # Hour grid lines
        grid_lines = ""
        for h in hours:
            top = (h - START_HOUR) * PX_PER_HOUR
            grid_lines += (
                f'<div style="position:absolute;top:{top}px;left:0;right:0;'
                f'border-top:1px solid #eeeeee;"></div>'
            )

        # Events for this day
        evs_html = ""
        day_events = events_by_date.get(d, [])
        timed = [e for e in day_events if not e["all_day"] and e.get("time")]
        allday = [e for e in day_events if e["all_day"] or not e.get("time")]

        for e, col, cols in _layout_overlaps(timed):
            bg, fg = CATEGORY_COLORS.get(e["category"], ("#e0e0e0", "#555"))
            top = _time_to_px(e["time"])
            h_px = _duration_px(e["time"], e["end_time"]) if e.get("end_time") else 40
            h_px = min(h_px, TIMELINE_HEIGHT - top)
            t_label = e["time"][:5]
            if e.get("end_time"):
                t_label += f"–{e['end_time'][:5]}"
            ev_id = e["id"]
            width_pct = 100 / cols
            left_pct = col * width_pct
            evs_html += (
                f'<div data-event-id="{ev_id}" '
                f'style="position:absolute;top:{top}px;'
                f'left:calc({left_pct}% + 1px);width:calc({width_pct}% - 2px);'
                f'height:{h_px}px;background:{bg};color:{fg};border-radius:3px;'
                f'padding:2px 4px;font-size:10px;font-family:JetBrains Mono,monospace;'
                f'overflow:hidden;box-sizing:border-box;z-index:1;cursor:pointer;'
                f'border:1px solid #fafaf5;">'
                f'<div style="font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">'
                f'{e["title"]}</div>'
                f'<div style="font-size:9px;opacity:0.8;">{t_label}</div>'
                f'</div>'
            )

        # All-day strip — compact, fits within ALLDAY_ROW_HEIGHT
        allday_strip = ""
        for e in allday[:1]:
            bg, fg = CATEGORY_COLORS.get(e["category"], ("#e0e0e0", "#555"))
            allday_strip += (
                f'<div style="display:inline-block;background:{bg};color:{fg};font-size:9px;'
                f'padding:1px 4px;border-radius:2px;max-width:90%;white-space:nowrap;'
                f'overflow:hidden;text-overflow:ellipsis;vertical-align:top;">{e["title"]}</div>'
            )
        if len(allday) > 1:
            allday_strip += f'<span style="font-size:9px;color:#aaa;"> +{len(allday)-1}</span>'

        day_cols += (
            f'<div style="flex:1;min-width:0;border-left:1px solid #d4d4c8;">'
            f'<div style="background:{hdr_bg};padding:4px;text-align:center;'
            f'font-family:JetBrains Mono,monospace;font-size:12px;color:{hdr_color};'
            f'font-weight:{hdr_weight};border-bottom:1px solid #d4d4c8;height:{HEADER_ROW_HEIGHT}px;'
            f'box-sizing:border-box;">{label}</div>'
            f'<div style="padding:2px;border-bottom:1px solid #d4d4c8;'
            f'height:{ALLDAY_ROW_HEIGHT}px;box-sizing:border-box;overflow:hidden;">{allday_strip}</div>'
            f'<div style="position:relative;height:{total_h}px;">'
            f'{grid_lines}{evs_html}</div></div>'
        )

    js = _proxy_click_script("data-event-id", "eventsel_")
    return (
        f'<div style="font-family:JetBrains Mono,monospace;overflow-x:auto;">'
        f'<div style="display:flex;min-width:600px;">'
        f'{time_col}{day_cols}'
        f'</div></div>{js}'
    )


def _render_event_detail_panel(event: dict):
    bg, fg = CATEGORY_COLORS.get(event["category"], ("#e0e0e0", "#555"))
    time_str = ""
    if event.get("time"):
        end = f" → {event['end_time'][:5]}" if event.get("end_time") else ""
        time_str = f" [{event['time'][:5]}{end}]"
    desc = (f'<br><span style="font-size:11px;color:#888;">{event["description"]}</span>'
            if event.get("description") else "")

    st.html(
        f'<p style="font-family:JetBrains Mono,monospace;font-size:13px;'
        f'color:#2d6a4f;font-weight:700;margin:14px 0 6px;">-- event details --</p>'
    )
    col_ev, col_ed, col_del = st.columns([8, 2, 2])
    with col_ev:
        st.html(
            f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">'
            f'<span style="background:{bg};color:{fg};font-size:11px;padding:2px 6px;'
            f'border-radius:3px;font-family:JetBrains Mono,monospace;">{event["category"]}</span>'
            f'<span style="font-family:JetBrains Mono,monospace;font-size:13px;color:#333;">'
            f'{event["title"]}{time_str}</span>{desc}</div>'
        )
    with col_ed:
        with st.container(key=f"linkbtn_wedit_{event['id']}"):
            if st.button("[edit]", key=f"wedit_{event['id']}", help="Edit"):
                st.session_state["editing_event_id"] = event["id"]
                st.session_state.pop("selected_event_id", None)
                st.rerun()
    with col_del:
        with st.container(key=f"linkbtn_wdel_{event['id']}"):
            if st.button("[delete]", key=f"wdel_{event['id']}", help="Delete"):
                delete_event(event["id"])
                st.session_state.pop("selected_event_id", None)
                st.success(f"[ok] Event '{event['title']}' deleted.")
                st.rerun()


def _render_week(days: list[date], events: list):
    events_by_date: dict[date, list] = {}
    by_id: dict[int, dict] = {}
    for e in events:
        d = date.fromisoformat(e["date"])
        events_by_date.setdefault(d, []).append(e)
        by_id[e["id"]] = e

    html = _build_week_html(days, events_by_date)
    st.html(html, unsafe_allow_javascript=True)

    with st.container(key="cal_event_proxies"):
        for e in events:
            if not e["all_day"] and e.get("time"):
                eid = e["id"]
                _render_proxy_button(
                    f"eventsel_{eid}",
                    lambda eid=eid: st.session_state.update(selected_event_id=eid),
                )

    _render_legend()

    selected_event_id = st.session_state.get("selected_event_id")
    if selected_event_id is not None:
        event = by_id.get(selected_event_id) or get_event(selected_event_id)
        if event:
            _render_event_detail_panel(event)


# ── Entry point ───────────────────────────────────────────────────────────────

def render_calendar():
    today = date.today()
    _init_state(today)

    year = st.session_state["cal_year"]
    month = st.session_state["cal_month"]
    view = st.session_state["cal_view"]
    if view not in ("month", "week"):
        view = st.session_state["cal_view"] = "month"
    selected = st.session_state["selected_date"]

    _render_nav(year, month, view, today)

    if view == "month":
        events = get_events_for_month(year, month)
        events_by_date: dict[date, list] = {}
        for e in events:
            d = date.fromisoformat(e["date"])
            events_by_date.setdefault(d, []).append(e)
        _render_month(year, month, events_by_date)

    elif view == "week":
        monday = selected - timedelta(days=selected.weekday())
        sunday = monday + timedelta(days=6)
        events = get_events_for_range(monday.isoformat(), sunday.isoformat())
        days = [monday + timedelta(days=i) for i in range(7)]
        _render_week(days, events)
