import sys
from nlp_bourses import get_engine, EXAMPLES

e = get_engine()
print(f"classes={len(e.scope_cls)} props={len(e.scope_props)} individus={len(e.scope_inds)}\n")
for q in EXAMPLES:
    r = e.ask(q)
    if r["ok"]:
        n = r.get("answer") if r["type"] == "ask" else f"{len(r['rows'])} ligne(s)"
        print(f"OK   {q}  ->  {n}")
    else:
        print(f"ERR  {q}  ->  {r['error']}")
    if "--sparql" in sys.argv and r.get("sparql"):
        print(r["sparql"], "\n")