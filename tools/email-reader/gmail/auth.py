import imaplib
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import get_gmail_accounts


def get_imap_connection(account_name: str) -> imaplib.IMAP4_SSL:
    account = next((a for a in get_gmail_accounts() if a["name"] == account_name), None)
    if not account:
        raise ValueError(f"Account '{account_name}' not found in config")
    if not account["address"] or not account["app_password"]:
        raise ValueError(f"Account '{account_name}' not configured in .env")
    conn = imaplib.IMAP4_SSL("imap.gmail.com", timeout=60)
    conn.login(account["address"], account["app_password"])
    return conn
