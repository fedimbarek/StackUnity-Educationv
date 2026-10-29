"""Vérifie que les 16 requêtes SPARQL de la bibliothèque s'exécutent sur l'ontologie (et combien de lignes elles retournent).
Usage : cd backend && python check_queries.py"""
from store import run_readonly
from queries import QUERIES

bad = 0
for q in QUERIES:
    try:
        vars_, rows = run_readonly(q["query"])
        print(f"OK   {q['id']:<28} {len(rows):>3} ligne(s)  {'(ASK = ' + rows[0]['ASK'] + ')' if vars_ == ['ASK'] else ''}")
        if not rows:
            print("     ^ aucun résultat : vérifier les données ou la requête")
    except Exception as e:
        bad += 1
        print(f"FAIL {q['id']:<28} {e}")
print("\nTout est bon." if not bad else f"\n{bad} requête(s) en erreur.")
