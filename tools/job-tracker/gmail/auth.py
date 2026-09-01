import imaplib
from config import GMAIL_ACCOUNTS


def get_imap_connection(account_name: str) -> imaplib.IMAP4_SSL:
    account = next((a for a in GMAIL_ACCOUNTS if a["name"] == account_name), None)
    if not account:
        raise ValueError(f"Account '{account_name}' not found in config")

    if not account["address"] or not account["app_password"]:
        raise ValueError(f"Account '{account_name}' not configured in .env")

    conn = imaplib.IMAP4_SSL("imap.gmail.com", timeout=60)
    conn.login(account["address"], account["app_password"])
    return conn