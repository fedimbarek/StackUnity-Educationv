"""Rôles : le rôle d'un compte découle de la classe de la Personne de l'ontologie à laquelle il est lié.

    compte (users.json)  --person-->  individu de l'ontologie (ex. Amira)  --rdf:type-->  classe (Apprenant, Medecin…)
                                                                                         |
                                                                       rôle = profil dont la classe racine est un ancêtre

Si la classe de la personne change dans Protégé / l'UI, le rôle suit au prochain login (rien n'est figé dans users.json).
"""
import re, unicodedata
from rdflib import URIRef, Literal, RDF, RDFS, OWL
from store import BASE, LOCK, onto, short, text, uri_of, is_class, individual_exists, save

# rôle -> classe racine de l'ontologie. Ordre = priorité si un individu a plusieurs types.
PROFILES = {
    "apprenant":         dict(label="Apprenant",           root="Apprenant"),
    "enseignant":        dict(label="Enseignant",          root="Enseignant"),
    "medical":           dict(label="Personnel médical",   root="PersonnelMedical"),
    "responsable_club":  dict(label="Responsable de club", root="ResponsableClub"),
    "tuteur":            dict(label="Tuteur",              root="Tuteur"),
    "tuteur_entreprise": dict(label="Tuteur d'entreprise", root="TuteurEntreprise"),
}
PERSONNE = URIRef(BASE + "Personne")


def _ancestors(c):
    return set(onto.transitive_objects(c, RDFS.subClassOf))


def role_of_person(person):
    """Rôle (clé de PROFILES) d'un individu, ou None s'il n'a pas de profil connu."""
    u = uri_of(person)
    if not individual_exists(u):
        return None
    anc = set()
    for t in onto.objects(u, RDF.type):
        anc |= _ancestors(t)
    return next((r for r, p in PROFILES.items() if URIRef(BASE + p["root"]) in anc), None)


def label_of(person):
    u = uri_of(person)
    return (text(u, RDFS.label) or text(u, URIRef(BASE + "nom")) or person) if u else person


def type_label(person):
    """Libellé de la classe la plus précise de la personne (ex. « Médecin »)."""
    u = uri_of(person)
    best = None
    for t in onto.objects(u, RDF.type):
        if t == OWL.NamedIndividual or not str(t).startswith(BASE):
            continue
        if best is None or best in _ancestors(t):          # t est plus spécifique que best
            best = t
    return (text(best, RDFS.label) or short(best)) if best is not None else ""


def profile_classes(role):
    """Classes proposées à l'inscription pour créer une nouvelle personne de ce profil (racine + sous-classes)."""
    root = URIRef(BASE + PROFILES[role]["root"])
    cs = sorted(onto.transitive_subjects(RDFS.subClassOf, root), key=lambda c: (c != root, text(c, RDFS.label) or short(c)))
    return [dict(name=short(c), label=text(c, RDFS.label) or short(c)) for c in cs]


def available_persons(taken):
    """Personnes de l'ontologie par profil, hors celles déjà liées à un compte."""
    out = {r: [] for r in PROFILES}
    for u in onto.subjects(RDF.type, OWL.NamedIndividual):
        pid = short(u)
        role = role_of_person(pid)
        if role and pid not in taken:
            out[role].append(dict(id=pid, label=label_of(pid), type=type_label(pid)))
    for r in out:
        out[r].sort(key=lambda p: p["label"].lower())
    return out


def _slug(name):
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return "".join(w[0].upper() + w[1:] for w in re.findall(r"[A-Za-z0-9]+", s)) or "Personne"


def create_person(name, cls_name, role):
    """Crée une nouvelle Personne (NamedIndividual + type + label + nom) dans formation_.ttl. Retourne son id."""
    c = uri_of(cls_name)
    if role not in PROFILES or not is_class(c) or URIRef(BASE + PROFILES[role]["root"]) not in _ancestors(c):
        raise ValueError("Type de personne invalide pour ce profil")
    name = " ".join(name.split())
    if len(name) < 2:
        raise ValueError("Nom complet requis (2 caractères minimum)")
    with LOCK:
        base = _slug(name)[:60]
        pid, n = base, 2
        while (uri_of(pid), None, None) in onto:
            pid, n = f"{base}{n}", n + 1
        u = URIRef(BASE + pid)
        for t in [(u, RDF.type, OWL.NamedIndividual), (u, RDF.type, c), (u, RDFS.label, Literal(name)),
                  (u, URIRef(BASE + "nom"), Literal(name))]:
            onto.add(t)
        save()
    return pid
