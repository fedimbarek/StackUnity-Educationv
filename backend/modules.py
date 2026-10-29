"""Un module métier = un sous-arbre de l'ontologie (classe racine). Chaque module expose son propre
blueprint REST : /api/<module>/classes … et /api/<module>/items … (CRUD complet)."""
from flask import Blueprint, jsonify, request
from rdflib import URIRef, Literal, RDF, RDFS, OWL
from auth import auth_required
from store import (BASE, LOCK, onto, short, sparql, uri_of, is_class, individual_exists, save,
                   text, set_text, props, build_triples, describe)

MODULES = [
    dict(id="personnes", title="Personnes", icon="👤", root="Personne", desc="Enseignants, apprenants, tuteurs, personnel médical…"),
    dict(id="formations", title="Formations & Domaines", icon="🎓", root="Domaine", desc="Formations, diplômes, compétences, certifications, parcours, niveaux, périodes"),
    dict(id="matieres", title="Matières & Pédagogie", icon="📚", root="Matiere", desc="Matières, séances, évaluations, ressources, outils numériques"),
    dict(id="clubs", title="Clubs & Événements", icon="🎭", root="Club", desc="Clubs, événements, concerts, tournois"),
    dict(id="organismes", title="Organismes & Stages", icon="🏢", root="Organisme", desc="Universités, entreprises, laboratoires, stages"),
    dict(id="espaces", title="Espaces", icon="🏫", root="Espace", desc="Salles, amphithéâtres, départements, infirmerie"),
    dict(id="inscriptions", title="Inscriptions", icon="📝", root="Inscription", desc="Inscriptions administratives, pédagogiques, clubs"),
    dict(id="bourses", title="Bourses", icon="💰", root="Bourse", desc="Bourses de mérite, sociales, de mobilité"),
    dict(id="sante", title="Santé", icon="🩺", root="ServiceMedical", desc="Consultations, prévention, soutien psychologique, certificats"),
    dict(id="vie", title="Vie étudiante", icon="🏠", root="ServiceVieEtudiante", desc="Hébergement, restauration, transport, orientation"),
]

def module_classes(m):
    return set(onto.transitive_subjects(RDFS.subClassOf, URIRef(BASE + m["root"])))

def module_instances(m):
    cs = module_classes(m)
    return {i for c in cs for i in onto.subjects(RDF.type, c) if individual_exists(i)}

def module_of(type_uri):
    for m in MODULES:
        if type_uri in module_classes(m):
            return m["id"]


def make_blueprint(m):
    root = URIRef(BASE + m["root"])
    bp = Blueprint(m["id"], __name__, url_prefix=f"/api/{m['id']}")

    def cls(name):                       # classe valide ET appartenant à ce module
        u = uri_of(name)
        return u if is_class(u) and root in set(onto.transitive_objects(u, RDFS.subClassOf)) else None

    def item(name):                      # instance appartenant à ce module
        u = uri_of(name)
        ok = individual_exists(u) and any(root in set(onto.transitive_objects(t, RDFS.subClassOf))
                                          for t in onto.objects(u, RDF.type))
        return u if ok else None

    # ---------------- CRUD des CLASSES ----------------
    @bp.get("/classes")
    @auth_required
    def classes():
        cs, counts = module_classes(m), {}
        counts = dict.fromkeys(cs, 0)
        for i in onto.subjects(RDF.type, OWL.NamedIndividual):
            hit = set()
            for t in onto.objects(i, RDF.type):
                hit |= set(onto.transitive_objects(t, RDFS.subClassOf))
            for c in hit & cs:
                counts[c] += 1
        rows = []
        for c in cs:
            ps = [p for p in onto.objects(c, RDFS.subClassOf) if p in cs]
            rows.append(dict(name=short(c), parent=short(ps[0]) if ps else None, count=counts[c],
                             label=text(c, RDFS.label), comment=text(c, RDFS.comment)))
        return jsonify(sorted(rows, key=lambda r: r["name"]))

    @bp.post("/classes")
    @auth_required
    def create_class():
        d = request.get_json(force=True)
        u, parent = uri_of(d.get("name", "")), cls(d.get("parent", ""))
        if not u or parent is None:
            return jsonify(error="Nom (lettres/chiffres/_) et classe parente du module requis"), 400
        with LOCK:
            if (u, None, None) in onto:
                return jsonify(error="Ce nom existe déjà dans l'ontologie"), 409
            onto.add((u, RDF.type, OWL.Class)); onto.add((u, RDFS.subClassOf, parent))
            set_text(u, RDFS.label, d.get("label"), "fr"); set_text(u, RDFS.comment, d.get("comment"), "fr")
            save()
        return jsonify(name=d["name"]), 201

    @bp.put("/classes/<name>")
    @auth_required
    def update_class(name):
        u, d = cls(name), request.get_json(force=True)
        if u is None:
            return jsonify(error="Classe introuvable dans ce module"), 404
        with LOCK:
            if u != root and d.get("parent") and short(d["parent"]) != "":
                p = cls(d["parent"])
                if p is None or p in set(onto.transitive_subjects(RDFS.subClassOf, u)):
                    return jsonify(error="Parent invalide (hors module ou cycle)"), 400
                for old in [o for o in onto.objects(u, RDFS.subClassOf) if isinstance(o, URIRef)]:
                    onto.remove((u, RDFS.subClassOf, old))
                onto.add((u, RDFS.subClassOf, p))
            set_text(u, RDFS.label, d.get("label"), "fr"); set_text(u, RDFS.comment, d.get("comment"), "fr")
            save()
        return jsonify(name=name)

    @bp.delete("/classes/<name>")
    @auth_required
    def delete_class(name):
        u = cls(name)
        if u is None:
            return jsonify(error="Classe introuvable dans ce module"), 404
        if u == root:
            return jsonify(error="La classe racine d'un module ne peut pas être supprimée"), 403
        if any(isinstance(s, URIRef) for s in onto.subjects(RDFS.subClassOf, u)):
            return jsonify(error="Supprime d'abord les sous-classes"), 409
        if (None, RDF.type, u) in onto:
            return jsonify(error="Cette classe contient des instances : supprime-les d'abord"), 409
        with LOCK:
            n = len(list(onto.triples((u, None, None)))) + len(list(onto.triples((None, None, u))))
            onto.remove((u, None, None)); onto.remove((None, None, u))   # + domain/range qui la citaient
            save()
        return jsonify(deletedTriples=n)

    @bp.get("/classes/<name>/properties")
    @auth_required
    def class_properties(name):
        u = cls(name)
        if u is None:
            return jsonify(error="Classe introuvable"), 404
        anc = {short(a) for a in onto.transitive_objects(u, RDFS.subClassOf)}
        return jsonify(sorted(n for n, p in props().items() if p["domain"] is None or p["domain"] in anc))

    # ---------------- CRUD des INSTANCES ----------------
    @bp.get("/classes/<name>/items")
    @auth_required
    def items(name):
        u = cls(name)
        if u is None:
            return jsonify(error="Classe introuvable"), 404
        rows = sparql("""
            SELECT ?id ?label (SAMPLE(?t) AS ?type) WHERE {
              ?id a owl:NamedIndividual ; a/rdfs:subClassOf* ?cls ; a ?t .
              FILTER(?t != owl:NamedIndividual)
              OPTIONAL { ?id rdfs:label ?label }
            } GROUP BY ?id ?label ORDER BY ?label""", cls=str(u))
        meta = props()                                   # ?columns=email,telephone => valeurs des propriétés demandées
        cols = [c for c in request.args.get("columns", "").split(",") if c in meta]
        for r in rows:
            s = URIRef(BASE + r["id"])
            r["cols"] = {c: ", ".join(short(o) for o in onto.objects(s, URIRef(BASE + c))) for c in cols}
        return jsonify(rows)

    @bp.post("/items")
    @auth_required
    def create_item():
        d = request.get_json(force=True)
        u, c = uri_of(d.get("id", "")), cls(d.get("type", ""))
        if not u or c is None:
            return jsonify(error="Identifiant (lettres/chiffres/_) et classe du module requis"), 400
        with LOCK:
            if (u, None, None) in onto:
                return jsonify(error="Cet identifiant existe déjà"), 409
            try:
                triples = build_triples(u, d)
            except ValueError as e:
                return jsonify(error=str(e)), 400
            for t in [(u, RDF.type, OWL.NamedIndividual), (u, RDF.type, c)] + triples:
                onto.add(t)
            save()
        return jsonify(id=d["id"]), 201

    @bp.get("/items/<name>")
    @auth_required
    def read_item(name):
        u = item(name)
        if u is None:
            return jsonify(error="Introuvable"), 404
        return jsonify(describe(u))

    @bp.put("/items/<name>")
    @auth_required
    def update_item(name):
        u = item(name)
        if u is None:
            return jsonify(error="Introuvable"), 404
        with LOCK:
            try:
                triples = build_triples(u, request.get_json(force=True))
            except ValueError as e:
                return jsonify(error=str(e)), 400
            for p, o in list(onto.predicate_objects(u)):
                if p != RDF.type:
                    onto.remove((u, p, o))
            for t in triples:
                onto.add(t)
            save()
        return jsonify(id=name)

    @bp.delete("/items/<name>")
    @auth_required
    def delete_item(name):
        u = item(name)
        if u is None:
            return jsonify(error="Introuvable"), 404
        with LOCK:
            n = len(list(onto.triples((u, None, None)))) + len(list(onto.triples((None, None, u))))
            onto.remove((u, None, None)); onto.remove((None, None, u))
            save()
        return jsonify(deletedTriples=n)

    return bp
