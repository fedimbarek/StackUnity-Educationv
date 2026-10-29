"""Exécute des questions de référence (français -> SPARQL -> rdflib) et affiche le nombre de lignes obtenues.
Usage : cd backend && python check_nlp.py        (utile avant la démo : détecte toute requête générée invalide)"""
from ai import translator
from store import run_readonly
import nlp

QUESTIONS = [
    "Quels apprenants ont une bourse ?", "Combien d'apprenants ont une bourse ?", "Combien de membres par club ?",
    "Quels clubs ont plus de 20 membres ?", "Quel club a le plus de membres ?", "Quelles matières ont un coefficient supérieur à 3 ?",
    "Quelles matières ont un coefficient entre 2 et 4 ?", "Quels stages sont rémunérés ?", "Quels services médicaux sont gratuits ?",
    "Quels apprenants ne sont membres d'aucun club ?", "Existe-t-il un apprenant boursier ?", "Quels boursiers ?",
    "Que sais-tu sur Amira ?", "Quels sont les clubs d'Amira ?", "Quels profs enseignent la programmation web ?",
    "Donne les enseignants du département informatique", "Quel est le montant des bourses ?",
]
print("Outils NLP actifs :", nlp.tools(), "\n")
bad = 0
nl = translator()
for q in QUESTIONS:
    r = nl.translate(q)
    try:
        vars_, rows = run_readonly(r["sparql"])
        print(f"OK   {len(rows):>3} ligne(s)  {q}" + ("   (ASK = " + rows[0]["ASK"] + ")" if vars_ == ["ASK"] else ""))
        if not rows:
            print("     ^ 0 résultat : normal si la donnée n'existe pas, sinon vérifier la requête :\n" + r["sparql"])
    except Exception as e:
        bad += 1
        print(f"FAIL {q}\n     {e}\n{r['sparql']}")
print("\nTout est bon." if not bad else f"\n{bad} question(s) en erreur.")
