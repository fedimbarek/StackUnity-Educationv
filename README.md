# StackUnity — Application web sur ontologie (Angular + Flask + SPARQL)

    Front Angular (Auth, token JWT) --HTTP/JSON--> Serveur Flask --SPARQL (rdflib)--> backend/ontology/formation_.ttl  <-- Protégé

Toute création / modification / suppression (instances, classes, propriétés) **réécrit `formation_.ttl`**
(copie `formation_.ttl.bak` au premier enregistrement). Dans Protégé : File > Open > ce fichier (rouvrir après chaque modification).

## Lancer
    cd backend && python -m venv venv && source venv/bin/activate && pip install -r requirements.txt && python app.py   # :5000
    cd frontend && npm install && npx ng serve                                                                        # :4200
Compte démo `admin` / `admin123`, ou « Créer un compte » (comptes gardés dans backend/users.json).
Comptes de démo par profil (mot de passe `demo123`) : `amira` apprenant · `bilel` stagiaire · `ahmed`, `walid` enseignants · `drsonia` médecin · `mariem` psychologue · `rim` responsable de club · `mehdi` tuteur d'entreprise · `sami` tuteur (désactivables : `SEED_DEMO_USERS=0`).

> **Validation** : voir `GUIDE_VALIDATION.md` (critère par critère, déroulé de démo).

## Les 10 modules (1 module = 1 sous-arbre de l'ontologie = 1 blueprint Flask = 1 page Angular)
| Module (route / API) | Classe racine | Classes |
|---|---|---|
| personnes | Personne | 17 |
| formations | Domaine (Formation, Diplôme, Compétence, Certification, Parcours, Niveau, Période) | 42 |
| matieres | Matiere (Séance, Évaluation, Ressource, Outil numérique) | 26 |
| clubs | Club (Événement…) | 26 |
| organismes | Organisme (Université, Entreprise, Laboratoire, Stage) | 17 |
| espaces | Espace | 9 |
| inscriptions | Inscription | 4 |
| bourses | Bourse | 4 |
| sante | ServiceMedical | 25 |
| vie | ServiceVieEtudiante | 17 |
+ module **Propriétés** (`/api/properties`, page `/proprietes`) : CRUD des ObjectProperty / DatatypeProperty.
Total : 187 classes, toutes couvertes.

## API Flask (JWT : `Authorization: Bearer <token>`)
Pour chaque module `<m>` :
| Méthode | Route | Rôle |
|---|---|---|
| GET / POST | /api/<m>/classes | lister (hiérarchie + nb d'instances) / créer une sous-classe |
| PUT / DELETE | /api/<m>/classes/<Classe> | modifier (label, description, parent) / supprimer (refusée s'il reste sous-classes ou instances) |
| GET | /api/<m>/classes/<Classe>/items?columns=a,b | instances (sous-classes incluses) + valeurs des propriétés demandées |
| GET | /api/<m>/classes/<Classe>/properties | propriétés applicables (selon rdfs:domain) |
| POST | /api/<m>/items | créer une instance |
| GET / PUT / DELETE | /api/<m>/items/<Id> | lire / modifier / supprimer |
IA & requêtes : `GET /api/queries` (bibliothèque de 16 requêtes SPARQL), `POST /api/queries/<id>/run`, `POST /api/ai/ask` (NLP → SPARQL), `POST /api/sparql/update` (CRUD, admin), `POST /api/ai/explain`, `GET /api/ai/recommend/<id>`, `GET /api/ai/status`.
Transversal : `POST /api/auth/register|login`, `GET /api/modules`, `/api/stats`, `/api/search?q=`, `POST /api/sparql` (SELECT/ASK), `GET /api/export.ttl`,
`GET /api/individuals/<Id>` (fiche globale + module), `GET /api/classes/<Classe>/individuals`, `GET/POST /api/properties`, `PUT/DELETE /api/properties/<nom>`.

## Frontend Angular : composants
- **shared/** (composants réutilisés par tous les modules) : `module-page` (en-tête + onglets), `entity-crud` (CRUD d'une sous-entité),
  `item-table`, `item-detail`, `item-form` (champs typés : date, nombre, oui/non, liste d'instances), `class-manager`, `class-tree`, `class-form`.
- **features/<module>/<module>.component.ts** : 1 composant par module (10) ; chacun déclare ses onglets = ses sous-entités
  (57 au total), avec les colonnes du tableau et les champs du formulaire propres à chaque sous-entité.
  Exemple : Personnes → Enseignants, Apprenants, Personnel médical, Tuteurs, Tuteurs entreprise, Responsables de club, Administrateurs.
- Dans chaque module : onglets d'entités (CRUD instances) + onglet « ⚙ Classes » (CRUD des classes du module).
- **pages/** : login, dashboard (recherche globale), schema (CRUD des propriétés), sparql (bibliothèque de requêtes), **ai** (assistant NLP → SPARQL), **scenario** (dossier 360° d'Amira).

## Où est quoi
- backend/nlp.py (NLP → SPARQL, spaCy + NLTK) · ai.py (API IA) · queries.py (16 requêtes SPARQL) · check_queries.py (vérification)
- backend/app.py (assemblage) · modules.py (10 modules + CRUD) · schema.py (propriétés) · auth.py · misc.py · store.py (rdflib + écriture .ttl)
- frontend/src/app/core (auth, api.service, modules.ts, module.types.ts) · shared/ · features/ · pages/

## Comptes, rôles et dashboards personnalisés
Chaque compte (hors `admin`) est **lié à une Personne de l'ontologie** ; son **rôle vient de la classe de cette personne** (calculé à chaque connexion, `backend/roles.py`) :

| Rôle | Classes de l'ontologie | Dashboard (`GET /api/me/dashboard`) |
|---|---|---|
| apprenant | Apprenant, Étudiant, Stagiaire, Boursier… | formations, inscriptions, séances, évaluations, clubs, stage, bourse, santé, certificats, certifications, compétences |
| enseignant | Enseignant, Professeur, Chargé de cours, Vacataire | matières, formations, séances, apprenants de ses séances, stages encadrés, clubs encadrés, départements |
| medical | Médecin, Infirmier, Psychologue | services assurés, bénéficiaires, certificats délivrés |
| responsable_club | ResponsableClub | clubs, membres, événements, compétences |
| tuteur | Tuteur | apprenants tutorés, leurs stages |
| tuteur_entreprise | TuteurEntreprise | stages supervisés, stagiaires, organismes, compétences |
| admin / user | compte `admin`, anciens comptes sans profil | dashboard général (inchangé), accès complet |

- **Inscription** : l'utilisateur choisit son profil, puis soit sa fiche existante dans l'ontologie (une fiche = un seul compte), soit « Nouveau profil » (crée la Personne dans `formation_.ttl`). `GET /api/auth/profiles` (public) alimente le formulaire ; `administrateur` n'est pas auto-inscriptible.
- **Ajouter un rôle / une section** : `backend/dashboard.py` (dictionnaire `DASHBOARDS`, une section = une requête SPARQL avec `?me`) et `backend/roles.py` (`PROFILES`) ; côté Angular, pages visibles par rôle dans `core/roles.ts`.
- **Menu et routes** : un rôle ne voit que ses modules (`accessGuard`) ; propriétés, console SPARQL, assistant IA, scénario et export .ttl restent réservés à admin.
