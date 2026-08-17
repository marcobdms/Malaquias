import json
import unittest
from pathlib import Path

from benchmark.adjudication.overlay import apply_overlay, evaluate_label_views, validate_overlay


class AdjudicationOverlayTests(unittest.TestCase):
    def setUp(self):
        path = Path("benchmark/adjudication/provisional_external_review.json")
        self.overlay = json.loads(path.read_text(encoding="utf-8"))

    def test_overlay_is_valid_and_explicitly_provisional(self):
        validate_overlay(self.overlay)
        self.assertEqual(self.overlay["status"], "provisional")
        self.assertTrue(all(row["status"] == "provisional" for row in self.overlay["judgments"]))

    def test_original_mapping_is_not_mutated(self):
        original = {"66203": 0, "51488": 1}
        adjudicated = apply_overlay(original, self.overlay, "96027", mode="adjudicated")
        self.assertEqual(original, {"66203": 0, "51488": 1})
        self.assertEqual(adjudicated, {"66203": 0, "51488": 2})

    def test_unknown_aware_excludes_provisional_cases(self):
        original = {"66203": 0, "51488": 1}
        view = apply_overlay(original, self.overlay, "96027", mode="unknown_aware")
        self.assertEqual(view, {"66203": 0, "51488": "unknown"})

    def test_unknown_aware_keeps_provisional_regression_with_unchanged_label(self):
        original = {"66203": 0, "51488": 1}
        view = apply_overlay(original, self.overlay, "96027", mode="unknown_aware")
        self.assertEqual(view["66203"], 0)

    def test_reports_three_metric_views(self):
        original = {"66203": 0, "51488": 1, "56940": 1}
        result = evaluate_label_views(
            ["66203", "51488", "56940"], original, self.overlay, "96027", (1, 3)
        )
        self.assertEqual(set(result), {"original", "provisional_adjudicated", "unknown_aware"})
        self.assertEqual(result["original"]["precision@1"], 0.0)
        self.assertEqual(result["unknown_aware"]["precision@1"], 0.0)


if __name__ == "__main__":
    unittest.main()
