import hashlib
import json
import unittest
from pathlib import Path

from benchmark.experiments.lexical_v2 import score_lexical_criterion


ROOT = Path(__file__).resolve().parents[2]
V1_PATH = ROOT / "benchmark" / "criteria" / "talentclef-development-es-v1.json"
V2_PATH = ROOT / "benchmark" / "criteria" / "talentclef-development-es-v2-experimental.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class TalentClefCriteriaCatalogV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v1 = _load(V1_PATH)
        cls.v2 = _load(V2_PATH)

    def test_catalog_is_complete_and_traceable_to_v1(self):
        self.assertEqual("1.1", self.v2["schema_version"])
        self.assertEqual("2.0-experimental", self.v2["criteria_version"])
        self.assertEqual(10, len(self.v2["jobs"]))
        self.assertEqual(75, sum(len(job["criteria"]) for job in self.v2["jobs"]))

        digest = hashlib.sha256(V1_PATH.read_bytes()).hexdigest()
        self.assertEqual(digest, self.v2["source"]["based_on_sha256"])
        self.assertEqual(
            "benchmark/criteria/talentclef-development-es-v1.json",
            self.v2["source"]["based_on"],
        )

    def test_v2_preserves_query_criterion_priority_and_source_hash_contract(self):
        self.assertEqual(
            [job["query_id"] for job in self.v1["jobs"]],
            [job["query_id"] for job in self.v2["jobs"]],
        )
        for source_job, experimental_job in zip(self.v1["jobs"], self.v2["jobs"]):
            self.assertEqual(source_job["job_text_sha256"], experimental_job["job_text_sha256"])
            self.assertEqual(
                [(row["id"], row["priority"]) for row in source_job["criteria"]],
                [(row["id"], row["priority"]) for row in experimental_job["criteria"]],
            )

    def test_every_scorable_criterion_has_specific_anchors(self):
        for job in self.v2["jobs"]:
            for criterion in job["criteria"]:
                with self.subTest(criterion=criterion["id"]):
                    self.assertIsInstance(criterion["equivalences"], list)
                    self.assertTrue(criterion["equivalences"])
                    self.assertIsInstance(criterion["anchor_terms"], list)
                    if criterion["priority"] == "not_evaluable":
                        self.assertEqual([], criterion["anchor_terms"])
                        self.assertIn("No evaluable", criterion["experimental_note"])
                    else:
                        self.assertTrue(criterion["anchor_terms"])

    def test_failure_criterion_includes_reviewed_fmea_vocabulary(self):
        job = next(job for job in self.v2["jobs"] if job["query_id"] == "96027")
        criterion = next(
            row for row in job["criteria"] if row["id"] == "96027-failure-root-cause"
        )
        normalized = {value.casefold() for value in criterion["equivalences"]}
        self.assertTrue(
            {"fmea", "amfe", "análisis de modo de falla y efectos"}.issubset(normalized)
        )

        result = score_lexical_criterion(
            criterion,
            "Ingeniero de calidad: análisis de modo de falla y efectos (FMEA) de producto.",
        )
        self.assertEqual(1.0, result["score"])
        self.assertTrue(result["exact"])

    def test_business_analysis_words_do_not_confirm_failure_engineering(self):
        job = next(job for job in self.v2["jobs"] if job["query_id"] == "96027")
        criterion = next(
            row for row in job["criteria"] if row["id"] == "96027-failure-root-cause"
        )
        result = score_lexical_criterion(
            criterion,
            "Analista de negocio y BI. Análisis de requisitos, datos y documentación funcional.",
        )
        self.assertLessEqual(result["score"], 0.12)
        self.assertFalse(result["exact"])


if __name__ == "__main__":
    unittest.main()
