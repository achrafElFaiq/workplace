#!/bin/bash
set -e

echo ""
echo "  [job-tracker] setup"
echo "  ==================="
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "  [x] Python 3 non trouve. Installe-le : https://python.org"
    exit 1
fi
echo "  [ok] Python $(python3 --version | cut -d' ' -f2)"

# Check uv
if ! command -v uv &> /dev/null; then
    echo "  [..] Installation de uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi
echo "  [ok] uv $(uv --version | cut -d' ' -f2)"

# Install dependencies
echo "  [..] Installation des dependances..."
UV_HTTP_TIMEOUT=120 uv sync
echo "  [ok] Dependances installees"

# Check tectonic (optional, needed for CV / lettre de motivation)
if ! command -v tectonic &> /dev/null; then
    echo "  [!] tectonic non trouve — generation CV/lettre desactivee."
    echo "      Pour l'activer : brew install tectonic"
else
    echo "  [ok] tectonic $(tectonic --version | head -1 | cut -d' ' -f2)"
fi

# Create directories
mkdir -p data

# Check .env
if [ ! -f .env ]; then
    echo ""
    echo "  [x] Fichier .env manquant."
    echo ""
    echo "  Cree un fichier .env avec le contenu suivant :"
    echo ""
    echo "    OPENROUTER_API_KEY=sk-or-v1-ta-cle-ici"
    echo "    OPENROUTER_MODEL=google/gemini-2.5-flash"
    echo "    GMAIL_PERSO_ADDRESS=ton-email@gmail.com"
    echo "    GMAIL_PERSO_APP_PASSWORD=xxxx xxxx xxxx xxxx"
    echo "    GMAIL_PRO_ADDRESS=ton-email-pro@gmail.com"
    echo "    GMAIL_PRO_APP_PASSWORD=xxxx xxxx xxxx xxxx"
    echo ""
    echo "  OpenRouter : https://openrouter.ai/keys"
    echo "  App Password Gmail : https://myaccount.google.com/apppasswords"
    echo ""
    exit 1
fi

# Validate .env content
source_ok=true
if ! grep -q "OPENROUTER_API_KEY=sk-" .env; then
    echo "  [!] OPENROUTER_API_KEY semble invalide dans .env"
    source_ok=false
fi
if ! grep -q "GMAIL_PERSO_ADDRESS=" .env; then
    echo "  [!] GMAIL_PERSO_ADDRESS manquant dans .env (Gmail sync desactive)"
fi

if [ "$source_ok" = true ]; then
    echo "  [ok] .env valide"
fi

# Init database
echo "  [..] Initialisation de la base de donnees..."
uv run python -m db.database
echo "  [ok] Base de donnees prete"

echo ""
echo "  ==================="
echo "  [ok] Setup termine"
echo ""
echo "  Lance l'app :"
echo "    uv run streamlit run app.py"
echo ""