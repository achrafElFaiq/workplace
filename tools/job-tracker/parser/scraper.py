import re
import requests
from bs4 import BeautifulSoup
from config import USER_AGENT, REQUEST_TIMEOUT

# Common job description container selectors
JOB_SELECTORS = [
    {"class_": re.compile(r"job.*(description|detail|content|body)", re.I)},
    {"class_": re.compile(r"posting.*(body|content|detail)", re.I)},
    {"class_": re.compile(r"vacancy.*(description|detail|content)", re.I)},
    {"id": re.compile(r"job.*(description|detail|content)", re.I)},
    {"role": "main"},
    {"tag": "article"},
]

NOISE_PATTERNS = [
    # No trailing ".*$": re.split(pattern, text)[0] already discards
    # everything from the match onward, and without re.DOTALL "." can't
    # cross newlines anyway — ".*$" here would just silently never match
    # once anything follows the noise section on a later line.
    r"(?i)show\s+more\s*\n\s*show\s+less",
    r"(?i)similar\s+jobs",
    r"(?i)people\s+also\s+viewed",
    r"(?i)you\s+may\s+also\s+like",
    r"(?i)related\s+jobs",
    r"(?i)sign\s+in\s+to\s+see",
    r"(?i)sign\s+in\s+to\s+create",
    r"(?i)new\s+to\s+linkedin",
    r"(?i)cookie\s+policy.*?accept.*?reject",
    r"(?i)explore\s+top\s+content",
    r"(?i)referrals\s+increase\s+your\s+chances",
    r"(?i)get\s+notified\s+(about|when)",
    r"(?i)seniority\s+level\n.*?employment\s+type\n.*?job\s+function\n.*?industries\n",
]

def _find_job_content(soup: BeautifulSoup) -> str | None:
    """Try to find the main job description container."""
    for selector in JOB_SELECTORS:
        if "tag" in selector:
            el = soup.find(selector["tag"])
        else:
            el = soup.find("div", selector)
        if el and len(el.get_text(strip=True)) > 200:
            return el.get_text(separator="\n", strip=True)
    return None


def _clean_noise(text: str) -> str:
    """Remove common noise sections from scraped text."""
    for pattern in NOISE_PATTERNS:
        text = re.split(pattern, text)[0]

    # Remove duplicate empty lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Limit length to ~5000 chars (job descriptions are rarely longer)
    if len(text) > 5000:
        text = text[:5000]

    return text.strip()


def fetch_url(url: str) -> str | None:
    """Fetch a job posting URL and return cleaned text."""
    try:
        response = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
    except requests.RequestException:
        return None

    soup = BeautifulSoup(response.text, "html.parser")

    # Remove noise tags
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form", "iframe"]):
        tag.decompose()

    # Try targeted extraction first
    text = _find_job_content(soup)

    # Fallback to full page
    if not text:
        text = soup.get_text(separator="\n", strip=True)

    if not text or len(text) < 200:
        return None

    return _clean_noise(text)


def clean_pasted_text(text: str) -> str:
    """Cleanup for manually pasted or extension-captured job descriptions.
    Runs the same noise-stripping pass as a URL fetch — a full-page capture
    (or a paste that includes surrounding page chrome) can carry the exact
    same "Similar jobs" / cookie-banner / nav clutter a raw HTML fetch does."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    text = "\n".join(lines)
    return _clean_noise(text)