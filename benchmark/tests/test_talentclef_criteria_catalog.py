import hashlib
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = ROOT / "benchmark" / "criteria" / "talentclef-development-es-v1.json"
EXPECTED_QUERY_IDS = {
    "75767",
    "76474",
    "85803",
    "86302",
    "87280",
    "88540",
    "90596",
    "91821",
    "96027",
    "96356",
}
ALLOWED_PRIORITIES = {"required", "important", "preferred", "not_evaluable"}


class TalentClefCriteriaCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))

    def test_catalog_identity_and_query_coverage(self):
        self.assertEqual("1.0", self.catalog["schema_version"])
        self.assertEqual("talentclef-development-es", self.catalog["catalog_id"])
        self.assertEqual("1.0", self.catalog["criteria_version"])
        self.assertEqual("es", self.catalog["language"])

        query_ids = [job["query_id"] for job in self.catalog["jobs"]]
        self.assertEqual(10, len(query_ids))
        self.assertEqual(10, len(set(query_ids)))
        self.assertEqual(EXPECTED_QUERY_IDS, set(query_ids))

    def test_jobs_are_traceable_to_complete_source_queries(self):
        query_root = ROOT / self.catalog["source"]["query_root"]
        self.assertTrue(query_root.is_dir())

        for job in self.catalog["jobs"]:
            with self.subTest(query_id=job["query_id"]):
                source_path = query_root / job["query_id"]
                self.assertTrue(source_path.is_file())
                digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
                self.assertEqual(job["job_text_sha256"], digest)

    def test_each_job_has_well_formed_criteria(self):
        for job in self.catalog["jobs"]:
            with self.subTest(query_id=job["query_id"]):
                self.assertTrue(job["title"].strip())
                criteria = job["criteria"]
                self.assertGreaterEqual(len(criteria), 5)
                self.assertLessEqual(len(criteria), 10)
                criterion_ids = [criterion["id"] for criterion in criteria]
                self.assertEqual(len(criterion_ids), len(set(criterion_ids)))
                self.assertTrue(any(c["priority"] == "required" for c in criteria))

                for criterion in criteria:
                    self.assertTrue(criterion["id"].startswith(f"{job['query_id']}-"))
                    self.assertTrue(criterion["label"].strip())
                    self.assertIn(criterion["priority"], ALLOWED_PRIORITIES)
                    self.assertTrue(criterion["expected_evidence"].strip())

                    equivalences = criterion["equivalences"]
                    self.assertIsInstance(equivalences, list)
                    self.assertGreaterEqual(len(equivalences), 1)
                    self.assertTrue(all(isinstance(value, str) and value.strip() for value in equivalences))
                    normalized = [value.strip().casefold() for value in equivalences]
                    self.assertEqual(len(normalized), len(set(normalized)))
                    self.assertNotIn(criterion["label"].strip().casefold(), normalized)

    def test_catalog_does_not_invent_numeric_year_requirements(self):
        serialized = json.dumps(self.catalog["jobs"], ensure_ascii=False)
        self.assertIsNone(re.search(r"\b\d+\s*años?\b", serialized, flags=re.IGNORECASE))


if __name__ == "__main__":
    unittest.main()
