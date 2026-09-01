import json
import os
from datetime import datetime

from openai import OpenAI
from db.queries import list_applications, add_email, update_status, get_known_email_ids
from gmail.fetcher import fetch_recent_emails
from logger import get_logger
from config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, OPENROUTER_MODEL, GMAIL_ACCOUNTS

log = get_logger("gmail.matcher")

client = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url=OPENROUTER_BASE_URL,
)

IGNORED_DOMAINS_FILE = "data/ignored_domains.txt"


def _load_ignored_domains() -> set:
    try:
        with open(IGNORED_DOMAINS_FILE) as f:
            return {line.strip().lower() for line in f if line.strip()}
    except FileNotFoundError:
        return set()


def _is_ignored(domain: str) -> bool:
    ignored = _load_ignored_domains()
    return any(d in domain for d in ignored)


def _extract_domain(from_address: str) -> str:
    if "<" in from_address:
        addr = from_address.split("<")[1].strip(">")
    else:
        addr = from_address
    return addr.split("@")[-1].lower()


def _match_batch_with_llm(emails: list[dict], active_apps: list[dict]) -> list[dict]:
    apps_list = "\n".join(
        f"- id:{a['id']} | {a['company']} | {a['position']}"
        for a in active_apps
    )

    emails_list = "\n".join(
        f"- email_index:{i} | De: {em['from_address']} | Objet: {em['subject']} | Extrait: {em['snippet'][:100]}"
        for i, em in enumerate(emails)
    )

    prompt = f"""Tu reçois une liste d'emails et une liste de candidatures actives.
Pour chaque email, détermine s'il est lié à une candidature et classifie-le.

EMAILS:
{emails_list}

CANDIDATURES ACTIVES:
{apps_list}

Réponds UNIQUEMENT en JSON (array):
[
  {{
    "email_index": <index>,
    "application_id": <id ou null>,
    "classification": "acknowledgment | interview_invite | technical_test | rejection | auto_rejection | offer | info_request | other",
    "confidence": "high | medium | low"
  }}
]

Distingue bien "rejection" (refus visiblement ecrit/personnalise par une
vraie personne) de "auto_rejection" (refus generique automatise : reponse
ATS standard, aucune personnalisation, ton de formulaire type "nous ne
donnerons pas suite a votre candidature").

Si un email ne correspond à aucune candidature, mets application_id à null.
"""

    try:
        response = client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        raw = response.choices[0].message.content
        raw = raw.strip().removeprefix("```json").removesuffix("```").strip()
        return json.loads(raw)
    except Exception as e:
        log.error(f"Batch matching error: {e}")
        return []


STATUS_MAP = {
    "acknowledgment": "in_progress",
    "interview_invite": "in_progress",
    "technical_test": "in_progress",
    "rejection": "rejected",
    "auto_rejection": "Sans retour",
    # "offer" intentionally has no mapping — an offer email still gets linked
    # to the application via add_email above, but doesn't auto-change status;
    # accepting/rejecting an offer is the user's own call.
}

def sync_emails() -> dict:
    stats = {"fetched": 0, "matched": 0, "skipped": 0}
    all_processed = []

    active_apps = list_applications()
    active_apps = [a for a in active_apps if a["status"] not in ("rejected", "accepted", "Sans retour")]
    log.info(f"{len(active_apps)} candidatures actives")

    if not active_apps:
        log.info("Aucune candidature active, skip")
        return stats

    known_ids = get_known_email_ids()
    log.info(f"{len(known_ids)} emails déjà enregistrés en base")

    for account in [acc["name"] for acc in GMAIL_ACCOUNTS]:

        try:
            emails = fetch_recent_emails(account)
        except Exception as e:
            log.error(f"Erreur fetch {account}: {e}")
            continue

        stats["fetched"] += len(emails)

        # Separate ignored from to-match
        to_match = []
        for em in emails:
            domain = _extract_domain(em["from_address"])
            entry = {
                "account": account,
                "from": em["from_address"],
                "subject": em["subject"],
                "snippet": em["snippet"],
                "received_at": em["received_at"],
                "action": None,
                "match": None,
            }
            if em["gmail_id"] in known_ids:
                log.info(f"  ↩ Déjà enregistré: {em['subject'][:50]}")
                entry["action"] = "already_known"
                all_processed.append(entry)
                stats["skipped"] += 1
            elif _is_ignored(domain):
                log.info(f"  ⏭ Domaine ignoré: {domain}")
                entry["action"] = "skipped_ignored"
                all_processed.append(entry)
                stats["skipped"] += 1
            else:
                to_match.append((em, entry))

        if not to_match:
            log.info(f"  Aucun email à matcher pour {account}")
            continue

        # Process in batches of 5
        batch_size = 5
        for i in range(0, len(to_match), batch_size):
            batch = to_match[i:i + batch_size]
            batch_emails = [em for em, _ in batch]

            log.info(f"  🔍 Batch {i // batch_size + 1}: {len(batch)} emails")
            results = _match_batch_with_llm(batch_emails, active_apps)

            # Index results by email_index for easy lookup
            results_map = {r.get("email_index"): r for r in results if r.get("email_index") is not None}

            for j, (em, entry) in enumerate(batch):
                result = results_map.get(j)

                if not result or not result.get("application_id") or result.get("confidence") == "low":
                    log.info(f"  ❌ Pas de match: {em['subject'][:50]}")
                    entry["action"] = "no_match"
                    all_processed.append(entry)
                    stats["skipped"] += 1
                    continue

                log.info(f"  ✅ Match #{result['application_id']} — {result['classification']}")
                em["application_id"] = result["application_id"]
                em["classification"] = result["classification"]
                add_email(em)

                new_status = STATUS_MAP.get(result["classification"])
                if new_status:
                    update_status(result["application_id"], new_status, trigger="email")

                entry["action"] = "matched"
                entry["match"] = result
                all_processed.append(entry)
                stats["matched"] += 1

    # Save sync log
    sync_dir = "data/syncs"
    os.makedirs(sync_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    sync_log = {
        "timestamp": timestamp,
        "stats": stats,
        "emails": all_processed,
    }
    log_path = f"{sync_dir}/sync_{timestamp}.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(sync_log, f, ensure_ascii=False, indent=2)
    log.info(f"Sync log saved: {log_path}")

    log.info(f"Sync terminé: {stats}")
    return stats