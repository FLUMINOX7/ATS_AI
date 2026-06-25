"""
«component» RAG Pipeline (cf. diagramme, package BACKEND) — implémenté.

Pipeline conforme à la spec :
  Étape 1  extraction.py     CV PDF -> texte (PyMuPDF)
  Étape 2  chunking.py       texte -> chunks par section (regex de titres)
  Étape 3  embeddings.py     chunk -> vecteur (sentence-transformers/all-MiniLM-L6-v2)
  Étape 4  vector_store.py   stockage {id candidat, section_type, vecteur} dans FAISS

Orchestration : pipeline.py (index_cv, similarity_search).
Le ranking final par candidat est dans services/ats_engine.

API publique :
    from services.rag_pipeline import (
        extract_text_from_pdf, extract_text_from_path,
        chunk_cv, Chunk,
        get_embedder, set_embedder, SentenceTransformerEmbedder,
        FaissVectorStore,
        index_cv, similarity_search,
    )
"""

from .chunking import Chunk, chunk_cv
from .embeddings import SentenceTransformerEmbedder, get_embedder, set_embedder
from .extraction import extract_text_from_path, extract_text_from_pdf
from .pipeline import index_cv, similarity_search
from .vector_store import FaissVectorStore

__all__ = [
    "extract_text_from_pdf",
    "extract_text_from_path",
    "chunk_cv",
    "Chunk",
    "get_embedder",
    "set_embedder",
    "SentenceTransformerEmbedder",
    "FaissVectorStore",
    "index_cv",
    "similarity_search",
]
