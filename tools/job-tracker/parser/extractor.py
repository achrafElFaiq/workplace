import json
import re
from openai import OpenAI
from config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, OPENROUTER_MODEL

client = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url=OPENROUTER_BASE_URL,
)

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


def extract_job_data(text: str) -> dict | None:
    """Send raw job text to LLM and return structured data."""
    try:
        response = client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=[
                {"role": "system", "content": EXTRACTION_PROMPT},
                {"role": "user", "content": text},
            ],
            temperature=0,
        )
        raw = response.choices[0].message.content
        # Strip a markdown code fence regardless of language tag (```json,
        # bare ```, etc.) — .removeprefix("```json") only matched that exact
        # variant and silently left a bare ``` fence in place, breaking
        # json.loads.
        raw = raw.strip()
        raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
        raw = re.sub(r"```$", "", raw).strip()
        # The model sometimes prefixes the JSON with a conversational
        # sentence — extract the {...} span regardless of what surrounds it.
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            raw = match.group(0)
        return json.loads(raw)
    except (json.JSONDecodeError, Exception) as e:
        print(f"Extraction error: {e}")
        return None