"""
«component» API Offres (cf. diagramme, package BACKEND).

Squelette : logique métier en Phase 3. La sécurité est déjà branchée
(Phase 1) :
- consultation des offres : publique (les candidats doivent pouvoir parcourir)
- création / modification / suppression : RH ou Admin
- candidater à une offre : tout utilisateur connecté
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from security import role_required

offers_bp = Blueprint("offers", __name__, url_prefix="/offers")


@offers_bp.get("")
def list_offers():
    """TODO (Phase 3) : filtres ?department=&location=&status=. Public."""
    request.args.get("status")
    return jsonify({"error": "Not implemented yet (Phase 3 - API Offres)"}), 501


@offers_bp.post("")
@role_required("RH", "Admin")
def create_offer():
    """TODO (Phase 3) : valider avec OfferCreate."""
    request.get_json(silent=True)
    return jsonify({"error": "Not implemented yet (Phase 3 - API Offres)"}), 501


@offers_bp.get("/<offer_id>")
def get_offer(offer_id):
    """TODO (Phase 3) : récupérer une offre par son id. Public."""
    return jsonify({"error": "Not implemented yet (Phase 3 - API Offres)", "id": offer_id}), 501


@offers_bp.patch("/<offer_id>")
@role_required("RH", "Admin")
def update_offer(offer_id):
    """TODO (Phase 3) : modifier une offre."""
    request.get_json(silent=True)
    return jsonify({"error": "Not implemented yet (Phase 3 - API Offres)", "id": offer_id}), 501


@offers_bp.delete("/<offer_id>")
@role_required("RH", "Admin")
def delete_offer(offer_id):
    """TODO (Phase 3) : supprimer une offre."""
    return jsonify({"error": "Not implemented yet (Phase 3 - API Offres)", "id": offer_id}), 501


@offers_bp.post("/<offer_id>/apply")
@jwt_required()
def apply_to_offer(offer_id):
    """TODO (Phase 4 - Gestion Candidatures) : upload CV (GridFS) + création candidature."""
    return jsonify({"error": "Not implemented yet (Phase 4 - Gestion Candidatures)", "offer_id": offer_id}), 501
