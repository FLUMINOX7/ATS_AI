"""
Tests du pipeline IA (RAG Pipeline + ATS IA Engine).

On utilise un embedder factice déterministe (sac-de-mots) pour tester toute
la mécanique sans télécharger le vrai modèle all-MiniLM-L6-v2 :
- Étape 1 : extraction PyMuPDF sur les vrais CV
- Étape 2 : chunking sémantique par section
- Étape 4 : stockage/persistance FAISS + recherche
- Section 7 : regroupement par candidat + ranking (moyenne des similarités)
"""

import re
from pathlib import Path

import numpy as np
import pytest

from services.ats_engine import search_candidates
from services.rag_pipeline import (
    FaissVectorStore,
    chunk_cv,
    extract_text_from_path,
    index_cv,
    similarity_search,
)

CVS_DIR = Path(__file__).resolve().parent.parent / "mock_data" / "cvs"


class FakeEmbedder:
    """Sac-de-mots hashé, normalisé. Déterministe et sans dépendance réseau."""

    def __init__(self, dim: int = 384):
        self.dim = dim

    def encode(self, texts: list[str]) -> np.ndarray:
        vecs = np.zeros((len(texts), self.dim), dtype="float32")
        for i, t in enumerate(texts):
            for tok in re.findall(r"\w+", t.lower()):
                # hash stable (pas le hash() de Python qui est salé par run)
                h = sum(bytearray(tok.encode("utf-8")))
                vecs[i, h % self.dim] += 1.0
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return (vecs / norms).astype("float32")


@pytest.fixture()
def embedder():
    return FakeEmbedder()


# --- Étape 1 : extraction --------------------------------------------------
def test_extraction_pdf_reelle():
    text = extract_text_from_path(str(CVS_DIR / "ryan_maria_paul.pdf"))
    assert len(text) > 500
    assert "Python" in text
    assert "Allianz" in text  # contenu réel du CV


# --- Étape 2 : chunking ----------------------------------------------------
def test_chunking_detecte_sections():
    text = extract_text_from_path(str(CVS_DIR / "ryan_maria_paul.pdf"))
    chunks = chunk_cv(text)
    types = {c.section_type for c in chunks}
    # Ce CV contient au moins formation, compétences, langues
    assert "formation" in types
    assert "competences" in types
    assert "langues" in types
    assert all(c.text.strip() for c in chunks)  # pas de chunk vide


def test_chunking_inline_header():
    """Cas de la spec : 'Skills: Python, Flask, Docker, NLP' sur une seule ligne."""
    text = "John Doe\nSkills: Python, Flask, Docker, NLP\nExperience: 2 years backend at XYZ"
    chunks = chunk_cv(text)
    by_type = {c.section_type: c.text for c in chunks}
    assert "competences" in by_type
    assert "Python" in by_type["competences"]
    assert "experience" in by_type


# --- Étape 4 : stockage FAISS ---------------------------------------------
def test_index_and_search(embedder):
    store = FaissVectorStore(dim=embedder.dim)
    n = index_cv("cand_test", store, text="Skills: Python Docker\nExperience: Data Engineer", embedder=embedder)
    assert n >= 2
    assert len(store) == n
    hits = similarity_search("Python Docker", store, top_k=5, embedder=embedder)
    assert hits
    assert hits[0]["candidate_id"] == "cand_test"
    assert "score" in hits[0] and "section_type" in hits[0]


def test_persistence_roundtrip(embedder, tmp_path):
    store = FaissVectorStore(dim=embedder.dim)
    index_cv("c1", store, text="Skills: Python Docker Spark", embedder=embedder)
    store.save(tmp_path)

    reloaded = FaissVectorStore.load(tmp_path)
    assert len(reloaded) == len(store)
    hits = similarity_search("Python", reloaded, top_k=3, embedder=embedder)
    assert hits and hits[0]["candidate_id"] == "c1"


# --- Section 7 : ranking par candidat -------------------------------------
def test_ranking_groupe_par_candidat(embedder):
    store = FaissVectorStore(dim=embedder.dim)
    index_cv("data_eng", store, text="Skills: Python Spark Docker ETL\nExperience: Data Engineer pipelines", embedder=embedder)
    index_cv("designer", store, text="Skills: Figma Photoshop\nExperience: UX Designer maquettes", embedder=embedder)

    result = search_candidates("data engineer python spark", store, top_k_chunks=20, embedder=embedder)
    assert len(result) == 2
    # le data engineer doit être classé devant le designer
    assert result[0]["candidate_id"] == "data_eng"
    # le score est bien une moyenne (entre 0 et 1 ici, vecteurs normalisés)
    assert 0.0 <= result[0]["score"] <= 1.0
    # un seul candidat par entrée (regroupement)
    assert len({r["candidate_id"] for r in result}) == len(result)


def test_ranking_sur_vrais_cv(embedder):
    store = FaissVectorStore(dim=embedder.dim)
    for pdf in CVS_DIR.glob("*.pdf"):
        index_cv(pdf.stem, store, pdf_path=str(pdf), embedder=embedder)
    result = search_candidates("data engineer python docker", store, embedder=embedder)
    assert len(result) == 3  # 3 candidats
    # les scores sont triés décroissants
    scores = [r["score"] for r in result]
    assert scores == sorted(scores, reverse=True)
