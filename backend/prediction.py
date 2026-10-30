"""Extraction des résultats RDF et prédiction de difficulté des matières."""
from dataclasses import dataclass
import math
import os
from pathlib import Path
import re
import unicodedata

from flask import Blueprint, current_app, jsonify, request

from auth import auth_required
from store import BASE, sparql, uri_of

bp = Blueprint("prediction", __name__, url_prefix="/api/prediction")
MODEL_PATH = Path(__file__).parent / "models" / "difficulty_model.pkl"
DATASET_PATH = Path(os.getenv(
    "DIFFICULTY_DATASET_PATH",
    Path(__file__).parent / "tests" / "data.csv",
))
DATASET_COLUMNS = (
    "matiere_id",
    "matiere_label",
    "coefficient",
    "nombre_heures",
    "etudiant_id",
    "evaluation_id",
    "note",
    "note_max",
    "seuil_reussite",
)
FEATURE_COLUMNS = ("moyenne", "note_minimale", "note_maximale", "ecart_type", "nombre_evaluations")
DIFFICULTY_LABELS = ("Facile", "Moyenne", "Difficile")
_MODEL_CACHE = {"mtime": None, "artifact": None}


@dataclass(frozen=True)
class DifficultyConfig:
    passing_score: float = 10.0
    easy_min_success_rate: float = 75.0
    hard_max_success_rate: float = 40.0
    easy_coefficient_max: float = 1.5
    hard_coefficient_min: float = 3.0
    easy_hours_max: int = 24
    hard_hours_min: int = 45
    min_prediction_results: int = 5
    min_training_results: int = 5
    min_class_samples: int = 3


@dataclass(frozen=True)
class SubjectResults:
    subject_id: str
    name: str
    scores: tuple[float, ...]
    evaluation_count: int
    learner_scores: tuple[tuple[str, float], ...] = ()
    ambiguous_evaluation_count: int = 0
    coefficient: float | None = None
    study_hours: float | None = None
    competence_count: int = 0
    formation_success_rates: tuple[float, ...] = ()
    passing_score: float | None = None
    dataset_matter_id: str | None = None


class ModelNotTrainedError(Exception):
    """Le modèle persistant n'existe pas encore."""


def difficulty_config():
    """Charge les seuils configurables ; le barème par défaut suppose une note sur 20."""
    config = DifficultyConfig(
        passing_score=float(os.getenv("DIFFICULTY_PASSING_SCORE", "10")),
        easy_min_success_rate=float(os.getenv("DIFFICULTY_EASY_MIN_SUCCESS_RATE", "75")),
        hard_max_success_rate=float(os.getenv("DIFFICULTY_HARD_MAX_SUCCESS_RATE", "40")),
        easy_coefficient_max=float(os.getenv("DIFFICULTY_EASY_COEFFICIENT_MAX", "1.5")),
        hard_coefficient_min=float(os.getenv("DIFFICULTY_HARD_COEFFICIENT_MIN", "3")),
        easy_hours_max=int(os.getenv("DIFFICULTY_EASY_HOURS_MAX", "24")),
        hard_hours_min=int(os.getenv("DIFFICULTY_HARD_HOURS_MIN", "45")),
        min_prediction_results=int(os.getenv("DIFFICULTY_MIN_PREDICTION_RESULTS", "5")),
        min_training_results=int(os.getenv("DIFFICULTY_MIN_TRAINING_RESULTS", "5")),
        min_class_samples=int(os.getenv("DIFFICULTY_MIN_CLASS_SAMPLES", "3")),
    )
    if not math.isfinite(config.passing_score) or config.passing_score < 0:
        raise ValueError("DIFFICULTY_PASSING_SCORE doit être un nombre positif ou nul.")
    if not 0 <= config.hard_max_success_rate < config.easy_min_success_rate <= 100:
        raise ValueError("Les seuils de réussite doivent respecter 0 <= difficile < facile <= 100.")
    if not 0 <= config.easy_coefficient_max < config.hard_coefficient_min:
        raise ValueError("Les seuils de coefficient doivent respecter 0 <= facile < difficile.")
    if not 0 <= config.easy_hours_max < config.hard_hours_min:
        raise ValueError("Les seuils horaires doivent respecter 0 <= facile < difficile.")
    if min(config.min_prediction_results, config.min_training_results, config.min_class_samples) < 1:
        raise ValueError("Les minima de résultats et d'échantillons doivent être positifs.")
    return config


def _subject_row(subject_id):
    rows = sparql(
        """
        SELECT ?label ?name WHERE {
          ?id a owl:NamedIndividual ; a ?type .
          ?type rdfs:subClassOf* :Matiere .
          FILTER NOT EXISTS { ?type rdfs:subClassOf* :Evaluation }
          OPTIONAL { ?id rdfs:label ?label }
          OPTIONAL { ?id :nom ?name }
        }
        """,
        id=f"{BASE}{subject_id}",
    )
    return rows[0] if rows else None


def get_subject_results(subject_id):
    """Renvoie les scores reliés à une seule matière par une formation non ambiguë."""
    subject = _subject_row(subject_id)
    if subject is None:
        return None

    profile_rows = sparql(
        """
        SELECT DISTINCT ?coefficient ?hours ?competence WHERE {
          OPTIONAL { ?id :coefficient ?coefficient }
          OPTIONAL { ?id :nombreHeures ?hours }
          OPTIONAL { ?id :matiereDeveloppe ?competence }
        }
        """,
        id=f"{BASE}{subject_id}",
    )
    coefficient_values = {float(row["coefficient"]) for row in profile_rows if row.get("coefficient")}
    hour_values = {float(row["hours"]) for row in profile_rows if row.get("hours")}
    if len(coefficient_values) > 1 or len(hour_values) > 1:
        raise ValueError(f"Plusieurs coefficients ou volumes horaires sont définis pour {subject_id}.")
    coefficient = next(iter(coefficient_values), None)
    study_hours = next(iter(hour_values), None)
    if any(not math.isfinite(value) or value < 0 for value in (coefficient, study_hours) if value is not None):
        raise ValueError(f"Coefficient ou volume horaire invalide pour {subject_id}.")
    competence_count = len({row["competence"] for row in profile_rows if row.get("competence")})

    rate_rows = sparql(
        """
        SELECT DISTINCT ?formation ?rate WHERE {
          ?formation :aPourMatiere ?id ; :tauxReussite ?rate .
          {
            SELECT ?formation WHERE {
              ?formation :aPourMatiere ?onlySubject .
            }
            GROUP BY ?formation
            HAVING (COUNT(DISTINCT ?onlySubject) = 1)
          }
        }
        """,
        id=f"{BASE}{subject_id}",
    )
    formation_rates = tuple(sorted({float(row["rate"]) for row in rate_rows}))
    if any(not math.isfinite(rate) or not 0 <= rate <= 100 for rate in formation_rates):
        raise ValueError(f"Taux de réussite de formation invalide pour {subject_id}.")

    rows = sparql(
        """
        SELECT DISTINCT ?learner ?evaluation ?score WHERE {
          ?learner :passeEvaluation ?evaluation .
          ?evaluation :score ?score ; :concerneFormation ?formation .
          ?formation :aPourMatiere ?matiere .
          {
            SELECT ?formation WHERE {
              ?formation :aPourMatiere ?otherMatter .
            }
            GROUP BY ?formation
            HAVING (COUNT(DISTINCT ?otherMatter) = 1)
          }
        }
        """,
        matiere=f"{BASE}{subject_id}",
    )
    scores_by_evaluation = {}
    learners_by_evaluation = {}
    for row in rows:
        score = float(row["score"])
        if not math.isfinite(score) or score < 0:
            raise ValueError(f"Score invalide pour l'évaluation {row['evaluation']}.")
        scores_by_evaluation.setdefault(row["evaluation"], set()).add(score)
        learners_by_evaluation.setdefault(row["evaluation"], set()).add(row["learner"])

    learner_scores = tuple(
        (next(iter(learners_by_evaluation[evaluation])), next(iter(evaluation_scores)))
        for evaluation, evaluation_scores in scores_by_evaluation.items()
        if len(learners_by_evaluation[evaluation]) == 1 and len(evaluation_scores) == 1
    )
    return SubjectResults(
        subject_id=subject_id,
        name=subject.get("label") or subject.get("name") or subject_id,
        scores=tuple(score for _, score in learner_scores),
        evaluation_count=len(learner_scores),
        learner_scores=learner_scores,
        ambiguous_evaluation_count=len(scores_by_evaluation) - len(learner_scores),
        coefficient=coefficient,
        study_hours=study_hours,
        competence_count=competence_count,
        formation_success_rates=formation_rates,
    )


def extract_all_subject_results():
    """Extrait toutes les matières réelles, sans inclure les évaluations typées comme Matiere."""
    subjects = sparql(
        """
        SELECT DISTINCT ?id ?label ?name WHERE {
          ?id a owl:NamedIndividual ; a ?type .
          ?type rdfs:subClassOf* :Matiere .
          FILTER NOT EXISTS { ?type rdfs:subClassOf* :Evaluation }
          OPTIONAL { ?id rdfs:label ?label }
          OPTIONAL { ?id :nom ?name }
        }
        """
    )
    results_by_id = {}
    for subject in subjects:
        if subject["id"] not in results_by_id:
            results_by_id[subject["id"]] = get_subject_results(subject["id"])
    return list(results_by_id.values())


def _read_difficulty_csv(dataset_path=None):
    import pandas as pd

    path = Path(dataset_path or DATASET_PATH)
    if not path.is_file():
        raise FileNotFoundError(f"Fichier de résultats introuvable : {path}")
    frame = pd.read_csv(path)
    missing_columns = sorted(set(DATASET_COLUMNS) - set(frame.columns))
    if missing_columns:
        raise ValueError(f"Colonnes manquantes dans {path.name} : {', '.join(missing_columns)}.")
    if frame.empty:
        raise ValueError(f"Le fichier de résultats {path.name} est vide.")
    frame = frame.loc[:, DATASET_COLUMNS].copy()
    if frame.isnull().any().any():
        raise ValueError(f"Le fichier de résultats {path.name} contient des champs vides.")

    numeric_columns = ("coefficient", "nombre_heures", "note", "note_max", "seuil_reussite")
    for column in numeric_columns:
        frame[column] = pd.to_numeric(frame[column], errors="raise")
    for column in numeric_columns:
        if not frame[column].map(math.isfinite).all():
            raise ValueError(f"Le fichier de résultats contient une valeur non finie dans {column}.")
    if (frame["coefficient"] < 0).any() or (frame["nombre_heures"] < 0).any():
        raise ValueError("Coefficient et volume horaire doivent être positifs ou nuls.")
    if (frame["note_max"] <= 0).any():
        raise ValueError("Les notes maximales doivent être positives.")
    if ((frame["note"] < 0) | (frame["note"] > frame["note_max"])).any():
        raise ValueError("Une note est en dehors de son échelle autorisée.")
    if ((frame["seuil_reussite"] < 0) | (frame["seuil_reussite"] > frame["note_max"])).any():
        raise ValueError("Un seuil de réussite est en dehors de son échelle autorisée.")
    if frame.duplicated(["matiere_id", "etudiant_id", "evaluation_id"]).any():
        raise ValueError("Le fichier contient des résultats dupliqués pour un étudiant et une évaluation.")

    metadata_columns = ("matiere_label", "coefficient", "nombre_heures", "note_max", "seuil_reussite")
    variations = frame.groupby("matiere_id", dropna=False)[list(metadata_columns)].nunique()
    inconsistent = variations.gt(1).any(axis=1)
    if inconsistent.any():
        ids = ", ".join(str(value) for value in variations.index[inconsistent])
        raise ValueError(f"Les métadonnées varient pour les matières : {ids}.")
    return frame


def _normalized_subject_name(value):
    decomposed = unicodedata.normalize("NFKD", str(value))
    without_accents = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]", "", without_accents.casefold())


def results_from_csv(subject, dataset_path=None):
    """Associe les notes CSV à une matière RDF par identifiant ou nom normalisé."""
    frame = _read_difficulty_csv(dataset_path)
    csv_ids = frame["matiere_id"].astype(str)
    if (csv_ids == subject.subject_id).any():
        subject_rows = frame.loc[csv_ids == subject.subject_id]
    else:
        normalized_name = _normalized_subject_name(subject.name)
        name_matches = frame["matiere_label"].astype(str).map(_normalized_subject_name) == normalized_name
        matching_ids = frame.loc[name_matches, "matiere_id"].astype(str).unique()
        if len(matching_ids) > 1:
            raise ValueError(f"Le nom de matière « {subject.name} » correspond à plusieurs entrées CSV.")
        if not len(matching_ids):
            return subject
        subject_rows = frame.loc[name_matches]

    scores = tuple(float(value) for value in subject_rows["note"])
    learner_scores = tuple(
        (str(row.etudiant_id), float(row.note))
        for row in subject_rows.itertuples(index=False)
    )
    first = subject_rows.iloc[0]
    return SubjectResults(
        subject_id=subject.subject_id,
        name=subject.name,
        scores=scores,
        evaluation_count=len(scores),
        learner_scores=learner_scores,
        ambiguous_evaluation_count=0,
        coefficient=float(first["coefficient"]),
        study_hours=float(first["nombre_heures"]),
        competence_count=subject.competence_count,
        formation_success_rates=subject.formation_success_rates,
        passing_score=float(first["seuil_reussite"]),
        dataset_matter_id=str(first["matiere_id"]),
    )


def calculate_indicators(results, config=None):
    config = config or difficulty_config()
    passing_score = results.passing_score if results.passing_score is not None else config.passing_score
    scores = results.scores
    if not scores:
        return {
            "moyenne": None,
            "note_minimale": None,
            "note_maximale": None,
            "taux_reussite": None,
            "taux_echec": None,
            "ecart_type": None,
            "nombre_evaluations": results.evaluation_count,
            "nombre_resultats": 0,
            "evaluations_ambigues": results.ambiguous_evaluation_count,
            "seuil_reussite": passing_score,
            "coefficient": results.coefficient,
            "nombre_heures": results.study_hours,
            "nombre_competences": results.competence_count,
            "taux_reussite_formation": statistics_mean(results.formation_success_rates)
            if results.formation_success_rates else None,
        }

    passed = sum(score >= passing_score for score in scores)
    success_rate = passed * 100.0 / len(scores)
    return {
        "moyenne": statistics_mean(scores),
        "note_minimale": min(scores),
        "note_maximale": max(scores),
        "taux_reussite": success_rate,
        "taux_echec": 100.0 - success_rate,
        "ecart_type": statistics_stdev_population(scores),
        "nombre_evaluations": results.evaluation_count,
        "nombre_resultats": len(scores),
        "evaluations_ambigues": results.ambiguous_evaluation_count,
        "seuil_reussite": passing_score,
        "coefficient": results.coefficient,
        "nombre_heures": results.study_hours,
        "nombre_competences": results.competence_count,
        "taux_reussite_formation": statistics_mean(results.formation_success_rates)
        if results.formation_success_rates else None,
    }


def _features(indicators):
    return {
        "moyenne": indicators["moyenne"],
        "note_minimale": indicators["note_minimale"],
        "note_maximale": indicators["note_maximale"],
        "ecart_type": indicators["ecart_type"],
        "nombre_evaluations": indicators["nombre_evaluations"],
    }


def difficulty_label(success_rate, config=None):
    config = config or difficulty_config()
    if success_rate <= config.hard_max_success_rate:
        return "Difficile"
    if success_rate >= config.easy_min_success_rate:
        return "Facile"
    return "Moyenne"


def estimate_difficulty(results, indicators, config=None):
    """Estime depuis les indicateurs RDF disponibles, sans présenter une règle comme un modèle ML."""
    config = config or difficulty_config()
    if indicators["taux_reussite"] is not None:
        return difficulty_label(indicators["taux_reussite"], config), "regles_resultats"

    if results.formation_success_rates:
        rate = statistics_mean(results.formation_success_rates)
        return difficulty_label(rate, config), "regles_reussite_formation"

    signals = []
    if results.coefficient is not None:
        if results.coefficient >= config.hard_coefficient_min:
            signals.append(1)
        elif results.coefficient <= config.easy_coefficient_max:
            signals.append(-1)
        else:
            signals.append(0)
    if results.study_hours is not None:
        if results.study_hours >= config.hard_hours_min:
            signals.append(1)
        elif results.study_hours <= config.easy_hours_max:
            signals.append(-1)
        else:
            signals.append(0)
    if not signals:
        return None, None

    balance = sum(signals)
    difficulty = "Difficile" if balance > 0 else "Facile" if balance < 0 else "Moyenne"
    return difficulty, "regles_charge_pedagogique"


def prepare_training_dataset(subject_results=None, config=None):
    """Construit un DataFrame d'une ligne par matière avec des scores RDF réels."""
    import pandas as pd

    config = config or difficulty_config()
    subject_results = subject_results if subject_results is not None else extract_all_subject_results()
    rows = []
    for results in subject_results:
        if results is None or len(results.scores) < config.min_training_results:
            continue
        indicators = calculate_indicators(results, config)
        rows.append({
            "matiere_id": results.subject_id,
            **_features(indicators),
            "difficulte": difficulty_label(indicators["taux_reussite"], config),
        })
    return pd.DataFrame(rows, columns=("matiere_id", *FEATURE_COLUMNS, "difficulte"))


def prepare_training_dataset_from_csv(dataset_path=None, config=None):
    """Construit une ligne par matière à partir des notes réelles du fichier CSV."""
    import pandas as pd

    config = config or difficulty_config()
    frame = _read_difficulty_csv(dataset_path)
    rows = []
    for subject_id, subject_rows in frame.groupby("matiere_id", sort=True):
        scores = tuple(float(value) for value in subject_rows["note"])
        if len(scores) < config.min_training_results:
            continue
        first = subject_rows.iloc[0]
        results = SubjectResults(
            subject_id=str(subject_id),
            name=str(first["matiere_label"]),
            scores=scores,
            evaluation_count=len(scores),
            coefficient=float(first["coefficient"]),
            study_hours=float(first["nombre_heures"]),
            passing_score=float(first["seuil_reussite"]),
        )
        indicators = calculate_indicators(results, config)
        rows.append({
            "matiere_id": str(subject_id),
            **_features(indicators),
            "difficulte": difficulty_label(indicators["taux_reussite"], config),
        })
    return pd.DataFrame(rows, columns=("matiere_id", *FEATURE_COLUMNS, "difficulte"))


def load_model():
    """Recharge le modèle après modification du fichier, sans relire le pickle à chaque requête."""
    if not MODEL_PATH.is_file():
        raise ModelNotTrainedError("Le modèle n'est pas entraîné. Lancez `python train_model.py`.")
    mtime = MODEL_PATH.stat().st_mtime
    if _MODEL_CACHE["mtime"] != mtime:
        import joblib

        artifact = joblib.load(MODEL_PATH)
        if (
            not isinstance(artifact, dict)
            or artifact.get("features") != list(FEATURE_COLUMNS)
            or not isinstance(artifact.get("training_matter_ids"), list)
            or not isinstance(artifact.get("test_matter_ids"), list)
        ):
            raise ValueError("Format de modèle incompatible ; relancez `python train_model.py`.")
        _MODEL_CACHE["artifact"] = artifact
        _MODEL_CACHE["mtime"] = mtime
    return _MODEL_CACHE["artifact"]


@bp.post("/difficulte")
@auth_required
def predict_subject_difficulty():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="Envoyez un objet JSON avec l'identifiant de la matière."), 400
    subject_id = data.get("id")
    if not isinstance(subject_id, str) or not subject_id.strip() or uri_of(subject_id.strip()) is None:
        return jsonify(error="L'identifiant de la matière est manquant ou invalide."), 400
    subject_id = subject_id.strip()

    try:
        results = get_subject_results(subject_id)
        if results is None:
            return jsonify(error="Matière introuvable."), 404

        config = difficulty_config()
        csv_results = results_from_csv(results)
        uses_csv = csv_results is not results
        results = csv_results
        indicators = calculate_indicators(results, config)
        if len(results.scores) >= config.min_prediction_results:
            try:
                artifact = load_model()
            except ModelNotTrainedError:
                artifact = None
            if artifact is not None:
                import pandas as pd

                row = pd.DataFrame([_features(indicators)], columns=FEATURE_COLUMNS)
                model = artifact["model"]
                difficulty = str(model.predict(row)[0])
                class_index = list(model.classes_).index(difficulty)
                confidence = float(model.predict_proba(row)[0][class_index]) * 100
                training_ids = artifact["training_matter_ids"]
                test_ids = artifact["test_matter_ids"]
                if uses_csv and results.dataset_matter_id in training_ids:
                    confidence_warning = (
                        "Score predict_proba non calibré et calculé pour une matière déjà vue "
                        f"à l'entraînement ({artifact['dataset_subjects']} matières au total)."
                    )
                elif uses_csv and results.dataset_matter_id in test_ids:
                    confidence_warning = (
                        "Score predict_proba non calibré ; cette matière était tenue à l'écart "
                        f"de l'entraînement ({artifact['dataset_subjects']} matières au total)."
                    )
                elif not uses_csv:
                    confidence_warning = (
                        "Score predict_proba non calibré ; cette matière RDF n'est pas présente "
                        f"dans le CSV d'entraînement ({artifact['dataset_subjects']} matières)."
                    )
                else:
                    confidence_warning = (
                        "Score predict_proba non calibré ; cette matière ne figure pas dans "
                        f"l'échantillon d'entraînement ({artifact['dataset_subjects']} matières)."
                    )
                return jsonify(
                    matiere=results.name,
                    difficulte=difficulty,
                    methode="random_forest",
                    confiance_pct=round(confidence, 1),
                    confiance_avertissement=confidence_warning,
                    source_donnees=Path(DATASET_PATH).name if uses_csv else "ontologie RDF",
                    indicateurs=indicators,
                )

        difficulty, method = estimate_difficulty(results, indicators, config)
        if difficulty is None:
            return jsonify(
                error="Indicateurs insuffisants pour estimer la difficulté.",
                matiere=results.name,
                indicateurs=indicators,
            ), 422

        return jsonify(
            matiere=results.name,
            difficulte=difficulty,
            methode=method,
            avertissement="Estimation par règles à partir des données réelles disponibles ; ce résultat n'est pas issu d'un modèle ML entraîné.",
            source_donnees=Path(DATASET_PATH).name if uses_csv else "ontologie RDF",
            indicateurs=indicators,
        )
    except Exception:
        current_app.logger.exception("Erreur lors de la prédiction de difficulté")
        return jsonify(error="Erreur interne lors de la prédiction de difficulté."), 500


def statistics_mean(values):
    return sum(values) / len(values)


def statistics_stdev_population(values):
    mean = statistics_mean(values)
    return math.sqrt(sum((value - mean) ** 2 for value in values) / len(values))
