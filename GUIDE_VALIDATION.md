# Guide de validation — StackUnity (Web Sémantique 2026/2027)

Cahier des charges du mini-projet (Mme Mallek) → où chaque point est démontrable.

| Critère (pts) | Où le montrer | Ce qui est livré |
|---|---|---|
| **Requêtes SPARQL (4)** | Menu *Console SPARQL* | **Lecture** : bibliothèque de 16 requêtes (`backend/queries.py`) : jointures, FILTER, OPTIONAL, `COUNT/SUM/GROUP BY`, `GROUP_CONCAT`, `UNION`, `FILTER NOT EXISTS`, property paths, `ASK`, `BIND`. **Écriture (CRUD)** : onglet « Écriture » → `INSERT DATA`, `DELETE/INSERT WHERE`, `DELETE WHERE` (admin) ; chaque mise à jour réécrit `formation_.ttl`. **Recherche** : recherche globale du dashboard (`CONTAINS`). |
| **Individus (2)** | Dashboard + modules | 186 individus, 10 modules, CRUD complet via l'interface, fiche globale d'un individu. |
| **Scénario (2)** | Menu *Scénario Amira* → « Tout exécuter » | « Dossier 360° d'Amira » en 6 étapes, chacune appelle le backend : connexion JWT → recherche → fiche → SPARQL UNION → question en langage naturel → recommandation. |
| **Api IA (4)** — NLP → SPARQL | Menu *Assistant NLP* | Traducteur question française → SPARQL **sans LLM** (`backend/nlp.py`). Voir ci-dessous. |
| **Interfaces graphiques (3)** | Toute l'application | Angular 19 (front) + back-office : login, dashboard, 10 modules à onglets, schéma (classes/propriétés), console SPARQL, assistant NLP, scénario. |
| **Communication BE ↔ FE (3)** | DevTools → Réseau | API REST JSON (Flask) ↔ Angular `HttpClient`, JWT, intercepteur 401, CORS, codes HTTP cohérents. |
| **Valeur ajoutée (2)** | Assistant NLP + *Télécharger .ttl* | Trace visible du pipeline NLP, recommandations par raisonnement sur le graphe, ontologie éditable depuis l'UI **et** Protégé. |

## Ontologie (thématique : formation et vie étudiante)
188 classes, 134 propriétés (ObjectProperty + DataProperty), 186 individus. **Axiomes** : classes disjointes (`AllDisjointClasses`),
propriétés inverses (`inverseOf`), restrictions `someValuesFrom`, **propriétés fonctionnelles** (12), **classe définie**
`Boursier ≡ Apprenant ⊓ ∃beneficieDeBourse.Bourse` et **cardinalité maximale** (`Stage ⊑ ≤1 accueilliPar`). À montrer dans Protégé (lancer HermiT pour l'inférence de `Boursier`).

## Module NLP → SPARQL (sans API de LLM) — à mentionner dans la présentation
**Outils utilisés : spaCy (`fr_core_news_sm`) — tokenisation, lemmatisation, POS ; NLTK — `SnowballStemmer('french')` ; `difflib` — tolérance aux fautes ; rdflib — validation et exécution SPARQL ; Flask — API.** Aucun appel à Gemini / OpenAI / Claude ou autre LLM.

Pipeline (visible dans l'interface, bloc « Étapes du pipeline NLP ») :
1. **Analyse linguistique** : tokens, lemmes, racines.
2. **Lexique construit depuis l'ontologie** : labels et noms de classes, propriétés, individus + synonymes (étudiant → Apprenant, prof → Enseignant…).
3. **Liaison d'entités** : plus long n-gramme de racines ; fautes de frappe tolérées (« aprenants »).
4. **Intention** : liste, `COUNT` (combien), `ASK` (existe-t-il), fiche (que sais-tu sur…), superlatif (le plus / le moins), regroupement (par / chaque), négation (sans / aucun / pas).
5. **Contraintes** : comparateurs et nombres (plus de 20, supérieur à 3, entre 2 et 4), booléens (gratuit, rémunéré).
6. **Génération SPARQL guidée par le schéma** : domaines/portées des propriétés et hiérarchie des classes trouvent le chemin entre les entités citées ; `owl:inverseOf` géré par `(:p|^:q)` ; classes définies dépliées (Boursier).
7. **Validation + exécution** : `prepareQuery` (SELECT/ASK uniquement) puis rdflib.

Exemples à tester : « Quels apprenants ont une bourse ? » · « Combien de membres par club ? » · « Quels clubs ont plus de 20 membres ? » · « Quel club a le plus de membres ? » · « Quelles matières ont un coefficient entre 2 et 4 ? » · « Quels services médicaux ne sont pas gratuits ? » · « Quels apprenants ne sont membres d'aucun club ? » · « Existe-t-il un apprenant boursier ? » · « Que sais-tu sur Amira ? »

**Limites assumées** (à dire si on te les demande) : moteur à règles guidé par l'ontologie, pas d'apprentissage ; une question qui ne mentionne aucune entité connue est refusée avec des exemples ; pas de questions imbriquées complexes.

## Lancer
```bash
cd backend && python -m venv venv && source venv/bin/activate && pip install -r requirements.txt
python -m spacy download fr_core_news_sm
python tests/test_nlp.py         # 21 questions -> SPARQL (sans rdflib)
python check_queries.py          # 16 requêtes de la bibliothèque sur l'ontologie
python check_nlp.py              # 17 questions de bout en bout (NLP -> SPARQL -> rdflib)
python app.py                    # :5000
cd ../frontend && npm install && npx ng serve   # :4200   (admin / admin123)
```

## Valeur ajoutée : dashboards par rôle
Se connecter avec `amira` (apprenant), `ahmed` (enseignant), `drsonia` (médecin), `rim` (responsable de club) ou `mehdi` (tuteur d'entreprise), mot de passe `demo123` : chacun voit **son** dashboard, tiré de l'ontologie par SPARQL (`backend/dashboard.py`), et seulement les modules de son rôle. Créer un compte → choisir un profil → la Personne est créée/liée dans `formation_.ttl`.

## Déroulé de démo (≈ 5 min)
1. Login `admin / admin123` → dashboard (compteurs, recherche).
2. **Protégé** : classes, propriétés, axiomes (disjoint, inverse, fonctionnelle, `Boursier` équivalente) ; **individus** → un module, créer/supprimer un individu.
3. **SPARQL** : 3 requêtes de la bibliothèque (agrégat, UNION, ASK) ; **écriture** : `INSERT DATA` puis `DELETE WHERE`, montrer `formation_.ttl`.
4. **Scénario Amira** → « Tout exécuter ».
5. **Assistant NLP** : 3 questions, ouvrir « Étapes du pipeline » et la requête générée ; citer spaCy + NLTK.
6. **Réseau (F12)** : JWT, appels JSON, 401 sans token.
