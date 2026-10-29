"""Module « Propriétés » : CRUD des owl:ObjectProperty / owl:DatatypeProperty (domain, range, label)."""
from flask import Blueprint, jsonify, request
from rdflib import URIRef, RDF, RDFS, OWL, XSD
from auth import auth_required
from store import BASE, LOCK, onto, short, uri_of, is_class, save, props, set_text

bp = Blueprint("schema", __name__, url_prefix="/api/properties")
DATATYPES = ["string", "integer", "decimal", "float", "double", "boolean", "date", "dateTime", "time", "gYear", "anyURI"]

def parse(d, kind):
    dom = rng = None
    if d.get("domain"):
        dom = uri_of(d["domain"])
        if not is_class(dom):
            raise ValueError("Domaine : classe inconnue")
    if d.get("range"):
        if kind == "object":
            rng = uri_of(d["range"])
            if not is_class(rng):
                raise ValueError("Range : classe inconnue")
        elif d["range"] in DATATYPES:
            rng = XSD[d["range"]]
        else:
            raise ValueError("Type de donnée inconnu : " + d["range"])
    return dom, rng

def apply(u, d, dom, rng):
    for p in (RDFS.domain, RDFS.range):
        onto.remove((u, p, None))
    if dom: onto.add((u, RDFS.domain, dom))
    if rng: onto.add((u, RDFS.range, rng))
    set_text(u, RDFS.label, d.get("label"), "fr")

@bp.get("")
@auth_required
def list_props():
    out = []
    for m in props().values():
        u = URIRef(BASE + m["name"])
        out.append({**{k: v for k, v in m.items() if k != "_r"}, "usage": len(list(onto.subject_objects(u)))})
    return jsonify(sorted(out, key=lambda x: x["name"]))

@bp.post("")
@auth_required
def create_prop():
    d = request.get_json(force=True)
    u, kind = uri_of(d.get("name", "")), d.get("kind")
    if not u or kind not in ("object", "data"):
        return jsonify(error="Nom valide et type (object/data) requis"), 400
    with LOCK:
        if (u, None, None) in onto:
            return jsonify(error="Ce nom existe déjà dans l'ontologie"), 409
        try:
            dom, rng = parse(d, kind)
        except ValueError as e:
            return jsonify(error=str(e)), 400
        onto.add((u, RDF.type, OWL.ObjectProperty if kind == "object" else OWL.DatatypeProperty))
        apply(u, d, dom, rng); save()
    return jsonify(name=d["name"]), 201

@bp.put("/<name>")
@auth_required
def update_prop(name):
    m = props().get(name)
    if not m:
        return jsonify(error="Propriété introuvable"), 404
    d = request.get_json(force=True)
    with LOCK:
        try:
            dom, rng = parse(d, m["kind"])
        except ValueError as e:
            return jsonify(error=str(e)), 400
        apply(URIRef(BASE + name), d, dom, rng); save()
    return jsonify(name=name)

@bp.delete("/<name>")
@auth_required
def delete_prop(name):
    if name not in props():
        return jsonify(error="Propriété introuvable"), 404
    u = URIRef(BASE + name)
    with LOCK:
        n = len(list(onto.triples((u, None, None)))) + len(list(onto.triples((None, u, None))))
        onto.remove((u, None, None)); onto.remove((None, u, None)); onto.remove((None, None, u))
        save()
    return jsonify(deletedTriples=n)
