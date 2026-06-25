"""
Démo bout-en-bout du pipeline IA, sur les 3 vrais CV de mock_data/cvs/.

Indexe les CV (extraction -> chunking -> embeddings -> FAISS), puis lance une
requête RH et affiche le classement des candidats.

Usage :
    python scripts/demo_pipeline.py
    python scripts/demo_pipeline.py --query "data engineer python docker"
    python scripts/demo_pipeline.py --fake     # embedder factice, sans télécharger le modèle

Le mode --fake sert au test hors-ligne (CI, sandbox sans accès HuggingFace) :
il produit des vecteurs déterministes par sac-de-mots, suffisants pour
vérifier la mécanique (chunking, index, retrieval, ranking) — pas la qualité
sémantique réelle, qui nécessite le vrai modèle all-MiniLM-L6-v2.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Permet de lancer le script depuis n'importe où
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.ats_engine import search_candidates  # noqa: E402
from services.rag_pipeline import FaissVectorStore, get_embedder, index_cv, set_embedder  # noqa: E402

CVS_DIR = Path(__file__).resolve().parent.parent / "mock_data" / "cvs"


def use_fake_embedder(dim: int = 384) -> None:
    """Installe un embedder factice déterministe (sac-de-mots hashé, normalisé)."""
    import re

    import numpy as np

    class FakeEmbedder:
        def __init__(self, dim: int):
            self.dim = dim

        def encode(self, texts: list[str]) -> np.ndarray:
            vecs = np.zeros((len(texts), self.dim), dtype="float32")
            for i, t in enumerate(texts):
                for tok in re.findall(r"\w+", t.lower()):
                    vecs[i, hash(tok) % self.dim] += 1.0
            norms = np.linalg.norm(vecs, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            return (vecs / norms).astype("float32")

    set_embedder(FakeEmbedder(dim))


def main() -> None:
    parser = argparse.ArgumentParser(description="Démo du pipeline IA (RAG + ranking).")
    parser.add_argument("--query", default="Je cherche un data engineer avec Python et Docker")
    parser.add_argument("--fake", action="store_true", help="Embedder factice (hors-ligne).")
    parser.add_argument("--top-k", type=int, default=20)
    args = parser.parse_args()

    if args.fake:
        use_fake_embedder()
        print("[mode --fake : embedder factice, qualité sémantique non représentative]\n")

    embedder = get_embedder()
    store = FaissVectorStore(dim=embedder.dim)

    print("Indexation des CV…")
    for pdf in sorted(CVS_DIR.glob("*.pdf")):
        candidate_id = pdf.stem  # ex: "ryan_maria_paul"
        n = index_cv(candidate_id, store, pdf_path=str(pdf), embedder=embedder)
        print(f"  - {candidate_id:30} {n} chunks")
    print(f"Total : {len(store)} chunks indexés.\n")

    print(f"Requête RH : « {args.query} »\n")
    classement = search_candidates(args.query, store, top_k_chunks=args.top_k, embedder=embedder)

    print("Classement des candidats (score = moyenne des similarités) :")
    for rang, c in enumerate(classement, 1):
        print(f"  {rang}. {c['candidate_id']:30} score={c['score']:.3f}  ({c['n_chunks']} chunks)")
        meilleur = c["chunks"][0]
        apercu = meilleur["text"].replace("\n", " ")[:70]
        print(f"      meilleur chunk [{meilleur['section_type']}] : {apercu}…")


if __name__ == "__main__":
    main()
