"""Prepare a sample for human evidence review and summarize entered verdicts."""
from __future__ import annotations

from collections import Counter
import random

from .evaluate import _records, _valid_graph


def sample_evidence(predictions, sample_size, seed):
    """Sample unique document-local graph relations; do not judge support."""
    if sample_size <= 0:
        raise ValueError("sample_size must be positive")
    records = _records(predictions, "prediction")
    candidates, skipped, seen = [], 0, set()
    for doc_id, record in records.items():
        graph = record.get("graph")
        if record.get("status", "complete") != "complete" or not _valid_graph(graph):
            continue
        if not isinstance(record.get("text"), str):
            raise ValueError(f"prediction {doc_id}: source text is required for evidence review")
        ids = Counter(str(e["id"]) for e in graph["entities"] if isinstance(e, dict) and "id" in e)
        nodes = {str(e["id"]): e for e in graph["entities"]
                 if isinstance(e, dict) and "id" in e and ids[str(e["id"])] == 1}
        for edge in graph["relations"]:
            if not isinstance(edge, dict):
                skipped += 1
                continue
            source, target = nodes.get(str(edge.get("source"))), nodes.get(str(edge.get("target")))
            relation = edge.get("relation")
            if source is None or target is None or not isinstance(relation, str) or not relation.strip():
                skipped += 1
                continue
            key = (doc_id, str(edge["source"]), relation, str(edge["target"]))
            if key in seen:
                continue
            seen.add(key)
            candidates.append({"document_id": doc_id, "text": record.get("text"),
                "source": {"id": edge["source"], "label": source.get("label"), "name": source.get("name")},
                "relation": relation,
                "target": {"id": edge["target"], "label": target.get("label"), "name": target.get("name")},
                "evidence": edge.get("evidence"), "verdict": None, "reviewer": None, "notes": ""})
    selected = random.Random(seed).sample(candidates, min(sample_size, len(candidates)))
    return {"format": "medicalner-evidence-review-v1", "prediction_dataset": predictions.get("dataset_id"),
            "seed": seed, "population_relations": len(candidates), "excluded_invalid_relations": skipped,
            "requested_sample_size": sample_size, "records": selected}


def summarize_evidence(review):
    """Summarize human verdicts, never infer them from text or the gold graph."""
    if review.get("format") != "medicalner-evidence-review-v1" or not isinstance(review.get("records"), list):
        raise ValueError("Expected an evidence review sheet")
    allowed = {None, "supported", "not_supported", "uncertain"}
    verdicts = [row.get("verdict") for row in review["records"]]
    if any(v not in allowed for v in verdicts):
        raise ValueError("Verdict must be supported, not_supported, uncertain, or null")
    counts = Counter(verdicts)
    decided = counts["supported"] + counts["not_supported"]
    return {"sampled": len(verdicts), "supported": counts["supported"],
            "not_supported": counts["not_supported"], "uncertain": counts["uncertain"],
            "unreviewed": counts[None], "decided": decided,
            "support_rate_among_decided": counts["supported"] / decided if decided else None,
            "definition": "Human support judgments among decided sampled relations; uncertain and unreviewed are excluded. This is not recall, F1, or automatic evidence verification.",
            "prediction_dataset": review.get("prediction_dataset"), "seed": review.get("seed"),
            "population_relations": review.get("population_relations"),
            "excluded_invalid_relations": review.get("excluded_invalid_relations")}
