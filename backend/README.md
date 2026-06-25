# ATS Intelligent — Backend (Flask)

Squelette du backend, en miroir du diagramme de composants : packages
`API Auth` / `API Utilisateurs` / `API Offres`, puis les services
`Gestion Candidatures`, `RAG Pipeline`, `ATS IA Engine`, `Chatbot LLM`.

À ce stade (Phase 1 terminée), **l'authentification est implémentée**
(`/auth/register`, `/auth/login`, `/auth/logout`, `/auth/me`), avec hachage
bcrypt, JWT porteur des claims `user_id`+`role`, et un décorateur
`@role_required(...)` déjà appliqué aux routes des Phases 2/3 (qui exigent
donc un token + le bon rôle, puis renvoient `501` en attendant leur logique
métier). Voir les `TODO` dans `routes/` et `services/` pour la suite.

### Endpoints d'authentification (Phase 1)

| Méthode | Route            | Accès            | Description                                  |
|---------|------------------|------------------|----------------------------------------------|
| POST    | `/auth/register` | public           | Inscription (rôle forcé à `Utilisateur`)     |
| POST    | `/auth/login`    | public           | Connexion → renvoie `access_token` + `user`  |
| POST    | `/auth/logout`   | token requis     | Révoque le token courant (blocklist)         |
| GET     | `/auth/me`       | token requis     | Renvoie le compte connecté                   |

Le token est un JWT à passer dans l'en-tête `Authorization: Bearer <token>`.
Il contient l'identité (`user_id`) et le rôle. Pour protéger une route :

```python
from security import role_required

@offers_bp.post("")
@role_required("RH", "Admin")     # 401 si pas de token, 403 si mauvais rôle
def create_offer(): ...
```

Note : `logout` est un **vrai** logout côté serveur (le `jti` du token est
mis dans la collection `token_blocklist`, vérifiée à chaque requête). Si vous
préférez vous reposer uniquement sur l'expiration côté client, vous pouvez
ignorer cet endpoint — mais la révocation immédiate est plus sûre.

## 1. Installation

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Configuration

```bash
cp .env.example .env
```

Puis éditez `.env` :

- **MONGO_URI / MONGO_DBNAME** : voir section 3 ci-dessous.
- **JWT_SECRET_KEY / SECRET_KEY** : remplacez par des valeurs aléatoires
  (ex. `python -c "import secrets; print(secrets.token_hex(32))"`).
- **LLM_API_KEY** : clé de votre fournisseur LLM (OpenAI, Mistral...),
  nécessaire seulement à partir de la Phase 6/8.

## 3. MongoDB Atlas

1. Créez un compte sur [mongodb.com/cloud/atlas](https://www.mongodb.com/cloud/atlas) et un cluster gratuit (M0).
2. Dans **Database Access**, créez un utilisateur applicatif (login/mot de passe).
3. Dans **Network Access**, autorisez votre IP (ou `0.0.0.0/0` en développement uniquement).
4. Dans **Connect > Drivers**, copiez l'URI `mongodb+srv://...` dans `MONGO_URI`.
5. **Vector Search** (nécessaire à partir de la Phase 6 — RAG Pipeline / ATS IA Engine) :
   sur la collection `embeddings`, onglet *Search* > *Create Search Index* >
   type *Atlas Vector Search*, avec une définition du type :
   ```json
   {
     "fields": [
       { "type": "vector", "path": "embedding", "numDimensions": 1536, "similarity": "cosine" }
     ]
   }
   ```
   (adaptez `numDimensions` au modèle d'embedding choisi). Donnez-lui le nom
   renseigné dans `VECTOR_INDEX_NAME` (`.env`).

Vous n'avez pas besoin de créer les collections à la main : `seed_db.py`
et le code applicatif les créeront à la première insertion.

## 4. Charger les données mockées

```bash
python seed_db.py
```

Cela insère dans Atlas :

- **7 comptes** (`mock_data/users.json`) : 1 Admin, 2 RH, 4 candidats —
  dont 3 construits à partir des vrais CV fournis (voir section 5).
  Mots de passe en clair dans le JSON, hashés (bcrypt) avant insertion.
- **3 offres** (`mock_data/offers.json`), reconstruites depuis le fichier
  brut `mock_data/raw/offre_mock.ndjson` que vous avez fourni.
- **3 candidatures** (`mock_data/applications.json`), chacune avec son
  vrai CV PDF uploadé dans GridFS (bucket `cv_files`).

Relancer le script est sûr (il évite les doublons par email/titre+entreprise).
Pour repartir de zéro : `python seed_db.py --reset`.

### Comptes de test après seed

| Rôle        | Email                          | Mot de passe |
|-------------|---------------------------------|---------------|
| Admin       | admin@ats.fr                    | admin123      |
| RH          | rh@ats.fr                       | rh123         |
| RH          | farid.moreau@ats.fr              | farid123      |
| Utilisateur | user@ats.fr                     | user123       |
| Utilisateur | veljovicbulatovicivan@gmail.com | ivan12345     |
| Utilisateur | ryanmariapaul7@gmail.com        | ryan12345     |
| Utilisateur | prades.mathew@gmail.com         | mathew12345   |

⚠️ Ces mots de passe sont uniquement pour le développement local. Ne
jamais réutiliser ce fichier de mock tel quel en production.

## 5. À propos des données mockées

- **Offres** : vous n'aviez fourni que `offre_mock` (NDJSON brut, plusieurs
  objets concaténés). `scripts/convert_offre_mock.py` documente comment il
  a été éclaté en objets JSON ; la réconciliation (associer les poids de
  compétences à la bonne offre, et **inventer entièrement la 3ᵉ offre**
  "Analyste Cybersécurité" dont seuls les `required_skills` pondérés
  étaient fournis) a été faite manuellement dans `mock_data/offers.json`
  (champ `_source_note` sur cette offre).
- **CV** : les 3 PDF que vous avez fournis sont dans `mock_data/cvs/`.
  Les comptes candidats associés (`mock_data/users.json`) reprennent le
  nom/email/téléphone réels extraits de chaque CV ; le mot de passe est
  inventé.
- **Scores ATS** des candidatures (`ats_score_placeholder` dans
  `applications.json`) : entièrement inventés, en attendant que l'ATS IA
  Engine (Phase 7) calcule un vrai score de matching.

## 6. Lancer l'API

```bash
python app.py
```

Puis vérifiez :

```bash
curl http://localhost:5000/          # {"status": "ok", ...}
curl http://localhost:5000/health/db # {"mongo_connected": true} si Atlas est bien configuré
```

## 7. Lancer les tests

```bash
pytest
```

## Structure du projet

```
backend/
├── app.py                  # factory Flask, enregistrement des blueprints
├── config.py                # configuration via variables d'environnement
├── extensions.py             # Mongo (connexion paresseuse), GridFS, JWT, CORS
├── seed_db.py                # charge les données mockées dans Atlas
├── routes/                   # «component» API Auth / API Utilisateurs / API Offres
├── services/
│   ├── candidatures/         # «component» Gestion Candidatures
│   ├── rag_pipeline/         # «component» RAG Pipeline
│   ├── ats_engine/           # «component» ATS IA Engine
│   └── chatbot/              # «component» Chatbot LLM
├── models/schemas.py          # schémas Pydantic (validation des payloads)
├── mock_data/                # offres, comptes, candidatures, CV PDF fournis
├── scripts/                   # utilitaires (conversion du NDJSON brut)
└── tests/
```

## Prochaines étapes

Voir la roadmap complète (phases 1 à 10). Chaque route de `routes/` et
chaque module de `services/` contient un commentaire `TODO` indiquant la
phase concernée et les signatures de fonctions prévues.

## Pipeline IA (RAG Pipeline + ATS IA Engine) — implémenté

Le pipeline suit la spec fournie, en 4 étapes (composant **RAG Pipeline**)
puis le ranking (composant **ATS IA Engine**) :

| Étape | Fichier                              | Rôle                                                        |
|-------|--------------------------------------|-------------------------------------------------------------|
| 1     | `services/rag_pipeline/extraction.py`| CV PDF → texte (PyMuPDF)                                     |
| 2     | `services/rag_pipeline/chunking.py`  | texte → chunks par section (regex de titres FR/EN)          |
| 3     | `services/rag_pipeline/embeddings.py`| chunk → vecteur (`sentence-transformers/all-MiniLM-L6-v2`)  |
| 4     | `services/rag_pipeline/vector_store.py`| stockage `{id candidat, section_type, vecteur}` dans FAISS |
| 7     | `services/ats_engine/__init__.py`    | requête → similarité cosinus → top-k → ranking par candidat |

Le ranking final donne, pour chaque candidat, un score = **moyenne des
similarités** de ses chunks retenus (exactement la formule de la spec).

### Essai rapide

```bash
# Démo sur les 3 vrais CV de mock_data/cvs/ (télécharge le modèle au 1er lancement) :
python scripts/demo_pipeline.py --query "Je cherche un data engineer avec Python et Docker"

# Version hors-ligne (embedder factice, pour tester la mécanique sans réseau) :
python scripts/demo_pipeline.py --fake
```

### Pour vos collaborateurs

L'API publique est exposée dans `services/rag_pipeline/__init__.py` :

```python
from services.rag_pipeline import FaissVectorStore, index_cv, get_embedder
from services.ats_engine import search_candidates, match_offer_candidates

store = FaissVectorStore(dim=get_embedder().dim)
index_cv("candidat_42", store, pdf_bytes=cv_pdf_bytes)   # ou pdf_path=..., ou text=...
resultats = search_candidates("data engineer python docker", store)
```

Notes d'intégration :
- L'**embedder** est injectable (`set_embedder(...)`) : c'est ce qui permet
  aux tests de tourner sans réseau, et c'est aussi utile si vous voulez
  changer de modèle plus tard.
- Le **stockage** est ici FAISS (« ou équivalent » selon la spec), persistable
  sur disque via `store.save(dir)` / `FaissVectorStore.load(dir)`. Le diagramme
  mentionne MongoDB Vector Search comme alternative : il suffirait de fournir
  une autre implémentation respectant la même interface `add/search`.
- Le **modèle** all-MiniLM-L6-v2 est téléchargé depuis HuggingFace au premier
  usage (prévoir un accès réseau au premier lancement ; ensuite il est mis en
  cache localement).


