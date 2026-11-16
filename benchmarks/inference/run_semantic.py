#!/usr/bin/env python3
"""Run the selected two-stage semantic model on a benchmark dataset."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agent"))
sys.path.insert(0, str(ROOT / "benchmarks"))

from framework.evaluate import _records
from framework.formats import FORMAT, read_json, write_json
from framework.semantic import semantic_mentions
from kg_agent.source import SourceRouter
import run_semantic_pipeline
from semantic import protocol, runtime


def load_generator(args):
    """Load the existing model once, accepting a CRLF checkout of an LF protocol.

    The original loader compares the protocol file byte-for-byte with the
    training receipt. Normalize only CRLF line endings, and only when both
    receipts match that normalized file. All other loader checks still run.
    """
    original_digest = runtime.protocol_digest
    receipts = [read_json(Path(path) / "training_manifest.json")
                for path in (args.entity_adapter, args.relation_adapter)]
    runtime.entity_strategy_contract(args.entity_variant, receipts[0], short_chars=args.short_chars)
    trained_variant = receipts[1].get("variant")
    if trained_variant != args.variant:
        raise ValueError(f"Relation adapter was trained for {trained_variant!r}, "
                         f"but inference requested {args.variant!r}")
    raw_protocol = Path(protocol.__file__).read_bytes()
    lf_protocol = raw_protocol.replace(b"\r\n", b"\n")
    if lf_protocol != raw_protocol:
        lf_digest = runtime.sha(lf_protocol)
        if all(receipt.get("protocol_sha256") == lf_digest for receipt in receipts):
            runtime.protocol_digest = lambda: lf_digest
    try:
        generator = runtime.SemanticGenerator(
            args.base_model, args.entity_adapter, args.relation_adapter,
            max_input_tokens=args.max_input_tokens, max_new_tokens=args.max_new_tokens,
            batch_size=args.batch_size,
        )
    finally:
        runtime.protocol_digest = original_digest

    return generator


def run_benchmark(dataset, args, *, generator_factory=load_generator):
    records = _records(dataset, "reference")
    for doc_id, record in records.items():
        if not isinstance(record.get("text"), str) or not record["text"].strip():
            raise ValueError(f"input {doc_id}: a nonempty text field is required")

    # Structured ICD records take the existing deterministic route. For any
    # free text, load the two adapters once before creating the run directory.
    directory = Path(args.run_dir)
    if directory.exists():
        raise FileExistsError(f"Run directory already exists: {directory}")
    router = SourceRouter()
    has_free_text = any(router.route(row["text"]).source_type != "structured_icd"
                        for row in records.values())
    generator = None
    if has_free_text:
        if not all((args.base_model, args.entity_adapter, args.relation_adapter)):
            raise ValueError("Free-text input requires --base-model, --entity-adapter and --relation-adapter")
        print("Loading base model and two LoRA adapters...", flush=True)
        generator = generator_factory(args)

    directory.mkdir(parents=True, mode=0o700, exist_ok=False)
    sources, traces = directory / "sources", directory / "traces"
    sources.mkdir(mode=0o700)
    traces.mkdir(mode=0o700)
    result = {
        "format": FORMAT, "dataset_id": dataset.get("dataset_id"), "kind": "prediction",
        "tasks": ["graph", "ner"], "model": "agent/run_semantic_pipeline.py",
        "model_parameters": {
            "base_model": args.base_model, "entity_adapter": args.entity_adapter,
            "relation_adapter": args.relation_adapter, "variant": args.variant,
            "entity_variant": args.entity_variant, "short_chars": args.short_chars,
            "max_input_tokens": args.max_input_tokens, "max_new_tokens": args.max_new_tokens,
            "batch_size": args.batch_size, "timeout_seconds": args.timeout_seconds,
        },
        "mention_policy": "Entity-stage body anchors, including all matching source occurrences.",
        "ner_unavailable_documents": [], "records": [],
    }
    write_json(directory / "predictions.json", result)
    for index, (doc_id, record) in enumerate(records.items(), 1):
        source = sources / f"{index:05d}.txt"
        trace_path = traces / f"{index:05d}.json"
        source.write_bytes(record["text"].encode("utf-8"))
        cli_args = argparse.Namespace(
            source_file=str(source), output=str(directory / f"{index:05d}.json"),
            title_source_file=None, source_group_id=None,
            base_model=args.base_model, entity_adapter=args.entity_adapter,
            relation_adapter=args.relation_adapter, variant=args.variant,
            entity_variant=args.entity_variant, short_chars=args.short_chars,
            max_input_tokens=args.max_input_tokens, max_new_tokens=args.max_new_tokens,
            batch_size=args.batch_size, timeout_seconds=args.timeout_seconds,
        )
        started = time.monotonic()
        envelope, trace, code = run_semantic_pipeline.execute(
            cli_args, generator_factory=lambda *a, **kw: generator)
        write_json(trace_path, trace)
        graph = envelope["graph"] if code == 0 else None
        if code == 0:
            annotated = semantic_mentions(graph, trace)
            if annotated is None:
                result["ner_unavailable_documents"].append(doc_id)
                result["tasks"] = ["graph"]
            else:
                graph = annotated
        result["records"].append({
            "id": doc_id, "text": record["text"],
            "status": "complete" if code == 0 else "failed", "graph": graph,
            "error": envelope.get("error"), "seconds": time.monotonic() - started,
            "source_type": envelope.get("source_type"), "trace_file": str(trace_path),
        })
        write_json(directory / "predictions.json", result, overwrite=True)
        print(f"[{index}/{len(records)}] {doc_id}: {result['records'][-1]['status']}", flush=True)
        if code == 130:
            raise KeyboardInterrupt
    return result


def positive_int(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="medicalner-benchmark-v1 JSON; only each record's text is used")
    parser.add_argument("--run-dir", required=True, help="New directory for predictions, original inputs and traces")
    parser.add_argument("--base-model", help="Local Qwen3-8B base model directory")
    parser.add_argument("--entity-adapter", help="Local semantic entity LoRA directory, including training_manifest.json")
    parser.add_argument("--relation-adapter", help="Local semantic relation LoRA directory, including training_manifest.json")
    parser.add_argument("--entity-variant", choices=runtime.ENTITY_VARIANTS, default="short_source")
    parser.add_argument("--variant", choices=("full_source", "short_source", "short_canonical"), default="short_canonical")
    parser.add_argument("--short-chars", type=positive_int, default=2400)
    parser.add_argument("--max-input-tokens", type=positive_int, default=8192)
    parser.add_argument("--max-new-tokens", type=positive_int, default=4096)
    parser.add_argument("--batch-size", type=positive_int, default=4, help="Maximum windows per model generation batch")
    parser.add_argument("--timeout-seconds", type=float, help="Optional per-document generation deadline")
    args = parser.parse_args(argv)
    if args.short_chars < 32:
        parser.error("--short-chars must be at least 32")
    if args.timeout_seconds is not None and not 0 < args.timeout_seconds < float("inf"):
        parser.error("--timeout-seconds must be finite and positive")
    try:
        run_benchmark(read_json(args.input), args)
    except (ValueError, OSError, RuntimeError, ImportError) as exc:
        parser.exit(1, f"Inference could not start or finish: {exc}\n")


if __name__ == "__main__":
    main()
