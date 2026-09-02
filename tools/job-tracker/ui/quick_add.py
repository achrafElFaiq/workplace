import os
import streamlit as st
from parser.scraper import fetch_url, clean_pasted_text
from parser.extractor import extract_job_data
from db.queries import add_application, add_document
from ui.components import SOURCES
from config import GMAIL_EMAILS, DOCUMENTS_DIR
from latex.compiler import LatexCompileError
from latex.storage import save_generated


def render_quick_add():
    st.title("Nouvelle candidature")

    # Step 1: URL input
    if "add_step" not in st.session_state:
        st.session_state["add_step"] = "url"

    if st.session_state["add_step"] == "url":
        url = st.text_input("Colle le lien de l'offre", placeholder="https://...")
        add_row = st.container(key="jt_add_row")
        col1, col2 = add_row.columns([1, 4])
        if col1.button("➕ Ajouter", type="primary", use_container_width=True):
            if not url:
                st.warning("Colle un lien.")
                return
            with st.spinner("Scraping..."):
                raw = fetch_url(url)
            if raw:
                st.session_state["raw_text"] = raw
                st.session_state["url"] = url
                st.session_state["add_step"] = "confirm"
                with st.spinner("Extraction LLM..."):
                    data = extract_job_data(raw)
                if data:
                    data["url"] = url
                    data["raw_text"] = raw
                    st.session_state["extracted"] = data
                    st.rerun()
                else:
                    st.error("Extraction échouée. Essaie en collant le texte.")
                    st.session_state["add_step"] = "text"
                    st.rerun()
            else:
                st.session_state["url"] = url
                st.session_state["add_step"] = "text"
                st.rerun()

        if col2.button("Coller le texte manuellement"):
            st.session_state["url"] = ""
            st.session_state["add_step"] = "text"
            st.rerun()

    elif st.session_state["add_step"] == "text":
        st.info("Le scraping a échoué ou tu préfères coller le texte. Pas de souci.")
        text = st.text_area("Colle la description de l'offre", height=300)
        url_fallback = st.text_input("URL (optionnel)", value=st.session_state.get("url", ""))
        if st.button("➕ Extraire", type="primary"):
            if not text:
                st.warning("Colle le texte de l'offre.")
                return
            cleaned = clean_pasted_text(text)
            with st.spinner("Extraction LLM..."):
                data = extract_job_data(cleaned)
            if data:
                data["url"] = url_fallback
                data["raw_text"] = cleaned
                st.session_state["extracted"] = data
                st.session_state["add_step"] = "confirm"
                st.rerun()
            else:
                st.error("Extraction échouée. Vérifie le texte et réessaie.")

        if st.button("← Retour"):
            st.session_state["add_step"] = "url"
            st.rerun()

    elif st.session_state["add_step"] == "confirm":
        data = st.session_state["extracted"]
        st.success(f"**{data.get('company')}** · {data.get('position')}")

        col1, col2 = st.columns(2)
        data["source"] = col1.selectbox("Source", SOURCES)
        data["applied_via_email"] = col2.selectbox("Email utilisé", GMAIL_EMAILS)

        with st.expander("Détail de l'extraction", expanded=False):
            st.json(data)

        # Keywords
        keywords = data.get("keywords") or []
        if keywords:
            st.markdown("**Mots-clés**")
            st.html(
                '<div style="display:flex; flex-wrap:wrap; gap:6px; margin-bottom:12px;">'
                + "".join(
                    f'<span style="font-family:JetBrains Mono,monospace; font-size:11px; '
                    f'padding:3px 10px; border:1px solid #2d6a4f; border-radius:3px; '
                    f'color:#2d6a4f; background:#e8f5ec;">{kw}</span>'
                    for kw in keywords
                )
                + '</div>'
            )

        st.divider()
        col_gen_cv, col_gen_lm = st.columns(2)
        with col_gen_cv:
            if st.button("[cv] Générer CV", use_container_width=True):
                with st.spinner("Génération du CV..."):
                    try:
                        from latex.cv_generator import generate_cv_pdf
                        pdf_bytes, tex_content, warnings = generate_cv_pdf(data)
                        st.session_state["pending_cv_pdf"] = pdf_bytes
                        st.session_state["pending_cv_tex"] = tex_content
                        for w in warnings:
                            st.warning(w)
                    except LatexCompileError as e:
                        st.error("Erreur de compilation LaTeX")
                        with st.expander("Log de compilation"):
                            st.code(e.log[-3000:])
                    except Exception as e:
                        st.error(f"Erreur génération CV: {e}")
            if st.session_state.get("pending_cv_pdf"):
                st.download_button(
                    "[dl] Télécharger CV",
                    data=st.session_state["pending_cv_pdf"],
                    file_name=f"CV_{data.get('company')}_{data.get('position')}.pdf",
                    mime="application/pdf",
                    key="dl_pending_cv",
                    use_container_width=True,
                )

        with col_gen_lm:
            if st.button("[lm] Générer Lettre de motivation", use_container_width=True):
                with st.spinner("Génération de la lettre..."):
                    try:
                        from latex.cover_letter_generator import generate_cover_letter_pdf
                        pdf_bytes, tex_content, warnings = generate_cover_letter_pdf(data)
                        st.session_state["pending_lm_pdf"] = pdf_bytes
                        st.session_state["pending_lm_tex"] = tex_content
                        for w in warnings:
                            st.warning(w)
                    except LatexCompileError as e:
                        st.error("Erreur de compilation LaTeX")
                        with st.expander("Log de compilation"):
                            st.code(e.log[-3000:])
                    except Exception as e:
                        st.error(f"Erreur génération lettre: {e}")
            if st.session_state.get("pending_lm_pdf"):
                st.download_button(
                    "[dl] Télécharger Lettre",
                    data=st.session_state["pending_lm_pdf"],
                    file_name=f"LM_{data.get('company')}_{data.get('position')}.pdf",
                    mime="application/pdf",
                    key="dl_pending_lm",
                    use_container_width=True,
                )

        # Documents
        st.divider()
        st.markdown("**Documents**")
        uploaded_files = st.file_uploader(
            "Joindre des documents (CV, lettre, etc.)",
            accept_multiple_files=True,
            key="pending_docs",
        )
        if uploaded_files:
            for uf in uploaded_files:
                st.caption(f"[file] {uf.name} ({uf.size // 1024} KB)")

        st.divider()
        col_save, col_edit, col_cancel = st.columns(3)
        if col_save.button("✅ Sauvegarder", type="primary", use_container_width=True):
            app_id = add_application(data)
            if st.session_state.get("pending_cv_tex"):
                save_generated(app_id, "cv", st.session_state["pending_cv_tex"])
            if st.session_state.get("pending_lm_tex"):
                save_generated(app_id, "lettre", st.session_state["pending_lm_tex"])
            if uploaded_files:
                doc_dir = os.path.join(DOCUMENTS_DIR, str(app_id))
                os.makedirs(doc_dir, exist_ok=True)
                for uf in uploaded_files:
                    filepath = os.path.join(doc_dir, uf.name)
                    with open(filepath, "wb") as f:
                        f.write(uf.getbuffer())
                    ext = os.path.splitext(uf.name)[1].lower()
                    doc_type = {".pdf": "pdf", ".docx": "docx", ".doc": "doc", ".txt": "text"}.get(ext, "other")
                    add_document(app_id, uf.name, filepath, doc_type)
            st.session_state.pop("pending_cv_pdf", None)
            st.session_state.pop("pending_cv_tex", None)
            st.session_state.pop("pending_lm_pdf", None)
            st.session_state.pop("pending_lm_tex", None)
            st.cache_data.clear()
            st.session_state["add_step"] = "url"
            del st.session_state["extracted"]
            st.toast(f"Candidature #{app_id} ajoutée — {data['company']} / {data['position']}", icon="✅")
            st.rerun()

        if col_edit.button("✏️ Corriger le texte", use_container_width=True):
            st.session_state["add_step"] = "text"
            st.session_state.pop("pending_cv_pdf", None)
            st.session_state.pop("pending_cv_tex", None)
            st.session_state.pop("pending_lm_pdf", None)
            st.session_state.pop("pending_lm_tex", None)
            del st.session_state["extracted"]
            st.rerun()

        if col_cancel.button("❌ Annuler", use_container_width=True):
            st.session_state["add_step"] = "url"
            st.session_state.pop("pending_cv_pdf", None)
            st.session_state.pop("pending_cv_tex", None)
            st.session_state.pop("pending_lm_pdf", None)
            st.session_state.pop("pending_lm_tex", None)
            if "extracted" in st.session_state:
                del st.session_state["extracted"]
            st.rerun()