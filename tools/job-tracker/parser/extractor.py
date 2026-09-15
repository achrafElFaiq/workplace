import json
import re
import time
from openai import OpenAI
from config import OPENROUTER_BASE_URL, get_openrouter_api_key, get_openrouter_model
from logger import get_logger

log = get_logger("parser.extractor")


EXTRACTION_PROMPT = """Tu es un parser d'offres d'emploi. Extrais les informations suivantes du texte fourni et retourne UNIQUEMENT un JSON valide, sans markdown, sans commentaire.

{
  "company": "Nom de l'entreprise",
  "position": "Intitulé du poste",
  "location": "Localisation",
  "contract_type": "CDI | CDD | Stage | Alternance | Freelance",
  "salary": "Fourchette salariale ou null",
  "missions": ["mission 1", "mission 2", "...max 5"],
  "stack": ["tech 1", "tech 2", "..."],
  "requirements": ["compétence 1", "compétence 2", "...max 5"],
  "process": ["etape 1", "etape 2", "..."],
  "sector": "Secteur d'activité ou null",
  "company_size": "Taille ou CA si mentionné, sinon null",
  "contact": "Nom du recruteur si mentionné, sinon null",
  "seniority": "junior | confirmé | senior | lead",
  "keywords": ["mot-clé 1", "mot-clé 2", "..."]
}

Règles :
- Si une info n'est pas dans le texte, mets null (ou liste vide pour les arrays)
- missions, stack, requirements, process, keywords sont des arrays de strings
- process : uniquement si l'offre decrit explicitement les etapes de son
  propre processus de recrutement (ex: "1. Appel telephonique 2. Test
  technique 3. Entretien final") — dans l'ordre indique. Liste vide si non
  mentionne, n'invente rien.
- keywords : les mots-clés techniques et métier pertinents pour cette offre
  (technologies, outils, méthodologies, compétences clés, certifications).
  Ce sont les termes qu'un ATS ou recruteur chercherait dans un CV. Max 15.
- Sois factuel, n'invente rien
"""


def _get_client() -> OpenAI:
    return OpenAI(api_key=get_openrouter_api_key(), base_url=OPENROUTER_BASE_URL)


def _call_llm(text: str, attempt: int) -> dict:
    model = get_openrouter_model()
    api_key = get_openrouter_api_key()
    key_preview = f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else "(empty/short)"

    log.info(f"[attempt {attempt}] model={model} key={key_preview} input={len(text)} chars")

    client = _get_client()
    t0 = time.time()
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": EXTRACTION_PROMPT},
                {"role": "user", "content": text},
            ],
            temperature=0,
        )
    except Exception as e:
        elapsed = time.time() - t0
        log.error(f"[attempt {attempt}] API call failed after {elapsed:.1f}s — {type(e).__name__}: {e}")
        raise

    elapsed = time.time() - t0
    raw = response.choices[0].message.content or ""
    usage = response.usage
    tokens_in = usage.prompt_tokens if usage else "?"
    tokens_out = usage.completion_tokens if usage else "?"
    finish = response.choices[0].finish_reason

    log.info(f"[attempt {attempt}] response in {elapsed:.1f}s — {tokens_in} tok in, {tokens_out} tok out, finish={finish}, raw={len(raw)} chars")

    raw = raw.strip()
    raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
    raw = re.sub(r"```$", "", raw).strip()
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        raw = match.group(0)
    else:
        log.error(f"[attempt {attempt}] no JSON object found in response: {raw[:500]}")
        raise ValueError(f"No JSON object in LLM response")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        log.error(f"[attempt {attempt}] JSON parse failed: {e} — raw: {raw[:500]}")
        raise

    company = data.get("company") or "?"
    position = data.get("position") or "?"
    log.info(f"[attempt {attempt}] parsed OK — company={company}, position={position}")
    return data


def extract_job_data(text: str) -> dict | None:
    """Send raw job text to LLM and return structured data. Retries once on failure."""
    log.info(f"--- extraction start — input {len(text)} chars ---")
    for attempt in range(1, 3):
        try:
            result = _call_llm(text, attempt)
            log.info(f"--- extraction OK (attempt {attempt}) ---")
            return result
        except Exception as e:
            log.error(f"[attempt {attempt}] failed — {type(e).__name__}: {e}")
    log.error(f"--- extraction FAILED after 2 attempts ---")
    return None
