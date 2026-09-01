import json
import os
import re

from openai import OpenAI

from config import CV_RULES_PATH, CV_TEX_PATH, OPENROUTER_API_KEY, OPENROUTER_BASE_URL, OPENROUTER_MODEL
from latex.compiler import compile_tex
from latex.edits import repair_json_backslashes
from logger import get_logger

log = get_logger("latex.cv_generator")

client = OpenAI(api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_BASE_URL, timeout=90)

# The actual tailoring rules live in data/guide/cv_change_rules.md
# (user-owned, gitignored) — this is the fixed scaffolding around them.
#
# Targeting is by LINE NUMBER, not text search. Earlier versions asked the
# LLM to copy exact LaTeX substrings to build a search key, which was
# unreliable (whitespace/markup mismatches silently dropped valid edits,
# and once it matched the candidate's own NAME instead of the subtitle it
# was trying to change). Indexing by line number can't fail to "find" the
# target — the model just needs to say which line and what it becomes.
CV_EDIT_PROMPT = """Tu es un assistant qui adapte un CV LaTeX a une offre d'emploi, en
suivant STRICTEMENT les regles ci-dessous (definies par le candidat lui-meme) :

{rules}

Le CV ci-dessous est numerote (une ligne = "NUMERO| contenu"). Pour chaque
changement, indique :
- "line" : le numero de la ligne a remplacer entierement
- "expect_contains" : un court extrait que tu vois reellement sur cette
  ligne (verification que tu cibles la bonne ligne, pas un texte a chercher)
- "new_content" : le contenu COMPLET de la nouvelle ligne (avec tout le
  balisage LaTeX necessaire — regarde comment la ligne actuelle est ecrite
  et garde la meme forme, ex: \\textbf{{...}}, \\vspace{{...}}\\\\ en fin de
  ligne s'il y en avait un)

Tu n'es pas limite a un remplacement mot-pour-mot : tu peux reformuler toute
la ligne pour integrer un mot-cle naturellement, du moment que la regle
correspondante est respectee (ex: taille fixe pour le bloc Competences).

Reperes utiles pour le bloc Competences (nombre d'items actuel par ligne —
respecte-le, ce n'est pas juste une suggestion) :
{competency_budget}

Reponds UNIQUEMENT en JSON, sans markdown, au format :
{{
  "edits": [
    {{"line": 42, "expect_contains": "court extrait reel de cette ligne", "new_content": "contenu complet de la nouvelle ligne"}}
  ]
}}

OFFRE (champs extraits) :
Entreprise: {company}
Poste: {position}
Stack: {stack}
Missions: {missions}
Requirements: {requirements}
Seniorite: {seniority}

OFFRE (texte complet — utilise-le pour le contexte que les champs extraits
au-dessus ne capturent pas : ce que fait vraiment l'entreprise, le ton de
l'annonce, des details specifiques) :
{raw_text}

CV (LaTeX, numerote) :
{numbered_cv}
"""


def _load_cv_tex() -> str:
    with open(CV_TEX_PATH, encoding="utf-8") as f:
        return f.read()


def _load_rules() -> str:
    with open(CV_RULES_PATH, encoding="utf-8") as f:
        return f.read().strip()


def _numbered_lines(cv_tex: str) -> str:
    return "\n".join(f"{i}| {line}" for i, line in enumerate(cv_tex.splitlines(), start=1))


_COMPETENCY_LINE_RE = re.compile(r"\\textbf\{([^}]+):\}\s*(.+)")


def _competency_section(cv_tex: str) -> str | None:
    match = re.search(
        r"\\section\{Comp[ée]tences Techniques\}(.*?)(?=\\section\{|\Z)",
        cv_tex, re.DOTALL,
    )
    return match.group(1) if match else None


def _line_items(rest: str) -> list[str]:
    rest = re.sub(r"\\vspace\{[^}]*\}\s*\\\\?\s*$", "", rest).strip()
    return [i.strip() for i in rest.split(",") if i.strip()]


def _competency_budget(cv_tex: str) -> str:
    """Pull the current Competences lines out of the CV and count their
    items, so the prompt can hand the model an explicit number per line
    instead of an abstract "don't lengthen" instruction."""
    section = _competency_section(cv_tex)
    if section is None:
        return "(section Competences Techniques introuvable)"

    lines = []
    for raw_line in section.splitlines():
        match = _COMPETENCY_LINE_RE.match(raw_line.strip())
        if not match:
            continue
        items = _line_items(match.group(2))
        if items:
            lines.append(f"- {match.group(1).strip()} : {len(items)} items actuellement ({', '.join(items)})")
    return "\n".join(lines) if lines else "(aucune ligne de competences detectee)"


_NUMBER_TOKEN_RE = re.compile(r"\d[\d.,]*\s*%?")


def _edit_warnings(cv_tex: str, old_line: str, new_line: str) -> list[str]:
    """Non-blocking sanity checks. The old design rejected edits that
    violated these — now they're surfaced as warnings instead, since a bad
    edit is still visible in the generated PDF and easy to notice/regenerate,
    which is the tradeoff the user explicitly chose over stricter blocking."""
    warnings = []

    comp_match = _COMPETENCY_LINE_RE.match(old_line.strip())
    if comp_match:
        category = comp_match.group(1).strip()
        old_items = _line_items(comp_match.group(2))
        new_match = _COMPETENCY_LINE_RE.match(new_line.strip())
        new_items = _line_items(new_match.group(2)) if new_match else []

        if len(new_items) != len(old_items):
            warnings.append(f"'{category}' a change de longueur ({len(old_items)} -> {len(new_items)} items)")

        outside_section = cv_tex.replace(_competency_section(cv_tex) or "", "", 1)
        for item in old_items:
            if item in new_items or not item or len(item) <= 2:
                continue
            if re.search(r"\b" + re.escape(item) + r"\b", outside_section):
                warnings.append(f"'{item}' retire de '{category}' alors qu'il est mentionne ailleurs dans le CV")

    old_numbers = set(_NUMBER_TOKEN_RE.findall(old_line))
    new_numbers = set(_NUMBER_TOKEN_RE.findall(new_line))
    missing = old_numbers - new_numbers
    if missing:
        warnings.append(f"un nombre a disparu de la ligne ({', '.join(sorted(missing))}) — verifie qu'aucune metrique/date n'est perdue")

    return warnings


def _propose_edits(cv_tex: str, application: dict) -> list[dict]:
    prompt = CV_EDIT_PROMPT.format(
        rules=_load_rules(),
        competency_budget=_competency_budget(cv_tex),
        company=application.get("company", ""),
        position=application.get("position", ""),
        stack=", ".join(application.get("stack") or []),
        missions="; ".join(application.get("missions") or []),
        requirements="; ".join(application.get("requirements") or []),
        seniority=application.get("seniority", ""),
        raw_text=application.get("raw_text") or "(non disponible)",
        numbered_cv=_numbered_lines(cv_tex),
    )
    response = client.chat.completions.create(
        model=OPENROUTER_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    raw = response.choices[0].message.content
    raw = raw.strip()
    raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
    raw = re.sub(r"```$", "", raw).strip()
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        raw = match.group(0)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = json.loads(repair_json_backslashes(raw))
    return data.get("edits", [])


def _normalize_for_match(s: str) -> str:
    """expect_contains is a sanity check, not an exact-match key — the LLM
    routinely writes LaTeX special chars without their escaping backslash
    (e.g. "MLOps & Cloud" for actual text "MLOps \\& Cloud"). Strip
    backslashes that only exist to escape a special char before comparing,
    so a real line match isn't rejected over LaTeX markup noise."""
    return re.sub(r"\\(?=[&%_#{}])", "", s).lower()


def _apply_line_edits(cv_tex: str, edits: list[dict]) -> tuple[str, list[str]]:
    lines = cv_tex.splitlines()
    warnings = []

    for edit in edits:
        line_no = edit.get("line")
        expect = (edit.get("expect_contains") or "").strip()
        new_content = edit.get("new_content")

        if not isinstance(line_no, int) or not (1 <= line_no <= len(lines)):
            warnings.append(f"Ligne {line_no!r} hors limites, edit ignore.")
            continue
        if new_content is None or not new_content.strip():
            warnings.append(f"Ligne {line_no} : nouveau contenu vide, edit ignore.")
            continue

        old_line = lines[line_no - 1]
        if expect and _normalize_for_match(expect) not in _normalize_for_match(old_line):
            warnings.append(f"Ligne {line_no} : ne correspond pas a ce qui etait attendu ({expect!r}), edit ignore.")
            continue

        warnings.extend(f"Ligne {line_no} : {w}" for w in _edit_warnings(cv_tex, old_line, new_content))
        lines[line_no - 1] = new_content

    return "\n".join(lines), warnings


def generate_cv_pdf(application: dict) -> tuple[bytes, str, list[str]]:
    """Generate a tailored CV PDF for this application. Never modifies the
    source cv.tex on disk — edits happen on an in-memory copy only.
    Returns (pdf_bytes, tailored_tex, warnings) — warnings flags anything
    worth a second look (line-length changes, a dropped corroborated skill,
    a missing number) without blocking the edit; review the result and
    regenerate if something's off.
    """
    cv_tex = _load_cv_tex()
    edits = _propose_edits(cv_tex, application)
    tailored_tex, warnings = _apply_line_edits(cv_tex, edits)
    pdf_bytes = compile_tex(tailored_tex, asset_dir=os.path.dirname(CV_TEX_PATH))
    return pdf_bytes, tailored_tex, warnings
