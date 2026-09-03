import json
import os
from flask import Flask, send_file, jsonify, request, Response
from db.database import init_db
from db.queries import (
    add_application, get_application, list_applications, update_application,
    update_status, update_notes, delete_application, mark_ghosted, export_csv,
    list_application_companies, list_application_positions, list_application_locations,
    get_emails_for_application, get_status_history, get_stats,
    add_contact, list_contacts, get_contact, update_contact_notes, delete_contact,
    list_contact_companies, list_contact_functions,
    add_document, list_documents, delete_document,
)
from config import GMAIL_EMAILS, DOCUMENTS_DIR

app = Flask(__name__)
init_db()


@app.route("/")
def index():
    return send_file("index.html")


# ── Applications ──

@app.route("/api/stats")
def api_stats():
    return jsonify(get_stats())


@app.route("/api/applications")
def api_applications():
    apps = list_applications(
        status=request.args.get("status"),
        source=request.args.get("source"),
        company=request.args.get("company"),
        position=request.args.get("position"),
        location=request.args.get("location"),
    )
    return jsonify(apps)


@app.route("/api/applications/<int:app_id>")
def api_application(app_id):
    a = get_application(app_id)
    if not a:
        return jsonify({"error": "not found"}), 404
    return jsonify(a)


@app.route("/api/applications", methods=["POST"])
def api_add_application():
    data = request.json
    app_id = add_application(data)
    return jsonify({"id": app_id})


@app.route("/api/applications/<int:app_id>", methods=["PUT"])
def api_update_application(app_id):
    data = request.json
    update_application(app_id, data)
    return jsonify({"ok": True})


@app.route("/api/applications/<int:app_id>/status", methods=["PUT"])
def api_update_status(app_id):
    data = request.json
    update_status(app_id, data["status"])
    return jsonify({"ok": True})


@app.route("/api/applications/<int:app_id>", methods=["DELETE"])
def api_delete_application(app_id):
    delete_application(app_id)
    return jsonify({"ok": True})


@app.route("/api/applications/<int:app_id>/emails")
def api_emails(app_id):
    return jsonify(get_emails_for_application(app_id))


@app.route("/api/applications/<int:app_id>/history")
def api_history(app_id):
    return jsonify(get_status_history(app_id))


@app.route("/api/applications/<int:app_id>/documents")
def api_documents(app_id):
    return jsonify(list_documents(app_id))


@app.route("/api/applications/<int:app_id>/documents", methods=["POST"])
def api_upload_document(app_id):
    if "file" not in request.files:
        return jsonify({"error": "no file"}), 400
    f = request.files["file"]
    doc_dir = os.path.join(DOCUMENTS_DIR, str(app_id))
    os.makedirs(doc_dir, exist_ok=True)
    filepath = os.path.join(doc_dir, f.filename)
    f.save(filepath)
    ext = os.path.splitext(f.filename)[1].lower()
    doc_type = {".pdf": "pdf", ".docx": "docx", ".doc": "doc", ".txt": "text"}.get(ext, "other")
    doc_id = add_document(app_id, f.filename, filepath, doc_type)
    return jsonify({"id": doc_id})


@app.route("/api/documents/<int:doc_id>", methods=["DELETE"])
def api_delete_document(doc_id):
    filepath = delete_document(doc_id)
    if filepath and os.path.isfile(filepath):
        os.remove(filepath)
    return jsonify({"ok": True})


@app.route("/api/documents/<int:doc_id>/download")
def api_download_document(doc_id):
    from db.database import get_connection
    conn = get_connection()
    row = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
    conn.close()
    if not row or not os.path.isfile(row["filepath"]):
        return jsonify({"error": "not found"}), 404
    return send_file(row["filepath"], as_attachment=True, download_name=row["filename"])


@app.route("/api/filter-options")
def api_filter_options():
    return jsonify({
        "companies": list_application_companies(),
        "positions": list_application_positions(),
        "locations": list_application_locations(),
    })


# ── Scraping & Extraction ──

@app.route("/api/scrape", methods=["POST"])
def api_scrape():
    from parser.scraper import fetch_url
    url = request.json.get("url", "")
    if not url:
        return jsonify({"error": "no url"}), 400
    text = fetch_url(url)
    if not text:
        return jsonify({"text": None})
    return jsonify({"text": text})


@app.route("/api/extract", methods=["POST"])
def api_extract():
    from parser.extractor import extract_job_data
    text = request.json.get("text", "")
    if not text:
        return jsonify({"error": "no text"}), 400
    data = extract_job_data(text)
    return jsonify({"data": data})


@app.route("/api/clean-text", methods=["POST"])
def api_clean_text():
    from parser.scraper import clean_pasted_text
    text = request.json.get("text", "")
    return jsonify({"text": clean_pasted_text(text)})


# ── Gmail Sync ──

@app.route("/api/sync-emails", methods=["POST"])
def api_sync_emails():
    from gmail.matcher import sync_emails
    result = sync_emails()
    return jsonify(result)


@app.route("/api/ghosted", methods=["POST"])
def api_ghosted():
    count = mark_ghosted()
    return jsonify({"count": count})


@app.route("/api/export")
def api_export():
    csv_data = export_csv()
    return Response(csv_data, mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=candidatures.csv"})


# ── Contacts ──

@app.route("/api/contacts")
def api_contacts():
    return jsonify(list_contacts(
        name_query=request.args.get("name"),
        company=request.args.get("company"),
        function=request.args.get("function"),
    ))


@app.route("/api/contacts", methods=["POST"])
def api_add_contact():
    data = request.json
    cid = add_contact(data)
    return jsonify({"id": cid})


@app.route("/api/contacts/<int:cid>")
def api_contact(cid):
    c = get_contact(cid)
    if not c:
        return jsonify({"error": "not found"}), 404
    return jsonify(c)


@app.route("/api/contacts/<int:cid>/notes", methods=["PUT"])
def api_update_contact_notes(cid):
    update_contact_notes(cid, request.json.get("notes", ""))
    return jsonify({"ok": True})


@app.route("/api/contacts/<int:cid>", methods=["DELETE"])
def api_delete_contact(cid):
    delete_contact(cid)
    return jsonify({"ok": True})


@app.route("/api/contacts/filter-options")
def api_contact_filter_options():
    return jsonify({
        "companies": list_contact_companies(),
        "functions": list_contact_functions(),
    })


# ── Config ──

@app.route("/api/config")
def api_get_config():
    import yaml
    from config import CONFIG_PATH
    try:
        with open(CONFIG_PATH) as f:
            cfg = yaml.safe_load(f) or {}
    except FileNotFoundError:
        cfg = {}
    return jsonify({
        "openrouter_api_key": cfg.get("openrouter_api_key", ""),
        "openrouter_model": cfg.get("openrouter_model", "google/gemini-2.5-flash"),
        "gmail_accounts": cfg.get("gmail_accounts", []),
    })


@app.route("/api/config", methods=["POST"])
def api_save_config():
    import yaml
    from config import CONFIG_PATH
    try:
        with open(CONFIG_PATH) as f:
            cfg = yaml.safe_load(f) or {}
    except FileNotFoundError:
        cfg = {}
    data = request.json
    cfg["openrouter_api_key"] = data.get("openrouter_api_key", "")
    cfg["openrouter_model"] = data.get("openrouter_model", "google/gemini-2.5-flash")
    cfg["gmail_accounts"] = data.get("gmail_accounts", [])
    with open(CONFIG_PATH, "w") as f:
        yaml.dump(cfg, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    return jsonify({"ok": True})


@app.route("/api/gmail-emails")
def api_gmail_emails():
    return jsonify(GMAIL_EMAILS)


# ── LaTeX Generation ──

@app.route("/api/generate/cv", methods=["POST"])
def api_generate_cv():
    from latex.cv_generator import generate_cv_pdf
    from latex.compiler import LatexCompileError
    data = request.json
    try:
        pdf_bytes, tex_content, warnings = generate_cv_pdf(data)
        import base64
        return jsonify({
            "pdf": base64.b64encode(pdf_bytes).decode(),
            "tex": tex_content,
            "warnings": warnings,
        })
    except LatexCompileError as e:
        return jsonify({"error": "compile_error", "log": e.log[-3000:]}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/generate/cover-letter", methods=["POST"])
def api_generate_cover_letter():
    from latex.cover_letter_generator import generate_cover_letter_pdf
    from latex.compiler import LatexCompileError
    data = request.json
    try:
        pdf_bytes, tex_content, warnings = generate_cover_letter_pdf(data)
        import base64
        return jsonify({
            "pdf": base64.b64encode(pdf_bytes).decode(),
            "tex": tex_content,
            "warnings": warnings,
        })
    except LatexCompileError as e:
        return jsonify({"error": "compile_error", "log": e.log[-3000:]}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/compile/<int:app_id>/<kind>", methods=["POST"])
def api_compile_generated(app_id, kind):
    from latex.storage import compile_generated, get_generated_tex
    from latex.compiler import LatexCompileError
    if kind not in ("cv", "lettre"):
        return jsonify({"error": "invalid kind"}), 400
    if get_generated_tex(app_id, kind) is None:
        return jsonify({"error": "no tex"}), 404
    try:
        pdf_bytes = compile_generated(app_id, kind)
        import base64
        return jsonify({"pdf": base64.b64encode(pdf_bytes).decode()})
    except LatexCompileError as e:
        return jsonify({"error": "compile_error", "log": e.log[-3000:]}), 500


@app.route("/api/generated/<int:app_id>/<kind>")
def api_has_generated(app_id, kind):
    from latex.storage import get_generated_tex
    return jsonify({"exists": get_generated_tex(app_id, kind) is not None})


@app.route("/api/save-generated", methods=["POST"])
def api_save_generated():
    from latex.storage import save_generated
    data = request.json
    save_generated(data["app_id"], data["kind"], data["tex"])
    return jsonify({"ok": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8501))
    app.run(host="0.0.0.0", port=port, debug=False)
