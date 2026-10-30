
"""StackUnity - Serveur Flask : API JSON <-> requêtes SPARQL sur l'ontologie formation_.ttl."""
import os
from flask import Flask, request, jsonify
import auth, schema, misc, queries, ai, dashboard, prediction
from modules import MODULES, make_blueprint
from nlp import generer_sparql
from store import sparql
from auth import auth_required

app = Flask(__name__)
app.register_blueprint(auth.bp)
app.register_blueprint(dashboard.bp)   # dashboard personnalisé selon le rôle (/api/me/dashboard)
app.register_blueprint(misc.bp)
app.register_blueprint(schema.bp)
app.register_blueprint(queries.bp)     # bibliothèque de requêtes SPARQL
app.register_blueprint(ai.bp)          # API IA (question -> SPARQL, explication, recommandation)
app.register_blueprint(prediction.bp)  # API de prédiction de difficulté des matières

for m in MODULES:                       # un blueprint REST par module métier
    app.register_blueprint(make_blueprint(m))

@app.after_request
def cors(resp):                         # CORS pour Angular (localhost:4200)
    resp.headers["Access-Control-Allow-Origin"] = os.getenv("FRONT_ORIGIN", "http://localhost:4200")
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    return resp

@app.route("/api/<path:_>", methods=["OPTIONS"])
def preflight(_):
    return "", 204

# Assistant NLP Personnes et Organismes — compatible avec le frontend Angular
@app.post("/api/nlp")
@auth_required
def assistant_nlp():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify(error="Envoyez un objet JSON contenant la question."), 400

    question = data.get("question", "")

    try:
        analyse = generer_sparql(question)
        resultats = sparql(analyse["sparql"])

        return jsonify({
            "question": question,
            "classe": analyse["classe"],
            "intention": analyse["intention"],
            "sparql": analyse["sparql"],
            "resultats": resultats,
        })

    except ValueError as exc:
        return jsonify(error=str(exc)), 400

    except Exception:
        app.logger.exception("Erreur lors de l'exécution de la requête NLP")
        return jsonify(error="Erreur lors de l'analyse NLP ou de l'exécution SPARQL."), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)
