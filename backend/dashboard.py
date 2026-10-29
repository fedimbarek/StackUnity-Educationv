"""Tableau de bord personnalisé : GET /api/me/dashboard.

Le dashboard dépend du rôle du compte connecté (classe de sa Personne dans l'ontologie) et ne montre QUE ses données :
chaque section est une requête SPARQL où ?me est lié à la personne du compte.
Ajouter un rôle ou une section = ajouter une entrée dans DASHBOARDS (aucune autre modification côté back).
"""
import datetime
from flask import Blueprint, jsonify, request
from rdflib import URIRef, Literal, RDF, RDFS
from auth import auth_required, session_info
from modules import module_of
from store import BASE, PREFIXES, onto, short, text, uri_of, individual_exists
import roles

bp = Blueprint("dashboard", __name__, url_prefix="/api/me")

# Chemins SPARQL qui tolèrent les relations inverses (le .ttl n'en matérialise souvent qu'un sens)
MEMBRE = "(:estMembreDe|^:aMembre)"
STAGE = "(:effectueStage|^:estEffectuePar)"
SERVICE_PAR = "(:assureParPersonnel|:consultePar)"


def S(key, title, icon, cols, where, select=None, empty="Rien à afficher pour le moment."):
    """Section : `cols` = [(variable, en-tête)] ; `where` = corps SPARQL où ?me est la personne connectée."""
    vars_ = " ".join("?" + v for v, _ in cols)
    return dict(key=key, title=title, icon=icon, cols=cols, empty=empty,
                query=f"SELECT DISTINCT {select or vars_} WHERE {{ {where} }}")


DASHBOARDS = {
    # ------------------------------------------------------------------ APPRENANT
    "apprenant": dict(
        title="Mon espace apprenant", subtitle="Votre parcours, vos résultats, vos clubs et vos services.",
        profile=[("Email", "email"), ("Téléphone", "telephone"), ("Moyenne générale", "moyenneGenerale"),
                 ("Niveau de langue", "niveauDeLangue"), ("Langues parlées", "parleLangue")],
        stats=[("Formations", "formations"), ("Séances", "seances"), ("Évaluations", "evaluations"), ("Clubs", "clubs"),
               ("Stages", "stages"), ("Certifications", "certifications"), ("Compétences", "competences")],
        sections=[
            S("formations", "Mes formations", "🎓", [("f", "Formation"), ("domaine", "Domaine"), ("duree", "Durée (h)"), ("taux", "Taux de réussite")],
              """{ ?me :inscritA ?f } UNION { ?i :inscriptionDe ?me ; :inscriptionPourFormation ?f }
                 OPTIONAL { ?f :appartientAuDomaine ?domaine } OPTIONAL { ?f :duree ?duree } OPTIONAL { ?f :tauxReussite ?taux }""",
              empty="Aucune formation associée à votre profil."),
            S("inscriptions", "Mes inscriptions", "📝", [("i", "Inscription"), ("type", "Type"), ("date", "Date"), ("statut", "Statut"), ("periode", "Période")],
              """?i :inscriptionDe ?me ; a ?type . FILTER(?type != owl:NamedIndividual && ?type != owl:Thing)
                 OPTIONAL { ?i :dateInscription ?date } OPTIONAL { ?i :statutInscription ?statut } OPTIONAL { ?i :inscriptionPourPeriode ?periode }"""),
            S("seances", "Mes séances", "🗓", [("s", "Séance"), ("date", "Date"), ("debut", "Début"), ("lieu", "Lieu"), ("ens", "Enseignant"), ("f", "Formation")],
              """?me :participeA ?s OPTIONAL { ?s :dateSeance ?date } OPTIONAL { ?s :heureDebut ?debut } OPTIONAL { ?s :lieuSeance ?lieu }
                 OPTIONAL { ?s :animePar ?ens } OPTIONAL { ?s :seanceDe ?f }"""),
            S("evaluations", "Mes évaluations", "📊", [("e", "Évaluation"), ("date", "Date"), ("score", "Note"), ("f", "Formation")],
              """?me :passeEvaluation ?e OPTIONAL { ?e :dateEvaluation ?date } OPTIONAL { ?e :score ?score } OPTIONAL { ?e :concerneFormation ?f }"""),
            S("clubs", "Mes clubs", "🎭", [("c", "Club"), ("jour", "Jour"), ("resp", "Responsable"), ("enc", "Encadrant")],
              f"""?me {MEMBRE} ?c OPTIONAL {{ ?c :jourSeance ?jour }} OPTIONAL {{ ?c :dirigePar ?resp }} OPTIONAL {{ ?c :encadrePar ?enc }}"""),
            S("stages", "Mon stage", "🏢", [("s", "Stage"), ("sujet", "Sujet"), ("org", "Organisme"), ("acad", "Encadrant académique"), ("tut", "Tuteur entreprise"), ("debut", "Début"), ("fin", "Fin")],
              f"""?me {STAGE} ?s OPTIONAL {{ ?s :sujet ?sujet }} OPTIONAL {{ ?s :accueilliPar ?org }} OPTIONAL {{ ?s :encadreAcademique ?acad }}
                  OPTIONAL {{ ?s :superviseParTuteur ?tut }} OPTIONAL {{ ?s :dateDebut ?debut }} OPTIONAL {{ ?s :dateFin ?fin }}"""),
            S("bourses", "Ma bourse", "💰", [("b", "Bourse"), ("montant", "Montant"), ("fin", "Financée par")],
              """?me :beneficieDeBourse ?b OPTIONAL { ?b :montantBourse ?montant } OPTIONAL { ?b :financePar ?fin }""",
              empty="Aucune bourse."),
            S("sante", "Mes services de santé", "🩺", [("s", "Service"), ("p", "Assuré par"), ("h", "Horaires"), ("gratuit", "Gratuit")],
              """?me :beneficieDuService ?s OPTIONAL { ?s :assureParPersonnel ?p } OPTIONAL { ?s :horairesOuverture ?h } OPTIONAL { ?s :estGratuit ?gratuit }"""),
            S("certificats", "Mes certificats médicaux", "📄", [("c", "Certificat"), ("date", "Date"), ("valide", "Validité (mois)"), ("par", "Délivré par")],
              """?c :certificatPour ?me OPTIONAL { ?c :dateCertificat ?date } OPTIONAL { ?c :validiteMois ?valide } OPTIONAL { ?par :delivreCertificat ?c }"""),
            S("certifications", "Mes certifications", "🏅", [("c", "Certification"), ("annee", "Année")],
              """?me :obtientCertification ?c OPTIONAL { ?c :anneeObtention ?annee }"""),
            S("competences", "Mes compétences", "🧩", [("c", "Compétence")], """?me :possedeCompetence ?c"""),
        ]),

    # ------------------------------------------------------------------ ENSEIGNANT
    "enseignant": dict(
        title="Mon espace enseignant", subtitle="Vos matières, vos séances, vos stagiaires encadrés et vos clubs.",
        profile=[("Email", "email"), ("Téléphone", "telephone"), ("Département", "appartientADepartement"),
                 ("Dirige", "dirigeDepartement"), ("Langues parlées", "parleLangue")],
        stats=[("Matières", "matieres"), ("Formations", "formations"), ("Séances animées", "seances"),
               ("Stages encadrés", "stages"), ("Clubs encadrés", "clubs"), ("Apprenants", "apprenants", "a")],
        sections=[
            S("matieres", "Mes matières", "📚", [("m", "Matière"), ("code", "Code"), ("coef", "Coefficient"), ("heures", "Heures")],
              """?me :enseigneMatiere ?m OPTIONAL { ?m :codeMatiere ?code } OPTIONAL { ?m :coefficient ?coef } OPTIONAL { ?m :nombreHeures ?heures }"""),
            S("formations", "Mes formations", "🎓", [("f", "Formation"), ("domaine", "Domaine"), ("duree", "Durée (h)")],
              """{ ?f :enseigne ?me } UNION { ?me :enseigne ?f }
                 OPTIONAL { ?f :appartientAuDomaine ?domaine } OPTIONAL { ?f :duree ?duree }"""),
            S("seances", "Mes séances", "🗓", [("s", "Séance"), ("date", "Date"), ("debut", "Début"), ("fin", "Fin"), ("lieu", "Lieu"), ("f", "Formation")],
              """?s :animePar ?me OPTIONAL { ?s :dateSeance ?date } OPTIONAL { ?s :heureDebut ?debut } OPTIONAL { ?s :heureFin ?fin }
                 OPTIONAL { ?s :lieuSeance ?lieu } OPTIONAL { ?s :seanceDe ?f }"""),
            S("apprenants", "Apprenants de mes séances", "🧑‍🎓", [("a", "Apprenant"), ("s", "Séance"), ("moy", "Moyenne")],
              """?s :animePar ?me . ?a :participeA ?s OPTIONAL { ?a :moyenneGenerale ?moy }"""),
            S("stages", "Stages que j'encadre", "🏢", [("s", "Stage"), ("sujet", "Sujet"), ("a", "Stagiaire"), ("org", "Organisme"), ("tut", "Tuteur entreprise")],
              f"""?s :encadreAcademique ?me OPTIONAL {{ ?s :sujet ?sujet }} OPTIONAL {{ ?a {STAGE} ?s }}
                  OPTIONAL {{ ?s :accueilliPar ?org }} OPTIONAL {{ ?s :superviseParTuteur ?tut }}"""),
            S("clubs", "Clubs que j'encadre", "🎭", [("c", "Club"), ("n", "Membres"), ("resp", "Responsable"), ("jour", "Jour")],
              """?c :encadrePar ?me OPTIONAL { ?c :nombreMembres ?n } OPTIONAL { ?c :dirigePar ?resp } OPTIONAL { ?c :jourSeance ?jour }"""),
            S("departements", "Mes départements", "🏛", [("d", "Département"), ("role", "Rôle")],
              """{ ?me :dirigeDepartement ?d BIND("Directeur" AS ?role) } UNION { ?me :appartientADepartement ?d
                   FILTER NOT EXISTS { ?me :dirigeDepartement ?d } BIND("Membre" AS ?role) }"""),
        ]),

    # ------------------------------------------------------------------ PERSONNEL MÉDICAL
    "medical": dict(
        title="Mon espace médical", subtitle="Les services que vous assurez, vos bénéficiaires et vos certificats.",
        profile=[("Spécialité", "specialiteMedicale"), ("Email", "email"), ("Téléphone", "telephone"), ("Langues parlées", "parleLangue")],
        stats=[("Services assurés", "services"), ("Certificats délivrés", "certificats"), ("Bénéficiaires", "beneficiaires", "a")],
        sections=[
            S("services", "Services que j'assure", "🩺", [("s", "Service"), ("type", "Type"), ("h", "Horaires"), ("rdv", "Sur rendez-vous"), ("gratuit", "Gratuit"), ("lieu", "Lieu")],
              f"""?s {SERVICE_PAR} ?me . ?s a ?type
                  FILTER(?type != owl:NamedIndividual && ?type != owl:Thing)
                  OPTIONAL {{ ?s :horairesOuverture ?h }} OPTIONAL {{ ?s :surRendezVous ?rdv }} OPTIONAL {{ ?s :estGratuit ?gratuit }}
                  OPTIONAL {{ ?s :serviceLocaliseDans ?lieu }}"""),
            S("beneficiaires", "Bénéficiaires", "🧑‍🎓", [("a", "Apprenant"), ("s", "Service")],
              f"""?s {SERVICE_PAR} ?me . ?a :beneficieDuService ?s""", empty="Aucun bénéficiaire enregistré."),
            S("certificats", "Certificats délivrés", "📄", [("c", "Certificat"), ("a", "Apprenant"), ("date", "Date"), ("valide", "Validité (mois)")],
              """?me :delivreCertificat ?c OPTIONAL { ?c :certificatPour ?a } OPTIONAL { ?c :dateCertificat ?date } OPTIONAL { ?c :validiteMois ?valide }""",
              empty="Aucun certificat délivré."),
        ]),

    # ------------------------------------------------------------------ RESPONSABLE DE CLUB
    "responsable_club": dict(
        title="Mon espace responsable de club", subtitle="Vos clubs, leurs membres et vos événements.",
        profile=[("Email", "email"), ("Téléphone", "telephone"), ("Langues parlées", "parleLangue")],
        stats=[("Clubs dirigés", "clubs"), ("Membres", "membres", "a"), ("Événements", "evenements")],
        sections=[
            S("clubs", "Mes clubs", "🎭", [("c", "Club"), ("n", "Membres"), ("cap", "Capacité max"), ("cot", "Cotisation"), ("jour", "Jour"), ("annee", "Créé en"), ("enc", "Encadrant"), ("h", "Hébergé par")],
              """?c :dirigePar ?me OPTIONAL { ?c :nombreMembres ?n } OPTIONAL { ?c :capaciteMax ?cap } OPTIONAL { ?c :cotisation ?cot }
                 OPTIONAL { ?c :jourSeance ?jour } OPTIONAL { ?c :anneeCreation ?annee } OPTIONAL { ?c :encadrePar ?enc } OPTIONAL { ?c :heberge ?h }"""),
            S("membres", "Membres de mes clubs", "🧑‍🎓", [("a", "Apprenant"), ("c", "Club"), ("email", "Email")],
              f"""?c :dirigePar ?me . ?a {MEMBRE} ?c OPTIONAL {{ ?a :email ?email }}""", empty="Aucun membre enregistré dans vos clubs."),
            S("evenements", "Événements organisés", "📅", [("e", "Événement"), ("c", "Club"), ("date", "Date")],
              """?c :dirigePar ?me . ?c :organiseEvenement ?e OPTIONAL { ?e :dateEvenement ?date }""", empty="Aucun événement."),
            S("competences", "Compétences développées par mes clubs", "🧩", [("k", "Compétence"), ("c", "Club")],
              """?c :dirigePar ?me . ?c :developpeCompetenceClub ?k"""),
        ]),

    # ------------------------------------------------------------------ TUTEUR (académique)
    "tuteur": dict(
        title="Mon espace tuteur", subtitle="Les apprenants que vous accompagnez.",
        profile=[("Email", "email"), ("Téléphone", "telephone"), ("Langues parlées", "parleLangue")],
        stats=[("Apprenants tutorés", "tutores"), ("Stages en cours", "stages")],
        sections=[
            S("tutores", "Mes apprenants", "🧑‍🎓", [("a", "Apprenant"), ("moy", "Moyenne"), ("email", "Email")],
              """?me :tutore ?a OPTIONAL { ?a :moyenneGenerale ?moy } OPTIONAL { ?a :email ?email }""",
              empty="Aucun apprenant ne vous est encore affecté."),
            S("stages", "Stages de mes apprenants", "🏢", [("a", "Apprenant"), ("s", "Stage"), ("sujet", "Sujet"), ("org", "Organisme")],
              f"""?me :tutore ?a . ?a {STAGE} ?s OPTIONAL {{ ?s :sujet ?sujet }} OPTIONAL {{ ?s :accueilliPar ?org }}""", empty="Aucun stage."),
        ]),

    # ------------------------------------------------------------------ TUTEUR D'ENTREPRISE
    "tuteur_entreprise": dict(
        title="Mon espace tuteur d'entreprise", subtitle="Les stages que vous supervisez et vos stagiaires.",
        profile=[("Email", "email"), ("Téléphone", "telephone"), ("Langues parlées", "parleLangue")],
        stats=[("Stages supervisés", "stages"), ("Stagiaires", "stagiaires", "a"), ("Organismes", "organismes", "o")],
        sections=[
            S("stages", "Stages que je supervise", "🏢", [("s", "Stage"), ("sujet", "Sujet"), ("org", "Organisme"), ("acad", "Encadrant académique"), ("debut", "Début"), ("fin", "Fin"), ("grat", "Gratification"), ("conv", "N° convention")],
              """?s :superviseParTuteur ?me OPTIONAL { ?s :sujet ?sujet } OPTIONAL { ?s :accueilliPar ?org } OPTIONAL { ?s :encadreAcademique ?acad }
                 OPTIONAL { ?s :dateDebut ?debut } OPTIONAL { ?s :dateFin ?fin } OPTIONAL { ?s :gratification ?grat } OPTIONAL { ?s :numeroConvention ?conv }"""),
            S("stagiaires", "Mes stagiaires", "🧑‍🎓", [("a", "Apprenant"), ("s", "Stage"), ("moy", "Moyenne")],
              f"""?s :superviseParTuteur ?me . ?a {STAGE} ?s OPTIONAL {{ ?a :moyenneGenerale ?moy }}""", empty="Aucun stagiaire rattaché."),
            S("organismes", "Organismes d'accueil", "🏛", [("o", "Organisme"), ("ville", "Ville"), ("secteur", "Secteur")],
              """?s :superviseParTuteur ?me . ?s :accueilliPar ?o OPTIONAL { ?o :ville ?ville } OPTIONAL { ?o :secteurActivite ?secteur }"""),
            S("competences", "Compétences développées en stage", "🧩", [("k", "Compétence"), ("s", "Stage")],
              """?s :superviseParTuteur ?me . ?s :developpeCompetenceStage ?k"""),
        ]),
}


# ---------------------------------------------------------------- mise en forme des cellules
def cell(v):
    """Valeur RDF -> {t: texte, id?: identifiant d'instance, m?: module} (id/m permettent d'ouvrir la fiche côté Angular)."""
    if v is None:
        return {"t": "—"}
    if isinstance(v, URIRef):
        if not str(v).startswith(BASE):
            return {"t": str(v)}
        c = {"t": text(v, RDFS.label) or short(v)}
        if individual_exists(v):
            c["id"] = short(v)
            c["m"] = next((m for t in onto.objects(v, RDF.type) if (m := module_of(t))), None)
        return c
    py = v.toPython() if isinstance(v, Literal) else v
    if isinstance(py, bool):
        return {"t": "Oui" if py else "Non"}
    if isinstance(py, (datetime.date, datetime.time)):
        return {"t": py.isoformat()}
    return {"t": str(py)}


def run_section(sec, me):
    res = onto.query(PREFIXES + sec["query"], initBindings={"me": me})
    rows, seen = [], set()
    for r in res:
        raw = [r[v] if v in r.labels else None for v, _ in sec["cols"]]
        key = tuple(str(x) for x in raw)
        if key in seen:
            continue
        seen.add(key)
        rows.append(raw)
    rows.sort(key=lambda raw: [str(x or "").lower() for x in raw])
    return rows


def person_profile(me, spec):
    fields = []
    for label, prop in spec:
        vals = [cell(o) for o in onto.objects(me, URIRef(BASE + prop))]
        if vals:
            fields.append(dict(label=label, values=sorted(vals, key=lambda c: c["t"])))
    return fields


@bp.get("")
@auth_required
def me():
    return jsonify(session_info(request.user))


@bp.get("/dashboard")
@auth_required
def dashboard():
    info = session_info(request.user)
    spec = DASHBOARDS.get(info["role"])
    if spec is None or not info["person"]:
        return jsonify(error="Ce compte n'est lié à aucun profil : tableau de bord général", role=info["role"]), 404
    me_uri = uri_of(info["person"])

    sections, raw_rows = [], {}
    for sec in spec["sections"]:
        rows = run_section(sec, me_uri)
        raw_rows[sec["key"]] = (sec, rows)
        sections.append(dict(key=sec["key"], title=sec["title"], icon=sec["icon"], empty=sec["empty"],
                             columns=[h for _, h in sec["cols"]],
                             rows=[[cell(x) for x in raw] for raw in rows]))

    stats = []
    for st in spec["stats"]:
        label, key = st[0], st[1]
        sec, rows = raw_rows[key]
        if len(st) == 3:                                  # compte distinct sur une colonne (ex. apprenants distincts)
            idx = [v for v, _ in sec["cols"]].index(st[2])
            n = len({str(r[idx]) for r in rows if r[idx] is not None})
        else:
            n = len(rows)
        stats.append(dict(label=label, value=n, target=key))

    return jsonify(
        role=info["role"], profile=info["profile"], type=info["type"], title=spec["title"], subtitle=spec["subtitle"],
        person=dict(id=info["person"], name=info["name"], fields=person_profile(me_uri, spec["profile"])),
        stats=stats, sections=sections)
