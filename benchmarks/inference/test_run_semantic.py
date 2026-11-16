import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import run_semantic as inference
from framework.evaluate import evaluate
from framework.formats import FORMAT, read_json


def options(run_dir, **changes):
    values = dict(run_dir=str(run_dir), base_model="base", entity_adapter="entity",
                  relation_adapter="relation", entity_variant="short_source",
                  variant="short_canonical", short_chars=2400, max_input_tokens=8192,
                  max_new_tokens=4096, batch_size=4, timeout_seconds=None)
    values.update(changes)
    return argparse.Namespace(**values)


class FakeGenerator:
    batch_size = 4
    receipts = {"entities": {"variant": "short_source_complete_windows"},
                "relations": {"variant": "short_canonical"}}
    weight_verification = {}

    def __init__(self):
        self.calls = []

    def generate_many(self, prompts, stage, **kwargs):
        self.calls.extend((stage, prompt) for prompt in prompts)
        failed = len(self.calls) == 3  # The second document's entity stage.
        completion = ("Disease\tAlpha\tAlpha\nSymptom\tbeta\tbeta\n" if stage == "entities" else
                      "Symptom\tbeta\tis_associated_symptom_of\tDisease\tAlpha\tAlpha has beta.\n")
        return [{"completion_text": completion, "trace": {"complete": not failed, "eos_observed": not failed,
                 "budget_exhausted": False, "deadline_exhausted": False}} for _ in prompts]


class InferenceTests(unittest.TestCase):
    def test_batch_reuses_generator_does_not_read_gold_and_keeps_failures(self):
        graph = {"entities": [{"id": "a", "label": "Disease", "name": "Alpha"},
                              {"id": "b", "label": "Symptom", "name": "beta"}],
                 "relations": [{"source": "b", "target": "a", "relation": "is_associated_symptom_of"}]}
        data = {"format": FORMAT, "dataset_id": "test", "kind": "pilot", "tasks": ["graph"],
                "records": [{"id": "one", "text": "Alpha has beta. Alpha has beta.", "graph": graph},
                            {"id": "two", "text": "Alpha has beta.",
                             "graph": {"entities": [{"id": "s", "label": "Disease", "name": "SECRET_GOLD"}],
                                       "relations": []}}]}
        generator = FakeGenerator()
        loads = []

        def load(args):
            loads.append(args.base_model)
            return generator

        with tempfile.TemporaryDirectory() as tmp:
            result = inference.run_benchmark(data, options(Path(tmp) / "run"), generator_factory=load)
            self.assertEqual(loads, ["base"])
            self.assertEqual([row["status"] for row in result["records"]], ["complete", "failed"])
            self.assertEqual(result["tasks"], ["graph", "ner"])
            self.assertNotIn("SECRET_GOLD", json.dumps(generator.calls))
            self.assertNotIn("SECRET_GOLD", json.dumps(result))
            alpha = next(e for e in result["records"][0]["graph"]["entities"] if e["name"] == "Alpha")
            self.assertEqual([m["start"] for m in alpha["mentions"]], [0, 16])
            self.assertEqual(read_json(Path(tmp) / "run" / "predictions.json"), result)
            metrics = evaluate(data, result, ["graph"])
            self.assertEqual(metrics["prediction_status"], {"complete": 1, "failed": 1})
            self.assertEqual(metrics["metrics"]["graph_relation"]["micro"]["tp"], 1)
            self.assertEqual(metrics["metrics"]["graph_entity"]["micro"]["fn"], 1)

    def test_structured_source_runs_without_weights_and_does_not_claim_ner(self):
        data = {"format": FORMAT, "dataset_id": "icd", "kind": "pilot", "tasks": ["graph"],
                "records": [{"id": "icd", "text": '{"title": "Alpha", "code": "QA"}'}]}
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "input.json"
            source.write_text(json.dumps(data), encoding="utf-8")
            run_dir = Path(tmp) / "run"
            subprocess.run([sys.executable, str(Path(inference.__file__)), "--input", str(source),
                            "--run-dir", str(run_dir)], check=True, capture_output=True, text=True)
            result = read_json(run_dir / "predictions.json")
            self.assertEqual(result["records"][0]["status"], "complete")
            self.assertEqual(result["records"][0]["source_type"], "structured_icd")
            self.assertEqual(result["tasks"], ["graph"])
            self.assertEqual(result["ner_unavailable_documents"], ["icd"])

    def test_crlf_protocol_matches_lf_receipts_without_changing_protocol(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            protocol = root / "protocol.py"
            original = b"first\r\nsecond\r\n"
            protocol.write_bytes(original)
            expected = inference.runtime.sha(b"first\nsecond\n")
            for name, variant in (("entity", "short_source_complete_windows"), ("relation", "short_canonical")):
                (root / name).mkdir()
                (root / name / "training_manifest.json").write_text(
                    json.dumps({"protocol_sha256": expected, "variant": variant}), encoding="utf-8")
            args = options(root / "run", entity_adapter=str(root / "entity"), relation_adapter=str(root / "relation"))
            previous = inference.runtime.protocol_digest

            def make_generator(*args, **kwargs):
                self.assertEqual(inference.runtime.protocol_digest(), expected)
                return FakeGenerator()

            with patch.object(inference.protocol, "__file__", str(protocol)), \
                 patch.object(inference.runtime, "SemanticGenerator", side_effect=make_generator):
                inference.load_generator(args)
            self.assertIs(inference.runtime.protocol_digest, previous)
            self.assertEqual(protocol.read_bytes(), original)

            # A different protocol is not treated as merely a line-ending change.
            protocol.write_bytes(b"changed\r\nsecond\r\n")
            def reject_mismatch(*args, **kwargs):
                self.assertNotEqual(inference.runtime.protocol_digest(), expected)
                raise ValueError("Semantic protocol differs from the training receipt")
            with patch.object(inference.protocol, "__file__", str(protocol)), \
                 patch.object(inference.runtime, "SemanticGenerator", side_effect=reject_mismatch):
                with self.assertRaisesRegex(ValueError, "protocol differs"):
                    inference.load_generator(args)
            self.assertIs(inference.runtime.protocol_digest, previous)

            (root / "relation" / "training_manifest.json").write_text(
                json.dumps({"protocol_sha256": expected, "variant": "full_source"}), encoding="utf-8")
            with patch.object(inference.runtime, "SemanticGenerator") as load:
                with self.assertRaisesRegex(ValueError, "Relation adapter was trained"):
                    inference.load_generator(args)
                load.assert_not_called()


if __name__ == "__main__":
    unittest.main()
