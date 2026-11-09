"""Run the repository's existing semantic CLI over a benchmark input set."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import subprocess
import sys
import time

from .evaluate import _records
from .formats import FORMAT, read_json, write_json


def semantic_mentions(graph, trace):
    """Attach existing body anchors from the semantic entity-stage trace.

    The parser grounds each generated mention to all matching source positions.
    No location is inferred from the final canonical name. Structured ICD has no
    entity-stage parse and returns None rather than claiming NER coverage.
    """
    parsed = trace.get("result", {}).get("trace", {}).get("entity_parse", {}).get("filtered_entities")
    if not isinstance(parsed, list):
        return None
    by_id = {str(entity["id"]): entity for entity in parsed if isinstance(entity, dict) and "id" in entity}
    output = deepcopy(graph)
    for node in output["entities"]:
        entity = by_id.get(str(node.get("id")))
        if entity is None:
            return None
        anchors = [anchor for anchor in entity.get("mentions", []) if anchor.get("context") == "body"]
        node["mentions"] = [{"id": f"m{i}", "section": "text", "start": anchor["start"],
                             "end": anchor["end"], "text": anchor["text"]}
                            for i, anchor in enumerate(anchors, 1)]
    return output


def run_semantic(dataset, run_dir, *, base_model=None, entity_adapter=None,
                 relation_adapter=None, variant="full_source", entity_variant="full_source",
                 short_chars=2400, timeout_seconds=None):
    """Run one original source per process; the model is reloaded per document.

    This deliberately calls the existing public CLI instead of feeding reference
    graphs or gold entity tables into inference. When the entity-stage trace is
    available, its body anchors also support NER scoring.
    """
    records = _records(dataset, "reference")
    for doc_id, record in records.items():
        if not isinstance(record.get("text"), str) or not record["text"].strip():
            raise ValueError(f"input {doc_id}: a nonempty text field is required")
    directory = Path(run_dir)
    directory.mkdir(parents=True, mode=0o700, exist_ok=False)
    sources = directory / "sources"
    outputs = directory / "outputs"
    sources.mkdir(mode=0o700)
    outputs.mkdir(mode=0o700)
    script = Path(__file__).resolve().parents[2] / "agent" / "run_semantic_pipeline.py"
    result = {"format": FORMAT, "dataset_id": dataset.get("dataset_id"), "kind": "prediction", "tasks": ["graph", "ner"],
              "model": "agent/run_semantic_pipeline.py", "variant": variant,
              "entity_variant": entity_variant, "short_chars": short_chars,
              "model_parameters": {"base_model": base_model, "entity_adapter": entity_adapter,
                                   "relation_adapter": relation_adapter, "variant": variant,
                                   "entity_variant": entity_variant, "short_chars": short_chars,
                                   "timeout_seconds": timeout_seconds},
              "mention_policy": "Entity-stage trace body anchors, including all source occurrences grounded by the existing parser.",
              "ner_unavailable_documents": [], "records": []}
    for i, (doc_id, record) in enumerate(records.items(), start=1):
        source_path, output_path = sources / f"{i:05d}.txt", outputs / f"{i:05d}.json"
        source_path.write_bytes(record["text"].encode("utf-8"))
        cmd = [sys.executable, str(script), "--source-file", str(source_path),
               "--output", str(output_path), "--variant", variant,
               "--entity-variant", entity_variant, "--short-chars", str(short_chars)]
        for key, value in (("--base-model", base_model), ("--entity-adapter", entity_adapter),
                           ("--relation-adapter", relation_adapter), ("--timeout-seconds", timeout_seconds)):
            if value is not None:
                cmd.extend([key, str(value)])
        start = time.monotonic()
        process = subprocess.run(cmd, capture_output=True, text=True)
        elapsed = time.monotonic() - start
        envelope = read_json(output_path) if output_path.exists() else {}
        complete = process.returncode == 0 and envelope.get("status") == "complete"
        graph = envelope.get("graph") if complete else None
        if complete:
            trace_path = output_path.with_name(output_path.name + ".trace.json")
            annotated = semantic_mentions(graph, read_json(trace_path)) if trace_path.exists() else None
            if annotated is None:
                result["ner_unavailable_documents"].append(doc_id)
                result["tasks"] = ["graph"]
            else:
                graph = annotated
        if process.stderr:
            (outputs / f"{i:05d}.stderr.txt").write_text(process.stderr, encoding="utf-8")
        result["records"].append({
            "id": doc_id, "text": record["text"], "status": "complete" if complete else "failed",
            "graph": graph,
            "seconds": elapsed, "exit_code": process.returncode,
            "error": envelope.get("error"), "output_file": str(output_path) if output_path.exists() else None,
        })
        write_json(directory / "predictions.json", result, overwrite=True)
        print(f"[{i}/{len(records)}] {doc_id}: {'complete' if complete else 'failed'}", flush=True)
    return result
