import json
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from openai import OpenAI
from config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, OPENROUTER_MODEL
from logger import get_logger

log = get_logger("llm.classifier")

client = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url=OPENROUTER_BASE_URL,
)

CATEGORIES = ("action", "finance", "personal", "alert", "update")

SYSTEM_PROMPT = """You are an email importance classifier. You receive batches of emails and decide which are worth showing in an inbox reader.

IMPORTANT = any of:
- Requires a response or action
- Financial: bills, invoices, bank statements, transactions, payment confirmations
- From a real person (not automated)
- Legal, medical, government
- Important alerts: security, account access, service disruption
- Meaningful updates you'd actually want to know about

NOT IMPORTANT = skip these:
- Newsletters, marketing, promotions, deals, sales
- Social media notifications
- Automated system digests and reports
- Subscription updates that need no action
- Loyalty points, rewards programs
- Recommendations ("you might like...")

For each email marked important, set category to one of:
- action: needs a response or action from you
- finance: bills, payments, bank, invoices, receipts
- personal: from a real person (not automated)
- alert: security, account, service, or system alert
- update: important status or informational update

Return ONLY valid JSON, no markdown, no explanation."""

USER_TEMPLATE = """Classify these emails:

{emails_list}

Return JSON array, one object per email:
[
  {{"email_index": 0, "important": true, "category": "action", "summary": "One sentence about what this email is."}},
  {{"email_index": 1, "important": false}}
]"""


def classify_batch(emails: list[dict]) -> list[dict]:
    """
    Classify a batch of emails. Returns list of results with:
    - email_index: int
    - important: bool
    - category: str (if important)
    - summary: str (if important)
    """
    emails_list = "\n".join(
        f"[{i}] From: {em['from_name']} <{em['from_address']}> | Subject: {em['subject']} | Body: {em['body_preview'][:300]}"
        for i, em in enumerate(emails)
    )

    prompt = USER_TEMPLATE.format(emails_list=emails_list)

    try:
        response = client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
        )
        raw = response.choices[0].message.content.strip()
        raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        results = json.loads(raw)
        log.info(f"  [llm] Classified {len(emails)} emails: {sum(1 for r in results if r.get('important'))} important")
        return results
    except json.JSONDecodeError as e:
        log.error(f"  [llm] JSON parse error: {e} — raw: {raw[:200]}")
        return []
    except Exception as e:
        log.error(f"  [llm] Classification error: {e}")
        return []
