"""
Pipeline IA — orchestration du RAG Pipeline (Étapes 1 à 4 + requête).

- index_cv(...)          : CV -> texte -> chunks -> embeddings -> stockage
- similarity_search(...) : requête -> embedding -> top-k chunks les plus proches

Le regroupement par candidat et le ranking final (Section 7 de la spec) sont
dans services/ats_engine (composant « ATS IA Engine » du diagramme).
"""

from __future__ import annotations

from .chunking import chunk_cv
from .embeddings import Embedder, get_embedder
from .extraction import extract_text_from_path, extract_text_from_pdf
from .vector_store import FaissVectorStore


def index_cv(
    candidate_id: str,
    store: FaissVectorStore,
    *,
    pdf_bytes: bytes | None = None,
    pdf_path: str | None = None,
    text: str | None = None,
    embedder: Embedder | None = None,
    max_chunk_chars: int = 700,
) -> int:
    """
    Indexe un CV dans le store. Fournir l'une des sources : pdf_bytes, pdf_path
    ou text. Renvoie le nombre de chunks indexés.
    """
    embedder = embedder or get_embedder()

    if text is None:
        if pdf_bytes is not None:
            text = extract_text_from_pdf(pdf_bytes)
        elif pdf_path is not None:
            text = extract_text_from_path(pdf_path)
        else:
            raise ValueError("Fournir pdf_bytes, pdf_path ou text.")

    chunks = chunk_cv(text, max_chunk_chars=max_chunk_chars)
    if not chunks:
        return 0

    vectors = embedder.encode([c.text for c in chunks])
    metadatas = [
        {"candidate_id": candidate_id, "section_type": c.section_type, "text": c.text}
        for c in chunks
    ]
    store.add(vectors, metadatas)
    return len(chunks)


def similarity_search(
    query: str,
    store: FaissVectorStore,
    *,
    top_k: int = 5,
    embedder: Embedder | None = None,
) -> list[dict]:
    """
    Embedde la requête puis renvoie les top_k chunks les plus proches :
    [{score, candidate_id, section_type, text}].
    """
    embedder = embedder or get_embedder()
    query_vector = embedder.encode([query])[0]
    return store.search(query_vector, top_k=top_k)
