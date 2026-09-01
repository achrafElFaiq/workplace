import streamlit as st
from db.queries import get_stats

STATUSES = ["applied", "in_progress", "accepted", "rejected", "Sans retour"]

STATUS_COLORS = {
    "applied": "🔵",
    "in_progress": "🟡",
    "accepted": "✅",
    "rejected": "❌",
    "Sans retour": "👻",
}

SOURCES = ["linkedin", "wttj", "indeed", "hellowork", "apec", "site_carriere", "email", "autre"]


def render_stats():
    stats = get_stats()
    cols = st.columns(4)
    cols[0].metric("Total", stats["total"])
    cols[1].metric("Taux de réponse", f"{stats['response_rate']}%")

    top_statuses = sorted(stats["by_status"].items(), key=lambda x: x[1], reverse=True)[:2]
    for i, (status, count) in enumerate(top_statuses):
        cols[i + 2].metric(f"{STATUS_COLORS.get(status, '')} {status}", count)