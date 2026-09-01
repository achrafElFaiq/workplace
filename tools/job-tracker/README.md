# job-tracker

Suivi de candidatures. Colle un lien ou du texte, le LLM extrait les infos ;
génère un CV et une lettre de motivation adaptés à l'offre ; Gmail associe
les réponses des recruteurs et met à jour le statut automatiquement.

## Features

### Ajouter une candidature
- Colle un lien d'offre (ou le texte si le scraping échoue) — extraction
  automatique (entreprise, poste, localisation, contrat, salaire, stack,
  missions, prérequis, séniorité...) via LLM.
- Génère un **CV** et une **lettre de motivation** adaptés à l'offre avant
  même de sauvegarder la candidature — le CV part de ton `cv.tex` et
  l'ajuste légèrement (titre, quelques mots-clés) sans jamais réécrire tout
  le document ; la lettre est rédigée à partir de ton CV + l'offre et
  injectée dans un template LaTeX. Les deux sont compilés en PDF
  téléchargeable.

### Dashboard
- Liste des candidatures sous forme de cartes, colorées selon le statut
  (bleu = en attente, jaune = en cours, vert = accepté, rouge = refusé,
  gris = sans retour) — clique dessus pour voir/éditer les détails.
- Filtres : statut, source, entreprise, poste, localisation (menus
  déroulants alimentés uniquement par ce qui existe déjà en base).
- Stats en un coup d'œil : total, taux de réponse, et le nombre de
  candidatures dans chacun des 5 statuts.
- **Sync Gmail** — scanne tes boîtes, associe les emails aux candidatures
  actives, met à jour le statut automatiquement.
- **Auto "Sans retour"** — marque les candidatures sans réponse depuis 30j.
- Export CSV.

### Statuts
Volontairement réduits à 5 : `applied` (candidature envoyée, rien reçu) →
`in_progress` (accusé de réception, entretien, test technique...) → puis
`accepted` ou `rejected` (refus explicite, écrit par une vraie personne).
`Sans retour` regroupe le silence total et les refus automatiques
génériques (ATS) — ni l'un ni l'autre n'est un vrai signal humain, donc ni
l'un ni l'autre ne compte comme une réponse dans le taux de réponse.

### Contacts
Carnet de contacts manuel, indépendant des candidatures : nom, prénom,
fonction, entreprise, email, et une note libre par contact. Recherche par
nom (insensible à la casse, sous-chaîne), filtres entreprise/fonction
(menus déroulants, mêmes valeurs que celles déjà en base).

## Setup

```bash
git clone https://github.com/achrafElFaiq/job-tracker.git
cd job-tracker
```

Crée un fichier `.env` à la racine du projet :

```env
OPENROUTER_API_KEY=sk-or-v1-ta-cle-ici
OPENROUTER_MODEL=meta-llama/llama-3.3-70b-instruct

GMAIL_1_ADDRESS=ton-email@gmail.com
GMAIL_1_APP_PASSWORD=xxxx xxxx xxxx xxxx

GMAIL_2_ADDRESS=ton-autre-email@gmail.com
GMAIL_2_APP_PASSWORD=xxxx xxxx xxxx xxxx
```

Tu peux ajouter autant de comptes Gmail que nécessaire (1, 2, 3...) en
suivant le format `GMAIL_N_ADDRESS` / `GMAIL_N_APP_PASSWORD`. Gmail est
optionnel, le tracker fonctionne sans.

### Générer CV / lettre de motivation (optionnel)

Nécessite [tectonic](https://tectonic-typesetting.github.io) (compilateur
LaTeX) :

```bash
brew install tectonic
```

Place ensuite à la racine de `data/` :
- `cv.tex` — ton CV en LaTeX (jamais modifié sur disque, seulement lu ;
  chaque génération produit une copie adaptée à la volée).
- `cover_letter_template.tex` — ton template de lettre de motivation,
  avec le marqueur `%%LETTER_BODY%%` à l'endroit où le corps généré doit
  s'insérer.
- les images éventuellement référencées par ton CV (ex: photo de profil).

Ces fichiers contiennent tes informations personnelles : ils sont
gitignorés, jamais poussés sur le repo.

### Obtenir les clés

| Service | Lien | Notes |
|---------|------|-------|
| OpenRouter | [openrouter.ai/keys](https://openrouter.ai/keys) | Crée un compte puis génère une clé API |
| Gmail App Password | [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) | La validation en 2 étapes doit être activée |

### Lancer

```bash
./setup.sh
./run.sh
```

## Stack

Python — Streamlit — SQLite — OpenRouter — IMAP — LaTeX (tectonic)
