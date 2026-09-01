import email
import email.utils
import os
import sys
from datetime import datetime, timedelta
from email.header import decode_header

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from gmail.auth import get_imap_connection
from db.queries import get_meta, set_meta
from logger import get_logger
from config import MAX_EMAILS_PER_ACCOUNT

FIRST_RUN_DAYS = 3

log = get_logger("gmail.fetcher")

DATETIME_FMT = "%Y-%m-%d %H:%M:%S"
IMAP_DATE_FMT = "%d-%b-%Y"


def _get_last_check(account_name: str) -> str | None:
    return get_meta(f"last_check_{account_name}")


def _save_last_check(account_name: str, value: str):
    set_meta(f"last_check_{account_name}", value)


def _parse_stored_datetime(value: str) -> datetime | None:
    for fmt in (DATETIME_FMT, "%d-%b-%Y"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _decode_header_value(value: str) -> str:
    parts = decode_header(value or "")
    decoded = []
    for part, charset in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(part)
    return "".join(decoded)


def _extract_body(msg) -> str:
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and "attachment" not in str(part.get("Content-Disposition", "")):
                try:
                    body = part.get_payload(decode=True).decode("utf-8", errors="replace")
                    break
                except Exception:
                    continue
    else:
        try:
            body = msg.get_payload(decode=True).decode("utf-8", errors="replace")
        except Exception:
            body = ""
    return body.strip()


def _extract_from_name(from_str: str) -> str:
    if "<" in from_str:
        name = from_str.split("<")[0].strip().strip('"')
        return name if name else from_str.split("<")[1].strip(">")
    return from_str.split("@")[0]


def fetch_recent_emails(account_name: str, force_days: int = None) -> list[dict]:
    log.info(f"[fetch] Connecting to IMAP for '{account_name}'...")
    conn = get_imap_connection(account_name)
    conn.select("INBOX", readonly=True)

    last_str = _get_last_check(account_name)
    last_dt = _parse_stored_datetime(last_str) if last_str else None

    if force_days:
        cutoff_dt = datetime.now() - timedelta(days=force_days)
        imap_since = cutoff_dt.strftime(IMAP_DATE_FMT)
        filter_dt = cutoff_dt
        log.info(f"[fetch] Force resync: last {force_days} days (since {imap_since})")
    elif last_dt:
        imap_since = last_dt.strftime(IMAP_DATE_FMT)
        cutoff_dt = last_dt
        filter_dt = last_dt
        log.info(f"[fetch] Incremental sync since {last_str} — IMAP date: {imap_since}")
    else:
        cutoff_dt = datetime.now() - timedelta(days=FIRST_RUN_DAYS)
        imap_since = cutoff_dt.strftime(IMAP_DATE_FMT)
        filter_dt = None
        log.info(f"[fetch] First run — fetching last {FIRST_RUN_DAYS} days (since {imap_since})")

    search_criteria = f'(SINCE "{imap_since}")'
    log.info(f"[fetch] IMAP search: {search_criteria}")
    _, message_ids = conn.search(None, search_criteria)
    ids = message_ids[0].split()
    ids = ids[-MAX_EMAILS_PER_ACCOUNT:]
    log.info(f"[fetch] {len(ids)} emails from IMAP")

    emails = []
    skipped_old = 0

    for i, mid in enumerate(ids):
        try:
            _, msg_data = conn.fetch(mid, "(RFC822)")
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)

            from_raw = _decode_header_value(msg.get("From", ""))
            subject = _decode_header_value(msg.get("Subject", "(no subject)"))
            date_str = msg.get("Date", "")
            msg_id = msg.get("Message-ID", mid.decode())

            from_name = _extract_from_name(from_raw)
            body = _extract_body(msg)

            if "<" in from_raw:
                from_addr = from_raw.split("<")[1].strip(">").lower()
            else:
                from_addr = from_raw.strip().lower()

            try:
                parsed_date = email.utils.parsedate_to_datetime(date_str)
                received_dt = parsed_date.replace(tzinfo=None)
                received_at = received_dt.strftime(DATETIME_FMT)
            except Exception:
                received_dt = datetime.now()
                received_at = received_dt.strftime(DATETIME_FMT)

            if filter_dt and received_dt <= filter_dt:
                skipped_old += 1
                continue

            log.info(f"  [{i+1}/{len(ids)}] {from_addr[:35]} — {subject[:45]}")

            emails.append({
                "gmail_id": msg_id,
                "gmail_account": account_name,
                "from_name": from_name,
                "from_address": from_addr,
                "subject": subject,
                "body_preview": body,
                "received_at": received_at,
                "gmail_link": f"https://mail.google.com/mail/u/0/#search/rfc822msgid:{msg_id.strip('<>')}",
            })
        except Exception as e:
            log.error(f"  [error] Failed to parse email {mid}: {e}")
            continue

    conn.logout()

    if skipped_old:
        log.info(f"[fetch] Skipped {skipped_old} emails already seen (received <= {filter_dt})")

    now_str = datetime.now().strftime(DATETIME_FMT)
    _save_last_check(account_name, now_str)
    log.info(f"[fetch] last_check saved: {now_str}")

    return emails
