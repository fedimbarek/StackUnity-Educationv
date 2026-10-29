"""Requêtes SPARQL métier (filtres, stats, jointures) pour Vie & Santé."""
from flask import Blueprint, jsonify, request
from rdflib import URIRef
from auth import auth_required
from store import BASE, sparql

bp = Blueprint("business", __name__, url_prefix="/api/business")

# ==================== SANTÉ ====================

@bp.get("/sante/stats")
@auth_required
def sante_stats():
    total = sparql("""
        SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE {
          ?s a/rdfs:subClassOf* :ServiceMedical ; a ?t .
          FILTER(?t != owl:NamedIndividual)
        }""")[0]["n"]
    gratuits = sparql("""
        SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE {
          ?s a/rdfs:subClassOf* :ServiceMedical ; :estGratuit true .
        }""")[0]["n"]
    sur_rdv = sparql("""
        SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE {
          ?s a/rdfs:subClassOf* :ServiceMedical ; :surRendezVous true .
        }""")[0]["n"]
    par_type = sparql("""
        SELECT ?type (COUNT(?s) AS ?n) WHERE {
          ?s a/rdfs:subClassOf* :ServiceMedical ; a ?type .
          FILTER(?type != owl:NamedIndividual)
        } GROUP BY ?type ORDER BY DESC(?n)""")
    par_personnel = sparql("""
        SELECT ?medecin ?label (COUNT(?s) AS ?n) WHERE {
          ?s a/rdfs:subClassOf* :ServiceMedical ; :assureParPersonnel ?medecin .
          ?medecin rdfs:label ?label .
        } GROUP BY ?medecin ?label ORDER BY DESC(?n)""")
    return jsonify(total=int(total), gratuits=int(gratuits), sur_rdv=int(sur_rdv),
                   par_type=par_type, par_personnel=par_personnel)

@bp.get("/sante/gratuits")
@auth_required
def sante_gratuits():
    rows = sparql("""
        SELECT ?id ?label ?type ?horaire ?telephone WHERE {
          ?s a/rdfs:subClassOf* :ServiceMedical ; a ?type ; rdfs:label ?label ;
             :estGratuit true .
          OPTIONAL { ?s :horairesOuverture ?horaire }
          OPTIONAL { ?s :telephoneService ?telephone }
          BIND(?s AS ?id) FILTER(?type != owl:NamedIndividual)
        } ORDER BY ?label""")
    return jsonify(items=rows)

@bp.get("/sante/recherche")
@auth_required
def sante_recherche():
    q = (request.args.get("q") or "").strip()
    if not q:
        return jsonify(items=[])
    rows = sparql("""
        SELECT ?id ?label ?type ?horaires WHERE {
          ?s a/rdfs:subClassOf* :ServiceMedical ; a ?type ; rdfs:label ?label .
          OPTIONAL { ?s :horairesOuverture ?horaires }
          BIND(?s AS ?id)
          FILTER(?type != owl:NamedIndividual && CONTAINS(LCASE(STR(?label)), LCASE(?q)))
        } ORDER BY ?label""", q=q)
    return jsonify(items=rows, query=q)

@bp.get("/sante/par-user/<path:user_name>")
@auth_required
def sante_par_user(user_name):
    u = URIRef(BASE + user_name)
    rows = sparql("""
        SELECT ?id ?label ?type ?horaire WHERE {
          ?me :consulte ?svc .
          ?svc a/rdfs:subClassOf* :ServiceMedical ; a ?type ; rdfs:label ?label .
          OPTIONAL { ?svc :horairesOuverture ?horaire }
          BIND(?svc AS ?id) FILTER(?type != owl:NamedIndividual)
        } ORDER BY ?label""", me=str(u))
    return jsonify(user=user_name, items=rows)

# ==================== VIE ====================

@bp.get("/vie/stats")
@auth_required
def vie_stats():
    total = sparql("""
        SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE {
          ?s a/rdfs:subClassOf* :ServiceVieEtudiante ; a ?t .
          FILTER(?t != owl:NamedIndividual)
        }""")[0]["n"]
    par_cat = sparql("""
        SELECT ?cat (COUNT(?s) AS ?n) WHERE {
          ?s a/rdfs:subClassOf* :ServiceVieEtudiante ; a ?cat .
          FILTER(?cat != owl:NamedIndividual)
        } GROUP BY ?cat ORDER BY DESC(?n)""")
    par_lieu = sparql("""
        SELECT ?lieu (COUNT(?s) AS ?n) WHERE {
          ?s a/rdfs:subClassOf* :ServiceVieEtudiante ; :lieu ?lieu .
        } GROUP BY ?lieu ORDER BY DESC(?n)""")
    return jsonify(total=int(total), par_categorie=par_cat, par_lieu=par_lieu)

@bp.get("/vie/par-user/<path:user_name>")
@auth_required
def vie_par_user(user_name):
    u = URIRef(BASE + user_name)
    rows = sparql("""
        SELECT ?id ?label ?rel ?type WHERE {
          ?me ?rel ?svc .
          ?svc a/rdfs:subClassOf* :ServiceVieEtudiante ; a ?type ; rdfs:label ?label .
          BIND(?svc AS ?id)
          FILTER(?rel IN (:sInscritA, :habite, :utiliseTransport))
          FILTER(?type != owl:NamedIndividual)
        } ORDER BY ?label""", me=str(u))
    return jsonify(user=user_name, items=rows)