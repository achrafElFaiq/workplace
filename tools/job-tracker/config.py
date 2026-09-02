import os
import yaml
from dotenv import load_dotenv

load_dotenv()

_TOOL_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(_TOOL_DIR, "config.yaml")

_cfg = {}
try:
    with open(CONFIG_PATH) as f:
        _cfg = yaml.safe_load(f) or {}
except FileNotFoundError:
    pass

# LLM
OPENROUTER_API_KEY = _cfg.get("openrouter_api_key") or os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = _cfg.get("openrouter_model") or os.getenv("OPENROUTER_MODEL") or "google/gemini-2.5-flash"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Database
DB_PATH = os.path.join(_TOOL_DIR, "data", "tracker.db")

# LaTeX (CV / cover letter generation)
CV_TEX_PATH = os.path.join(_TOOL_DIR, "data", "cv.tex")
CV_RULES_PATH = os.path.join(_TOOL_DIR, "data", "guide", "cv_change_rules.md")
COVER_LETTER_TEMPLATE_PATH = os.path.join(_TOOL_DIR, "data", "cover_letter_template.tex")
COVER_LETTER_GUIDE_PATH = os.path.join(_TOOL_DIR, "data", "guide", "redaction_lettre_rules.md")
GENERATED_DIR = os.path.join(_TOOL_DIR, "data", "generated")
DOCUMENTS_DIR = os.path.join(_TOOL_DIR, "data", "documents")

# Gmail IMAP — config.yaml first, .env fallback
GMAIL_ACCOUNTS = []
_cfg_accounts = _cfg.get("gmail_accounts") or []
if _cfg_accounts:
    for _i, _acc in enumerate(_cfg_accounts, 1):
        if _acc.get("address"):
            GMAIL_ACCOUNTS.append({
                "name": f"account_{_i}",
                "address": _acc["address"],
                "app_password": _acc.get("app_password", ""),
            })
else:
    _i = 1
    while True:
        _addr = os.getenv(f"GMAIL_{_i}_ADDRESS")
        _pwd = os.getenv(f"GMAIL_{_i}_APP_PASSWORD")
        if not _addr:
            break
        GMAIL_ACCOUNTS.append({"name": f"account_{_i}", "address": _addr, "app_password": _pwd})
        _i += 1

GMAIL_EMAILS = [acc["address"] for acc in GMAIL_ACCOUNTS]

# Scraping
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
REQUEST_TIMEOUT = 15
