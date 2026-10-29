"""API IA / NLP (barème « Api IA ») — traducteur question en français -> SPARQL, SANS API de LLM.

  POST /api/ai/ask             question -> pipeline NLP (nlp.py) -> SPARQL -> exécution -> réponse + trace des étapes
  POST /api/ai/explain         fiche d'un individu expliquée en langage naturel (génération par gabarits)
  GET  /api/ai/recommend/<id>  recommandations pour un apprenant (raisonnement sur le graphe)
  GET  /api/ai/status          outils NLP réellement actifs (spaCy, NLTK...)

Outils : spaCy (fr_core_news_sm) pour la tokenisation / lemmatisation / POS, NLTK (SnowballStemmer) pour la racinisation,
difflib pour la tolérance aux fautes, rdflib pour la validation et l'exécution SPARQL. Aucun appel à un LLM distant.
"""
import re
from flask import Blueprint, jsonify, request
from auth import auth_required
from store import onto, sparql, run_readonly, uri_of, individual_exists, describe, props
from queries import QUERIES
import nlp

bp = Blueprint("ai", __name__, url_prefix="/api/ai")
_CACHE = {"version": None, "engine": None}


def translator():
    """Traducteur NL->SPARQL ; reconstruit le schéma si l'ontologie a changé (CRUD) depuis le dernier appel."""
    version = len(onto)
    if _CACHE["version"] != version:
        _CACHE["engine"] = nlp.NL2SPARQL(nlp.Schema.from_ontology())
        _CACHE["version"] = version
    return _CACHE["engine"]


def norm(s):
    return nlp.unaccent(str(s).lower())

def fallback_library(question):
    """Dernier recours : mots-clés -> bibliothèque de requêtes validées (queries.py)."""
    words = set(re.findall(r"[a-z0-9]+", norm(question)))
    best = max(QUERIES, key=lambda q: sum(1 for k in q["keywords"] if k in words or k + "s" in words), default=None)
    if best and any(k in words or k + "s" in words for k in best["keywords"]):
        return best["query"], best["title"]
    return None, None

def answer_text(kind, vars_, rows, subject=None):
    if kind == "ask" or vars_ == ["ASK"]:
        return "Oui, c'est le cas dans l'ontologie." if rows and rows[0]["ASK"] == "True" else "Non, rien de tel dans l'ontologie."
    if not rows:
        return "Aucun résultat dans l'ontologie pour cette question."
    if kind == "describe":
        return f"Fiche de {subject} : {len(rows)} propriété(s) trouvée(s)."
    if kind == "count" and vars_ == ["nombre"]:
        return f"Il y en a {rows[0]['nombre']}."
    if kind == "count":
        return "Répartition : " + ", ".join(f"{r[vars_[0]]} ({r['nombre']})" for r in rows[:8]) + ("…" if len(rows) > 8 else ".")
    if kind == "rank":
        return f"{rows[0][vars_[0]]} avec {rows[0]['nombre']}."
    head = ", ".join(str(r.get(vars_[0], "")) for r in rows[:5])
    return f"{len(rows)} résultat(s) : {head}{'…' if len(rows) > 5 else ''}."


@bp.get("/status")
@auth_required
def status():
    return jsonify(engine="nlp", tools=nlp.tools(), llm=False)

@bp.post("/ask")
@auth_required
def ask():
    question = (request.get_json(force=True).get("question") or "").strip()
    if len(question) < 3:
        return jsonify(error="Pose une question (3 caractères minimum)"), 400
    out = dict(question=question, engine="nlp", sparql=None, vars=[], rows=[], answer="", warning=None, trace=None)
    res = translator().translate(question)
    out["trace"] = res["trace"]
    sparql_text, kind, subject = res.get("sparql"), res.get("kind", "select"), res.get("subject")
    if sparql_text is None:
        sparql_text, title = fallback_library(question)
        if sparql_text is None:
            out["answer"] = ("Je n'ai pas reconnu d'entité de l'ontologie dans cette question. Essaie par exemple : "
                             "« Quels apprenants ont une bourse ? », « Combien de membres par club ? » ou « Que sais-tu sur Amira ? ».")
            return jsonify(out)
        out["warning"] = f"Traduction directe impossible : requête de la bibliothèque utilisée (« {title} »)."
        kind = "select"
    out["sparql"] = sparql_text
    try:
        out["vars"], out["rows"] = run_readonly(sparql_text, limit=200)
    except (ValueError, PermissionError) as e:
        out["warning"] = f"La requête produite est invalide : {e}"
        out["answer"] = "La traduction n'a pas abouti ; reformule la question."
        return jsonify(out)
    out["answer"] = answer_text(kind, out["vars"], out["rows"], subject)
    return jsonify(out)

@bp.post("/explain")
@auth_required
def explain():
    name = (request.get_json(force=True).get("id") or "").strip()
    u = uri_of(name)
    if not individual_exists(u):
        return jsonify(error="Individu introuvable"), 404
    d = describe(u)
    labels = {m["name"]: m["label"] or m["name"] for m in props().values()}
    facts = [f"{labels.get(r['property'], r['property']).lower()} : {r['value']}" for r in d["properties"]]
    text = f"{d['label']} est de type {', '.join(d['types']) or 'inconnu'}. " + ("; ".join(facts) + "." if facts else "Aucune propriété renseignée.")
    if d["incoming"]:
        text += " Il/elle est référencé(e) par : " + ", ".join(f"{i['source']} ({labels.get(i['property'], i['property']).lower()})" for i in d["incoming"][:6]) + "."
    return jsonify(id=name, label=d["label"], engine="nlp", text=text, facts=facts)

@bp.get("/recommend/<name>")
@auth_required
def recommend(name):
    """Recommandation par raisonnement sur le graphe : clubs / stages / matières / ateliers qui développent des
    compétences que l'apprenant ne possède pas encore (classés par nombre de compétences nouvelles)."""
    u = uri_of(name)
    if not individual_exists(u):
        return jsonify(error="Apprenant introuvable"), 404
    rows = sparql(f"""SELECT ?item ?label (COUNT(DISTINCT ?c) AS ?score) (GROUP_CONCAT(DISTINCT ?cl; separator=", ") AS ?competences) WHERE {{
        ?item (:developpeCompetenceClub|:developpeCompetenceStage|:matiereDeveloppe|:developpe) ?c .
        ?c rdfs:label ?cl .
        OPTIONAL {{ ?item rdfs:label ?lab }}
        BIND(COALESCE(?lab, STRAFTER(STR(?item), "#")) AS ?label)
        FILTER NOT EXISTS {{ :{name} :possedeCompetence ?c }}
      }} GROUP BY ?item ?label ORDER BY DESC(?score) ?label LIMIT 8""")
    owned = [r["l"] for r in sparql(f"SELECT ?l WHERE {{ :{name} :possedeCompetence ?c . ?c rdfs:label ?l }}")]
    items = [dict(id=r["item"], label=r["label"], score=int(r["score"]), competences=r["competences"]) for r in rows]
    text = (f"{name} possède déjà : {', '.join(owned) or 'aucune compétence renseignée'}. " +
            (f"Pour élargir son profil, la meilleure piste est « {items[0]['label']} » ({items[0]['competences']})." if items else "Aucune piste trouvée."))
    return jsonify(id=name, engine="nlp", owned=owned, items=items, text=text)
