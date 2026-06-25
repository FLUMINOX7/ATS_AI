"""
«component» ATS IA Engine (cf. diagramme, package BACKEND) — implémenté.

Implémente le « Pipeline de requête utilisateur » (Section 7 de la spec) :
  Étape 1  embedding de la requête          (via rag_pipeline)
  Étape 2  similarité cosinus               (via FAISS, rag_pipeline)
  Étape 3  retrieval top-k chunks + regroupement par candidat
  Étape 4  ranking final : score = moyenne des similarités des chunks du candidat

S'appuie entièrement sur services.rag_pipeline (le RAG Pipeline du diagramme).
"""

from __future__ import annotations

from statistics import mean

from services.rag_pipeline import similarity_search
from services.rag_pipeline.embeddings import Embedder
from services.rag_pipeline.vector_store import FaissVectorStore


def search_candidates(
    query: str,
    store: FaissVectorStore,
    *,
    top_k_chunks: int = 20,
    embedder: Embedder | None = None,
) -> list[dict]:
    """
    Recherche RH en langage naturel -> candidats classés.

    Exemple : "Je cherche un data engineer avec Python et Docker"

    Renvoie une liste triée par score décroissant :
        [{
            "candidate_id": ...,
            "score": moyenne des similarités des chunks retenus,
            "n_chunks": nombre de chunks de ce candidat dans le top-k,
            "chunks": [{score, section_type, text}, ...]
        }, ...]
    """
    # Étapes 1 & 2 & 3 : embedding requête -> similarité -> top-k chunks
    hits = similarity_search(query, store, top_k=top_k_chunks, embedder=embedder)

    # Étape 3 (suite) : regroupement par candidat
    par_candidat: dict[str, list[dict]] = {}
    for hit in hits:
        par_candidat.setdefault(hit["candidate_id"], []).append(hit)

    # Étape 4 : ranking final, score = moyenne des similarités des chunks
    classement = []
    for candidate_id, chunks in par_candidat.items():
        classement.append(
            {
                "candidate_id": candidate_id,
                "score": mean(c["score"] for c in chunks),
                "n_chunks": len(chunks),
                "chunks": [
                    {"score": c["score"], "section_type": c["section_type"], "text": c["text"]}
                    for c in sorted(chunks, key=lambda c: c["score"], reverse=True)
                ],
            }
        )

    classement.sort(key=lambda c: c["score"], reverse=True)
    return classement


def match_offer_candidates(
    offer: dict,
    store: FaissVectorStore,
    *,
    top_k_chunks: int = 20,
    embedder: Embedder | None = None,
) -> list[dict]:
    """
    Matching Offre <-> CV : construit une requête à partir de l'offre
    (titre + compétences requises + mots-clés) puis réutilise search_candidates.

    `offer` suit la forme de mock_data/offers.json.
    """
    skills = offer.get("required_skills", [])
    skill_names = [s["name"] if isinstance(s, dict) else str(s) for s in skills]
    query = " ".join(
        [offer.get("title", "")]
        + skill_names
        + offer.get("keywords", [])
    ).strip()
    return search_candidates(query, store, top_k_chunks=top_k_chunks, embedder=embedder)
