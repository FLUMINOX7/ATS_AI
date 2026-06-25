"""
«component» API Auth (cf. diagramme, package BACKEND) — implémenté (Phase 1).

- POST /auth/register : inscription d'un candidat (rôle forcé à "Utilisateur")
- POST /auth/login    : connexion, renvoie un JWT (claims user_id + role)
- POST /auth/logout   : révoque le token courant (blocklist)
- GET  /auth/me       : renvoie le compte connecté
"""

from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    get_jwt,
    jwt_required,
)
from pydantic import ValidationError

from extensions import get_db
from models.schemas import UserCreate, UserLogin
from security import (
    current_user,
    hash_password,
    revoke_token,
    serialize_user,
    verify_password,
)

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def _validation_error(exc: ValidationError):
    details = [
        {"champ": ".".join(str(p) for p in e["loc"]), "message": e["msg"]}
        for e in exc.errors()
    ]
    return jsonify({"error": "Validation échouée.", "details": details}), 400


@auth_bp.post("/register")
def register():
    payload = request.get_json(silent=True) or {}
    try:
        data = UserCreate(**payload)
    except ValidationError as exc:
        return _validation_error(exc)

    db = get_db()
    if db.users.find_one({"email": data.email.lower()}):
        return jsonify({"error": "Un compte avec cet email existe déjà."}), 409

    # Sécurité : l'inscription publique crée toujours un candidat.
    # L'attribution des rôles RH/Admin passe par l'API Utilisateurs (Phase 2),
    # réservée à un Admin — on ne laisse pas un inconnu se déclarer Admin.
    doc = {
        "prenom": data.prenom.strip(),
        "nom": data.nom.strip(),
        "email": data.email.lower(),
        "mdp_hash": hash_password(data.mdp),
        "role": "Utilisateur",
        "date_creation": datetime.now(timezone.utc),
    }
    result = db.users.insert_one(doc)
    doc["_id"] = result.inserted_id
    return jsonify({"message": "Compte créé.", "user": serialize_user(doc)}), 201


@auth_bp.post("/login")
def login():
    payload = request.get_json(silent=True) or {}
    try:
        data = UserLogin(**payload)
    except ValidationError as exc:
        return _validation_error(exc)

    user = get_db().users.find_one({"email": data.email.lower()})
    if not user or not verify_password(data.mdp, user.get("mdp_hash", "")):
        # Message volontairement générique (ne pas révéler si l'email existe).
        return jsonify({"error": "Email ou mot de passe incorrect."}), 401

    token = create_access_token(
        identity=str(user["_id"]),
        additional_claims={"role": user["role"]},
    )
    return jsonify({"access_token": token, "user": serialize_user(user)}), 200


@auth_bp.post("/logout")
@jwt_required()
def logout():
    revoke_token(get_jwt()["jti"])
    return jsonify({"message": "Déconnecté."}), 200


@auth_bp.get("/me")
@jwt_required()
def me():
    user = current_user()
    if not user:
        return jsonify({"error": "Compte introuvable."}), 404
    return jsonify({"user": serialize_user(user)}), 200
