import json
import re
from openai import OpenAI
from config import OPENROUTER_BASE_URL, get_openrouter_api_key, get_openrouter_model

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


def _call_llm(text: str) -> dict:
    client = _get_client()
    response = client.chat.completions.create(
        model=get_openrouter_model(),
        messages=[
            {"role": "system", "content": EXTRACTION_PROMPT},
            {"role": "user", "content": text},
        ],
        temperature=0,
    )
    raw = response.choices[0].message.content
    raw = raw.strip()
    raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
    raw = re.sub(r"```$", "", raw).strip()
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        raw = match.group(0)
    return json.loads(raw)


def extract_job_data(text: str) -> dict | None:
    """Send raw job text to LLM and return structured data. Retries once on failure."""
    for attempt in range(2):
        try:
            return _call_llm(text)
        except Exception as e:
            print(f"Extraction error (attempt {attempt + 1}): {e}")
    return None
