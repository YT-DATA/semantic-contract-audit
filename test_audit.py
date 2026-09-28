import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from audit import compare, load, validate

HERE = Path(__file__).resolve().parent


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.base = load(HERE / "examples" / "before.json")

    def test_each_semantic_dimension_is_reported(self):
        alternatives = {"grain": ["customer_id"], "unit": "cents", "currency": "AUD",
                        "aggregation": "avg", "expression": "gross_amount",
                        "filter": "", "timezone": "Australia/Melbourne", "joins": {}}
        for field, value in alternatives.items():
            with self.subTest(field=field):
                changed = copy.deepcopy(self.base)
                changed["metrics"]["net_revenue"][field] = value
                report = compare(self.base, changed)
                self.assertEqual(report["change_count"], 1)
                self.assertEqual(report["changes"][0]["field"], field)

    def test_join_cardinality_is_reported(self):
        changed = copy.deepcopy(self.base)
        changed["metrics"]["net_revenue"]["joins"]["customer"]["cardinality"] = "many_to_many"
        self.assertEqual(compare(self.base, changed)["changes"][0]["field"], "joins")

    def test_reordered_grain_is_unchanged(self):
        changed = copy.deepcopy(self.base)
        changed["metrics"]["net_revenue"]["grain"].reverse()
        self.assertEqual(compare(self.base, changed)["status"], "unchanged")

    def test_added_removed_metrics(self):
        empty = {"schema_version": 1, "metrics": {}}
        self.assertEqual(compare(empty, self.base)["changes"][0]["kind"], "added")
        self.assertEqual(compare(self.base, empty)["changes"][0]["kind"], "removed")

    def test_invalid_inputs_are_rejected(self):
        cases = [None, {}, {"schema_version": True, "metrics": {}}]
        for field, value in (("grain", ["x", "x"]), ("aggregation", "guess"),
                             ("currency", None), ("joins", []), ("extra", "unknown")):
            bad = copy.deepcopy(self.base)
            bad["metrics"]["net_revenue"][field] = value
            cases.append(bad)
        for case in cases:
            with self.subTest(case=case), self.assertRaises(ValueError):
                validate(case)

    def test_duplicate_keys_and_invalid_json_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad.json"
            for content in ('{"metrics": {}, "metrics": {}}', '{', 'NaN'):
                path.write_text(content, encoding="utf-8")
                with self.assertRaises(ValueError):
                    load(path)

    def test_cli_codes_and_deterministic_output(self):
        command = [sys.executable, str(HERE / "audit.py"), str(HERE / "examples/before.json")]
        same = subprocess.run(command + [command[-1]], capture_output=True, text=True)
        self.assertEqual(same.returncode, 0)
        changed = subprocess.run(command + [str(HERE / "examples/after.json")], capture_output=True, text=True)
        self.assertEqual(changed.returncode, 1)
        self.assertEqual(json.loads(changed.stdout)["change_count"], 5)
        again = subprocess.run(command + [str(HERE / "examples/after.json")], capture_output=True, text=True)
        self.assertEqual(changed.stdout, again.stdout)
        missing = subprocess.run(command + [str(HERE / "absent.json")], capture_output=True, text=True)
        self.assertEqual(missing.returncode, 2)
        self.assertIn("error", json.loads(missing.stderr))


if __name__ == "__main__":
    unittest.main()
