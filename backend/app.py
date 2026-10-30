"""StackUnity - Serveur Flask : API JSON <-> requêtes SPARQL sur l'ontologie formation_.ttl."""
import os
from flask import Flask, request, jsonify
import auth, schema, misc, queries, ai, dashboard
from modules import MODULES, make_blueprint
from nlp import generer_sparql
from store import sparql
from auth import auth_required
import nefzi_business_api
import nefzi_nlp_api

app = Flask(__name__)
app.register_blueprint(auth.bp)
app.register_blueprint(dashboard.bp)
app.register_blueprint(misc.bp)
app.register_blueprint(schema.bp)
app.register_blueprint(queries.bp)
app.register_blueprint(ai.bp)
app.register_blueprint(nefzi_business_api.bp)
app.register_blueprint(nefzi_nlp_api.bp)

for m in MODULES:
    app.register_blueprint(make_blueprint(m))

@app.route("/")
def index():
    return {"status": "ok", "service": "StackUnity API"}

@app.after_request
def cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = os.getenv("FRONT_ORIGIN", "http://localhost:4200")
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    return resp

@app.route("/api/<path:_>", methods=["OPTIONS"])
def preflight(_):
    return "", 204

# --- Assistant NLP Dhia : POST /api/nlp ---
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