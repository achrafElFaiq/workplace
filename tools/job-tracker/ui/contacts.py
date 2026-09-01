import streamlit as st

from db.queries import (
    add_contact, delete_contact, get_contact, list_contact_companies,
    list_contact_functions, list_contacts, update_contact_notes,
)

_FIELD_MAX_LEN = 18

_CARD_CSS = """
<style>
.st-key-contacts_grid .stButton > button {
    height: 92px;
    width: 100%;
    white-space: normal;
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 4;
    -webkit-box-orient: vertical;
    text-align: left;
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    line-height: 1.4;
    border: 1px solid #d4d4c8 !important;
    background: #fafaf5 !important;
    color: #1a1a1a !important;
    border-radius: 6px !important;
}
.st-key-contacts_grid .stButton > button:hover {
    background: #f0f0e8 !important;
    border-color: #2d6a4f !important;
    color: #1a1a1a !important;
}
</style>
"""

_DETAIL_STYLE = """
<style>
    .jt-contact-detail { font-family: 'JetBrains Mono', monospace; font-size: 13px; color: #1a1a1a; }
    .jt-contact-card { border: 1px solid #d4d4c8; border-radius: 6px; padding: 16px; background: #fafaf5; }
    .jt-contact-row { display: flex; padding: 7px 0; border-bottom: 1px solid #eee; }
    .jt-contact-row:last-child { border-bottom: none; }
    .jt-contact-label { color: #888; min-width: 120px; }
</style>
"""

_NEW_CONTACT_FIELDS = [
    "new_contact_first", "new_contact_last", "new_contact_function",
    "new_contact_company", "new_contact_email", "new_contact_phone",
]


@st.cache_data(ttl=60)
def _cached_contacts(name_query=None, company=None, function=None):
    return list_contacts(name_query=name_query, company=company, function=function)


@st.cache_data(ttl=60)
def _cached_companies():
    return list_contact_companies()


@st.cache_data(ttl=60)
def _cached_functions():
    return list_contact_functions()


def _truncate(text: str, max_len: int = _FIELD_MAX_LEN) -> str:
    text = text or "N/A"
    return text if len(text) <= max_len else text[: max_len - 1].rstrip() + "…"


def _card_label(c: dict) -> str:
    name = f"{c.get('first_name') or ''} {c.get('last_name') or ''}".strip() or "N/A"
    parts = [_truncate(name), _truncate(c.get("function")), _truncate(c.get("company"))]
    return " - ".join(parts)


@st.dialog("Ajouter un contact")
def _add_contact_dialog():
    first_name = st.text_input("Prenom", key="new_contact_first")
    last_name = st.text_input("Nom", key="new_contact_last")
    function = st.text_input("Fonction", key="new_contact_function")
    company = st.text_input("Entreprise", key="new_contact_company")
    email = st.text_input("Email (optionnel)", key="new_contact_email")
    phone = st.text_input("Telephone (optionnel)", key="new_contact_phone")

    if st.button("[save] Enregistrer", type="primary", key="add_contact_btn"):
        if not last_name and not first_name:
            st.warning("Renseigne au moins un nom ou un prenom.")
        else:
            add_contact({
                "first_name": first_name or None,
                "last_name": last_name or None,
                "function": function or None,
                "company": company or None,
                "email": email or None,
                "phone": phone or None,
            })
            st.cache_data.clear()
            for field_key in _NEW_CONTACT_FIELDS:
                st.session_state.pop(field_key, None)
            st.toast("Contact ajoute", icon="✅")
            st.rerun()


@st.dialog("Contact", width="large")
def _show_contact(contact_id: int):
    c = get_contact(contact_id)
    if not c:
        st.error("Contact introuvable.")
        return

    name = f"{c.get('first_name') or ''} {c.get('last_name') or ''}".strip() or "N/A"

    st.html(_DETAIL_STYLE)
    st.html(f"""
    <div class="jt-contact-detail">
        <div class="jt-contact-card">
            <div class="jt-contact-row"><span class="jt-contact-label">Nom complet:</span><span>{name}</span></div>
            <div class="jt-contact-row"><span class="jt-contact-label">Fonction:</span><span>{c.get('function') or 'N/A'}</span></div>
            <div class="jt-contact-row"><span class="jt-contact-label">Entreprise:</span><span>{c.get('company') or 'N/A'}</span></div>
            <div class="jt-contact-row"><span class="jt-contact-label">Email:</span><span>{c.get('email') or 'N/A'}</span></div>
            <div class="jt-contact-row"><span class="jt-contact-label">Telephone:</span><span>{c.get('phone') or 'N/A'}</span></div>
        </div>
    </div>
    """)

    st.divider()
    notes = st.text_area("Note", value=c.get("notes") or "", height=150, key=f"contact_notes_{c['id']}")
    if st.button("[save] Enregistrer la note", key=f"save_notes_{c['id']}"):
        update_contact_notes(c["id"], notes)
        st.cache_data.clear()
        st.toast("Note enregistree", icon="✅")
        st.rerun()

    st.divider()
    if st.button("[x] Supprimer le contact", key=f"delete_contact_{c['id']}"):
        st.session_state[f"confirm_delete_contact_{c['id']}"] = True

    if st.session_state.get(f"confirm_delete_contact_{c['id']}"):
        st.warning("Irreversible. Tu confirmes ?")
        col1, col2 = st.columns(2)
        if col1.button("Oui", key=f"yes_del_contact_{c['id']}"):
            delete_contact(c["id"])
            del st.session_state[f"confirm_delete_contact_{c['id']}"]
            st.cache_data.clear()
            st.toast("Contact supprime", icon="🗑")
            st.rerun()
        if col2.button("Non", key=f"no_del_contact_{c['id']}"):
            del st.session_state[f"confirm_delete_contact_{c['id']}"]
            st.rerun()


def render_contacts():
    st.title("Contacts")

    if st.button("[+] Ajouter un contact", type="primary"):
        _add_contact_dialog()

    st.divider()

    col1, col2, col3 = st.columns(3)
    name_query = col1.text_input("Recherche (nom complet)", key="contact_search_name")
    company_filter = col2.selectbox("Entreprise", ["Tous"] + _cached_companies(), key="contact_filter_company")
    function_filter = col3.selectbox("Fonction", ["Tous"] + _cached_functions(), key="contact_filter_function")

    contacts = _cached_contacts(
        name_query=name_query or None,
        company=None if company_filter == "Tous" else company_filter,
        function=None if function_filter == "Tous" else function_filter,
    )

    st.divider()

    if not contacts:
        st.info("Aucun contact.")
        return

    st.html(_CARD_CSS)
    with st.container(key="contacts_grid"):
        cols_per_row = 4
        columns = st.columns(cols_per_row)
        for i, c in enumerate(contacts):
            with columns[i % cols_per_row]:
                if st.button(_card_label(c), key=f"contact_card_{c['id']}", use_container_width=True):
                    _show_contact(c["id"])
