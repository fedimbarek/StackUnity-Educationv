import traceback
from flask import Blueprint, request, jsonify
from auth import auth_required
from nlp_bourses import get_engine, EXAMPLES, STEMMER, ROOTS

bp = Blueprint("bourses_ai", __name__, url_prefix="/api/bourses-ai")


@bp.get("/status")
@auth_required
def status():
    try:
        e = get_engine()
        return jsonify({"module": "NLP Bourses + Inscriptions", "stemmer": STEMMER, "roots": ROOTS,
                        "classes": len(e.scope_cls), "proprietes": len(e.scope_props),
                        "individus": len(e.scope_inds), "llm": False})
    except Exception as ex:
        traceback.print_exc()
        return jsonify({"ok": False, "error": f"{type(ex).__name__}: {ex}"}), 500


@bp.get("/examples")
@auth_required
def examples():
    return jsonify(EXAMPLES)


@bp.post("/ask")
@auth_required
def ask():
    q = (request.get_json(silent=True) or {}).get("question", "").strip()
    if not q:
        return jsonify({"ok": False, "error": "Question vide"}), 400
    try:
        return jsonify(get_engine().ask(q))
    except Exception as ex:
        traceback.print_exc()
        return jsonify({"ok": False, "error": f"{type(ex).__name__}: {ex}"}), 500