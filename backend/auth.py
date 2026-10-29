"""Authentification : inscription / connexion / JWT. Comptes persistés dans users.json.

Un compte = identifiants + (optionnel) lien vers une Personne de l'ontologie :
    users.json : { "amira": { "hash": "...", "role": "apprenant", "person": "Amira" }, ... }
Le rôle effectif est recalculé à chaque connexion depuis la classe de la personne (voir roles.py).
Cas particuliers : « admin » (accès complet) et les anciens comptes sans personne (rôle « user », accès complet comme avant).
"""
import os, json, datetime, functools, threading
import jwt
from flask import Blueprint, jsonify, request
from werkzeug.security import generate_password_hash, check_password_hash
import roles

SECRET = os.getenv("JWT_SECRET", "change-me-in-prod")
USERS_FILE = os.path.join(os.path.dirname(__file__), "users.json")
bp = Blueprint("auth", __name__, url_prefix="/api/auth")
_LOCK = threading.Lock()

if os.path.exists(USERS_FILE):
    USERS = json.load(open(USERS_FILE, encoding="utf-8"))
else:                                           # compte par défaut : admin / admin123
    USERS = {"admin": {"hash": generate_password_hash("admin123"), "role": "admin"}}

# Comptes de démonstration (un par profil) : identifiant -> personne de l'ontologie. Mot de passe : demo123.
# Désactiver avec  SEED_DEMO_USERS=0  (à faire hors démo).
DEMO_USERS = {"amira": "Amira", "bilel": "Bilel", "ahmed": "Ahmed", "walid": "Walid", "drsonia": "DrSonia",
              "mariem": "PsychologueMariem", "rim": "Rim", "mehdi": "Mehdi", "sami": "Sami"}


def _save_users():
    with _LOCK:
        json.dump(USERS, open(USERS_FILE, "w", encoding="utf-8"), indent=2)


def _seed_demo():
    added = False
    for username, person in DEMO_USERS.items():
        if username not in USERS and roles.role_of_person(person):
            USERS[username] = {"hash": generate_password_hash("demo123"), "role": roles.role_of_person(person), "person": person}
            added = True
    if added:
        _save_users()


if os.getenv("SEED_DEMO_USERS", "1") != "0":
    _seed_demo()


def session_info(username):
    """Rôle effectif + identité d'un compte (calculés depuis l'ontologie)."""
    u = USERS[username]
    person = u.get("person")
    role = roles.role_of_person(person) if person else None
    if role:
        return dict(username=username, role=role, person=person, name=roles.label_of(person),
                    profile=roles.PROFILES[role]["label"], type=roles.type_label(person))
    if u.get("role") == "admin":
        return dict(username=username, role="admin", person=None, name=username, profile="Administrateur", type="")
    return dict(username=username, role="user", person=None, name=username, profile="Utilisateur", type="")


def make_token(username):
    info = session_info(username)
    exp = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=8)
    return jwt.encode({"sub": username, "role": info["role"], "person": info["person"], "exp": exp},
                      SECRET, algorithm="HS256")


def _answer(username, status=200):
    return jsonify(token=make_token(username), **session_info(username)), status


def auth_required(fn):
    @functools.wraps(fn)
    def wrapper(*a, **kw):
        try:
            payload = jwt.decode(request.headers.get("Authorization", "").removeprefix("Bearer "),
                                 SECRET, algorithms=["HS256"])
            if payload["sub"] not in USERS:
                raise jwt.InvalidTokenError("compte supprimé")
            request.user = payload["sub"]
            request.role = payload.get("role", "user")
            request.person = payload.get("person")
        except jwt.PyJWTError:
            return jsonify(error="Token invalide ou expiré"), 401
        return fn(*a, **kw)
    return wrapper


@bp.get("/profiles")
def profiles():
    """Public : profils proposés à l'inscription + personnes de l'ontologie encore libres (non liées à un compte)."""
    taken = {u["person"] for u in USERS.values() if u.get("person")}
    free = roles.available_persons(taken)
    return jsonify([dict(role=r, label=p["label"], classes=roles.profile_classes(r), persons=free[r])
                    for r, p in roles.PROFILES.items()])


@bp.post("/register")
def register():
    """Inscription : identifiants + profil. Soit on se lie à une personne existante (`person`), soit on en crée une (`name`, `type`)."""
    d = request.get_json(force=True)
    u, p = (d.get("username") or "").strip(), d.get("password") or ""
    role, person = d.get("role"), (d.get("person") or "").strip()
    if len(u) < 3 or len(p) < 6:
        return jsonify(error="Nom (3+) et mot de passe (6+) requis"), 400
    if role not in roles.PROFILES:
        return jsonify(error="Choisissez votre profil (apprenant, enseignant, …)"), 400
    with _LOCK:                                    # un seul inscrit à la fois : évite deux comptes sur la même personne
        if u in USERS:
            return jsonify(error="Utilisateur existant"), 409
        if person:
            if roles.role_of_person(person) != role:
                return jsonify(error="Cette personne n'existe pas pour ce profil"), 400
            if any(x.get("person") == person for x in USERS.values()):
                return jsonify(error="Cette personne est déjà liée à un autre compte"), 409
        else:
            try:
                person = roles.create_person(d.get("name") or "", d.get("type") or roles.PROFILES[role]["root"], role)
            except ValueError as e:
                return jsonify(error=str(e)), 400
        USERS[u] = {"hash": generate_password_hash(p), "role": role, "person": person}
        json.dump(USERS, open(USERS_FILE, "w", encoding="utf-8"), indent=2)
    return _answer(u, 201)


@bp.post("/login")
def login():
    d = request.get_json(force=True)
    u = USERS.get(d.get("username"))
    if not u or not check_password_hash(u["hash"], d.get("password", "")):
        return jsonify(error="Identifiants incorrects"), 401
    return _answer(d["username"])


@bp.get("/me")
@auth_required
def me():
    return jsonify(session_info(request.user))
