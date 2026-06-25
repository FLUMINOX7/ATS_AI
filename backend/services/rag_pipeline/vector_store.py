"""
Pipeline IA — Étape 4 : Stockage.

Chaque chunk est stocké sous forme : id candidat + type de section + vecteur,
dans un index FAISS (« ou équivalent » selon la spec).

On utilise IndexFlatIP (produit scalaire). Comme les vecteurs sont normalisés
(cf. embeddings.py), le produit scalaire = cosinus, ce qui correspond à la
mesure de similarité demandée :  cos(θ) = A·B / (||A|| ||B||).

L'index et ses métadonnées sont persistables sur disque :
- <dir>/index.faiss       : l'index vectoriel
- <dir>/metadata.json     : la liste des métadonnées, alignée sur l'index
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np


class FaissVectorStore:
    def __init__(self, dim: int):
        import faiss  # import paresseux

        self.dim = dim
        self.index = faiss.IndexFlatIP(dim)
        self.metadata: list[dict] = []

    def __len__(self) -> int:
        return len(self.metadata)

    def add(self, vectors: np.ndarray, metadatas: list[dict]) -> None:
        if len(vectors) == 0:
            return
        if len(vectors) != len(metadatas):
            raise ValueError("vectors et metadatas doivent avoir la même longueur.")
        self.index.add(np.ascontiguousarray(vectors, dtype="float32"))
        self.metadata.extend(metadatas)

    def search(self, query_vector: np.ndarray, top_k: int = 5) -> list[dict]:
        """Renvoie les top_k chunks les plus proches : [{score, ...metadata}]."""
        if len(self.metadata) == 0:
            return []
        q = np.ascontiguousarray(query_vector.reshape(1, -1), dtype="float32")
        k = min(top_k, len(self.metadata))
        scores, indices = self.index.search(q, k)
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            results.append({"score": float(score), **self.metadata[idx]})
        return results

    # --- Persistance -----------------------------------------------------
    def save(self, directory: str | Path) -> None:
        import faiss

        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(directory / "index.faiss"))
        (directory / "metadata.json").write_text(
            json.dumps({"dim": self.dim, "metadata": self.metadata}, ensure_ascii=False),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, directory: str | Path) -> "FaissVectorStore":
        import faiss

        directory = Path(directory)
        payload = json.loads((directory / "metadata.json").read_text(encoding="utf-8"))
        store = cls(dim=payload["dim"])
        store.index = faiss.read_index(str(directory / "index.faiss"))
        store.metadata = payload["metadata"]
        return store
