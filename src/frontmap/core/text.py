"""text — tokenisation lexicale + scoring borné (socle partagé pour le verbe `where`).

Vendorisé de `code-map` (`codemap/symbols.py`, parties `tokenize`/`_score`), généralisé pour scorer
**n'importe quel enregistrement** (nom + texte-foin) plutôt que le seul `Symbol`. Sert `query.where` :
« quelle primitive / quel token pour X ? ». Ranking lexical BORNÉ [0,1] (couverture + bonus nom exact),
pas d'IDF (hygiène lexicale seule).
"""
from __future__ import annotations

import re
import unicodedata

_SPLIT = re.compile(r"[^a-z0-9]+")

# Mots-outils FR+EN sans valeur de recherche (hygiène, PAS de l'IDF).
STOPWORDS = {
    "le", "la", "les", "un", "une", "des", "de", "du", "d", "l", "et", "ou", "à", "a",
    "au", "aux", "en", "dans", "pour", "par", "sur", "avec", "ce", "cet", "cette", "ces",
    "que", "qui", "se", "son", "sa", "ses", "the", "of",
    "an", "and", "or", "to", "in", "on", "for", "by", "with", "this", "that", "is", "be",
    "as", "at", "from", "into",
}


def _fold(text: str) -> str:
    """Replie les accents (résoudre → resoudre) — NFKD + drop des marques combinantes."""
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def tokenize(text: str) -> list[str]:
    """Tokens lexicaux : accents repliés, minuscules, camel/snake éclatés, mots-outils retirés, dédup."""
    text = _fold(text)
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)  # éclate camelCase
    seen: set[str] = set()
    out: list[str] = []
    for tok in _SPLIT.split(text.lower()):
        if tok and tok not in seen and tok not in STOPWORDS:
            seen.add(tok)
            out.append(tok)
    return out


def score(intent_tokens: list[str], name: str, haystack: str) -> float:
    """Lexical borné [0,1] : couverture des termes de l'intention (nom pondéré) + bonus nom exact.

    `name` = identifiant de l'enregistrement (primitive/token) ; `haystack` = texte cherchable complet
    (nom + lead + valeur…). Signature générique → réutilisable hors du schéma `Symbol`.
    """
    if not intent_tokens:
        return 0.0
    name_toks = set(tokenize(name))
    hay = set(tokenize(haystack))
    covered = sum(1 for t in intent_tokens if t in hay)
    coverage = covered / len(intent_tokens)
    name_hits = sum(1 for t in intent_tokens if t in name_toks)
    name_bonus = 0.3 * (name_hits / len(intent_tokens))
    return round(min(1.0, 0.7 * coverage + name_bonus), 3)
