"""Accès à l'ontologie (rdflib) : lecture SPARQL + écriture dans formation_.ttl (Protégé)."""
import os, re, shutil, threading
from rdflib import Graph, URIRef, Literal, RDF, RDFS, OWL, XSD

BASE = "http://stackunity.org/education#"
TTL = os.path.join(os.path.dirname(__file__), "ontology", "formation_.ttl")
PREFIXES = f"""PREFIX : <{BASE}>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
"""
LOCK = threading.RLock()
onto = Graph()
onto.parse(TTL, format="turtle")


def short(v):
    s = str(v)
    return s.split("#")[-1] if s.startswith(BASE) else s

def sparql(q, **bind):
    res = onto.query(PREFIXES + q, initBindings={k: URIRef(v) for k, v in bind.items()})
    return [{str(k): short(v) for k, v in row.asdict().items()} for row in res]

def run_readonly(text, limit=500):
    """Exécute une requête SPARQL en lecture seule (SELECT / ASK). Retourne (vars, rows).
    Lève PermissionError si la requête n'est pas SELECT/ASK, ValueError si elle est invalide."""
    from rdflib.plugins.sparql import prepareQuery
    try:
        kind = prepareQuery(PREFIXES + text).algebra.name
    except Exception as e:
        raise ValueError(f"Requête invalide : {e}")
    if kind not in ("SelectQuery", "AskQuery"):
        raise PermissionError("Seules les requêtes SELECT/ASK sont autorisées")
    try:
        res = onto.query(PREFIXES + text)
    except Exception as e:
        raise ValueError(f"Requête invalide : {e}")
    if res.type == "ASK":
        return ["ASK"], [{"ASK": str(res.askAnswer)}]
    return ([str(v) for v in res.vars],
            [{str(k): short(v) for k, v in r.asdict().items()} for r in list(res)[:limit]])


def run_update(text):
    """SPARQL UPDATE (INSERT DATA / DELETE DATA / DELETE-INSERT WHERE) puis réécriture de formation_.ttl.
    Retourne (triplets_avant, triplets_après). Les opérations sur graphes (LOAD, CLEAR, DROP...) sont interdites."""
    from rdflib.plugins.sparql.parser import parseUpdate
    if re.search(r"(?im)^\s*(LOAD|CLEAR|DROP|CREATE|COPY|MOVE|ADD)\b", text):
        raise PermissionError("Opération sur graphe interdite (LOAD/CLEAR/DROP/CREATE/COPY/MOVE/ADD)")
    try:
        parseUpdate(PREFIXES + text)
    except Exception as e:
        raise ValueError(f"Mise à jour invalide : {e}")
    with LOCK:
        before = len(onto)
        try:
            onto.update(PREFIXES + text)
        except Exception as e:
            raise ValueError(f"Mise à jour invalide : {e}")
        after = len(onto)
        save()
    return before, after


def uri_of(name):
    return URIRef(BASE + name) if isinstance(name, str) and re.fullmatch(r"[A-Za-z0-9_]+", name) else None

def is_class(u):
    return u is not None and (u, RDF.type, OWL.Class) in onto

def individual_exists(u):
    return u is not None and (u, RDF.type, OWL.NamedIndividual) in onto

def save():
    """Réécrit formation_.ttl (à rouvrir dans Protégé). Copie .bak au 1er enregistrement."""
    if not os.path.exists(TTL + ".bak"):
        shutil.copy(TTL, TTL + ".bak")
    onto.serialize(TTL + ".tmp", format="turtle")
    os.replace(TTL + ".tmp", TTL)

def text(u, p):
    v = onto.value(u, p)
    return str(v) if v is not None else ""

def set_text(u, p, value, lang=None):
    onto.remove((u, p, None))
    if value and value.strip():
        onto.add((u, p, Literal(value.strip(), lang=lang)))


# ----- propriétés (schéma) -----
def props():
    out = {}
    for kind, t in (("object", OWL.ObjectProperty), ("data", OWL.DatatypeProperty)):
        for p in onto.subjects(RDF.type, t):
            if str(p).startswith(BASE):
                d, r = onto.value(p, RDFS.domain), onto.value(p, RDFS.range)
                out[short(p)] = {"name": short(p), "kind": kind, "_r": r, "label": text(p, RDFS.label),
                                 "domain": short(d) if d else None,
                                 "range": str(r).split("#")[-1] if r else None}
    return out

def to_node(m, value):
    if m["kind"] == "object":
        u = uri_of(value)
        if not individual_exists(u):
            raise ValueError(f"Instance inconnue : {value}")
        return u
    r = m["_r"]
    if r is not None and str(r).startswith(str(XSD)) and r != XSD.string:
        lit = Literal(value, datatype=r)
        if lit.value is None:
            raise ValueError(f"Valeur invalide pour {m['name']} ({m['range']}) : {value}")
        return lit
    return Literal(value)

def build_triples(uri, d):
    """Construit label + propriétés d'une instance à partir du JSON du formulaire."""
    meta, s = props(), URIRef(uri)
    out = [(s, RDFS.label, Literal((d.get("label") or "").strip() or str(uri).split("#")[-1]))]
    for r in d.get("properties", []):
        v = str(r.get("value", "")).strip()
        if not r.get("property") or not v:
            continue
        m = meta.get(r["property"])
        if not m:
            raise ValueError(f"Propriété inconnue : {r['property']}")
        out.append((s, URIRef(BASE + m["name"]), to_node(m, v)))
    return out


def describe(u):
    """Fiche d'une instance : types, propriétés (node=True si la valeur est une autre instance), relations entrantes."""
    rows = [{"property": short(p), "value": short(o), "node": isinstance(o, URIRef) and individual_exists(o)}
            for p, o in onto.predicate_objects(u) if p not in (RDF.type, RDFS.label)]
    inc = [{"source": short(s), "property": short(p)} for s, p in onto.subject_predicates(u)]
    return {"id": short(u), "label": text(u, RDFS.label) or short(u),
            "types": [short(t) for t in onto.objects(u, RDF.type) if t != OWL.NamedIndividual],
            "properties": sorted(rows, key=lambda r: r["property"]),
            "incoming": sorted(inc, key=lambda r: r["property"])}
