"""API NLP : POST /api/nlp/query {question} → {sparql, rows, meta}.

Wrapper Flask autour de NEFZI_NL2SPARQL (spaCy + NLTK + difflib).
Le traducteur est instancié une seule fois (singleton).
"""
from flask import Blueprint, request, jsonify
from auth import auth_required
from store import sparql

bp = Blueprint("nefzi_nlp", __name__, url_prefix="/api/nlp")

# --- Singleton : initialisation paresseuse ---
_translator = None


def _get_translator():
    global _translator
    if _translator is None:
        from nefzi_nl2sparql import Schema, NL2SPARQL, tools
        print("[NLP] Chargement du schéma…")
        schema = Schema.from_ontology()
        _translator = NL2SPARQL(schema)
        print(f"[NLP] Traducteur NL2SPARQL prêt | outils : {tools()}")
    return _translator


@bp.post("/query")
@auth_required
def query():
    # 1) Validation
    raw = request.get_data(as_text=True)
    try:
        data = request.get_json(force=True)
    except Exception as e:
        return jsonify(error=f"JSON invalide : {e}", raw=raw), 400
    if not data:
        return jsonify(error="Corps JSON manquant", raw=raw), 400

    question = (data.get("question") or "").strip()
    if not question:
        return jsonify(error="Question vide", received=data), 400

    print(f"[NLP API] Question : {question!r}")

    # 2) Traduction question → SPARQL
    try:
        tr = _get_translator()
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify(error=f"Traducteur indisponible : {e}"), 500

    result = tr.translate(question)
    sql = result.get("sparql")
    trace = result.get("trace", {})
    kind = result.get("kind", "select")

    print(f"[NLP API] kind={kind} | intents={trace.get('intent')} | "
          f"entities={len(trace.get('entities', []))}")

    if not sql:
        return jsonify(
            error="Je n'ai pas compris la question. Reformulez en citant une classe, "
                  "une propriété ou un individu de l'ontologie.",
            trace=trace,
        ), 422

    # 3) Exécution SPARQL
    try:
        rows = sparql(sql)
    except Exception as e:
        return jsonify(error=f"Erreur SPARQL : {e}", sparql=sql, trace=trace), 500

    print(f"[NLP API] ✅ {len(rows)} ligne(s)")

    # 4) Réponse compatible avec le frontend
    meta = {
        "kind": kind,
        "intent": ", ".join(trace.get("intent", [])) or "select",
        "spacy_used": bool(trace.get("tools", {}).get("spacy")),
        "nltk_used": bool(trace.get("tools", {}).get("nltk")),
        "entities": trace.get("entities", []),
        "constraints": trace.get("constraints", []),
        "notes": trace.get("notes", []),
        "tools": trace.get("tools", {}),
        "trace": trace,
    }
    return jsonify(sparql=sql, rows=rows, meta=meta)


@bp.get("/examples")
@auth_required
def examples():
    """Exemples cliquables dans l'UI — couvrent les 8 intentions du traducteur."""
    return jsonify(examples=[
        "Quels sont les services de santé gratuits ?",
        "Quels sont les services de vie étudiante ?",
        "Combien de services de santé ?",
        "Combien de services par type ?",
        "Que sais-tu sur Karim ?",
        "Donne-moi le profil de Amira",
        "Est-ce qu'il y a une consultation dentaire ?",
        "Quels services consulte Amira ?",
        "Quels services consulte Karm ?",
        "Quel club a le plus de membres ?",
        "Quels services sans rendez-vous ?",
        "Je cherche un psychologue",
    ])