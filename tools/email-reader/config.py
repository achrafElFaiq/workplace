import os
import yaml
from dotenv import load_dotenv

load_dotenv()

_TOOL_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(_TOOL_DIR, "config.yaml")

# Static paths — never change at runtime
DB_PATH = os.path.join(_TOOL_DIR, "data", "emails.db")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
INITIAL_SYNC_DAYS = 7
REGULAR_SYNC_DAYS = 3
MAX_EMAILS_PER_ACCOUNT = 100
IGNORED_DOMAINS_FILE = os.path.join(_TOOL_DIR, "data", "ignored_domains.txt")


def _load_cfg() -> dict:
    try:
        with open(CONFIG_PATH) as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}


def get_openrouter_api_key() -> str:
    return _load_cfg().get("openrouter_api_key") or os.getenv("OPENROUTER_API_KEY") or ""


def get_openrouter_model() -> str:
    return _load_cfg().get("openrouter_model") or os.getenv("OPENROUTER_MODEL") or "google/gemini-2.5-flash"


def get_gmail_accounts() -> list[dict]:
    cfg = _load_cfg()
    accounts = []
    cfg_accounts = cfg.get("gmail_accounts") or []
    if cfg_accounts:
        for i, acc in enumerate(cfg_accounts, 1):
            if acc.get("address"):
                accounts.append({
                    "name": f"account_{i}",
                    "address": acc["address"],
                    "app_password": acc.get("app_password", ""),
                })
    else:
        i = 1
        while True:
            addr = os.getenv(f"GMAIL_{i}_ADDRESS")
            pwd = os.getenv(f"GMAIL_{i}_APP_PASSWORD")
            if not addr:
                break
            accounts.append({"name": f"account_{i}", "address": addr, "app_password": pwd})
            i += 1
    return accounts


def get_gmail_emails() -> list[str]:
    return [acc["address"] for acc in get_gmail_accounts()]


# Backwards-compatible module-level aliases (read live)
def __getattr__(name):
    if name == "OPENROUTER_API_KEY":
        return get_openrouter_api_key()
    if name == "OPENROUTER_MODEL":
        return get_openrouter_model()
    if name == "GMAIL_ACCOUNTS":
        return get_gmail_accounts()
    if name == "GMAIL_EMAILS":
        return get_gmail_emails()
    raise AttributeError(f"module 'config' has no attribute {name!r}")
