from copy import deepcopy
import argparse
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from framework.evaluate import evaluate
from framework.formats import FORMAT, import_mdiec, import_project, read_json
from framework.review import sample_evidence, summarize_evidence
from framework.semantic import run_semantic, semantic_mentions


def annotated_document():
    return {
        "id": "d1", "text": "Alpha A Beta.", "status": "complete",
        "graph": {
            "entities": [
                {"id": "x", "label": "Disease", "name": "Alpha", "concept_id": "C:1",
                 "mentions": [{"id": "m1", "section": "text", "start": 0, "end": 5, "text": "Alpha"}]},
                {"id": "y", "label": "Drug", "name": "Beta", "concept_id": "C:2",
                 "mentions": [{"id": "m1", "section": "text", "start": 8, "end": 12, "text": "Beta"}]},
            ],
            "relations": [{"source": "x", "target": "y", "relation": "treated_by"}],
        },
    }


def dataset(documents, kind="gold", tasks=None):
    return {"format": FORMAT, "dataset_id": "sample", "kind": kind,
            "tasks": tasks or ["graph", "ner", "nel", "m_re", "c_re"], "records": documents}


def micro(result, metric):
    return result["metrics"][metric]["micro"]


class BenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)

    def test_four_layers_distinguish_span_surface_and_concept(self):
        gold = annotated_document()
        pred = deepcopy(gold)
        pred["graph"]["entities"][0]["mentions"][0].update(start=6, end=7, text="A")
        result = evaluate(dataset([gold]), dataset([pred], "prediction"), ["ner", "nel", "m_re", "c_re"])
        self.assertEqual([micro(result, "ner")[k] for k in ("tp", "fp", "fn")], [1, 1, 1])
        self.assertEqual([micro(result, "nel")[k] for k in ("tp", "fp", "fn")], [1, 1, 1])
        self.assertEqual([micro(result, "m_re")[k] for k in ("tp", "fp", "fn")], [0, 1, 1])
        self.assertEqual([micro(result, "c_re")[k] for k in ("tp", "fp", "fn")], [1, 0, 0])

    def test_relation_direction_and_type_are_not_partial_credit(self):
        gold = annotated_document()
        pred = deepcopy(gold)
        pred["graph"]["relations"][0].update(source="y", target="x")
        result = evaluate(dataset([gold]), dataset([pred], "prediction"), ["graph", "m_re", "c_re"])
        for metric in ("graph_relation", "m_re", "c_re"):
            self.assertEqual([micro(result, metric)[k] for k in ("tp", "fp", "fn")], [0, 1, 1])
        self.assertEqual(result["metrics"]["c_re"]["macro_f1"], 0)

    def test_deduplicates_within_each_document_and_counts_no_relation_documents(self):
        gold = annotated_document()
        pred = deepcopy(gold)
        pred["graph"]["relations"] *= 2
        gold2, pred2 = deepcopy(gold), deepcopy(pred)
        gold2["id"] = pred2["id"] = "d2"
        pred2["graph"]["relations"] = []
        empty = {"id": "d3", "text": "No findings.", "graph": {"entities": [], "relations": []}}
        result = evaluate(dataset([gold, gold2, empty]), dataset([pred, pred2, empty], "prediction"), ["graph"])
        self.assertEqual(result["documents"], 3)
        self.assertEqual([micro(result, "graph_relation")[k] for k in ("tp", "fp", "fn")], [1, 0, 1])

    def test_unavailable_fields_cannot_be_silently_claimed_as_scores(self):
        gold = annotated_document()
        pred = deepcopy(gold)
        gold["graph"]["entities"][0].pop("concept_id")
        with self.assertRaisesRegex(ValueError, "concept ID"):
            evaluate(dataset([gold]), dataset([pred], "prediction"), ["nel"])
        with self.assertRaisesRegex(ValueError, "prediction tasks"):
            evaluate(dataset([annotated_document()]), dataset([pred], "prediction", ["graph"]), ["ner"])
        with self.assertRaisesRegex(ValueError, "reference tasks"):
            evaluate(dataset([gold], tasks=["graph"]), dataset([pred], "prediction"), ["c_re"])

    def test_invalid_prediction_items_count_as_fp_and_reference_remains_fn(self):
        gold = annotated_document()
        pred = deepcopy(gold)
        pred["graph"]["entities"][0]["mentions"][0]["start"] = 1
        pred["graph"]["relations"][0]["target"] = "unknown"
        result = evaluate(dataset([gold]), dataset([pred], "prediction"), ["ner", "m_re"], include_errors=True)
        self.assertEqual([micro(result, "ner")[k] for k in ("tp", "fp", "fn")], [1, 1, 1])
        self.assertEqual([micro(result, "m_re")[k] for k in ("tp", "fp", "fn")], [0, 1, 1])
        self.assertEqual(result["per_document"][0]["metrics"]["m_re"]["false_positives"][0][0], "invalid")

    def test_multiple_mentions_need_an_explicit_relation_endpoint(self):
        gold = annotated_document()
        gold["graph"]["entities"][0]["mentions"].append({"id": "m2", "section": "text", "start": 6, "end": 7, "text": "A"})
        with self.assertRaisesRegex(ValueError, "explicit, valid mention"):
            evaluate(dataset([gold]), dataset([gold], "prediction"), ["m_re"])
        gold["graph"]["relations"][0]["source_mention"] = "m2"
        result = evaluate(dataset([gold]), dataset([deepcopy(gold)], "prediction"), ["m_re"])
        self.assertEqual(micro(result, "m_re")["tp"], 1)

    def test_mention_relation_ignores_location_but_ner_does_not(self):
        gold = annotated_document()
        gold["text"] = "Alpha A Beta. Alpha"
        pred = deepcopy(gold)
        pred["graph"]["entities"][0]["mentions"][0].update(start=14, end=19)
        result = evaluate(dataset([gold]), dataset([pred], "prediction"), ["ner", "m_re"])
        self.assertEqual([micro(result, "ner")[k] for k in ("tp", "fp", "fn")], [1, 1, 1])
        self.assertEqual(micro(result, "m_re")["tp"], 1)

    def test_missing_failed_and_mismatched_inputs(self):
        gold1 = annotated_document()
        gold2 = deepcopy(gold1)
        gold2["id"] = "d2"
        failed = {"id": "d1", "text": gold1["text"], "status": "failed", "graph": gold1["graph"]}
        result = evaluate(dataset([gold1, gold2], "silver"), dataset([failed], "prediction"), ["graph"])
        self.assertEqual(result["reference_kind"], "silver")
        self.assertEqual(result["prediction_status"], {"failed": 1, "missing": 1})
        self.assertEqual([micro(result, "graph_relation")[k] for k in ("tp", "fp", "fn")], [0, 0, 2])
        failed["text"] = "different text"
        with self.assertRaisesRegex(ValueError, "differs from reference"):
            evaluate(dataset([gold1]), dataset([failed], "prediction"), ["graph"])

    def test_project_export_conversion_preserves_only_existing_graph_data(self):
        path = self.path / "project.json"
        path.write_text(json.dumps([{"article_index": 7, "input": "complete", "input_used": "truncated",
                                    "output": {"entities": [{"id": "a", "label": "Disease", "name": "Foo"}], "relations": []},
                                    "success": True}]), encoding="utf-8")
        result = import_project(path, dataset_id="project", kind="silver")
        self.assertEqual(result["tasks"], ["graph"])
        self.assertEqual(result["records"][0]["text"], "truncated")
        self.assertNotIn("mentions", result["records"][0]["graph"]["entities"][0])
        self.assertNotIn("concept_id", result["records"][0]["graph"]["entities"][0])

    def test_mdiec_import_records_source_text_disagreement(self):
        (self.path / "123.txt").write_text("Alpha Beta", encoding="utf-8")
        (self.path / "123.ann").write_text("T1\tdisease 0 5\tALPHA\nT2\tdrug 6 10\tBeta\nR1\ttreats Arg1:T2 Arg2:T1\n", encoding="utf-8")
        result = import_mdiec(self.path, dataset_id="mdiec")
        self.assertEqual(result["tasks"], ["ner", "m_re"])
        self.assertEqual(result["import_issues"][0]["annotation_text"], "ALPHA")
        self.assertEqual(result["records"][0]["graph"]["entities"][0]["mentions"][0]["text"], "Alpha")
        self.assertEqual(micro(evaluate(result, result, ["ner", "m_re"]), "m_re")["tp"], 1)

    def test_real_semantic_entrypoint_structured_and_failed_free_text(self):
        structured = {"id": "structured", "text": json.dumps({"title": "Alpha", "code": "QA"}),
                      "graph": {"entities": [{"id": "private", "label": "Disease", "name": "SECRET_GOLD"}], "relations": []}}
        free_text = {"id": "missing-model", "text": "Alpha has a symptom.", "graph": {"entities": [], "relations": []}}
        result = run_semantic(dataset([structured, free_text]), self.path / "run")
        self.assertEqual([r["status"] for r in result["records"]], ["complete", "failed"])
        self.assertEqual(result["tasks"], ["graph"])
        self.assertNotIn("SECRET_GOLD", json.dumps(result))
        self.assertEqual(read_json(self.path / "run" / "predictions.json"), result)
        self.assertTrue((self.path / "run" / "outputs" / "00001.json.trace.json").exists())

    def test_mentions_come_from_actual_semantic_trace_not_canonical_names(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "agent"))
        import run_semantic_pipeline

        class FakeGenerator:
            batch_size = 2
            receipts = {"entities": {"stage": "entities", "variant": "full_source", "data_sha256": "test"},
                        "relations": {"stage": "relations", "variant": "full_source"}}
            weight_verification = {}

            def __init__(self, *args, **kwargs):
                pass

            def generate_many(self, prompts, stage, **kwargs):
                output = ("Disease\tAlpha\tAlpha\nSymptom\tbeta\tbeta\n" if stage == "entities" else
                          "Symptom\tbeta\tis_associated_symptom_of\tDisease\tAlpha\tAlpha has beta.\n")
                return [{"completion_text": output, "trace": {"complete": True, "eos_observed": True,
                        "budget_exhausted": False, "deadline_exhausted": False}} for _ in prompts]

        source = self.path / "source.txt"
        source.write_text("Alpha has beta. Alpha has beta.", encoding="utf-8")
        args = argparse.Namespace(source_file=str(source), output=str(self.path / "out.json"),
            base_model="base", entity_adapter="entity", relation_adapter="relation", variant="full_source",
            entity_variant="full_source", source_group_id=None, title_source_file=None,
            max_input_tokens=1024, max_new_tokens=1024, batch_size=2, short_chars=2400, timeout_seconds=None)
        envelope, trace, status = run_semantic_pipeline.execute(args, generator_factory=FakeGenerator)
        self.assertEqual(status, 0)
        graph = semantic_mentions(envelope["graph"], trace)
        alpha = next(e for e in graph["entities"] if e["name"] == "Alpha")
        self.assertEqual(len(alpha["mentions"]), 2)
        for mention in alpha["mentions"]:
            self.assertEqual(source.read_text()[mention["start"]:mention["end"]], mention["text"])
        self.assertNotIn("concept_id", alpha)

    def test_manual_evidence_review_keeps_uncertain_and_unreviewed_separate(self):
        doc = annotated_document()
        doc["graph"]["relations"] *= 2
        sheet = sample_evidence(dataset([doc], "prediction"), sample_size=5, seed=42)
        self.assertEqual(sheet["population_relations"], 1)
        self.assertIsNone(summarize_evidence(sheet)["support_rate_among_decided"])
        sheet["records"][0]["verdict"] = "uncertain"
        self.assertEqual(summarize_evidence(sheet)["uncertain"], 1)
        sheet["records"][0]["verdict"] = "supported"
        self.assertEqual(summarize_evidence(sheet)["support_rate_among_decided"], 1.0)


if __name__ == "__.main__":
    unittest.main()
