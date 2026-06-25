"""
Tests de la Phase 1 (authentification) avec MongoDB simulé (mongomock).

Couvre : inscription, unicité, validation, hachage, login, claims du JWT,
décorateur role_required (401/403), logout + révocation du token.
"""

import mongomock
import pytest

import extensions
from app import create_app
from security import hash_password


@pytest.fixture()
def app_client():
    app = create_app()
    app.config.update(TESTING=True)
    # Remplace le client Mongo réel par un mock en mémoire
    extensions._mongo_client = mongomock.MongoClient()
    client = app.test_client()

    # Insère un Admin et un RH directement (l'inscription publique ne crée
    # que des "Utilisateur", donc on les pose à la main pour les tests de rôle)
    with app.app_context():
        db = extensions.get_db()
        db.users.insert_one({
            "prenom": "Alice", "nom": "Admin", "email": "admin@ats.fr",
            "mdp_hash": hash_password("admin123"), "role": "Admin",
        })
        db.users.insert_one({
            "prenom": "Sophie", "nom": "RH", "email": "rh@ats.fr",
            "mdp_hash": hash_password("rh123"), "role": "RH",
        })
    return client


def _login(client, email, mdp):
    return client.post("/auth/login", json={"email": email, "mdp": mdp})


def _token(client, email, mdp):
    return _login(client, email, mdp).get_json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


# --- Inscription -----------------------------------------------------------
def test_register_ok(app_client):
    r = app_client.post("/auth/register", json={
        "prenom": "Bob", "nom": "Martin", "email": "bob@ats.fr", "mdp": "secret1"
    })
    assert r.status_code == 201
    user = r.get_json()["user"]
    assert user["email"] == "bob@ats.fr"
    assert user["role"] == "Utilisateur"
    assert "mdp" not in user and "mdp_hash" not in user  # jamais exposé


def test_register_force_role_utilisateur(app_client):
    """Même si on tente role=Admin, le compte créé est Utilisateur."""
    r = app_client.post("/auth/register", json={
        "prenom": "Eve", "nom": "Hack", "email": "eve@ats.fr",
        "mdp": "secret1", "role": "Admin"
    })
    assert r.status_code == 201
    assert r.get_json()["user"]["role"] == "Utilisateur"


def test_register_duplicate_email(app_client):
    payload = {"prenom": "A", "nom": "B", "email": "dup@ats.fr", "mdp": "secret1"}
    assert app_client.post("/auth/register", json=payload).status_code == 201
    assert app_client.post("/auth/register", json=payload).status_code == 409


def test_register_invalid(app_client):
    # mot de passe trop court + email invalide
    r = app_client.post("/auth/register", json={
        "prenom": "A", "nom": "B", "email": "pas-un-email", "mdp": "123"
    })
    assert r.status_code == 400
    assert "details" in r.get_json()


def test_password_is_hashed(app_client):
    app_client.post("/auth/register", json={
        "prenom": "C", "nom": "D", "email": "hash@ats.fr", "mdp": "secret1"
    })
    with app_client.application.app_context():
        doc = extensions.get_db().users.find_one({"email": "hash@ats.fr"})
        assert doc["mdp_hash"] != "secret1"
        assert doc["mdp_hash"].startswith("$2")  # préfixe bcrypt


# --- Login -----------------------------------------------------------------
def test_login_ok_returns_token_and_role(app_client):
    r = _login(app_client, "admin@ats.fr", "admin123")
    assert r.status_code == 200
    body = r.get_json()
    assert "access_token" in body
    assert body["user"]["role"] == "Admin"


def test_login_wrong_password(app_client):
    assert _login(app_client, "admin@ats.fr", "mauvais").status_code == 401


def test_login_unknown_email(app_client):
    assert _login(app_client, "inconnu@ats.fr", "x").status_code == 401


# --- /auth/me & JWT --------------------------------------------------------
def test_me_requires_token(app_client):
    assert app_client.get("/auth/me").status_code == 401


def test_me_with_token(app_client):
    token = _token(app_client, "rh@ats.fr", "rh123")
    r = app_client.get("/auth/me", headers=_auth(token))
    assert r.status_code == 200
    assert r.get_json()["user"]["email"] == "rh@ats.fr"


# --- role_required ---------------------------------------------------------
def test_protected_route_no_token(app_client):
    assert app_client.get("/users").status_code == 401


def test_protected_route_wrong_role(app_client):
    app_client.post("/auth/register", json={
        "prenom": "U", "nom": "Ser", "email": "u@ats.fr", "mdp": "secret1"
    })
    token = _token(app_client, "u@ats.fr", "secret1")  # rôle Utilisateur
    r = app_client.get("/users", headers=_auth(token))
    assert r.status_code == 403  # rôle insuffisant


def test_protected_route_right_role_reaches_stub(app_client):
    token = _token(app_client, "admin@ats.fr", "admin123")
    r = app_client.get("/users", headers=_auth(token))
    assert r.status_code == 501  # rôle OK -> on atteint le stub Phase 2


def test_offers_create_requires_rh_or_admin(app_client):
    token = _token(app_client, "rh@ats.fr", "rh123")
    r = app_client.post("/offers", headers=_auth(token), json={})
    assert r.status_code == 501  # RH autorisé -> atteint le stub Phase 3


def test_offers_list_is_public(app_client):
    assert app_client.get("/offers").status_code == 501  # pas de 401 : route publique


# --- Logout / révocation ---------------------------------------------------
def test_logout_revokes_token(app_client):
    token = _token(app_client, "admin@ats.fr", "admin123")
    # le token marche avant logout
    assert app_client.get("/auth/me", headers=_auth(token)).status_code == 200
    # logout
    assert app_client.post("/auth/logout", headers=_auth(token)).status_code == 200
    # le même token ne marche plus
    assert app_client.get("/auth/me", headers=_auth(token)).status_code == 401
