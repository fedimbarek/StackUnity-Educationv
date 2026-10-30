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

## Prédiction de difficulté des matières

`POST /api/prediction/difficulte` (JWT requis) reçoit `{"id":"Mathematiques"}`. Les résultats d'étudiants sont chargés depuis `backend/tests/data.csv` et associés à la matière RDF par son identifiant ou son nom. Ce CSV contient 800 notes sur 20, pour 10 matières et 80 résultats par matière. Les données de l'ontologie restent utilisées pour retrouver la matière et ses métadonnées ; si le CSV ne contient pas de notes correspondantes, l'API conserve les règles de secours décrites plus bas.

Le script entraîne un Random Forest sur une ligne agrégée par matière, jamais sur des lignes d'étudiants mélangées entre entraînement et test. Les labels sont dérivés du taux de réussite observé : « Difficile » jusqu'à 40 %, « Facile » à partir de 75 %, « Moyenne » entre les deux. Sur le CSV actuel, cela donne 3 matières difficiles, 3 moyennes et 4 faciles. Le split stratifié réserve 3 matières (une par classe) au test et entraîne sur les 7 autres. Ce jeu est très petit : les mesures de test sont indicatives et ne démontrent pas une généralisation fiable. Les indicateurs de taux de réussite ne sont pas fournis au modèle comme caractéristiques, car ils servent à produire les labels. `confiance_pct` est le score `predict_proba` du modèle, non calibré ; ce n'est ni la précision mesurée du modèle ni une garantie de fiabilité.

Le seuil de réussite par défaut est 10/20 ; les seuils de difficulté sont configurables par `DIFFICULTY_HARD_MAX_SUCCESS_RATE` (40) et `DIFFICULTY_EASY_MIN_SUCCESS_RATE` (75). Le chemin du CSV peut être remplacé avec `DIFFICULTY_DATASET_PATH`. L'entraînement refuse de sauvegarder un modèle si chaque classe ne contient pas au moins trois matières. Lors du dernier entraînement, les scores sur les 3 matières de test étaient : accuracy 0,667, precision macro 0,500, recall macro 0,667 et F1 macro 0,556. En l'absence de modèle ou de notes CSV adaptées, l'API peut estimer par règles à partir du taux de réussite d'une formation reliée à une seule matière, ou du coefficient et du volume horaire. Cette estimation n'est pas du ML. `422` signifie qu'aucun indicateur exploitable n'est disponible.

Pour l'estimation de secours uniquement, les seuils sont coefficient facile jusqu'à 1,5/difficile à partir de 3, et volume horaire facile jusqu'à 24 h/difficile à partir de 45 h ; les signaux opposés s'équilibrent en « Moyenne ». Ces seuils heuristiques sont configurables avec `DIFFICULTY_EASY_COEFFICIENT_MAX`, `DIFFICULTY_HARD_COEFFICIENT_MIN`, `DIFFICULTY_EASY_HOURS_MAX` et `DIFFICULTY_HARD_HOURS_MIN`. Confirmer les seuils avec les responsables pédagogiques avant usage en production.

Installation et entraînement (depuis `backend`) :

```powershell
python -m pip install -r requirements.txt
python train_model.py
python app.py
```

Le modèle entraîné est enregistré dans `backend/models/difficulty_model.pkl` et rechargé à la demande. Pour une requête Postman, sélectionner `POST`, l'URL `http://localhost:5000/api/prediction/difficulte`, le header `Authorization: Bearer <JWT>` et le body JSON `{"id":"Mathematiques"}`. La forme suivante est illustrative uniquement (ces nombres ne sont pas présents dans l'ontologie actuelle) :

```json
{
  "matiere": "Mathématiques",
  "difficulte": "Difficile",
  "methode": "random_forest",
  "confiance_pct": 94.0,
  "confiance_avertissement": "Score predict_proba non calibré et calculé pour une matière déjà vue à l'entraînement (10 matières au total).",
  "source_donnees": "data.csv",
  "indicateurs": {
    "moyenne": 8.15,
    "note_minimale": 1.42,
    "note_maximale": 15.29,
    "taux_reussite": 31.25,
    "taux_echec": 68.75,
    "ecart_type": 3.1393,
    "nombre_evaluations": 80,
    "nombre_resultats": 80,
    "evaluations_ambigues": 0,
    "seuil_reussite": 10.0,
    "coefficient": 4.0,
    "nombre_heures": 60.0,
    "nombre_competences": 0,
    "taux_reussite_formation": null
  }
}
```

Le frontend peut appeler cette route via son service HTTP partagé, envoyer le jeton JWT déjà utilisé par les autres API et afficher `difficulte`, `methode`, `confiance_pct` et `indicateurs`. Le score en pourcentage n'est présent que pour Random Forest ; il est accompagné d'un avertissement sur sa calibration et la taille limitée des données. Les codes d'erreur sont 400 (identifiant invalide), 404 (matière inconnue), 422 (aucun indicateur exploitable) et 500 (erreur interne).

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
