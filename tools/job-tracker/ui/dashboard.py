import streamlit as st
from db.queries import (
    list_applications, update_status, update_application,
    delete_application, get_status_history, get_stats, mark_ghosted, export_csv,
    list_application_companies, list_application_positions, list_application_locations,
)
from ui.components import STATUSES, SOURCES
from ui.detail_view import render_application_summary

_STATUS_CARD_COLORS = {
    "applied": {"bg": "#e8f0fb", "border": "#4a7fc7"},
    "in_progress": {"bg": "#fdf6e3", "border": "#c9a227"},
    "accepted": {"bg": "#e8f5ec", "border": "#2d6a4f"},
    "rejected": {"bg": "#fbe9e9", "border": "#b3413e"},
    "Sans retour": {"bg": "#ececec", "border": "#888888"},
}
_DEFAULT_CARD_COLORS = {"bg": "#fafaf5", "border": "#d4d4c8"}


@st.cache_data(ttl=60)
def _cached_stats():
    return get_stats()


@st.cache_data(ttl=30)
def _cached_applications(status=None, source=None, company=None, position=None, location=None):
    return list_applications(status=status, source=source, company=company, position=position, location=location)


@st.cache_data(ttl=60)
def _cached_companies():
    return list_application_companies()


@st.cache_data(ttl=60)
def _cached_positions():
    return list_application_positions()


@st.cache_data(ttl=60)
def _cached_locations():
    return list_application_locations()


@st.cache_data(ttl=60)
def _cached_export_csv():
    return export_csv()


def _expander_css(app_id: int, status: str) -> str:
    colors = _STATUS_CARD_COLORS.get(status, _DEFAULT_CARD_COLORS)
    return f"""
    <style>
    .st-key-app_row_{app_id} [data-testid="stExpander"] {{
        border: 1px solid {colors['border']} !important;
        border-radius: 6px;
        background: {colors['bg']} !important;
    }}
    </style>
    """


def render_dashboard():
    st.title("Dashboard")

    # Top bar
    with st.container(key="jt_dash_actions"):
        c_sync, c_ghost, c_export = st.columns([1, 1, 1])
        with c_sync:
            if st.button("[sync] Gmail", use_container_width=True):
                from gmail.matcher import sync_emails
                with st.spinner("Sync en cours..."):
                    result = sync_emails()
                st.cache_data.clear()
                st.success(f"Fetched: {result['fetched']} | Matched: {result['matched']} | Skipped: {result['skipped']}")
        with c_ghost:
            if st.button("[ghost] 30j sans reponse", use_container_width=True):
                count = mark_ghosted()
                st.cache_data.clear()
                if count:
                    st.warning(f"{count} candidature(s) marquee(s) ghosted")
                    st.rerun()
                else:
                    st.info("Aucune candidature a marquer")
        with c_export:
            st.download_button("[export] CSV", data=_cached_export_csv(), file_name="candidatures.csv", mime="text/csv", use_container_width=True)

    # Stats
    stats = _cached_stats()
    with st.container(key="jt_stats"):
        metric_cols = st.columns(2 + len(STATUSES))
        metric_cols[0].metric("Total", stats["total"])
        metric_cols[1].metric("Taux de reponse", f"{stats['response_rate']}%")
        for i, status in enumerate(STATUSES):
            metric_cols[2 + i].metric(status, stats["by_status"].get(status, 0))

    st.divider()

    # Filters
    col1, col2 = st.columns(2)
    filter_status = col1.selectbox("Statut", ["Tous"] + STATUSES)
    filter_source = col2.selectbox("Source", ["Tous"] + SOURCES)

    col3, col4, col5 = st.columns(3)
    filter_company = col3.selectbox("Entreprise", ["Tous"] + _cached_companies())
    filter_position = col4.selectbox("Poste", ["Tous"] + _cached_positions())
    filter_location = col5.selectbox("Localisation", ["Tous"] + _cached_locations())

    apps = _cached_applications(
        status=filter_status if filter_status != "Tous" else None,
        source=filter_source if filter_source != "Tous" else None,
        company=filter_company if filter_company != "Tous" else None,
        position=filter_position if filter_position != "Tous" else None,
        location=filter_location if filter_location != "Tous" else None,
    )

    if not apps:
        st.info("Aucune candidature.")
        return

    for app in apps:
        label = f"{app['company']} · {app['position']} · {app.get('location') or 'N/A'} · {app['applied_at']}"
        with st.container(key=f"app_row_{app['id']}"):
            st.html(_expander_css(app["id"], app["status"]))
            with st.expander(label):
                _render_detail(app)



def _render_detail(app: dict):
    render_application_summary(app)

    # Status history
    history = get_status_history(app["id"])
    if len(history) > 1:
        with st.expander("Historique des statuts"):
            for h in history:
                st.caption(f"{h['changed_at']} · {h['old_status'] or '—'} -> {h['new_status']} ({h['trigger']})")

    # Status + actions
    tab_status, tab_edit = st.tabs(["Statut", "Modifier"])

    with tab_status:
        new_status = st.selectbox(
            "Changer le statut", STATUSES,
            index=STATUSES.index(app["status"]),
            key=f"status_{app['id']}",
        )
        if new_status != app["status"]:
            if st.button("[ok] Mettre a jour", key=f"update_{app['id']}"):
                update_status(app["id"], new_status)
                st.cache_data.clear()
                st.rerun()

        st.divider()
        if st.button("[x] Supprimer", key=f"delete_{app['id']}"):
            st.session_state[f"confirm_delete_{app['id']}"] = True

        if st.session_state.get(f"confirm_delete_{app['id']}"):
            st.warning("Irreversible. Tu confirmes ?")
            c1, c2 = st.columns(2)
            if c1.button("Oui", key=f"yes_del_{app['id']}"):
                delete_application(app["id"])
                del st.session_state[f"confirm_delete_{app['id']}"]
                st.session_state.pop("selected_app", None)
                st.cache_data.clear()
                st.rerun()
            if c2.button("Non", key=f"no_del_{app['id']}"):
                del st.session_state[f"confirm_delete_{app['id']}"]
                st.rerun()

    with tab_edit:
        edit_open_key = f"edit_open_{app['id']}"
        if edit_open_key not in st.session_state:
            st.session_state[edit_open_key] = False

        with st.expander("Champs de la candidature", expanded=st.session_state[edit_open_key]):
            company = st.text_input("Entreprise", value=app.get("company", ""), key=f"edit_company_{app['id']}")
            position = st.text_input("Poste", value=app.get("position", ""), key=f"edit_position_{app['id']}")
            location = st.text_input("Localisation", value=app.get("location", ""), key=f"edit_location_{app['id']}")
            contract_type = st.text_input("Contrat", value=app.get("contract_type", ""), key=f"edit_contract_{app['id']}")
            salary = st.text_input("Salaire", value=app.get("salary") or "", key=f"edit_salary_{app['id']}")
            seniority = st.text_input("Seniorite", value=app.get("seniority", ""), key=f"edit_seniority_{app['id']}")
            sector = st.text_input("Secteur", value=app.get("sector") or "", key=f"edit_sector_{app['id']}")
            contact = st.text_input("Contact", value=app.get("contact") or "", key=f"edit_contact_{app['id']}")
            stack = st.text_input("Stack (virgules)", value=", ".join(app.get("stack") or []), key=f"edit_stack_{app['id']}")
            notes = st.text_area("Notes", value=app.get("notes") or "", key=f"edit_notes_{app['id']}")

            if st.button("[save] Sauvegarder", key=f"save_edit_{app['id']}"):
                update_application(app["id"], {
                    "company": company, "position": position, "location": location,
                    "contract_type": contract_type, "salary": salary or None,
                    "seniority": seniority, "sector": sector or None,
                    "contact": contact or None,
                    "stack": [s.strip() for s in stack.split(",") if s.strip()],
                    "missions": app.get("missions", []),
                    "requirements": app.get("requirements", []),
                    "company_size": app.get("company_size"),
                    "notes": notes or None,
                })
                st.session_state[edit_open_key] = False
                st.cache_data.clear()
                st.toast("Modifications enregistrees", icon="✅")
                st.rerun()

        if not st.session_state[edit_open_key]:
            if st.button("[edit] Modifier les champs", key=f"open_edit_{app['id']}"):
                st.session_state[edit_open_key] = True
                st.rerun()
