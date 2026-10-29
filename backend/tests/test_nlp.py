"""Tests du traducteur NLP -> SPARQL (sans rdflib : le schéma est lu dans le .ttl par regex).
Usage : cd backend && python tests/test_nlp.py"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from ttl_schema import load
from nlp import NL2SPARQL

nl = NL2SPARQL(load())
CASES = [  # (question, fragments attendus dans le SPARQL)
    ("Quels apprenants ont une bourse ?", [":Apprenant", ":beneficieDeBourse", ":Bourse"]),
    ("Quels étudiants ont une bourse ?", [":Apprenant", ":beneficieDeBourse"]),                       # synonyme
    ("aprenants avec une bourse", [":Apprenant", ":beneficieDeBourse"]),                              # faute de frappe
    ("Combien d'apprenants ont une bourse ?", ["COUNT(DISTINCT ?x)", ":beneficieDeBourse"]),
    ("Combien de membres par club ?", ["COUNT(DISTINCT ?x)", "GROUP BY ?club", ":estMembreDe", ":Club"]),
    ("Quels clubs ont plus de 20 membres ?", [":nombreMembres", "> 20"]),
    ("Quel club a le plus de membres ?", ["ORDER BY DESC(?nombre)", "LIMIT 1", ":estMembreDe"]),
    ("Quelles matières ont un coefficient supérieur à 3 ?", [":coefficient", "> 3"]),
    ("Quelles matières ont un coefficient entre 2 et 4 ?", [">= 2", "<= 4"]),
    ("Quelle matière a le plus grand coefficient ?", ["ORDER BY DESC(", "LIMIT 1"]),
    ("Quels stages sont rémunérés ?", [":Stage", ":estRemunere", "= true"]),
    ("Quels services médicaux ne sont pas gratuits ?", [":ServiceMedical", ":estGratuit", "= false"]),
    ("Combien de stages rémunérés ?", ["COUNT(DISTINCT ?x)", "= true"]),
    ("Quels apprenants ne sont membres d'aucun club ?", ["FILTER NOT EXISTS", ":Club"]),
    ("Existe-t-il un apprenant boursier ?", ["ASK", ":beneficieDeBourse"]),                           # classe définie dépliée
    ("Quels boursiers ?", [":Apprenant", ":beneficieDeBourse", ":Bourse"]),
    ("Que sais-tu sur Amira ?", [":Amira ?p ?v"]),
    ("Quels sont les clubs d'Amira ?", [":Club", ":Amira"]),
    ("Quels profs enseignent la programmation web ?", [":Enseignant", ":enseigneMatiere :ProgrammationWeb"]),
    ("Donne les enseignants du département informatique", [":Enseignant", ":appartientADepartement"]),
    ("Quel est le montant des bourses ?", [":montantBourse"]),
]
fail = 0
for q, frags in CASES:
    sp = nl.translate(q)["sparql"] or ""
    missing = [f for f in frags if f not in sp]
    print(("OK   " if not missing else "FAIL ") + q + (f"   manque {missing}" if missing else ""))
    fail += bool(missing)
print(f"\n{len(CASES) - fail}/{len(CASES)} questions traduites comme attendu")
sys.exit(1 if fail else 0)
