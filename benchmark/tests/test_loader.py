import json
import tempfile
import unittest
from pathlib import Path

from benchmark.loaders import load_dataset


class TalentClefLoaderTests(unittest.TestCase):
    def test_sampled_pool_is_reproducible(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            data = root / "data"
            (data / "queries").mkdir(parents=True)
            (data / "corpus").mkdir()
            (data / "queries" / "q1").write_text("Oferta python", encoding="utf-8")
            for candidate_id in ("c1", "c2", "c3", "c4"):
                (data / "corpus" / candidate_id).write_text(candidate_id, encoding="utf-8")
            (data / "qrels.tsv").write_text("q1\t0\tc1\t1\n", encoding="utf-8")
            manifest = {
                "schema_version": "1.0", "id": "fixture",
                "source": {"type": "talentclef", "root": "data"},
                "pool": {"strategy": "positives_plus_sampled_negatives", "negatives_per_query": 2},
            }
            path = root / "manifest.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            _, first = load_dataset(path, seed=19)
            _, second = load_dataset(path, seed=19)
            self.assertEqual(first.pools[0].candidate_ids, second.pools[0].candidate_ids)
            self.assertEqual(len(first.pools[0].candidate_ids), 3)

    def test_fixed_pool_is_loaded_and_hashed_as_input(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            data = root / "data"
            (data / "queries").mkdir(parents=True)
            (data / "corpus").mkdir()
            (data / "queries" / "q1").write_text("Oferta", encoding="utf-8")
            (data / "corpus" / "c1").write_text("Perfil uno", encoding="utf-8")
            (data / "corpus" / "c2").write_text("Perfil dos", encoding="utf-8")
            (data / "qrels.tsv").write_text("q1\t0\tc1\t1\n", encoding="utf-8")
            fixed = root / "fixed.json"
            fixed.write_text(json.dumps({"queries": {"q1": ["c1", "c2"]}}), encoding="utf-8")
            manifest = {
                "schema_version": "1.0", "id": "fixed-fixture",
                "source": {"type": "talentclef", "root": "data"},
                "pool": {"strategy": "fixed", "ids_file": "fixed.json"},
            }
            path = root / "manifest.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            _, dataset = load_dataset(path, seed=1)
            self.assertEqual(dataset.pools[0].candidate_ids, ("c1", "c2"))
            self.assertIn(fixed.resolve(), dataset.input_paths)


if __name__ == "__main__":
    unittest.main()
