"""
Configuration de l'application, lue depuis les variables d'environnement.

Rien n'est codé en dur ici : toutes les valeurs sensibles (URI Mongo, clé
JWT, clé du fournisseur LLM...) viennent du fichier .env (voir .env.example).
"""

import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()


def _get_bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


class Config:
    # --- Flask -----------------------------------------------------------
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    DEBUG = _get_bool("FLASK_DEBUG", True)
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH_MB", "10")) * 1024 * 1024  # taille max upload (CV)

    # --- MongoDB Atlas -----------------------------------------------------
    # «external» MongoDB Atlas du diagramme : base principale + stockage vecteurs
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    MONGO_DBNAME = os.getenv("MONGO_DBNAME", "ats_ia")

    # Nom de l'index Atlas Vector Search (à créer manuellement sur Atlas,
    # voir README) utilisé par le RAG Pipeline / ATS IA Engine.
    VECTOR_INDEX_NAME = os.getenv("VECTOR_INDEX_NAME", "vector_index")
    EMBEDDINGS_COLLECTION = os.getenv("EMBEDDINGS_COLLECTION", "embeddings")

    # --- GridFS (« Stockage PDF CV » du diagramme) ------------------------
    GRIDFS_BUCKET_NAME = os.getenv("GRIDFS_BUCKET_NAME", "cv_files")
    ALLOWED_CV_EXTENSIONS = {"pdf", "docx"}

    # --- JWT (API Auth) ----------------------------------------------------
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret-change-me")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=int(os.getenv("JWT_EXPIRES_HOURS", "8")))

    # --- LLM Provider (« external » du diagramme) --------------------------
    # Utilisé par le Chatbot LLM et par le RAG Pipeline (embeddings).
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")  # ex: openai, mistral...
    LLM_API_KEY = os.getenv("LLM_API_KEY", "")
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    LLM_CHAT_MODEL = os.getenv("LLM_CHAT_MODEL", "gpt-4o-mini")
    LLM_EMBEDDING_MODEL = os.getenv("LLM_EMBEDDING_MODEL", "text-embedding-3-small")

    # --- Pipeline IA (RAG) -------------------------------------------------
    # Modèle d'embedding local (sentence-transformers), conformément à la spec.
    # all-MiniLM-L6-v2 -> vecteurs de dimension 384.
    RAG_EMBEDDING_MODEL = os.getenv("RAG_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    RAG_EMBEDDING_DIM = int(os.getenv("RAG_EMBEDDING_DIM", "384"))
    # Stockage des vecteurs : index FAISS persisté sur disque (ou « équivalent »).
    FAISS_INDEX_DIR = os.getenv("FAISS_INDEX_DIR", "data/faiss")
    # Découpage : au-delà de cette taille, une section est sous-découpée.
    RAG_MAX_CHUNK_CHARS = int(os.getenv("RAG_MAX_CHUNK_CHARS", "700"))

    # --- CORS ---------------------------------------------------------------
    # Origine(s) autorisée(s) à appeler cette API (le frontend Streamlit).
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:8501").split(",")
