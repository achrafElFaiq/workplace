import json
import os
import shutil
from datetime import datetime, timedelta
from config import GENERATED_DIR
from db.database import get_connection


# ── Applications ──

def add_application(data: dict) -> int:
    conn = get_connection()
    cursor = conn.execute(
        """
        INSERT INTO applications
            (company, position, location, contract_type, salary,
             missions, stack, requirements, process, keywords, sector, company_size,
             contact, seniority, url, raw_text, source,
             applied_via_email, status, notes, applied_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data["company"],
            data["position"],
            data.get("location"),
            data.get("contract_type"),
            data.get("salary"),
            json.dumps(data.get("missions", []), ensure_ascii=False),
            json.dumps(data.get("stack", []), ensure_ascii=False),
            json.dumps(data.get("requirements", []), ensure_ascii=False),
            json.dumps(data.get("process", []), ensure_ascii=False),
            json.dumps(data.get("keywords", []), ensure_ascii=False),
            data.get("sector"),
            data.get("company_size"),
            data.get("contact"),
            data.get("seniority"),
            data.get("url"),
            data.get("raw_text"),
            data.get("source", "autre"),
            data.get("applied_via_email"),
            data.get("status", "applied"),
            data.get("notes"),
            data.get("applied_at", datetime.now().strftime("%Y-%m-%d")),
        ),
    )
    app_id = cursor.lastrowid

    # Initial status history entry
    conn.execute(
        "INSERT INTO status_history (application_id, old_status, new_status, trigger) VALUES (?, NULL, 'applied', 'creation')",
        (app_id,),
    )
    conn.commit()
    conn.close()
    return app_id


def get_application(app_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM applications WHERE id = ?", (app_id,)).fetchone()
    conn.close()
    if not row:
        return None
    app = dict(row)
    for field in ("missions", "stack", "requirements", "process", "keywords"):
        if app.get(field):
            app[field] = json.loads(app[field])
    return app


def list_applications(
    status: str = None, source: str = None,
    company: str = None, position: str = None, location: str = None,
) -> list[dict]:
    conn = get_connection()
    query = "SELECT * FROM applications WHERE 1=1"
    params = []
    if status:
        query += " AND status = ?"
        params.append(status)
    if source:
        query += " AND source = ?"
        params.append(source)
    if company:
        query += " AND LOWER(TRIM(company)) = LOWER(TRIM(?))"
        params.append(company)
    if position:
        query += " AND LOWER(TRIM(position)) = LOWER(TRIM(?))"
        params.append(position)
    if location:
        query += " AND LOWER(TRIM(location)) = LOWER(TRIM(?))"
        params.append(location)
    query += " ORDER BY applied_at DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()

    results = []
    for row in rows:
        app = dict(row)
        for field in ("missions", "stack", "requirements", "process", "keywords"):
            if app.get(field):
                app[field] = json.loads(app[field])
        results.append(app)
    return results


def list_application_companies() -> list[str]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT company FROM applications WHERE company IS NOT NULL AND TRIM(company) != ''"
    ).fetchall()
    conn.close()
    return _dedupe_case_insensitive([r["company"] for r in rows])


def list_application_positions() -> list[str]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT position FROM applications WHERE position IS NOT NULL AND TRIM(position) != ''"
    ).fetchall()
    conn.close()
    return _dedupe_case_insensitive([r["position"] for r in rows])


def list_application_locations() -> list[str]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT location FROM applications WHERE location IS NOT NULL AND TRIM(location) != ''"
    ).fetchall()
    conn.close()
    return _dedupe_case_insensitive([r["location"] for r in rows])


def update_status(app_id: int, new_status: str, trigger: str = "manual"):
    conn = get_connection()
    current = conn.execute("SELECT status FROM applications WHERE id = ?", (app_id,)).fetchone()
    if not current:
        conn.close()
        return
    old_status = current["status"]
    conn.execute(
        "UPDATE applications SET status = ?, updated_at = datetime('now') WHERE id = ?",
        (new_status, app_id),
    )
    conn.execute(
        "INSERT INTO status_history (application_id, old_status, new_status, trigger) VALUES (?, ?, ?, ?)",
        (app_id, old_status, new_status, trigger),
    )
    conn.commit()
    conn.close()


def update_notes(app_id: int, notes: str):
    conn = get_connection()
    conn.execute(
        "UPDATE applications SET notes = ?, updated_at = datetime('now') WHERE id = ?",
        (notes, app_id),
    )
    conn.commit()
    conn.close()


def mark_ghosted(days: int = 30):
    conn = get_connection()
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    rows = conn.execute(
        """
        SELECT id, status FROM applications
        WHERE status NOT IN ('rejected', 'accepted', 'Sans retour')
        AND updated_at < ?
        """,
        (cutoff,),
    ).fetchall()
    for row in rows:
        conn.execute("UPDATE applications SET status = 'Sans retour', updated_at = datetime('now') WHERE id = ?", (row["id"],))
        conn.execute(
            "INSERT INTO status_history (application_id, old_status, new_status, trigger) VALUES (?, ?, 'Sans retour', 'auto')",
            (row["id"], row["status"]),
        )
    conn.commit()
    conn.close()
    return len(rows)


# ── Emails ──

def add_email(data: dict) -> int:
    conn = get_connection()
    cursor = conn.execute(
        """
        INSERT OR IGNORE INTO emails
            (application_id, gmail_id, gmail_account, from_address,
             subject, snippet, classification, gmail_link, received_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data["application_id"],
            data["gmail_id"],
            data.get("gmail_account"),
            data.get("from_address"),
            data.get("subject"),
            data.get("snippet"),
            data.get("classification"),
            data.get("gmail_link"),
            data.get("received_at"),
        ),
    )
    conn.commit()
    email_id = cursor.lastrowid
    conn.close()
    return email_id


def get_emails_for_application(app_id: int) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM emails WHERE application_id = ? ORDER BY received_at DESC",
        (app_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Contacts ──

def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def _dedupe_case_insensitive(values: list[str]) -> list[str]:
    """Collapse variants that only differ by case/whitespace (e.g. "RH" vs
    "RH " vs "rh") down to a single representative value per group."""
    seen: dict[str, str] = {}
    for v in values:
        v = v.strip()
        if not v:
            continue
        seen.setdefault(v.casefold(), v)
    return sorted(seen.values(), key=str.casefold)


def add_contact(data: dict) -> int:
    conn = get_connection()
    cursor = conn.execute(
        """
        INSERT INTO contacts (first_name, last_name, function, company, email, phone, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            _clean(data.get("first_name")),
            _clean(data.get("last_name")),
            _clean(data.get("function")),
            _clean(data.get("company")),
            _clean(data.get("email")),
            _clean(data.get("phone")),
            data.get("notes"),
        ),
    )
    conn.commit()
    contact_id = cursor.lastrowid
    conn.close()
    return contact_id


def list_contacts(name_query: str = None, company: str = None, function: str = None) -> list[dict]:
    conn = get_connection()
    query = "SELECT * FROM contacts WHERE 1=1"
    params = []
    if name_query:
        query += " AND LOWER(COALESCE(first_name,'') || ' ' || COALESCE(last_name,'')) LIKE ?"
        params.append(f"%{name_query.strip().lower()}%")
    if company:
        query += " AND LOWER(TRIM(company)) = LOWER(TRIM(?))"
        params.append(company)
    if function:
        query += " AND LOWER(TRIM(function)) = LOWER(TRIM(?))"
        params.append(function)
    query += " ORDER BY last_name, first_name"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def list_contact_companies() -> list[str]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT company FROM contacts WHERE company IS NOT NULL AND TRIM(company) != ''"
    ).fetchall()
    conn.close()
    return _dedupe_case_insensitive([r["company"] for r in rows])


def list_contact_functions() -> list[str]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT function FROM contacts WHERE function IS NOT NULL AND TRIM(function) != ''"
    ).fetchall()
    conn.close()
    return _dedupe_case_insensitive([r["function"] for r in rows])


def get_contact(contact_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM contacts WHERE id = ?", (contact_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_contact_notes(contact_id: int, notes: str):
    conn = get_connection()
    conn.execute(
        "UPDATE contacts SET notes = ?, updated_at = datetime('now') WHERE id = ?",
        (notes, contact_id),
    )
    conn.commit()
    conn.close()


def delete_contact(contact_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
    conn.commit()
    conn.close()


# ── Status History ──

def get_status_history(app_id: int) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM status_history WHERE application_id = ? ORDER BY changed_at ASC",
        (app_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Stats ──

def get_stats() -> dict:
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) as c FROM applications").fetchone()["c"]
    by_status = conn.execute("SELECT status, COUNT(*) as c FROM applications GROUP BY status").fetchall()
    conn.close()

    by_status_map = {r["status"]: r["c"] for r in by_status}
    responded = sum(by_status_map.get(s, 0) for s in ("in_progress", "accepted", "rejected"))
    # "Sans retour" (timed out or an auto-generated rejection) isn't a real
    # response, so it's excluded from the response-rate denominator too.
    countable_total = total - by_status_map.get("Sans retour", 0)

    return {
        "total": total,
        "by_status": by_status_map,
        "response_rate": round(responded / countable_total * 100, 1) if countable_total > 0 else 0,
    }


import csv
import io

def export_csv() -> str:
    apps = list_applications()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Entreprise", "Poste", "Localisation", "Contrat",
        "Salaire", "Stack", "Statut", "Source", "Date candidature", "URL"
    ])
    for app in apps:
        stack = ", ".join(app.get("stack") or [])
        writer.writerow([
            app["id"], app["company"], app["position"], app["location"],
            app["contract_type"], app["salary"], stack, app["status"],
            app["source"], app["applied_at"], app["url"],
        ])
    return output.getvalue()


def update_application(app_id: int, data: dict):
    conn = get_connection()
    conn.execute(
        """
        UPDATE applications SET
            company = ?, position = ?, location = ?, contract_type = ?,
            salary = ?, missions = ?, stack = ?, requirements = ?,
            sector = ?, company_size = ?, contact = ?, seniority = ?,
            notes = ?, updated_at = datetime('now')
        WHERE id = ?
        """,
        (
            data.get("company"),
            data.get("position"),
            data.get("location"),
            data.get("contract_type"),
            data.get("salary"),
            json.dumps(data.get("missions", []), ensure_ascii=False),
            json.dumps(data.get("stack", []), ensure_ascii=False),
            json.dumps(data.get("requirements", []), ensure_ascii=False),
            data.get("sector"),
            data.get("company_size"),
            data.get("contact"),
            data.get("seniority"),
            data.get("notes"),
            app_id,
        ),
    )
    conn.commit()
    conn.close()


# ── Documents ──

def add_document(app_id: int, filename: str, filepath: str, doc_type: str = None) -> int:
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO documents (application_id, filename, filepath, doc_type) VALUES (?, ?, ?, ?)",
        (app_id, filename, filepath, doc_type),
    )
    conn.commit()
    doc_id = cursor.lastrowid
    conn.close()
    return doc_id


def list_documents(app_id: int) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM documents WHERE application_id = ? ORDER BY uploaded_at DESC",
        (app_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_document(doc_id: int) -> str | None:
    conn = get_connection()
    row = conn.execute("SELECT filepath FROM documents WHERE id = ?", (doc_id,)).fetchone()
    if row:
        conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        conn.commit()
        conn.close()
        return row["filepath"]
    conn.close()
    return None


def delete_application(app_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM documents WHERE application_id = ?", (app_id,))
    conn.execute("DELETE FROM emails WHERE application_id = ?", (app_id,))
    conn.execute("DELETE FROM status_history WHERE application_id = ?", (app_id,))
    conn.execute("DELETE FROM applications WHERE id = ?", (app_id,))
    conn.commit()
    conn.close()

    generated_dir = os.path.join(GENERATED_DIR, str(app_id))
    if os.path.isdir(generated_dir):
        shutil.rmtree(generated_dir)


# ── Meta ──

def get_meta(key: str) -> str | None:
    conn = get_connection()
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else None


def set_meta(key: str, value: str):
    conn = get_connection()
    conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()


def get_known_email_ids() -> set:
    conn = get_connection()
    rows = conn.execute("SELECT gmail_id FROM emails").fetchall()
    conn.close()
    return {r["gmail_id"] for r in rows}