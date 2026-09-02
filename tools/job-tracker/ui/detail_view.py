import os
import streamlit as st
from db.queries import get_emails_for_application, list_documents, add_document, delete_document
from config import DOCUMENTS_DIR
from ui.components import STATUS_COLORS


@st.cache_data(ttl=120)
def _cached_emails(app_id: int):
    return get_emails_for_application(app_id)


def render_application_summary(app: dict):
    """Read-only rendering of an application: info card, missions,
    requirements, matched emails, and CV/lettre download. Used by the
    Dashboard, which adds its own mutating controls below it."""
    stack_str = ", ".join(app.get("stack") or []) or "N/A"
    missions_items = app.get("missions") or []
    requirements_items = app.get("requirements") or []
    url_link = f'<a href="{app["url"]}" target="_blank" style="color:#2d6a4f; text-decoration:none;">Voir l\'offre ↗</a>' if app.get("url") else "N/A"

    missions_block = ""
    if missions_items:
        missions_list = "".join(f"<li>{m}</li>" for m in missions_items)
        missions_block = f"""
        <div class="jt-card">
            <div class="jt-card-title">&gt; Missions</div>
            <ul class="jt-list">{missions_list}</ul>
        </div>
        """

    req_block = ""
    if requirements_items:
        req_list = "".join(f"<li>{r}</li>" for r in requirements_items)
        req_block = f"""
        <div class="jt-card">
            <div class="jt-card-title">&gt; Prerequis</div>
            <ul class="jt-list">{req_list}</ul>
        </div>
        """

    process_items = app.get("process") or []
    process_block = ""
    if process_items:
        process_list = "".join(f"<li>{p}</li>" for p in process_items)
        process_block = f"""
        <div class="jt-card">
            <div class="jt-card-title">&gt; Process de recrutement</div>
            <ol class="jt-list">{process_list}</ol>
        </div>
        """

    keywords_items = app.get("keywords") or []
    keywords_block = ""
    if keywords_items:
        kw_tags = "".join(
            f'<span style="display:inline-block; font-size:11px; padding:3px 10px; '
            f'border:1px solid #2d6a4f; border-radius:3px; color:#2d6a4f; '
            f'background:#e8f5ec; margin:3px;">{kw}</span>'
            for kw in keywords_items
        )
        keywords_block = f"""
        <div class="jt-card">
            <div class="jt-card-title">&gt; Mots-cles</div>
            <div style="display:flex; flex-wrap:wrap; gap:4px;">{kw_tags}</div>
        </div>
        """

    emails = _cached_emails(app["id"])
    emails_block = ""
    if emails:
        emails_rows = "".join(
            f'<div class="jt-row" style="border-bottom:1px solid #eee;">'
            f'<span style="color:#888;">[{em["classification"] or "other"}]</span> '
            f'<b>{em["subject"]}</b> '
            f'<span style="color:#888;">— {em["received_at"]}</span> '
            f'<a href="{em["gmail_link"]}" target="_blank" style="color:#2d6a4f;">↗</a>'
            f'</div>'
            for em in emails
        )
        emails_block = f"""
        <div class="jt-card">
            <div class="jt-card-title">&gt; Emails ({len(emails)})</div>
            {emails_rows}
        </div>
        """

    html = f"""
    <style>
        .jt-detail {{ font-family: 'JetBrains Mono', monospace; font-size: 13px; color: #1a1a1a; }}
        .jt-header {{ font-size: 16px; font-weight: 700; color: #2d6a4f; margin-bottom: 4px; }}
        .jt-sub {{ color: #888; font-size: 12px; margin-bottom: 16px; }}
        .jt-cards {{ display: flex; gap: 16px; margin-bottom: 14px; }}
        .jt-card {{ border: 1px solid #d4d4c8; border-radius: 6px; padding: 16px; margin-bottom: 14px; background: #fafaf5; }}
        .jt-card-half {{ flex: 1; border: 1px solid #d4d4c8; border-radius: 6px; padding: 16px; background: #fafaf5; }}
        .jt-card-title {{ color: #2d6a4f; font-weight: 700; margin-bottom: 10px; }}
        .jt-row {{ display: flex; padding: 7px 0; border-bottom: 1px solid #eee; }}
        .jt-row:last-child {{ border-bottom: none; }}
        .jt-label {{ color: #888; min-width: 110px; }}
        .jt-list {{ margin: 0; padding-left: 18px; line-height: 1.8; }}
        .jt-list li {{ padding: 2px 0; }}
    </style>

    <div class="jt-detail">
        <div class="jt-header">{app['company']} · {app['position']}</div>
        <div class="jt-sub">{app.get('location') or 'N/A'} · {app.get('source') or ''} · {STATUS_COLORS.get(app['status'], '')} {app['status']} · {app['applied_at']}</div>

        <div class="jt-cards">
            <div class="jt-card-half">
                <div class="jt-row"><span class="jt-label">Contrat:</span><span>{app.get('contract_type') or 'N/A'}</span></div>
                <div class="jt-row"><span class="jt-label">Salaire:</span><span>{app.get('salary') or 'Non mentionne'}</span></div>
                <div class="jt-row"><span class="jt-label">Seniorite:</span><span>{app.get('seniority') or 'N/A'}</span></div>
                <div class="jt-row"><span class="jt-label">Stack:</span><span>{stack_str}</span></div>
            </div>
            <div class="jt-card-half">
                <div class="jt-row"><span class="jt-label">Secteur:</span><span>{app.get('sector') or 'N/A'}</span></div>
                <div class="jt-row"><span class="jt-label">Contact:</span><span>{app.get('contact') or 'N/A'}</span></div>
                <div class="jt-row"><span class="jt-label">Offre:</span><span>{url_link}</span></div>
            </div>
        </div>

        {missions_block}
        {req_block}
        {process_block}
        {keywords_block}
        {emails_block}
    </div>
    """

    st.html(html)

    # CV / cover letter actually used for this application (LaTeX source
    # saved at add-time, in Quick Add — recompiled here on demand since only
    # the .tex is persisted, not the heavier PDF)
    from latex.compiler import LatexCompileError
    from latex.storage import compile_generated, get_generated_tex

    col_cv, col_lm = st.columns(2)
    with col_cv:
        if get_generated_tex(app["id"], "cv") is None:
            st.caption("[cv] Aucun CV genere pour cette candidature")
        else:
            if st.button("[cv] Compiler le CV utilise", key=f"compile_cv_{app['id']}", use_container_width=True):
                try:
                    st.session_state[f"cv_pdf_{app['id']}"] = compile_generated(app["id"], "cv")
                except LatexCompileError as e:
                    st.error("Erreur de compilation LaTeX")
                    with st.expander("Log de compilation"):
                        st.code(e.log[-3000:])
            if st.session_state.get(f"cv_pdf_{app['id']}"):
                st.download_button(
                    "[dl] Telecharger CV",
                    data=st.session_state[f"cv_pdf_{app['id']}"],
                    file_name=f"CV_{app['company']}_{app['position']}.pdf",
                    mime="application/pdf",
                    key=f"dl_cv_{app['id']}",
                    use_container_width=True,
                )

    with col_lm:
        if get_generated_tex(app["id"], "lettre") is None:
            st.caption("[lm] Aucune lettre generee pour cette candidature")
        else:
            if st.button("[lm] Compiler la lettre utilisee", key=f"compile_lm_{app['id']}", use_container_width=True):
                try:
                    st.session_state[f"lm_pdf_{app['id']}"] = compile_generated(app["id"], "lettre")
                except LatexCompileError as e:
                    st.error("Erreur de compilation LaTeX")
                    with st.expander("Log de compilation"):
                        st.code(e.log[-3000:])
            if st.session_state.get(f"lm_pdf_{app['id']}"):
                st.download_button(
                    "[dl] Telecharger Lettre",
                    data=st.session_state[f"lm_pdf_{app['id']}"],
                    file_name=f"LM_{app['company']}_{app['position']}.pdf",
                    mime="application/pdf",
                    key=f"dl_lm_{app['id']}",
                    use_container_width=True,
                )

    # Documents
    docs = list_documents(app["id"])
    with st.expander(f"Documents ({len(docs)})", expanded=False):
        if docs:
            for doc in docs:
                dc1, dc2 = st.columns([6, 1])
                dc1.caption(f"[{doc['doc_type'] or 'file'}] {doc['filename']}")
                if os.path.isfile(doc["filepath"]):
                    with open(doc["filepath"], "rb") as f:
                        dc1.download_button(
                            "[dl]", data=f.read(), file_name=doc["filename"],
                            key=f"dl_doc_{doc['id']}",
                        )
                if dc2.button("[x]", key=f"rm_doc_{doc['id']}"):
                    filepath = delete_document(doc["id"])
                    if filepath and os.path.isfile(filepath):
                        os.remove(filepath)
                    st.rerun()
        else:
            st.caption("Aucun document.")

        new_docs = st.file_uploader(
            "Ajouter des documents", accept_multiple_files=True,
            key=f"upload_docs_{app['id']}",
        )
        if new_docs and st.button("[save] Enregistrer documents", key=f"save_docs_{app['id']}"):
            doc_dir = os.path.join(DOCUMENTS_DIR, str(app["id"]))
            os.makedirs(doc_dir, exist_ok=True)
            for uf in new_docs:
                filepath = os.path.join(doc_dir, uf.name)
                with open(filepath, "wb") as f:
                    f.write(uf.getbuffer())
                ext = os.path.splitext(uf.name)[1].lower()
                doc_type = {".pdf": "pdf", ".docx": "docx", ".doc": "doc", ".txt": "text"}.get(ext, "other")
                add_document(app["id"], uf.name, filepath, doc_type)
            st.rerun()
