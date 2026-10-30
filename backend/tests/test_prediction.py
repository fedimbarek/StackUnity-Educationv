import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from flask import Flask
from rdflib import Graph, Literal, Namespace, OWL, RDF, RDFS, URIRef, XSD

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import prediction
from auth import make_token
from store import BASE, PREFIXES
from prediction import DifficultyConfig, SubjectResults
from train_model import train_and_save


EX = Namespace(BASE)


def graph_sparql(graph, query, **bind):
    results = graph.query(
        PREFIXES + query,
        initBindings={key: URIRef(value) for key, value in bind.items()},
    )
    return [
        {
            str(key): str(value).split("#")[-1] if str(value).startswith(BASE) else str(value)
            for key, value in row.asdict().items()
        }
        for row in results
    ]


class PredictionTests(unittest.TestCase):
    def setUp(self):
        secret_patch = patch("auth.SECRET", "prediction-test-secret-with-at-least-32-bytes")
        secret_patch.start()
        self.addCleanup(secret_patch.stop)
        self.app = Flask(__name__)
        self.app.logger.disabled = True
        self.app.register_blueprint(prediction.bp)
        self.client = self.app.test_client()
        self.headers = {"Authorization": f"Bearer {make_token('admin')}"}
        self.config = DifficultyConfig(
            passing_score=10,
            easy_min_success_rate=75,
            hard_max_success_rate=40,
            min_prediction_results=2,
            min_training_results=2,
            min_class_samples=3,
        )

    def test_extracts_only_unambiguous_scored_subject_results(self):
        graph = Graph()
        graph.add((EX.Math, RDF.type, OWL.NamedIndividual))
        graph.add((EX.Math, RDF.type, EX.TechnicalSubject))
        graph.add((EX.Math, RDFS.label, Literal("Mathématiques", lang="fr")))
        graph.add((EX.TechnicalSubject, RDFS.subClassOf, EX.Matiere))
        graph.add((EX.Evaluation, RDF.type, OWL.Class))
        graph.add((EX.Evaluation, RDFS.subClassOf, EX.Matiere))
        graph.add((EX.Quiz, RDFS.subClassOf, EX.Evaluation))
        graph.add((EX.QuizResult, RDF.type, EX.Quiz))
        graph.add((EX.QuizResult, EX.score, Literal("12", datatype=XSD.decimal)))
        graph.add((EX.QuizResult, EX.concerneFormation, EX.SingleSubjectCourse))
        graph.add((EX.SingleSubjectCourse, EX.aPourMatiere, EX.Math))
        graph.add((EX.Math, EX.coefficient, Literal("3", datatype=XSD.decimal)))
        graph.add((EX.Math, EX.nombreHeures, Literal("60", datatype=XSD.integer)))
        graph.add((EX.Math, EX.matiereDeveloppe, EX.Algorithms))
        graph.add((EX.SingleSubjectCourse, EX.tauxReussite, Literal("85", datatype=XSD.decimal)))
        graph.add((EX.Learner, EX.passeEvaluation, EX.QuizResult))
        graph.add((EX.SharedResult, RDF.type, EX.Quiz))
        graph.add((EX.SharedResult, EX.score, Literal("15", datatype=XSD.decimal)))
        graph.add((EX.SharedResult, EX.concerneFormation, EX.SingleSubjectCourse))
        graph.add((EX.Learner, EX.passeEvaluation, EX.SharedResult))
        graph.add((EX.SecondLearner, EX.passeEvaluation, EX.SharedResult))

        with patch.object(prediction, "sparql", side_effect=lambda q, **b: graph_sparql(graph, q, **b)):
            result = prediction.get_subject_results("Math")

        self.assertEqual(result.name, "Mathématiques")
        self.assertEqual(result.scores, (12.0,))
        self.assertEqual(result.evaluation_count, 1)
        self.assertEqual(result.learner_scores, (("Learner", 12.0),))
        self.assertEqual(result.ambiguous_evaluation_count, 1)
        self.assertEqual(result.coefficient, 3.0)
        self.assertEqual(result.study_hours, 60.0)
        self.assertEqual(result.competence_count, 1)
        self.assertEqual(result.formation_success_rates, (85.0,))

        graph.add((EX.SingleSubjectCourse, EX.aPourMatiere, EX.OtherSubject))
        with patch.object(prediction, "sparql", side_effect=lambda q, **b: graph_sparql(graph, q, **b)):
            result = prediction.get_subject_results("Math")
        self.assertEqual(result.scores, ())
        self.assertEqual(result.formation_success_rates, ())

    def test_existing_ontology_subject_can_be_estimated_without_student_scores(self):
        results = prediction.get_subject_results("Mathematiques")
        self.assertIsNotNone(results)
        self.assertEqual(results.scores, ())
        self.assertEqual(results.coefficient, 3.0)
        self.assertEqual(results.study_hours, 60.0)
        indicators = prediction.calculate_indicators(results, self.config)
        self.assertEqual(
            prediction.estimate_difficulty(results, indicators, self.config),
            ("Difficile", "regles_charge_pedagogique"),
        )

        app = Flask(__name__)
        app.register_blueprint(prediction.bp)
        with app.test_client() as client:
            with patch.object(
                prediction,
                "load_model",
                side_effect=prediction.ModelNotTrainedError("not trained"),
            ):
                response = client.post(
                    "/api/prediction/difficulte",
                    json={"id": "Mathematiques"},
                    headers=self.headers,
                )
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["difficulte"], "Difficile")
        self.assertEqual(body["methode"], "regles_resultats")
        self.assertEqual(body["source_donnees"], "data.csv")
        self.assertIsNotNone(body["indicateurs"]["moyenne"])
        self.assertEqual(body["indicateurs"]["coefficient"], 4.0)
        self.assertEqual(body["indicateurs"]["nombre_resultats"], 80)

    def test_csv_training_dataset_has_one_row_per_subject_and_three_classes(self):
        dataset = prediction.prepare_training_dataset_from_csv(config=self.config)
        self.assertEqual(len(dataset), 10)
        self.assertEqual(dataset["matiere_id"].nunique(), 10)
        self.assertEqual(dataset["difficulte"].value_counts().to_dict(), {
            "Facile": 4,
            "Moyenne": 3,
            "Difficile": 3,
        })

    def test_csv_prediction_returns_model_score_percentage(self):
        results = SubjectResults("Math", "Mathématiques", (), 0)

        class FakeModel:
            classes_ = ["Difficile", "Facile", "Moyenne"]

            def predict(self, frame):
                return ["Difficile"]

            def predict_proba(self, frame):
                return [[0.85, 0.10, 0.05]]

        artifact = {
            "model": FakeModel(),
            "dataset_subjects": 10,
            "training_matter_ids": ["MAT_005"],
            "test_matter_ids": ["MAT_001", "MAT_002", "MAT_009"],
        }
        with (
            patch.object(prediction, "get_subject_results", return_value=results),
            patch.object(prediction, "difficulty_config", return_value=self.config),
            patch.object(prediction, "load_model", return_value=artifact),
        ):
            response = self.client.post(
                "/api/prediction/difficulte",
                json={"id": "Math"},
                headers=self.headers,
            )
        body = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["methode"], "random_forest")
        self.assertEqual(body["confiance_pct"], 85.0)
        self.assertIn("non calibré", body["confiance_avertissement"])
        self.assertIn("déjà vue à l'entraînement", body["confiance_avertissement"])
        self.assertEqual(body["indicateurs"]["nombre_resultats"], 80)

    def test_midrange_course_load_has_medium_estimated_difficulty(self):
        results = SubjectResults(
            "Databases",
            "Bases de données",
            (),
            0,
            coefficient=2.5,
            study_hours=42,
        )
        indicators = prediction.calculate_indicators(results, self.config)
        self.assertEqual(
            prediction.estimate_difficulty(results, indicators, self.config),
            ("Moyenne", "regles_charge_pedagogique"),
        )

    def test_real_ontology_has_no_linked_student_scores(self):
        results = prediction.get_subject_results("Mathematiques")
        self.assertIsNotNone(results)
        self.assertEqual(results.name, "Mathématiques")
        self.assertEqual(results.scores, ())
        self.assertEqual(results.evaluation_count, 0)

    def test_calculates_statistics_and_handles_no_scores(self):
        results = SubjectResults("Math", "Mathématiques", (8.0, 10.0, 14.0), 3)
        indicators = prediction.calculate_indicators(results, self.config)
        self.assertAlmostEqual(indicators["moyenne"], 32 / 3)
        self.assertEqual(indicators["note_minimale"], 8.0)
        self.assertEqual(indicators["note_maximale"], 14.0)
        self.assertAlmostEqual(indicators["taux_reussite"], 200 / 3)
        self.assertAlmostEqual(indicators["taux_echec"], 100 / 3)
        self.assertAlmostEqual(indicators["ecart_type"], 2.494438257849294)
        self.assertEqual(indicators["nombre_evaluations"], 3)

        empty = prediction.calculate_indicators(SubjectResults("Math", "Mathématiques", (), 0), self.config)
        self.assertIsNone(empty["moyenne"])
        self.assertEqual(empty["nombre_resultats"], 0)

    def test_invalid_and_unknown_subject_http_responses(self):
        response = self.client.post(
            "/api/prediction/difficulte",
            json={},
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 400)

        response = self.client.post(
            "/api/prediction/difficulte",
            json={"id": "bad-id"},
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 400)

        with patch.object(prediction, "get_subject_results", return_value=None):
            response = self.client.post(
                "/api/prediction/difficulte",
                json={"id": "Unknown"},
                headers=self.headers,
            )
        self.assertEqual(response.status_code, 404)

    def test_insufficient_results_return_422_with_indicators(self):
        results = SubjectResults("Math", "Mathématiques", (), 0)
        with (
            patch.object(prediction, "get_subject_results", return_value=results),
            patch.object(prediction, "results_from_csv", return_value=results),
        ):
            response = self.client.post(
                "/api/prediction/difficulte",
                json={"id": "Math"},
                headers=self.headers,
            )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.get_json()["indicateurs"]["nombre_resultats"], 0)

    def test_internal_prediction_error_returns_500(self):
        with patch.object(prediction, "get_subject_results", side_effect=RuntimeError("query failed")):
            response = self.client.post(
                "/api/prediction/difficulte",
                json={"id": "Math"},
                headers=self.headers,
            )
        self.assertEqual(response.status_code, 500)

    def test_predicts_when_model_and_results_are_available(self):
        results = SubjectResults("Math", "Mathématiques", (8.0, 12.0), 2)

        class FakeModel:
            classes_ = ["Difficile", "Facile", "Moyenne"]

            def predict(self, frame):
                self.frame = frame
                return ["Moyenne"]

            def predict_proba(self, frame):
                return [[0.1, 0.1, 0.8]]

        fake_model = FakeModel()
        with (
            patch.object(prediction, "get_subject_results", return_value=results),
            patch.object(prediction, "results_from_csv", return_value=results),
            patch.object(prediction, "difficulty_config", return_value=self.config),
            patch.object(
                prediction,
                "load_model",
                return_value={
                    "model": fake_model,
                    "dataset_subjects": 10,
                    "training_matter_ids": [],
                    "test_matter_ids": [],
                },
            ),
        ):
            response = self.client.post(
                "/api/prediction/difficulte",
                json={"id": "Math"},
                headers=self.headers,
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["difficulte"], "Moyenne")
        self.assertEqual(tuple(fake_model.frame.columns), prediction.FEATURE_COLUMNS)

    def test_random_forest_trains_and_persists_with_stratified_metrics(self):
        config = DifficultyConfig(
            passing_score=10,
            easy_min_success_rate=75,
            hard_max_success_rate=25,
            min_prediction_results=1,
            min_training_results=1,
            min_class_samples=3,
        )
        results = []
        score_sets = {
            "Difficile": (2.0, 3.0, 4.0, 5.0),
            "Moyenne": (8.0, 9.0, 11.0, 12.0),
            "Facile": (15.0, 16.0, 17.0, 18.0),
        }
        for label, scores in score_sets.items():
            for index in range(5):
                results.append(SubjectResults(f"{label}{index}", label, scores, len(scores)))
        dataset = prediction.prepare_training_dataset(results, config)
        self.assertEqual(dataset["difficulte"].value_counts().to_dict(), {
            "Difficile": 5,
            "Moyenne": 5,
            "Facile": 5,
        })

        with tempfile.TemporaryDirectory() as directory:
            model_path = os.path.join(directory, "difficulty_model.pkl")
            artifact = train_and_save(dataset, model_path, config)
            self.assertTrue(os.path.isfile(model_path))
            self.assertEqual(
                set(artifact["metrics"]),
                {"accuracy", "precision_macro", "recall_macro", "f1_macro"},
            )
            self.assertEqual(artifact["test_subjects"], 3)
            self.assertFalse(set(artifact["training_matter_ids"]) & set(artifact["test_matter_ids"]))
            self.assertEqual(len(artifact["training_matter_ids"]), artifact["training_subjects"])
            self.assertEqual(len(artifact["test_matter_ids"]), artifact["test_subjects"])
            with (
                patch.object(prediction, "MODEL_PATH", Path(model_path)),
                patch.object(prediction, "_MODEL_CACHE", {"mtime": None, "artifact": None}),
            ):
                loaded = prediction.load_model()
                self.assertIs(loaded, prediction.load_model())
                self.assertEqual(loaded["features"], list(prediction.FEATURE_COLUMNS))

    def test_training_refuses_missing_classes_without_saving(self):
        dataset = prediction.prepare_training_dataset(
            [SubjectResults(f"Hard{index}", "Hard", (1.0, 2.0), 2) for index in range(2)],
            self.config,
        )
        with tempfile.TemporaryDirectory() as directory:
            model_path = os.path.join(directory, "difficulty_model.pkl")
            with self.assertRaisesRegex(ValueError, "Exemples insuffisants par classe"):
                train_and_save(dataset, model_path, self.config)
            self.assertFalse(os.path.exists(model_path))

    def test_missing_model_falls_back_to_real_result_indicators(self):
        results = SubjectResults("Math", "Mathématiques", (8.0, 12.0), 2)
        with (
            patch.object(prediction, "get_subject_results", return_value=results),
            patch.object(prediction, "results_from_csv", return_value=results),
            patch.object(prediction, "difficulty_config", return_value=self.config),
            patch.object(prediction, "load_model", side_effect=prediction.ModelNotTrainedError("not trained")),
        ):
            response = self.client.post(
                "/api/prediction/difficulte",
                json={"id": "Math"},
                headers=self.headers,
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["methode"], "regles_resultats")
        self.assertEqual(response.get_json()["difficulte"], "Moyenne")


if __name__ == "__main__":
    unittest.main()
