"""
Pipeline IA — Étape 3 : Embeddings.

Chaque chunk (et chaque requête) est converti en vecteur via
sentence-transformers/all-MiniLM-L6-v2 (dimension 384).

Les vecteurs sont normalisés (norme L2 = 1) afin que le produit scalaire
calculé par l'index FAISS corresponde directement au cosinus (cf. Étape 4).

L'import de `sentence_transformers` est paresseux : le module se charge sans
la dépendance (utile pour les tests, qui injectent un embedder factice), et
le vrai modèle n'est téléchargé/chargé qu'à la première utilisation.
"""

from __future__ import annotations

from typing import Protocol

import numpy as np


class Embedder(Protocol):
    """Interface minimale d'un embedder (permet l'injection d'un faux en test)."""

    dim: int

    def encode(self, texts: list[str]) -> np.ndarray:  # (n, dim), float32, normalisé
        ...


def _l2_normalize(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0  # évite la division par zéro sur un vecteur nul
    return (vectors / norms).astype("float32")


class SentenceTransformerEmbedder:
    """Embedder réel basé sur sentence-transformers."""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None
        self._dim: int | None = None

    def _load(self):
        if self._model is None:
            # Import paresseux : la dépendance n'est requise qu'ici.
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
            self._dim = self._model.get_sentence_embedding_dimension()
        return self._model

    @property
    def dim(self) -> int:
        if self._dim is None:
            self._load()
        return self._dim

    def encode(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, self.dim), dtype="float32")
        model = self._load()
        vectors = np.asarray(model.encode(texts, convert_to_numpy=True), dtype="float32")
        return _l2_normalize(vectors)


# Singleton réutilisé dans toute l'app (évite de recharger le modèle).
_default_embedder: Embedder | None = None


def get_embedder(model_name: str | None = None) -> Embedder:
    global _default_embedder
    if _default_embedder is None:
        from config import Config

        _default_embedder = SentenceTransformerEmbedder(model_name or Config.RAG_EMBEDDING_MODEL)
    return _default_embedder


def set_embedder(embedder: Embedder) -> None:
    """Permet d'injecter un embedder (ex: un faux déterministe pour les tests)."""
    global _default_embedder
    _default_embedder = embedder
