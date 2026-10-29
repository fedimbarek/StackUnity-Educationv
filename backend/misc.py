"""Routes transverses : modules (vue d'ensemble), stats, recherche, console SPARQL, export .ttl."""
from flask import Blueprint, jsonify, request, send_file
from rdflib import Literal, RDF, OWL, URIRef
from rdflib.plugins.sparql import prepareQuery
from auth import auth_required
from modules import MODULES, module_classes, module_instances, module_of
from store import onto, short, sparql, TTL, PREFIXES, individual_exists, uri_of, is_class, describe, run_readonly, run_update

bp = Blueprint("misc", __name__, url_prefix="/api")

@bp.get("/modules")
@auth_required
def modules():
    return jsonify([{**m, "classes": len(module_classes(m)), "instances": len(module_instances(m))} for m in MODULES])

@bp.get("/stats")
@auth_required
def stats():
    one = lambda q: int(sparql(q)[0]["n"])
    return jsonify(
        triples=len(onto),
        classes=one("SELECT (COUNT(DISTINCT ?c) AS ?n) WHERE { ?c a owl:Class . FILTER(isIRI(?c)) }"),
        objectProperties=one("SELECT (COUNT(DISTINCT ?p) AS ?n) WHERE { ?p a owl:ObjectProperty }"),
        dataProperties=one("SELECT (COUNT(DISTINCT ?p) AS ?n) WHERE { ?p a owl:DatatypeProperty }"),
        individuals=one("SELECT (COUNT(DISTINCT ?i) AS ?n) WHERE { ?i a owl:NamedIndividual }"))

@bp.get("/classes")
@auth_required
def all_classes():
    return jsonify(sorted(short(c) for c in onto.subjects(RDF.type, OWL.Class) if "#" in str(c)))

@bp.get("/individuals")
@auth_required
def all_individuals():
    return jsonify(sparql("SELECT DISTINCT ?id ?label WHERE { ?id a owl:NamedIndividual . OPTIONAL { ?id rdfs:label ?label } } ORDER BY ?id"))

@bp.get("/classes/<name>/individuals")
@auth_required
def individuals_of(name):
    """Toutes les instances d'une classe (sous-classes incluses) : alimente les listes déroulantes des formulaires."""
    u = uri_of(name)
    if not is_class(u):
        return jsonify([])
    return jsonify(sparql("""SELECT DISTINCT ?id ?label WHERE {
        ?id a owl:NamedIndividual ; a/rdfs:subClassOf* ?cls . OPTIONAL { ?id rdfs:label ?label } } ORDER BY ?label""", cls=str(u)))

@bp.get("/individuals/<name>")
@auth_required
def individual(name):
    """Fiche d'une instance de n'importe quel module (+ le module auquel elle appartient)."""
    u = uri_of(name)
    if not individual_exists(u):
        return jsonify(error="Introuvable"), 404
    d = describe(u)
    d["module"] = next((mod for t in onto.objects(u, RDF.type) if (mod := module_of(t))), None)
    return jsonify(d)

@bp.get("/search")
@auth_required
def search():
    q = request.args.get("q", "").strip()
    if len(q) < 2:
        return jsonify([])
    res = onto.query(PREFIXES + """
        SELECT DISTINCT ?id ?label ?type WHERE {
          ?id a owl:NamedIndividual ; rdfs:label ?label ; a ?type .
          FILTER(?type != owl:NamedIndividual && CONTAINS(LCASE(STR(?label)), LCASE(?q)))
        } LIMIT 50""", initBindings={"q": Literal(q)})
    return jsonify([{"id": short(r["id"]), "label": str(r["label"]), "type": short(r["type"]),
                     "module": module_of(r["type"])} for r in res])

@bp.post("/sparql")
@auth_required
def raw_sparql():
    """Console SPARQL : lecture seule (SELECT / ASK uniquement)."""
    text = (request.get_json(force=True).get("query") or "").strip()
    try:
        vars_, rows = run_readonly(text)
    except PermissionError as e:
        return jsonify(error=str(e)), 403
    except ValueError as e:
        return jsonify(error=str(e)), 400
    return jsonify(vars=vars_, rows=rows)

@bp.post("/sparql/update")
@auth_required
def sparql_update():
    """CRUD par SPARQL UPDATE (INSERT / DELETE / DELETE-INSERT) — réservé au rôle admin ; réécrit formation_.ttl."""
    if getattr(request, "role", "") != "admin":
        return jsonify(error="Réservé aux administrateurs"), 403
    text = (request.get_json(force=True).get("update") or "").strip()
    if not text:
        return jsonify(error="Mise à jour vide"), 400
    try:
        before, after = run_update(text)
    except PermissionError as e:
        return jsonify(error=str(e)), 403
    except ValueError as e:
        return jsonify(error=str(e)), 400
    return jsonify(ok=True, triples_before=before, triples_after=after, delta=after - before)

@bp.get("/export.ttl")
@auth_required
def export_ttl():
    return send_file(TTL, mimetype="text/turtle", as_attachment=True, download_name="formation_.ttl")
