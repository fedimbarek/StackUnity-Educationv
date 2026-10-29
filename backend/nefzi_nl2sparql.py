# backend/nefzi_nl2sparql.py
# -*- coding: utf-8 -*-
"""NEFZI_NL2SPARQL — Traduction français → SPARQL pour formation_.ttl.

API publique :
    Schema.from_ontology(path=None)   → charge l'ontologie (rdflib)
    NL2SPARQL(schema).translate(q)    → {"sparql": str|None, "kind": ..., "trace": {...}}
    tools()                           → état des outils NLP disponibles
"""
from __future__ import annotations

import os
import re
import unicodedata
import difflib
from pathlib import Path

try:
    from rdflib import Graph, RDF, RDFS, OWL, URIRef
    _HAS_RDFLIB = True
except ImportError:
    _HAS_RDFLIB = False

_SPACY = None
try:
    import spacy
    try:
        _SPACY = spacy.load("fr_core_news_sm")
    except Exception:
        try:
            _SPACY = spacy.blank("fr")
        except Exception:
            _SPACY = None
except ImportError:
    _SPACY = None

try:
    import nltk  # noqa: F401
    _HAS_NLTK = True
except ImportError:
    _HAS_NLTK = False

# Base de l'ontologie — doit correspondre à formation_.ttl
BASE = "http://stackunity.org/education#"


def tools() -> dict:
    return {
        "rdflib": _HAS_RDFLIB,
        "spacy": _SPACY is not None,
        "nltk": _HAS_NLTK,
        "difflib": True,
    }


def _norm(s: str) -> str:
    """Minuscule + sans accents."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return s.lower()


# ---------------------------------------------------------------------------
# Alias sémantiques français → id court de la classe
# Ordre "long d'abord" géré côté matching
# ---------------------------------------------------------------------------
KEYWORD_CLASS = {
    # --- Santé ---
    "sante": "ServiceMedical",
    "medical": "ServiceMedical",
    "medicale": "ServiceMedical",
    "consultation": "ConsultationMedicale",
    "consultations": "ConsultationMedicale",
    "dentaire": "ConsultationDentaire",
    "ophtalmo": "ConsultationOphtalmologique",
    "prevention": "PreventionSante",
    "depistage": "PreventionSante",
    "vaccination": "Vaccination",
    "psycholog": "SoutienPsychologique",
    "soutien": "SoutienPsychologique",
    "stress": "AtelierGestionStress",
    "secours": "PremiersSecoursMedicaux",
    "urgence": "PremiersSecoursMedicaux",
    "sportive": "SanteSportive",
    "kine": "Kinesitherapie",
    "certificat": "CertificatMedical",
    # --- Vie étudiante ---
    "vie etudiante": "ServiceVieEtudiante",
    "vie": "ServiceVieEtudiante",
    "hebergement": "ServiceHebergement",
    "logement": "ServiceHebergement",
    "residence": "ResidenceUniversitaire",
    "restauration": "ServiceRestauration",
    "restaurant": "RestaurantUniversitaire",
    "cafeteria": "Cafeteria",
    "transport": "ServiceTransport",
    "navette": "NavetteUniversitaire",
    "covoiturage": "CovoiturageEtudiant",
    "orientation": "ServiceOrientationEmploi",
    "emploi": "ServiceOrientationEmploi",
    # --- Génériques ---
    "formation": "Formation",
    "cours": "Cours",
    "module": "Module",
    "programme": "Programme",
    "club": "Club",
    "apprenant": "Apprenant",
    "etudiant": "Apprenant",
    "enseignant": "Enseignant",
    "stage": "Stage",
    "competence": "Competence",
    "certification": "Certification",
    "bourse": "Bourse",
    "parcours": "ParcoursApprentissage",
    "matiere": "Matiere",
    "seance": "Seance",
    "evenement": "Evenement",
}


# Contraintes NLP → (regex, prop_id, valeur, type)
CONSTRAINT_PATTERNS = [
    (r"\bgratuit", "estGratuit", "true", "boolean"),
    (r"\bpayant", "estGratuit", "false", "boolean"),
    (r"\bsans rendez", "surRendezVous", "false", "boolean"),
    (r"\bavec rendez", "surRendezVous", "true", "boolean"),
    (r"\bsur rendez", "surRendezVous", "true", "boolean"),
    (r"\bremunere", "estRemunere", "true", "boolean"),
]


# ---------------------------------------------------------------------------
# Schéma
# ---------------------------------------------------------------------------
class Schema:
    def __init__(self, classes, obj_props, data_props, individuals):
        self.classes = classes
        self.obj_props = obj_props
        self.data_props = data_props
        self.individuals = individuals

    @classmethod
    def from_ontology(cls, path: str | None = None) -> "Schema":
        if not _HAS_RDFLIB:
            print("[NLP] rdflib absent → schéma vide.")
            return cls({}, {}, {}, {})

        if path is None:
            here = Path(__file__).resolve().parent
            candidate = here / "ontology" / "formation_.ttl"
            if not candidate.exists():
                candidate = here / "formation_.ttl"
            path = str(candidate)

        if not os.path.exists(path):
            print(f"[NLP] Ontologie introuvable : {path}")
            return cls({}, {}, {}, {})

        g = Graph()
        try:
            g.parse(path, format="turtle")
        except Exception as e:
            print(f"[NLP] Erreur parsing TTL : {e}")
            return cls({}, {}, {}, {})

        print(f"[NLP] Ontologie chargée : {len(g)} triplets ({path})")

        def short(u):
            s = str(u)
            return s.split("#")[-1].split("/")[-1]

        def label_of(u):
            for lbl in g.objects(u, RDFS.label):
                return str(lbl)
            return short(u)

        classes, obj_props, data_props, individuals = {}, {}, {}, {}

        # Classes
        for c in set(g.subjects(RDF.type, OWL.Class)) | set(g.subjects(RDF.type, RDFS.Class)):
            if not isinstance(c, URIRef):
                continue
            key = short(c).lower()
            classes[key] = (str(c), label_of(c))

        # Propriétés
        for p in g.subjects(RDF.type, OWL.ObjectProperty):
            key = short(p).lower()
            obj_props[key] = (str(p), label_of(p))
        for p in g.subjects(RDF.type, OWL.DatatypeProperty):
            key = short(p).lower()
            data_props[key] = (str(p), label_of(p))

        # Individus
        excluded = {OWL.Class, RDFS.Class, OWL.ObjectProperty, OWL.DatatypeProperty,
                    OWL.NamedIndividual, RDFS.Resource}
        class_uris = {u for u, _ in classes.values()}
        for s, _, o in g.triples((None, RDF.type, None)):
            if o in excluded:
                continue
            if not isinstance(s, URIRef) or not isinstance(o, URIRef):
                continue
            if str(o) in class_uris:
                continue
            lbl = label_of(s)
            individuals[lbl.lower()] = (str(s), lbl, str(o))

        print(f"[NLP] Schéma : {len(classes)} classes, {len(obj_props)} obj-props, "
              f"{len(data_props)} data-props, {len(individuals)} individus")
        return cls(classes, obj_props, data_props, individuals)


# ---------------------------------------------------------------------------
# Traducteur
# ---------------------------------------------------------------------------
class NL2SPARQL:
    def __init__(self, schema: Schema):
        self.schema = schema

    # --- Helpers ---------------------------------------------------------
    def _class_uri(self, cls_name: str) -> str | None:
        key = cls_name.lower()
        if key in self.schema.classes:
            return self.schema.classes[key][0]
        for k, (uri, _) in self.schema.classes.items():
            if key in k:
                return uri
        return None

    def _prop_uri(self, prop_id: str) -> str | None:
        pid = prop_id.lower()
        for d in (self.schema.data_props, self.schema.obj_props):
            if pid in d:
                return d[pid][0]
            for k, (uri, _) in d.items():
                if pid in k:
                    return uri
        return None

    # --- Détections ------------------------------------------------------
    def _detect_class_from_keywords(self, question: str):
        """Retourne (uri, cls_name, kw) ou (None, None, None)."""
        q = _norm(question)
        matches = []
        for kw, cls_name in KEYWORD_CLASS.items():
            if re.search(r"\b" + re.escape(kw), q):
                matches.append((len(kw), kw, cls_name))
        if not matches:
            return None, None, None
        # Plus long = plus spécifique
        matches.sort(key=lambda t: -t[0])
        for _, kw, cls_name in matches:
            uri = self._class_uri(cls_name)
            if uri:
                return uri, cls_name, kw
        return None, None, None

    def _detect_individual(self, question: str):
        """Fuzzy match d'un individu (Karim, Amira…) dans la question."""
        if not self.schema.individuals:
            return None, None
        tokens = re.findall(r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9_]{2,}", question)
        keys = list(self.schema.individuals.keys())
        for tok in tokens:
            if _norm(tok) in KEYWORD_CLASS:  # skip mots-clés de classe
                continue
            m = difflib.get_close_matches(tok.lower(), keys, n=1, cutoff=0.85)
            if m:
                uri, lbl, _ = self.schema.individuals[m[0]]
                return uri, lbl
        return None, None

    def _detect_intent(self, question: str) -> list[str]:
        q = _norm(question)
        intents = []
        if re.search(r"\bcombien\b|\bnombre\b", q):
            intent = "count"
            intents.append(intent)
        if re.search(r"\best.ce qu|\by a.t.il\b", q):
            intents.append("ask")
        if re.search(r"\bque sais.tu\b|\bprofil de\b|\binfos? sur\b|\bparle.moi de\b", q):
            intents.append("describe")
        if re.search(r"\bquels?\b|\bquelles?\b|\bliste\b|\bdonne.moi\b", q):
            intents.append("list")
        return intents or ["list"]

    def _detect_constraints(self, question: str) -> list[dict]:
        q = _norm(question)
        found = []
        for pattern, prop_id, value, vtype in CONSTRAINT_PATTERNS:
            if re.search(pattern, q):
                found.append({"prop": prop_id, "value": value, "type": vtype})
        return found

    # --- Construction des réponses --------------------------------------
    def _entities(self, indiv_uri, indiv_name, cls_uri, cls_name, kw):
        ents = []
        if indiv_uri:
            ents.append({"text": indiv_name or "", "name": indiv_name,
                         "kind": "individual", "uri": indiv_uri, "fuzzy": False})
        if cls_uri:
            ents.append({"text": kw or cls_name, "name": cls_name,
                         "kind": "class", "uri": cls_uri, "fuzzy": False})
        return ents

    def _reply(self, sparql, kind, intent, constraints, notes, entities):
        return {
            "sparql": sparql,
            "kind": kind,
            "trace": {
                "intent": intent,
                "entities": entities,
                "constraints": [f"{c['prop']} = {c['value']}" for c in constraints],
                "notes": notes,
                "tools": tools(),
            },
        }

    # --- Point d'entrée --------------------------------------------------
    def translate(self, question: str) -> dict:
        if not question or not question.strip():
            return self._reply(None, "select", [], [], ["Question vide"], [])

        intent = self._detect_intent(question)
        constraints = self._detect_constraints(question)

        indiv_uri, indiv_name = self._detect_individual(question)
        cls_uri, cls_name, kw = self._detect_class_from_keywords(question)

        # Fallback fuzzy sur les classes
        notes = []
        if cls_uri is None:
            tokens = re.findall(r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9_]{2,}", question)
            for tok in tokens:
                m = difflib.get_close_matches(tok.lower(), list(self.schema.classes.keys()),
                                              n=1, cutoff=0.75)
                if m:
                    cls_uri = self.schema.classes[m[0]][0]
                    cls_name = m[0]
                    notes.append(f"Classe fuzzy : {cls_name}")
                    break

        # -- describe (profil d'un individu) --
        if "describe" in intent and indiv_uri:
            sparql = (
                f"PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n"
                f"SELECT ?predicat ?valeur WHERE {{\n"
                f"  <{indiv_uri}> ?predicat ?valeur .\n"
                f"}} LIMIT 100"
            )
            return self._reply(sparql, "select", intent, constraints, notes,
                               self._entities(indiv_uri, indiv_name, None, None, None))

        if cls_uri is None:
            return self._reply(None, "select", intent, constraints,
                               notes + ["Aucune classe identifiable."],
                               self._entities(indiv_uri, indiv_name, None, None, None))

        # -- Filtres FILTER (contraintes) --
        filt_parts = []
        for c in constraints:
            prop_uri = self._prop_uri(c["prop"])
            if prop_uri:
                filt_parts.append(f"  ?individu <{prop_uri}> {c['value']} .")
        filt = ("\n" + "\n".join(filt_parts)) if filt_parts else ""

        ents = self._entities(indiv_uri, indiv_name, cls_uri, cls_name, kw)

        # -- count --
        if "count" in intent:
            sparql = (
                f"PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n"
                f"SELECT (COUNT(DISTINCT ?individu) AS ?total) WHERE {{\n"
                f"  ?individu a ?type .\n"
                f"  ?type rdfs:subClassOf* <{cls_uri}> .\n"
                f"{filt}"
                f"}}"
            )
            return self._reply(sparql, "count", intent, constraints, notes, ents)

        # -- ask --
        if "ask" in intent:
            sparql = (
                f"PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n"
                f"ASK WHERE {{\n"
                f"  ?individu a ?type .\n"
                f"  ?type rdfs:subClassOf* <{cls_uri}> .\n"
                f"{filt}"
                f"}}"
            )
            return self._reply(sparql, "ask", intent, constraints, notes, ents)

        # -- list (défaut) --
        sparql = (
            f"PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n"
            f"SELECT DISTINCT ?individu ?nom WHERE {{\n"
            f"  ?individu a ?type .\n"
            f"  ?type rdfs:subClassOf* <{cls_uri}> .\n"
            f"{filt}\n"
            f"  OPTIONAL {{ ?individu rdfs:label ?nom }}\n"
            f"}} LIMIT 100"
        )
        return self._reply(sparql, "select", intent, constraints, notes, ents)