"""
sync.py — fetch emails from Gmail, classify with LLM, save important ones to DB.
"""
import json
import os
import sys
from datetime import datetime

from config import GMAIL_ACCOUNTS, IGNORED_DOMAINS_FILE
from db.queries import save_email, get_known_gmail_ids
from gmail.fetcher import fetch_recent_emails
from llm.classifier import classify_batch
from blocked import get_blocked_senders
from logger import get_logger

log = get_logger("sync")

BATCH_SIZE = 5


def _load_ignored_domains() -> set:
    try:
        with open(IGNORED_DOMAINS_FILE) as f:
            return {line.strip().lower() for line in f if line.strip() and not line.startswith("#")}
    except FileNotFoundError:
        return set()


def _extract_domain(from_address: str) -> str:
    return from_address.split("@")[-1].lower().strip(">").strip()


def _is_ignored(from_address: str, ignored: set) -> bool:
    domain = _extract_domain(from_address)
    return any(d in domain for d in ignored)


def run_sync(force_days: int = None) -> dict:
    stats = {
        "fetched": 0,
        "ignored_domain": 0,
        "blocked_sender": 0,
        "already_known": 0,
        "sent_to_llm": 0,
        "saved": 0,
        "skipped_not_important": 0,
        "errors": 0,
    }
    all_processed = []
    ignored_domains = _load_ignored_domains()
    blocked_senders = get_blocked_senders()
    known_ids = get_known_gmail_ids()

    log.info(f"[sync] Starting sync — {len(GMAIL_ACCOUNTS)} account(s)")
    log.info(f"[sync] {len(ignored_domains)} ignored domains, {len(blocked_senders)} blocked senders, {len(known_ids)} known emails in DB")

    for account in GMAIL_ACCOUNTS:
        account_name = account["name"]
        log.info(f"[sync] --- Account: {account_name} ({account['address']}) ---")

        try:
            emails = fetch_recent_emails(account_name, force_days=force_days)
        except Exception as e:
            log.error(f"[sync] Fetch failed for {account_name}: {e}")
            stats["errors"] += 1
            continue

        stats["fetched"] += len(emails)

        # Pre-filter
        to_classify = []
        for em in emails:
            entry = {
                "account": account_name,
                "from": em["from_address"],
                "subject": em["subject"],
                "received_at": em["received_at"],
                "action": None,
            }

            # Skip already known
            if em["gmail_id"] in known_ids:
                log.info(f"  [skip] Already in DB: {em['subject'][:50]}")
                entry["action"] = "already_known"
                all_processed.append(entry)
                stats["already_known"] += 1
                continue

            # Skip ignored domains
            if _is_ignored(em["from_address"], ignored_domains):
                log.info(f"  [skip] Ignored domain: {_extract_domain(em['from_address'])}")
                entry["action"] = "ignored_domain"
                all_processed.append(entry)
                stats["ignored_domain"] += 1
                continue

            # Skip blocked senders
            if em["from_address"].lower().strip() in blocked_senders:
                log.info(f"  [skip] Blocked sender: {em['from_address']}")
                entry["action"] = "blocked_sender"
                all_processed.append(entry)
                stats["blocked_sender"] += 1
                continue

            to_classify.append((em, entry))

        if not to_classify:
            log.info(f"  [sync] Nothing to classify for {account_name}")
            continue

        stats["sent_to_llm"] += len(to_classify)
        log.info(f"  [sync] Sending {len(to_classify)} emails to LLM (batches of {BATCH_SIZE})")

        # Classify in batches
        for i in range(0, len(to_classify), BATCH_SIZE):
            batch = to_classify[i:i + BATCH_SIZE]
            batch_emails = [em for em, _ in batch]
            batch_entries = [entry for _, entry in batch]

            log.info(f"  [batch] {i + 1}–{i + len(batch)} of {len(to_classify)}")
            results = classify_batch(batch_emails)

            results_map = {r.get("email_index"): r for r in results if r.get("email_index") is not None}

            for j, (em, entry) in enumerate(batch):
                result = results_map.get(j)

                if not result:
                    log.warning(f"  [warn] No LLM result for: {em['subject'][:50]}")
                    entry["action"] = "llm_error"
                    stats["errors"] += 1
                    all_processed.append(entry)
                    continue

                if not result.get("important"):
                    log.info(f"  [x] Not important: {em['subject'][:50]}")
                    entry["action"] = "not_important"
                    all_processed.append(entry)
                    stats["skipped_not_important"] += 1
                    continue

                category = result.get("category", "update")
                summary = result.get("summary", em["subject"])

                record = {
                    **em,
                    "summary": summary,
                    "category": category,
                }

                inserted = save_email(record)
                if inserted:
                    known_ids.add(em["gmail_id"])
                    stats["saved"] += 1
                    log.info(f"  [ok] Saved [{category}]: {em['subject'][:50]}")
                    entry["action"] = "saved"
                    entry["category"] = category
                    entry["summary"] = summary
                else:
                    entry["action"] = "duplicate"
                    stats["already_known"] += 1

                all_processed.append(entry)

    # Save sync log
    sync_dir = os.path.join(os.path.dirname(__file__), "data", "syncs")
    os.makedirs(sync_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    sync_log = {
        "timestamp": timestamp,
        "stats": stats,
        "emails": all_processed,
    }
    log_path = os.path.join(sync_dir, f"sync_{timestamp}.json")
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(sync_log, f, ensure_ascii=False, indent=2)

    log.info(f"[sync] Done: {stats}")
    log.info(f"[sync] Log saved: {log_path}")
    return stats


if __name__ == "__main__":
    from db.database import init_db
    init_db()
    run_sync()
