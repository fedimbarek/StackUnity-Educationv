"""Entraîne et évalue le classifieur Random Forest à partir des notes de data.csv."""
import math
import os
from pathlib import Path
import tempfile

import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split

from prediction import (
    DIFFICULTY_LABELS,
    FEATURE_COLUMNS,
    MODEL_PATH,
    difficulty_config,
    prepare_training_dataset_from_csv,
)


def train_and_save(dataset, model_path=MODEL_PATH, config=None):
    config = config or difficulty_config()
    if dataset.empty:
        raise ValueError("Aucune matière ne possède assez de résultats réels pour l'entraînement.")

    class_counts = dataset["difficulte"].value_counts()
    minimum_class_samples = max(config.min_class_samples, 3)
    missing = {
        label: int(class_counts.get(label, 0))
        for label in DIFFICULTY_LABELS
        if class_counts.get(label, 0) < minimum_class_samples
    }
    if missing:
        details = ", ".join(f"{label}: {count}/{minimum_class_samples}" for label, count in missing.items())
        raise ValueError(f"Exemples insuffisants par classe ({details}). Aucun modèle n'a été sauvegardé.")

    features = dataset.loc[:, list(FEATURE_COLUMNS)]
    labels = dataset["difficulte"]
    test_size = max(len(DIFFICULTY_LABELS), math.ceil(len(dataset) * 0.2))
    if len(dataset) - test_size < len(DIFFICULTY_LABELS):
        raise ValueError("Dataset trop petit pour séparer entraînement et test stratifiés.")

    x_train, x_test, y_train, y_test = train_test_split(
        features,
        labels,
        test_size=test_size,
        random_state=42,
        stratify=labels,
    )
    train_class_counts = y_train.value_counts()
    if any(train_class_counts.get(label, 0) < 2 for label in DIFFICULTY_LABELS):
        raise ValueError("Le jeu d'entraînement doit conserver au moins deux matières par classe.")
    model = RandomForestClassifier(
        n_estimators=200,
        random_state=42,
        class_weight="balanced",
    )
    model.fit(x_train, y_train)
    predictions = model.predict(x_test)
    metrics = {
        "accuracy": float(accuracy_score(y_test, predictions)),
        "precision_macro": float(precision_score(y_test, predictions, average="macro", zero_division=0)),
        "recall_macro": float(recall_score(y_test, predictions, average="macro", zero_division=0)),
        "f1_macro": float(f1_score(y_test, predictions, average="macro", zero_division=0)),
    }
    artifact = {
        "model": model,
        "features": list(FEATURE_COLUMNS),
        "classes": list(DIFFICULTY_LABELS),
        "metrics": metrics,
        "thresholds": {
            "passing_score": config.passing_score,
            "easy_min_success_rate": config.easy_min_success_rate,
            "hard_max_success_rate": config.hard_max_success_rate,
        },
        "training_subjects": int(len(x_train)),
        "test_subjects": int(len(x_test)),
        "dataset_subjects": int(len(dataset)),
        "training_source": "CSV",
        "confidence_calibrated": False,
        "training_matter_ids": sorted(
            str(value) for value in dataset.loc[x_train.index, "matiere_id"]
        ),
        "test_matter_ids": sorted(
            str(value) for value in dataset.loc[x_test.index, "matiere_id"]
        ),
    }

    model_path = Path(model_path)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=model_path.parent, suffix=".tmp", delete=False) as temporary:
        temporary_path = Path(temporary.name)
    try:
        joblib.dump(artifact, temporary_path)
        os.replace(temporary_path, model_path)
    finally:
        temporary_path.unlink(missing_ok=True)
    return artifact


def main():
    config = difficulty_config()
    try:
        dataset = prepare_training_dataset_from_csv(config=config)
        artifact = train_and_save(dataset, config=config)
    except (OSError, ValueError, ImportError) as exc:
        print(f"Entraînement annulé : {exc}")
        return 1

    print(f"Modèle enregistré dans {MODEL_PATH}")
    print(f"Matières : {len(dataset)} ; entraînement : {artifact['training_subjects']} ; test : {artifact['test_subjects']}")
    for metric, value in artifact["metrics"].items():
        print(f"{metric}: {value:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
