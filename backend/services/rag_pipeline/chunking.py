"""
Pipeline IA — Étape 2 : Chunking structuré (sémantique, pas un simple découpage).

Méthode (conforme à la spec) :
- détection de titres de section par regex (FR + EN),
- segmentation par sections,
- sous-découpage des sections trop longues (« classification de phrases si nécessaire »).

Chaque chunk porte un `section_type` normalisé (competences, experience,
formation, langues, projets, profil...) qui servira de métadonnée au stockage.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


@dataclass
class Chunk:
    section_type: str
    text: str


# Type de section normalisé -> motifs d'en-tête reconnus (sans accent, minuscule).
SECTION_PATTERNS: dict[str, list[str]] = {
    "competences": [r"competences?", r"skills?", r"atouts?", r"savoir[- ]faire", r"technologies?", r"outils( et logiciels)?", r"langages?( de programmation)?", r"frameworks?( et bibliotheques?)?", r"environnements?( & outils| et outils)?"],
    "experience": [r"experiences?( professionnelles?)?", r"parcours( professionnel)?", r"emplois?"],
    "formation": [r"formations?", r"diplomes?( et formations?)?", r"education", r"etudes", r"scolarite", r"cursus"],
    "langues": [r"langues?", r"languages?"],
    "projets": [r"projets?", r"projects?", r"realisations?"],
    "interets": [r"centres? d.?interets?", r"loisirs", r"hobbies", r"interests"],
    "profil": [r"profil", r"a propos", r"objectif(s)?", r"summary", r"about( me)?", r"presentation"],
    "certifications": [r"certifications?", r"certificats?"],
    "references": [r"references?"],
    "contact": [r"contact", r"coordonnees", r"informations? (personnelles?|de contact)"],
}


def _normalize(s: str) -> str:
    """Minuscule + suppression des accents, pour comparer les en-têtes."""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower().strip()


# Pré-compilation : pour chaque type, un regex qui matche la ligne d'en-tête,
# éventuellement suivie de « : » et d'un contenu inline (ex: "Skills: Python, ...").
_COMPILED: list[tuple[str, re.Pattern]] = []
for _type, _patterns in SECTION_PATTERNS.items():
    _alt = "|".join(_patterns)
    _COMPILED.append(
        (_type, re.compile(rf"^\s*(?:{_alt})\s*:?\s*(?P<inline>.*)$", re.IGNORECASE))
    )


def _match_header(line: str) -> tuple[str | None, str]:
    """
    Si la ligne est un titre de section, renvoie (type, contenu_inline).
    Sinon (None, "").
    """
    norm = _normalize(line)
    if not norm or len(norm) > 45:  # un titre est court ; évite les faux positifs
        return None, ""
    for section_type, pattern in _COMPILED:
        m = pattern.match(norm)
        if m:
            # Le contenu inline doit être repris depuis la ligne ORIGINALE (accents),
            # pas la version normalisée : on récupère ce qui suit le « : ».
            inline = ""
            if ":" in line:
                inline = line.split(":", 1)[1].strip()
            return section_type, inline
    return None, ""


def _split_long(text: str, max_chars: int) -> list[str]:
    """Sous-découpe une section trop longue, en regroupant les lignes/phrases."""
    if len(text) <= max_chars:
        return [text]
    pieces: list[str] = []
    buffer = ""
    # On découpe d'abord par lignes, puis on regroupe jusqu'à max_chars.
    for line in text.split("\n"):
        if buffer and len(buffer) + len(line) + 1 > max_chars:
            pieces.append(buffer.strip())
            buffer = line
        else:
            buffer = f"{buffer}\n{line}" if buffer else line
    if buffer.strip():
        pieces.append(buffer.strip())
    return pieces


def chunk_cv(text: str, max_chunk_chars: int = 700) -> list[Chunk]:
    """
    Découpe le texte d'un CV en chunks par section sémantique.

    Le bloc situé avant le premier titre détecté (souvent nom + contact) est
    conservé sous le type « entete ».
    """
    sections: list[tuple[str, list[str]]] = []
    current_type = "entete"
    current_lines: list[str] = []

    for line in text.split("\n"):
        section_type, inline = _match_header(line)
        if section_type:
            sections.append((current_type, current_lines))
            current_type = section_type
            current_lines = [inline] if inline else []
        else:
            current_lines.append(line)
    sections.append((current_type, current_lines))

    chunks: list[Chunk] = []
    for section_type, lines in sections:
        content = "\n".join(l for l in lines).strip()
        if not content:
            continue
        for piece in _split_long(content, max_chunk_chars):
            if piece.strip():
                chunks.append(Chunk(section_type=section_type, text=piece.strip()))
    return chunks
