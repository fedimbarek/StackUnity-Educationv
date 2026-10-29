"""Bibliothèque de requêtes SPARQL (barème « Requêtes SPARQL »).

Chaque requête illustre une fonctionnalité de SPARQL 1.1 (jointure, FILTER, OPTIONAL, agrégats,
property paths, UNION, NOT EXISTS, ASK, BIND…). Elles sont servies par GET /api/queries et
exécutables via POST /api/queries/<id>/run ; la console SPARQL du front les charge dynamiquement.
Les préfixes (: rdf: rdfs: owl: xsd:) sont ajoutés par store.PREFIXES.
"""
from flask import Blueprint, jsonify
from auth import auth_required
from store import onto, short, PREFIXES

bp = Blueprint("queries", __name__, url_prefix="/api/queries")

# keywords : mots-clés (minuscules, sans accents) utilisés par le moteur local de l'API IA
QUERIES = [
    dict(id="enseignants_departement", category="Jointure", title="Enseignants et leur département",
         question="Quels enseignants appartiennent à quel département ?",
         keywords=["enseignant", "professeur", "departement", "prof"],
         query="""SELECT ?enseignant ?departement WHERE {
  ?e a/rdfs:subClassOf* :Enseignant ; rdfs:label ?enseignant ;
     :appartientADepartement ?d .
  ?d rdfs:label ?departement
} ORDER BY ?enseignant"""),

    dict(id="matieres_coefficient", category="FILTER", title="Matières à fort coefficient (> 3)",
         question="Quelles matières ont un coefficient supérieur à 3 ?",
         keywords=["matiere", "coefficient"],
         query="""SELECT ?matiere ?coef WHERE {
  ?m a/rdfs:subClassOf* :Matiere ; rdfs:label ?matiere ; :coefficient ?coef .
  FILTER(?coef > 3)
} ORDER BY DESC(?coef)"""),

    dict(id="formations_matieres", category="OPTIONAL", title="Formations, matières et volume horaire",
         question="Quelles matières comporte chaque formation ?",
         keywords=["formation", "matiere", "comporte", "programme"],
         query="""SELECT ?formation ?matiere ?heures WHERE {
  ?f a/rdfs:subClassOf* :Formation ; rdfs:label ?formation ; :aPourMatiere ?m .
  ?m rdfs:label ?matiere .
  OPTIONAL { ?m :nombreHeures ?heures }
} ORDER BY ?formation ?matiere"""),

    dict(id="volume_horaire_formation", category="Agrégat (SUM / COUNT)", title="Volume horaire total par formation",
         question="Quel est le volume horaire total de chaque formation ?",
         keywords=["volume", "horaire", "heures", "total", "duree"],
         query="""SELECT ?formation (COUNT(?m) AS ?nbMatieres) (SUM(?h) AS ?totalHeures) WHERE {
  ?f a/rdfs:subClassOf* :Formation ; rdfs:label ?formation ; :aPourMatiere ?m .
  ?m :nombreHeures ?h
} GROUP BY ?formation ORDER BY DESC(?totalHeures)"""),

    dict(id="boursiers", category="Jointure", title="Apprenants boursiers et montants",
         question="Quels apprenants ont une bourse et de quel montant ?",
         keywords=["bourse", "boursier", "montant", "financement"],
         query="""SELECT ?apprenant ?bourse ?montant WHERE {
  ?a :beneficieDeBourse ?b ; rdfs:label ?apprenant .
  ?b rdfs:label ?bourse ; :montantBourse ?montant
} ORDER BY DESC(?montant)"""),

    dict(id="stages_remuneres", category="FILTER + OPTIONAL", title="Stages rémunérés",
         question="Quels stages sont rémunérés ?",
         keywords=["stage", "remunere", "gratification", "pfe", "entreprise"],
         query="""SELECT ?stage ?gratification ?entreprise WHERE {
  ?s a/rdfs:subClassOf* :Stage ; rdfs:label ?stage ;
     :estRemunere ?r ; :gratification ?gratification .
  FILTER(?r = true)
  OPTIONAL { ?s :accueilliPar ?e . ?e rdfs:label ?entreprise }
} ORDER BY DESC(?gratification)"""),

    dict(id="clubs_membres", category="Agrégat (GROUP BY)", title="Nombre d'apprenants inscrits par club",
         question="Combien d'apprenants sont membres de chaque club ?",
         keywords=["club", "membre", "membres", "inscrit"],
         query="""SELECT ?club (COUNT(?a) AS ?membres) WHERE {
  ?a :estMembreDe ?c .
  ?c rdfs:label ?club
} GROUP BY ?club ORDER BY DESC(?membres)"""),

    dict(id="clubs_remplissage", category="BIND / calcul", title="Taux de remplissage des clubs",
         question="Quel est le taux de remplissage des clubs ?",
         keywords=["remplissage", "capacite", "club", "taux", "place"],
         query="""SELECT ?club ?membres ?capacite (ROUND(100 * ?membres / ?capacite) AS ?tauxPourcent) WHERE {
  ?c a/rdfs:subClassOf* :Club ; rdfs:label ?club ;
     :nombreMembres ?membres ; :capaciteMax ?capacite
} ORDER BY DESC(?tauxPourcent)"""),

    dict(id="competences_apprenants", category="GROUP_CONCAT", title="Compétences de chaque apprenant",
         question="Quelles compétences possède chaque apprenant ?",
         keywords=["competence", "competences", "possede", "apprenant", "etudiant"],
         query="""SELECT ?apprenant (GROUP_CONCAT(DISTINCT ?comp; separator=", ") AS ?competences) WHERE {
  ?a a/rdfs:subClassOf* :Apprenant ; rdfs:label ?apprenant ; :possedeCompetence ?c .
  ?c rdfs:label ?comp
} GROUP BY ?apprenant ORDER BY ?apprenant"""),

    dict(id="enseignant_competences", category="Chaîne de jointures", title="Enseignant → matière → compétence développée",
         question="Quelles compétences chaque enseignant permet-il de développer ?",
         keywords=["enseignant", "competence", "developpe", "matiere"],
         query="""SELECT DISTINCT ?enseignant ?matiere ?competence WHERE {
  ?e a/rdfs:subClassOf* :Enseignant ; rdfs:label ?enseignant ; :enseigneMatiere ?m .
  ?m rdfs:label ?matiere ; :matiereDeveloppe ?c .
  ?c rdfs:label ?competence
} ORDER BY ?enseignant"""),

    dict(id="services_medicaux_gratuits", category="FILTER (booléen)", title="Services médicaux gratuits",
         question="Quels services médicaux sont gratuits ?",
         keywords=["medical", "sante", "gratuit", "consultation", "medecin"],
         query="""SELECT ?service ?duree ?horaires WHERE {
  ?s a/rdfs:subClassOf* :ServiceMedical ; rdfs:label ?service ; :estGratuit ?g .
  FILTER(?g = true)
  OPTIONAL { ?s :dureeConsultationMinutes ?duree }
  OPTIONAL { ?s :horairesOuverture ?horaires }
} ORDER BY ?service"""),

    dict(id="apprenants_sans_club", category="FILTER NOT EXISTS", title="Apprenants sans club",
         question="Quels apprenants ne sont membres d'aucun club ?",
         keywords=["sans", "aucun", "club", "apprenant", "etudiant"],
         query="""SELECT ?apprenant WHERE {
  ?a a/rdfs:subClassOf* :Apprenant ; rdfs:label ?apprenant .
  FILTER NOT EXISTS { ?a :estMembreDe ?c }
} ORDER BY ?apprenant"""),

    dict(id="dossier_amira", category="UNION + BIND", title="Dossier 360° d'Amira",
         question="Donne-moi le dossier complet d'Amira",
         keywords=["dossier", "amira", "complet", "profil"],
         query="""SELECT ?categorie ?element WHERE {
  { :Amira :beneficieDeBourse ?x . BIND("Bourse" AS ?categorie) }
  UNION { :Amira :effectueStage ?x . BIND("Stage" AS ?categorie) }
  UNION { :Amira :estMembreDe ?x . BIND("Club" AS ?categorie) }
  UNION { :Amira :beneficieDuService ?x . BIND("Service" AS ?categorie) }
  UNION { :Amira :possedeCompetence ?x . BIND("Compétence" AS ?categorie) }
  UNION { :Amira :obtientCertification ?x . BIND("Certification" AS ?categorie) }
  OPTIONAL { ?x rdfs:label ?l }
  BIND(COALESCE(?l, STRAFTER(STR(?x), "#")) AS ?element)
} ORDER BY ?categorie ?element"""),

    dict(id="hierarchie_stage", category="Property path (+)", title="Hiérarchie des types de stage",
         question="Quelle est la hiérarchie des classes de stage ?",
         keywords=["hierarchie", "sous-classe", "classe", "types", "type"],
         query="""SELECT ?sousClasse ?parent WHERE {
  ?sousClasse rdfs:subClassOf+ :Stage ;
              rdfs:subClassOf ?parent .
  FILTER(isIRI(?parent))
} ORDER BY ?parent ?sousClasse"""),

    dict(id="instances_par_type", category="Agrégat + LIMIT", title="Nombre d'individus par classe",
         question="Combien d'individus y a-t-il par classe ?",
         keywords=["combien", "nombre", "individus", "instances", "statistiques"],
         query="""SELECT ?type (COUNT(?i) AS ?individus) WHERE {
  ?i a owl:NamedIndividual , ?type .
  FILTER(?type != owl:NamedIndividual)
} GROUP BY ?type ORDER BY DESC(?individus) LIMIT 15"""),

    dict(id="existe_boursier_membre", category="ASK", title="Un boursier est-il membre d'un club ?",
         question="Existe-t-il un apprenant boursier qui est aussi membre d'un club ?",
         keywords=["existe", "boursier", "membre", "club"],
         query="""ASK {
  ?a :beneficieDeBourse ?b ;
     :estMembreDe ?c
}"""),
]

BY_ID = {q["id"]: q for q in QUERIES}


def public(q):
    return {k: v for k, v in q.items() if k != "keywords"}


@bp.get("")
@auth_required
def list_queries():
    return jsonify([public(q) for q in QUERIES])


@bp.post("/<qid>/run")
@auth_required
def run_query(qid):
    q = BY_ID.get(qid)
    if not q:
        return jsonify(error="Requête inconnue"), 404
    res = onto.query(PREFIXES + q["query"])
    if res.type == "ASK":
        return jsonify(vars=["ASK"], rows=[{"ASK": str(res.askAnswer)}], **public(q))
    return jsonify(vars=[str(v) for v in res.vars],
                   rows=[{str(k): short(v) for k, v in r.asdict().items()} for r in list(res)[:500]], **public(q))
