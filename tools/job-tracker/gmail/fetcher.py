import email
import json
import os
from datetime import datetime, timedelta
from email.header import decode_header

from gmail.auth import get_imap_connection
from db.queries import get_meta, set_meta
from logger import get_logger

log = get_logger("gmail.fetcher")

_LEGACY_JSON = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "last_check.json")


def _get_last_check(account_name: str) -> str | None:
    val = get_meta(f"last_check_{account_name}")
    if val is None and os.path.exists(_LEGACY_JSON):
        try:
            with open(_LEGACY_JSON) as f:
                data = json.load(f)
            if account_name in data:
                val = data[account_name]
                set_meta(f"last_check_{account_name}", val)
        except Exception:
            pass
    return val


def _save_last_check(account_name: str, value: str):
    set_meta(f"last_check_{account_name}", value)


def _decode_header_value(value: str) -> str:
    parts = decode_header(value)
    decoded = []
    for part, charset in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(part)
    return "".join(decoded)


def fetch_recent_emails(account_name: str) -> list[dict]:
    log.info(f"Connexion IMAP pour '{account_name}'...")
    conn = get_imap_connection(account_name)
    conn.select("INBOX", readonly=True)

    last = _get_last_check(account_name)

    if last:
        search_criteria = f'(SINCE "{last}")'
    else:
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%d-%b-%Y")
        search_criteria = f'(SINCE "{yesterday}")'

    log.info(f"Recherche: {search_criteria}")
    _, message_ids = conn.search(None, search_criteria)
    ids = message_ids[0].split()
    log.info(f"{len(ids)} emails trouvés, traitement des 50 derniers...")

    ids = ids[-50:]

    emails = []
    for i, mid in enumerate(ids):
        _, msg_data = conn.fetch(mid, "(RFC822)")
        raw = msg_data[0][1]
        msg = email.message_from_bytes(raw)

        from_addr = _decode_header_value(msg.get("From", ""))
        subject = _decode_header_value(msg.get("Subject", ""))
        log.info(f"  [{i+1}/{len(ids)}] {from_addr[:30]} — {subject[:50]}")
        date_str = msg.get("Date", "")
        msg_id = msg.get("Message-ID", mid.decode())

        snippet = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    snippet = part.get_payload(decode=True).decode("utf-8", errors="replace")[:200]
                    break
        else:
            snippet = msg.get_payload(decode=True).decode("utf-8", errors="replace")[:200]

        try:
            parsed_date = email.utils.parsedate_to_datetime(date_str)
            received_at = parsed_date.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            received_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        emails.append({
            "gmail_id": msg_id,
            "gmail_account": account_name,
            "from_address": from_addr,
            "subject": subject,
            "snippet": snippet,
            "received_at": received_at,
            "gmail_link": f"https://mail.google.com/mail/u/0/#search/rfc822msgid:{msg_id}",
        })

    conn.logout()

    _save_last_check(account_name, datetime.now().strftime("%d-%b-%Y"))

    return emails
