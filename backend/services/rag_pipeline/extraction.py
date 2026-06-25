"""
Pipeline IA — Étape 1 : Extraction PDF.

CV PDF -> texte brut, avec PyMuPDF (import `fitz`).
"""

from __future__ import annotations

from pathlib import Path

import fitz  # PyMuPDF


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extrait le texte d'un PDF fourni sous forme d'octets (ex: lu depuis GridFS)."""
    text_parts: list[str] = []
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for page in doc:
            text_parts.append(page.get_text("text"))
    return _clean("\n".join(text_parts))


def extract_text_from_path(path: str | Path) -> str:
    """Extrait le texte d'un fichier PDF sur disque (pratique pour les tests / le seed)."""
    with fitz.open(path) as doc:
        text_parts = [page.get_text("text") for page in doc]
    return _clean("\n".join(text_parts))


def _clean(text: str) -> str:
    """Nettoyage léger : normalise les espaces et supprime les lignes vides en trop."""
    lines = [line.strip() for line in text.replace("\r", "\n").split("\n")]
    # On retire les lignes totalement vides en double (mais on garde une séparation)
    cleaned: list[str] = []
    for line in lines:
        if line == "" and (not cleaned or cleaned[-1] == ""):
            continue
        cleaned.append(line)
    return "\n".join(cleaned).strip()
