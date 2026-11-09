#!/usr/bin/env python3
"""Prepare and score medical KG benchmarks without requiring model packages."""
from __future__ import annotations

import argparse
import json

from framework.evaluate import TASK_METRICS, evaluate
from framework.formats import import_mdiec, import_project, read_json, write_json
from framework.review import sample_evidence, summarize_evidence
from framework.semantic import run_semantic


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    project = commands.add_parser("import-project", help="Convert existing project annotations or predictions")
    project.add_argument("--input", required=True)
    project.add_argument("--output", required=True)
    project.add_argument("--dataset-id", required=True)
    project.add_argument("--kind", choices=("gold", "silver", "pilot", "prediction"), required=True)

    mdiec = commands.add_parser("import-mdiec", help="Convert local BRAT files using their native labels")
    mdiec.add_argument("--input-dir", required=True)
    mdiec.add_argument("--output", required=True)
    mdiec.add_argument("--dataset-id", default="mdiec-public-unsplit")

    score = commands.add_parser("evaluate", help="Score predictions against a declared reference")
    score.add_argument("--reference", required=True)
    score.add_argument("--predictions", required=True)
    score.add_argument("--output", required=True)
    score.add_argument("--tasks", nargs="+", choices=tuple(TASK_METRICS), required=True)
    score.add_argument("--include-errors", action="store_true", help="Include item-level false positives and negatives")

    sample = commands.add_parser("sample-evidence", help="Create a random sample for human review")
    sample.add_argument("--predictions", required=True)
    sample.add_argument("--output", required=True)
    sample.add_argument("--size", type=int, required=True)
    sample.add_argument("--seed", type=int, default=42)

    review = commands.add_parser("summarize-evidence", help="Summarize manually entered review verdicts")
    review.add_argument("--input", required=True)
    review.add_argument("--output", required=True)

    infer = commands.add_parser("run-semantic", help="Call the existing semantic CLI once per source")
    infer.add_argument("--input", required=True, help="Benchmark JSON; only record text is sent to inference")
    infer.add_argument("--run-dir", required=True, help="New directory for inputs, outputs, traces and predictions")
    infer.add_argument("--base-model")
    infer.add_argument("--entity-adapter")
    infer.add_argument("--relation-adapter")
    infer.add_argument("--variant", choices=("full_source", "short_source", "short_canonical"), default="full_source")
    infer.add_argument("--entity-variant", choices=("full_source", "short_source"), default="full_source")
    infer.add_argument("--short-chars", type=int, default=2400)
    infer.add_argument("--timeout-seconds", type=float)

    args = parser.parse_args(argv)
    if args.command == "import-project":
        result = import_project(args.input, dataset_id=args.dataset_id, kind=args.kind)
        write_json(args.output, result)
        print(json.dumps({"records": len(result["records"]), "kind": result["kind"], "output": args.output}))
    elif args.command == "import-mdiec":
        result = import_mdiec(args.input_dir, dataset_id=args.dataset_id)
        write_json(args.output, result)
        print(json.dumps({"records": len(result["records"]), "import_issues": len(result["import_issues"]), "output": args.output}))
    elif args.command == "evaluate":
        result = evaluate(read_json(args.reference), read_json(args.predictions), args.tasks,
                          include_errors=args.include_errors)
        write_json(args.output, result)
        print(json.dumps({"documents": result["documents"], "reference_kind": result["reference_kind"],
                          "metrics": {k: v["micro"] for k, v in result["metrics"].items()},
                          "output": args.output}, ensure_ascii=False))
    elif args.command == "sample-evidence":
        result = sample_evidence(read_json(args.predictions), args.size, args.seed)
        write_json(args.output, result)
        print(json.dumps({"sampled": len(result["records"]), "population": result["population_relations"], "output": args.output}))
    elif args.command == "summarize-evidence":
        result = summarize_evidence(read_json(args.input))
        write_json(args.output, result)
        print(json.dumps(result, ensure_ascii=False))
    else:
        run_semantic(read_json(args.input), args.run_dir, base_model=args.base_model,
                     entity_adapter=args.entity_adapter, relation_adapter=args.relation_adapter,
                     variant=args.variant, entity_variant=args.entity_variant,
                     short_chars=args.short_chars, timeout_seconds=args.timeout_seconds)


if __name__ == "__main__":
    main()
