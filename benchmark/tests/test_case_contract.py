import json
import tempfile
import unittest
from pathlib import Path

from benchmark.case_contract import build_case_request, load_case_request, request_form_data


class CaseContractTests(unittest.TestCase):
    def test_form_data_matches_ui_fields(self):
        request = build_case_request(
            "Oferta suficientemente detallada",
            [{"id": "c1", "label": "Python", "priority": "required"}],
            categoria="tecnologia",
            strictness="normal",
            balance=0.5,
        )
        form = request_form_data(request)
        self.assertEqual(form["job_description"], request["job_description"])
        self.assertEqual(form["categoria"], "tecnologia")
        self.assertEqual(form["stack"], "")
        self.assertEqual(form["balance"], "0.5")
        self.assertEqual(json.loads(form["criteria_json"]), request["criteria"])

    def test_request_json_is_preferred_over_legacy_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            request = build_case_request("Oferta desde request", [], balance=0.25)
            (root / "request.json").write_text(json.dumps(request), encoding="utf-8")
            (root / "offer.txt").write_text("Oferta antigua", encoding="utf-8")
            (root / "criteria.json").write_text("[]", encoding="utf-8")
            loaded = load_case_request(root, {})
        self.assertEqual(loaded["job_description"], "Oferta desde request")
        self.assertEqual(loaded["balance"], 0.25)

    def test_invalid_balance_is_rejected(self):
        with self.assertRaises(ValueError):
            build_case_request("Oferta", [], balance=1.5)

    def test_explicit_missing_request_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(FileNotFoundError):
                load_case_request(root, {}, root / "missing.json")


if __name__ == "__main__":
    unittest.main()
