import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from ttl_schema import load
from nlp import NL2SPARQL, tools
S = load()
print(len(S.classes), "classes", len(S.props), "propriétés", len(S.inds), "individus", tools())
nl = NL2SPARQL(S)
qs = sys.argv[1:] or ["Quels apprenants ont une bourse ?"]
for q in qs:
    r = nl.translate(q)
    print("\n>>", q, "\n   entités:", [(e["text"], e["kind"], e["name"]) for e in r["trace"]["entities"]], "intent:", r["trace"]["intent"], "notes:", r["trace"]["notes"])
    print(r["sparql"])
