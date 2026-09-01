import json
import os
import re
from datetime import date

from openai import OpenAI

from config import (
    CV_TEX_PATH,
    COVER_LETTER_GUIDE_PATH,
    COVER_LETTER_TEMPLATE_PATH,
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    OPENROUTER_MODEL,
)
from latex.compiler import compile_tex
from latex.edits import repair_json_backslashes
from logger import get_logger

log = get_logger("latex.cover_letter_generator")

client = OpenAI(api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_BASE_URL, timeout=90)

# Placeholders as they literally appear in data/cover_letter_template.tex.
# The template also carries per-paragraph guidance as LaTeX comments (%...)
# right above each one — that's candidate-specific context (which real
# achievements to reach for) the general redaction guide doesn't know
# about, so the whole template (comments included) goes into the prompt.
_PARAGRAPH_PLACEHOLDERS = {
    "paragraph_1": "[Rédiger 3-4 phrases : le constat fort + ce que ça dit de ma façon de travailler + le lien avec l'offre.]",
    "paragraph_2": "[Rédiger 4-5 phrases : ce que j'ai construit + l'angle sécurité + le réflexe production.]",
    "paragraph_3": "[Rédiger 3 phrases : ce qui m'attire précisément chez eux + comment mon expérience y répond.]",
    "paragraph_4": "[Rédiger 1-2 phrases : proposer un entretien + remercier simplement.]",
}
_COMPANY_PLACEHOLDER = "[Nom Entreprise]"
_LOCATION_DATE_PLACEHOLDER = "[Ville du poste], le [JJ mois AAAA]"
_POSITION_PLACEHOLDER = "[d'Intitulé exact de l'offre]"
_REFERENCE_SUFFIX = " (réf. [XYZ])"  # dropped outright — job postings essentially never give job-trackerable references

_FR_MONTHS = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]

COVER_LETTER_PROMPT = """Tu rediges les 4 paragraphes du corps d'une lettre de motivation en
francais, en suivant STRICTEMENT le guide de redaction ci-dessous (regles de
fond, de style et de ponctuation) :

{guide}

Rappel specifique (piege frequent) : ne termine JAMAIS un paragraphe par une
enumeration de technologies façon "j'ai travaille avec X, Y, Z, W" — meme
en fin de paragraphe 2. C'est exactement le type de phrase generique que le
guide interdit (section 2, paragraphe 2) : le CV liste deja la stack de
chaque experience, la lettre raconte une situation/action/resultat, elle ne
reformule pas la liste de competences en prose.

Le template LaTeX ci-dessous contient, pour chaque paragraphe, un
commentaire (ligne commencant par %) qui precise QUOI raconter pour CE
candidat precis (ses vraies realisations). Respecte ces indications, elles
s'ajoutent au guide de redaction, ne le remplacent pas :

{template}

CV du candidat (pour contexte factuel uniquement — ne jamais inventer une
realisation qui n'y figure pas) :
{cv_tex}

OFFRE (champs extraits) :
Entreprise: {company}
Poste: {position}
Stack: {stack}
Missions: {missions}
Requirements: {requirements}
Seniorite: {seniority}

OFFRE (texte complet — c'est ta MEILLEURE source pour le paragraphe 3 : un
fait reel sur l'entreprise que les champs extraits au-dessus ne donnent
pas — un projet cite, un secteur, une orientation, un enjeu mentionne) :
{raw_text}

Derniers rappels avant de rediger (les plus souvent oublies) :
- Interdit mot pour mot : "je suis convaincu que", "il convient de souligner",
  "non seulement... mais aussi", et toute liste de technologies en fin de
  paragraphe ("j'ai travaille avec X, Y, Z").
- Zero tiret cadratin (—). Deux-points sobres, pas un par phrase.
- Phrases de longueurs variees (une courte, une longue, une moyenne) — pas
  un rythme regulier et lisse.
- Reponds UNIQUEMENT avec l'objet JSON, sans aucune phrase avant ou après
  (pas de "Voici les paragraphes :", rien d'autre que l'objet JSON).

Reponds en JSON, sans markdown, avec exactement ces 4 champs
(texte brut, sans LaTeX, sans markdown, un paragraphe = une chaine) :
{{
  "paragraph_1": "...",
  "paragraph_2": "...",
  "paragraph_3": "...",
  "paragraph_4": "..."
}}
"""

_LATEX_ESCAPES = [
    ("\\", r"\textbackslash{}"),
    ("&", r"\&"),
    ("%", r"\%"),
    ("$", r"\$"),
    ("#", r"\#"),
    ("_", r"\_"),
    ("{", r"\{"),
    ("}", r"\}"),
    ("~", r"\textasciitilde{}"),
    ("^", r"\textasciicircum{}"),
]


def _escape_latex(text: str) -> str:
    for char, escaped in _LATEX_ESCAPES:
        text = text.replace(char, escaped)
    return text


def _load(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def _today_fr() -> str:
    today = date.today()
    return f"{today.day} {_FR_MONTHS[today.month - 1]} {today.year}"


def _position_with_elision(position: str) -> str:
    position = (position or "").strip()
    if not position:
        return "de [poste]"
    return f"d'{position}" if position[0].lower() in "aeiouyh" else f"de {position}"


def _generate_paragraphs(application: dict, template: str) -> dict:
    prompt = COVER_LETTER_PROMPT.format(
        guide=_load(COVER_LETTER_GUIDE_PATH),
        template=template,
        cv_tex=_load(CV_TEX_PATH),
        company=application.get("company", ""),
        position=application.get("position", ""),
        stack=", ".join(application.get("stack") or []),
        missions="; ".join(application.get("missions") or []),
        requirements="; ".join(application.get("requirements") or []),
        seniority=application.get("seniority", ""),
        raw_text=application.get("raw_text") or "(non disponible)",
    )
    response = client.chat.completions.create(
        model=OPENROUTER_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
    )
    raw = response.choices[0].message.content
    raw = raw.strip()
    raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
    raw = re.sub(r"```$", "", raw).strip()
    # The model sometimes prefixes the JSON with a conversational sentence
    # ("Voici les 4 paragraphes...") — extract the {...} span regardless of
    # what surrounds it, rather than assuming the response starts at "{".
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        raw = match.group(0)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return json.loads(repair_json_backslashes(raw))


_BANNED_PHRASES = [
    "je suis convaincu que",
    "il convient de souligner",
    "non seulement",
]


def _scan_banned_phrases(paragraphs: dict) -> list[str]:
    """The model doesn't reliably self-censor these even when explicitly
    told not to (observed repeatedly in testing) — flag them so the user
    knows exactly where to review before sending, since we can't safely
    auto-rewrite prose the way apply_replacements can reject a bad edit."""
    warnings = []
    for key in ("paragraph_1", "paragraph_2", "paragraph_3", "paragraph_4"):
        text = (paragraphs.get(key) or "").lower()
        for phrase in _BANNED_PHRASES:
            if phrase in text:
                warnings.append(f"{key} : tournure a eviter detectee ({phrase!r})")
    return warnings


def generate_cover_letter_pdf(application: dict) -> tuple[bytes, str, list[str]]:
    """Returns (pdf_bytes, filled_tex, warnings) — filled_tex is the LaTeX
    source actually used, the thing worth persisting since the PDF can
    always be recompiled from it on demand. warnings flags banned-phrase
    usage the model didn't avoid on its own — review those spots by hand."""
    if not os.path.exists(COVER_LETTER_TEMPLATE_PATH):
        raise FileNotFoundError(
            f"Template de lettre de motivation introuvable : {COVER_LETTER_TEMPLATE_PATH}"
        )
    template = _load(COVER_LETTER_TEMPLATE_PATH)

    missing = [p for p in (_COMPANY_PLACEHOLDER, _LOCATION_DATE_PLACEHOLDER, _POSITION_PLACEHOLDER, *_PARAGRAPH_PLACEHOLDERS.values()) if p not in template]
    if missing:
        raise ValueError(f"Le template ne contient pas le(s) marqueur(s) attendu(s) : {missing}")

    paragraphs = _generate_paragraphs(application, template)

    filled = template
    filled = filled.replace(_REFERENCE_SUFFIX, "")
    filled = filled.replace(_COMPANY_PLACEHOLDER, _escape_latex(application.get("company") or ""))
    filled = filled.replace(_POSITION_PLACEHOLDER, _escape_latex(_position_with_elision(application.get("position"))))

    location = (application.get("location") or "").strip()
    location_date = f"{_escape_latex(location)}, le {_today_fr()}" if location else f"le {_today_fr()}"
    filled = filled.replace(_LOCATION_DATE_PLACEHOLDER, location_date)

    for key, placeholder in _PARAGRAPH_PLACEHOLDERS.items():
        filled = filled.replace(placeholder, _escape_latex((paragraphs.get(key) or "").strip()))

    warnings = _scan_banned_phrases(paragraphs)
    pdf_bytes = compile_tex(filled, asset_dir=os.path.dirname(CV_TEX_PATH))
    return pdf_bytes, filled, warnings
