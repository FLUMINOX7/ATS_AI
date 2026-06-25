"""
«component» API Utilisateurs (cf. diagramme, package BACKEND).

Squelette protégé : la logique métier (CRUD, recherche, changement de rôle)
sera implémentée en Phase 2. En revanche la SÉCURITÉ est déjà branchée
(Phase 1) via @role_required, pour montrer la réutilisation du décorateur :
ces routes exigent un JWT valide et le bon rôle, puis renvoient 501.
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from security import role_required

users_bp = Blueprint("users", __name__, url_prefix="/users")


@users_bp.get("")
@role_required("Admin")
def list_users():
    """TODO (Phase 2) : filtrer par ?q=... (nom/prénom/id)."""
    request.args.get("q")
    return jsonify({"error": "Not implemented yet (Phase 2 - API Utilisateurs)"}), 501


@users_bp.post("")
@role_required("Admin")
def create_user():
    """TODO (Phase 2) : valider avec UserCreate, vérifier l'email, hasher le mdp."""
    request.get_json(silent=True)
    return jsonify({"error": "Not implemented yet (Phase 2 - API Utilisateurs)"}), 501


@users_bp.get("/me")
@jwt_required()
def get_me():
    """TODO (Phase 2) : renvoyer le profil courant (accessible à tout connecté)."""
    return jsonify({"error": "Not implemented yet (Phase 2 - API Utilisateurs)"}), 501


@users_bp.get("/<user_id>")
@role_required("Admin")
def get_user(user_id):
    """TODO (Phase 2) : récupérer un utilisateur par son id."""
    return jsonify({"error": "Not implemented yet (Phase 2 - API Utilisateurs)", "id": user_id}), 501


@users_bp.patch("/<user_id>")
@role_required("Admin")
def update_user(user_id):
    """TODO (Phase 2) : changer le rôle / les infos."""
    request.get_json(silent=True)
    return jsonify({"error": "Not implemented yet (Phase 2 - API Utilisateurs)", "id": user_id}), 501


@users_bp.delete("/<user_id>")
@role_required("Admin")
def delete_user(user_id):
    """TODO (Phase 2) : supprimer un compte."""
    return jsonify({"error": "Not implemented yet (Phase 2 - API Utilisateurs)", "id": user_id}), 501
