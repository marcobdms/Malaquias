import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
import sys

sys.path.insert(0, str(ROOT))

from benchmark.review.generate import (  # noqa: E402
    build_review_package,
    professional_evidence,
    redact_direct_pii,
    write_review_package,
)


class RedactionTests(unittest.TestCase):
    def test_redacts_direct_identifiers(self):
        text = "Ana Pérez ana@example.com +34 600 123 123 linkedin.com/in/ana"
        safe = redact_direct_pii(text, known_name="Ana Pérez")
        self.assertNotIn("Ana Pérez", safe)
        self.assertNotIn("ana@example.com", safe)
        self.assertNotIn("600 123 123", safe)
        self.assertNotIn("linkedin.com", safe)

    def test_professional_evidence_skips_header_and_plain_employer_lines(self):
        text = """Ana Pérez
Calle Privada 10
ana@example.com
EXPERIENCIA PROFESIONAL
Ingeniera de datos
Empresa Secreta, Madrid
2020 - 2024
• Construcción de pipelines con Python y SQL
HABILIDADES
Lenguajes: Python, SQL
"""
        evidence, warnings = professional_evidence(text)
        self.assertEqual([], warnings)
        self.assertIn("pipelines con Python", evidence)
        self.assertIn("Lenguajes: Python, SQL", evidence)
        self.assertNotIn("Ana Pérez", evidence)
        self.assertNotIn("Calle Privada", evidence)
        self.assertNotIn("Empresa Secreta", evidence)


class PackageTests(unittest.TestCase):
    def _fixture(self, root: Path) -> Path:
        source = root / "source"
        (source / "queries").mkdir(parents=True)
        (source / "corpus").mkdir()
        (source / "queries" / "job-1").write_text("Analista Python y SQL", encoding="utf-8")
        for candidate_id, skill in (("a", "Python y SQL"), ("b", "Ventas"), ("c", "Python")):
            (source / "corpus" / candidate_id).write_text(
                f"Persona {candidate_id}\npersona@example.com\nEXPERIENCIA PROFESIONAL\n"
                f"• Experiencia demostrable en {skill}\n",
                encoding="utf-8",
            )
        run = {
            "schema_version": "1.0",
            "run_id": "run-test",
            "inputs": {"source_root": str(source)},
            "queries": [{
                "query_id": "job-1",
                "pool_size": 3,
                "relevant_count": 2,
                "metrics": {"precision@1": 0.0},
                "ranking": [
                    {"candidate_id": "b", "score": 0.9, "semantic_score": 0.8, "relevance": 0},
                    {"candidate_id": "a", "score": 0.8, "keyword_score": 0.7, "relevance": 1},
                    {"candidate_id": "c", "score": 0.7, "relevance": 1,
                     "eligibility_state": "eligible", "required_coverage": 1.0},
                ],
            }],
        }
        run_path = root / "result.json"
        run_path.write_text(json.dumps(run), encoding="utf-8")
        return run_path

    def test_builds_top_and_false_negative_without_original_ids(self):
        with tempfile.TemporaryDirectory() as temp:
            run_path = self._fixture(Path(temp))
            package = build_review_package(run_path, top=1, errors=1)
            candidates = package["queries"][0]["candidates"]
            self.assertEqual(2, len(candidates))
            self.assertEqual("falso_positivo", candidates[0]["benchmark_outcome_at_cutoff"])
            self.assertEqual("falso_negativo", candidates[1]["benchmark_outcome_at_cutoff"])
            serialized = json.dumps(package, ensure_ascii=False)
            self.assertNotIn('"candidate_id"', serialized)
            self.assertNotIn("persona@example.com", serialized)

    def test_writes_deterministic_package_and_empty_form(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            package = build_review_package(self._fixture(root), top=2, errors=0)
            first = root / "first"
            second = root / "second"
            write_review_package(package, first)
            write_review_package(package, second)
            self.assertEqual(
                (first / "review_package.json").read_bytes(),
                (second / "review_package.json").read_bytes(),
            )
            form = json.loads((first / "review_form.json").read_text(encoding="utf-8"))
            self.assertIsNone(form["queries"][0]["candidates"][0]["human_label"])
            self.assertTrue((first / "review.md").is_file())

    def test_preserves_optional_ui_pipeline_diagnostics(self):
        with tempfile.TemporaryDirectory() as temp:
            run_path = self._fixture(Path(temp))
            run = json.loads(run_path.read_text(encoding="utf-8"))
            run["timing"] = {"total_local_seconds": 1.25}
            candidate = run["queries"][0]["ranking"][2]
            candidate["parse_ms"] = 12.5
            candidate["score_components"] = {
                "criteria": [{
                    "id": "c1", "label": "Python", "priority": "required",
                    "score": 0.9, "semantic_score": 0.8, "keyword_score": 1.0,
                    "status": "confirmed",
                }]
            }
            run_path.write_text(json.dumps(run), encoding="utf-8")
            package = build_review_package(run_path, top=3, errors=0)
            candidate = package["queries"][0]["candidates"][2]
            self.assertEqual("eligible", candidate["requirements"]["eligibility_state"])
            self.assertEqual(1.0, candidate["requirements"]["required_coverage"])
            self.assertEqual(1.0, candidate["score_components"]["required_coverage"])
            self.assertEqual("c1", candidate["requirements"]["criteria_scores"][0]["id"])
            self.assertEqual(12.5, candidate["timing"]["parse_ms"])
            self.assertEqual(1.25, package["source_run"]["timing"]["total_local_seconds"])
            self.assertNotIn(
                "Este run no conserva estados ni cobertura de requisitos obligatorios.",
                package["limitations"],
            )

    def test_manual_case_uses_ground_truth_relation_to_find_corpus(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            case = root / "benchmark" / "results" / "manual_cases" / "case-1"
            corpus = root / "benchmark" / "data" / "dataset" / "corpus"
            case.mkdir(parents=True)
            corpus.mkdir(parents=True)
            (case / "offer.txt").write_text("Vacante Python", encoding="utf-8")
            (corpus / "991").write_text(
                "Nombre Privado\nprivado@example.com\nEXPERIENCIA PROFESIONAL\n"
                "• Automatización con Python y SQL\n",
                encoding="utf-8",
            )
            (case / "ground_truth.json").write_text(json.dumps({
                "query_id": "job-991",
                "candidates": [{"filename": "perfil.pdf", "candidate_id": "991", "display_name": "Nombre Privado"}],
            }), encoding="utf-8")
            run_path = case / "local_pipeline_result.json"
            run_path.write_text(json.dumps({
                "case_id": "case-1",
                "ranking": [{
                    "candidate_id": "cv-0", "filename": "perfil.pdf",
                    "expected_relevance": 1, "match_score": 80,
                }],
            }), encoding="utf-8")
            package = build_review_package(run_path, top=1, errors=0)
            query = package["queries"][0]
            candidate = query["candidates"][0]
            self.assertEqual("job-991", query["query_id"])
            self.assertEqual("talentclef_corpus", candidate["evidence_source"])
            self.assertIn("Python y SQL", candidate["professional_evidence"])
            serialized = json.dumps(package, ensure_ascii=False)
            self.assertNotIn("Nombre Privado", serialized)
            self.assertNotIn("privado@example.com", serialized)
            self.assertNotIn('"991"', serialized)

    def test_reads_offer_from_inputs_request_for_grid_run(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run_dir = root / "benchmark" / "results" / "case_grids" / "grid"
            request_dir = root / "benchmark" / "results" / "manual_cases" / "case"
            run_dir.mkdir(parents=True)
            request_dir.mkdir(parents=True)
            request_path = request_dir / "request.criteria-v1.json"
            request_path.write_text(json.dumps({
                "job_description": "Ingeniero de climatización con diseño HVAC"
            }), encoding="utf-8")
            run_path = run_dir / "keyword-1.json"
            run_path.write_text(json.dumps({
                "case_id": "case-grid",
                "inputs": {"request": str(request_path)},
                "ranking": [{
                    "candidate_id": "cv-0", "expected_relevance": 1,
                    "ranking_score": 0.8,
                }],
            }), encoding="utf-8")
            package = build_review_package(run_path, top=1, errors=0)
            offer = package["queries"][0]["offer"]
            self.assertEqual("Ingeniero de climatización con diseño HVAC", offer["text"])
            self.assertEqual([], offer["warnings"])

    def test_rejects_missing_query(self):
        with tempfile.TemporaryDirectory() as temp:
            run_path = self._fixture(Path(temp))
            with self.assertRaisesRegex(ValueError, "No se encontraron"):
                build_review_package(run_path, query_ids=["missing"])


if __name__ == "__main__":
    unittest.main()
