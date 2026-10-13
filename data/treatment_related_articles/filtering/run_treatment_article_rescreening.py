#!/usr/bin/env python3
"""Apply a mental-health domain gate to valid first-pass KEEP/REVIEW articles."""

from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterator

import run_gpt56_luna_article_screening as base


STAGE = "mental-health-domain-rescreen-v2"
DEFAULT_PROMPT = base.REPO_ROOT / "schemas/treatment_article_mental_health_rescreen_prompt.md"
DEFAULT_CHECKPOINT = base.SCRIPT_DIR / "treatment_article_rescreen_checkpoint.jsonl"
DEFAULT_OUTPUT = base.SCRIPT_DIR / "treatment_article_rescreen.json"
PROMPT_SEPARATOR = "<!-- ABSTRACT_REVIEW -->"


@dataclass(frozen=True)
class PhaseState:
    valid: bool
    decision: str | None
    offset: int


def load_first_pass(path: Path) -> dict[int, dict[str, Any]]:
    """Keep the last attempt, including failures; load its candidates by offset later."""
    latest = {}
    with path.open("rb") as handle:
        next_offset = 0
        for line in handle:
            offset = next_offset
            next_offset += len(line)
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("record_type") != "attempt":
                continue
            output = row.get("output") or {}
            latest[row["index"]] = {
                "valid_output": row.get("valid_output") is True,
                "decision": output.get("decision"),
                "model": row.get("model"),
                "schema_version": output.get("schema_version"),
                "offset": offset,
            }
    return latest


def select_candidates(first_pass, review_file, max_samples):
    review_indices = None
    if review_file is not None:
        reviews = json.loads(review_file.read_text(encoding="utf-8"))["reviews"]
        review_indices = {row["article_index"] for row in reviews}
    selected = {
        index: row for index, row in sorted(first_pass.items())
        if row["valid_output"] and row["decision"] in {"KEEP", "REVIEW"}
        and (review_indices is None or index in review_indices)
    }
    if max_samples is not None:
        selected = dict(list(selected.items())[:max_samples])
    return selected


def iter_selected_articles(path: Path, indices: list[int]) -> Iterator[dict[str, Any]]:
    if len(indices) <= 100:
        for index in indices:
            yield from base.iter_article_range(path, index, index + 1)
    elif indices:
        wanted = set(indices)
        for record in base.iter_article_range(path, indices[0], indices[-1] + 1):
            if record["index"] in wanted:
                yield record


def load_prompts(path: Path) -> dict[str, str]:
    candidate, abstract = path.read_text(encoding="utf-8").split(PROMPT_SEPARATOR)
    if not candidate.strip() or not abstract.strip():
        raise ValueError("Both candidate and abstract prompts are required")
    return {"candidate": candidate.strip(), "abstract": abstract.strip()}


def parse_json(content: str) -> dict[str, Any]:
    text = content.strip()
    fence = re.fullmatch(r"\x60{3}(?:json)?\s*\n(.*?)\n\s*\x60{3}", text, re.DOTALL | re.IGNORECASE)
    if fence:
        text = fence.group(1)
    output, strict = base.parse_response(text)
    if not strict:
        raise ValueError("Unexpected text outside JSON")
    return output


def validate_abstract_review(review):
    errors = []
    if set(review) != {"decision", "reason"}:
        errors.append("abstract review must have exactly decision and reason")
    if review.get("decision") not in {"KEEP", "REVIEW", "DROP"}:
        errors.append("abstract review only allows KEEP, REVIEW, or DROP")
    if not isinstance(review.get("reason"), str) or not review["reason"].strip():
        errors.append("reason must be a non-empty string")
    return errors


def validate_candidate_review(review, source_output):
    errors = []
    if set(review) != {"decision", "candidate_kind", "candidate_index", "reason"}:
        errors.append("candidate review must have exactly four required fields")
    if not isinstance(review.get("reason"), str) or not review["reason"].strip():
        errors.append("reason must be a non-empty string")
    decision = review.get("decision")
    kind, index = review.get("candidate_kind"), review.get("candidate_index")
    if decision == "KEEP":
        key = {"relation": "candidate_relations", "property": "candidate_properties"}.get(
            kind if isinstance(kind, str) else ""
        )
        items = source_output.get(key, []) if key else []
        if not key or type(index) is not int or not 0 <= index < len(items):
            errors.append("KEEP must select one existing candidate by kind and zero-based index")
    elif decision == "READ_ABSTRACT":
        if kind is not None or index is not None:
            errors.append("READ_ABSTRACT must have null candidate_kind and candidate_index")
    else:
        errors.append("candidate review only allows KEEP or READ_ABSTRACT")
    return errors


def retained_output(review, source_output):
    if review["decision"] == "READ_ABSTRACT":
        return {"decision": "READ_ABSTRACT", "reason": review["reason"]}
    key = {"relation": "candidate_relations", "property": "candidate_properties"}[review["candidate_kind"]]
    return {
        "decision": "KEEP",
        "reason": review["reason"],
        "candidate_kind": review["candidate_kind"],
        "candidate_index": review["candidate_index"],
        "source_schema_version": source_output["schema_version"],
        "candidate": source_output[key][review["candidate_index"]],
    }


def request_phase(client, model, phase, prompt, record, original, source_output):
    attempt = {
        "record_type": "attempt", "index": record["index"], "stage": STAGE, "phase": phase,
        "model": model, "source": record.get("source"),
        "original_decision": original["decision"], "original_model": original["model"],
        "original_schema_version": original["schema_version"],
        "attempt_started_at": base.utc_now(), "status": "request_failed",
        "valid_output": False, "request_performed": False,
    }
    if phase == "candidate" and not any(
        source_output.get(key) for key in ("candidate_relations", "candidate_properties")
    ):
        return {
            **attempt, "status": "completed", "valid_output": True,
            "attempt_finished_at": base.utc_now(),
            "output": {"decision": "READ_ABSTRACT", "reason": "首轮没有候选事实，读取摘要。"},
            "usage": {},
        }
    if phase == "candidate":
        payload = {
            "title": record["title"],
            "source_schema_version": source_output["schema_version"],
            "candidate_relations": source_output.get("candidate_relations", []),
            "candidate_properties": source_output.get("candidate_properties", []),
        }
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ]
    else:
        messages = base.request_messages(prompt, record)
    try:
        attempt["request_performed"] = True
        completion = client.chat.completions.create(model=model, messages=messages)
        if not completion.choices:
            raise ValueError("API response contains no choices")
        choice = completion.choices[0]
        content, reasoning = base.response_message_text(choice.message)
        attempt.update(
            status="parse_failed", response_id=getattr(completion, "id", None),
            response_model=getattr(completion, "model", None),
            finish_reason=getattr(choice, "finish_reason", None),
            raw_response=content, reasoning_content=reasoning, usage=base.usage_dict(completion),
        )
        if phase == "candidate":
            review = parse_json(content)
            errors = validate_candidate_review(review, source_output)
            attempt["candidate_review"] = review
            output = retained_output(review, source_output) if not errors else None
        else:
            output = parse_json(content)
            errors = validate_abstract_review(output)
        if attempt["finish_reason"] in {"length", "content_filter"}:
            errors.append(f"incomplete response: {attempt['finish_reason']}")
        attempt.update(
            output=output, validation_errors=errors, valid_output=not errors,
            status="completed" if not errors else "completed_with_validation_errors",
        )
    except Exception as exc:
        attempt.update(error_type=type(exc).__name__, error=str(exc))
    attempt["attempt_finished_at"] = base.utc_now()
    return attempt


def load_checkpoint(path: Path, total_records: int) -> dict[tuple[int, str], PhaseState]:
    if not path.exists():
        return {}
    states = {}
    with path.open("rb") as handle:
        metadata = json.loads(handle.readline())
        if metadata.get("stage") != STAGE or metadata.get("total_records") != total_records:
            raise ValueError("Checkpoint does not match this strategy/articles file; use a separate path")
        while True:
            offset = handle.tell()
            line = handle.readline()
            if not line:
                break
            if not line.strip():
                continue
            row = json.loads(line)
            index, phase = row.get("index"), row.get("phase")
            if (row.get("record_type") != "attempt" or phase not in {"candidate", "abstract"}
                    or type(index) is not int or not 0 <= index < total_records):
                raise ValueError(f"Invalid checkpoint record at byte {offset}")
            states[index, phase] = PhaseState(
                row.get("valid_output") is True, (row.get("output") or {}).get("decision"), offset
            )
    return states


def next_phase(index, states, retry_failed):
    candidate = states.get((index, "candidate"))
    if candidate is None:
        return "candidate"
    if not candidate.valid:
        return "candidate" if retry_failed else None
    if candidate.decision == "KEEP":
        return None
    abstract = states.get((index, "abstract"))
    if abstract is None:
        return "abstract"
    if not abstract.valid and retry_failed:
        return "abstract"
    return None


def export_results(checkpoint_path, output_path, selected, states):
    entries, missing, failed, needs_abstract = [], [], [], []
    decisions, transitions, routes = Counter(), Counter(), Counter()
    usage, requests, phase_usage = Counter(), Counter(), {"candidate": Counter(), "abstract": Counter()}
    if checkpoint_path.exists():
        with checkpoint_path.open("rb") as handle:
            # Account for all actual requests, including superseded failed attempts.
            for line in handle:
                row = json.loads(line)
                if row.get("record_type") != "attempt" or row["index"] not in selected:
                    continue
                if row.get("request_performed"):
                    requests[row["phase"]] += 1
                    usage.update(row.get("usage", {}))
                    phase_usage[row["phase"]].update(row.get("usage", {}))
            for index in selected:
                candidate = states.get((index, "candidate"))
                if candidate is None:
                    missing.append(index)
                    continue
                if not candidate.valid:
                    failed.append(index)
                    continue
                phase = "candidate" if candidate.decision == "KEEP" else "abstract"
                state = states.get((index, phase))
                if state is None:
                    needs_abstract.append(index)
                    continue
                if not state.valid:
                    failed.append(index)
                    continue
                handle.seek(state.offset)
                row = json.loads(handle.readline())
                decision = row["output"]["decision"]
                decisions[decision] += 1
                transitions[f"{row['original_decision']}->{decision}"] += 1
                routes[phase] += 1
                entries.append({key: row[key] for key in (
                    "index", "phase", "original_decision", "original_model",
                    "original_schema_version", "output",
                )})
    else:
        missing = list(selected)
    summary = {
        "stage": STAGE, "complete": not missing and not failed and not needs_abstract,
        "selected_records": len(selected), "valid_outputs": len(entries),
        "decision_counts": dict(sorted(decisions.items())), "transitions": dict(sorted(transitions.items())),
        "completed_by_phase": dict(routes),
        "unattempted_indices": missing, "needs_abstract_indices": needs_abstract, "failed_indices": failed,
        "api_requests": dict(requests), "usage": dict(usage),
        "usage_by_phase": {phase: dict(counts) for phase, counts in phase_usage.items()},
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(output_path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump({**summary, "records": entries}, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    temporary.replace(output_path)
    return summary


def run(args: argparse.Namespace, client_factory: Callable[[int, str], Any] | None = None):
    if args.workers <= 0 or (args.max_samples is not None and args.max_samples <= 0):
        raise ValueError("--workers and --max-samples must be positive")
    input_paths = {path.resolve() for path in (
        args.articles, args.first_pass, args.system_prompt,
        base.DEFAULT_CHECKPOINT_PATH, base.DEFAULT_OUTPUT_PATH,
    )}
    if args.review_file:
        input_paths.add(args.review_file.resolve())
    if args.checkpoint.resolve() in input_paths or args.output.resolve() in input_paths:
        raise ValueError("Rescreen outputs must not overwrite input or first-pass files")
    if args.checkpoint.resolve() == args.output.resolve():
        raise ValueError("--checkpoint and --output must be different files")

    first_pass = load_first_pass(args.first_pass)
    selected = select_candidates(first_pass, args.review_file, args.max_samples)
    if not selected:
        raise ValueError("No valid first-pass KEEP/REVIEW articles match the selection")
    total_records = base.article_record_count(args.articles)
    if min(selected) < 0 or max(selected) >= total_records:
        raise ValueError("First-pass indices are outside the articles file")
    prompts = load_prompts(args.system_prompt)
    states = load_checkpoint(args.checkpoint, total_records)
    pending = {
        index: phase for index in selected
        if (phase := next_phase(index, states, args.retry_failed)) is not None
    }
    plan = {
        "model": args.model, "api_base": args.api_base,
        "first_pass_records": len(first_pass),
        "first_pass_valid_decisions": dict(Counter(
            row["decision"] for row in first_pass.values() if row["valid_output"]
        )),
        "selected_records": len(selected), "pending_articles": len(pending),
        "next_phases": dict(Counter(pending.values())),
        "max_requests": sum(2 if phase == "candidate" else 1 for phase in pending.values()),
        "workers": args.workers, "automatic_retries": 0,
        "checkpoint": str(args.checkpoint), "output": str(args.output),
    }
    print(json.dumps(plan, ensure_ascii=False, indent=2), flush=True)
    if args.preview:
        return {"plan": plan}

    if pending:
        resolved_key = os.getenv("XI_AI_API_KEY", "").strip() or base.api_key.strip()
        if not resolved_key and client_factory is None:
            raise ValueError("Set XI_AI_API_KEY for the configured service")
        if client_factory is None:
            from openai import OpenAI

            def client_factory(worker_id, key):
                return OpenAI(api_key=key, base_url=args.api_base, timeout=600.0, max_retries=0)

        if not args.checkpoint.exists():
            base.create_checkpoint(args.checkpoint, {
                "record_type": "run_metadata", "stage": STAGE, "total_records": total_records,
                "articles_file": str(args.articles), "first_pass_file": str(args.first_pass),
                "system_prompt_file": str(args.system_prompt), "prompts": prompts,
                "model": args.model, "api_base": args.api_base, "automatic_retries": 0,
            })
        worker_count = min(args.workers, len(pending))
        clients = [client_factory(worker, resolved_key) for worker in range(worker_count)]
        records = iter_selected_articles(args.articles, list(pending))
        finished_articles = 0
        try:
            with ThreadPoolExecutor(max_workers=worker_count) as pool, args.checkpoint.open(
                "a", encoding="utf-8"
            ) as checkpoint, args.first_pass.open("rb") as first_handle:
                futures = {}

                def submit(worker, phase, record, original, source_output):
                    future = pool.submit(
                        request_phase, clients[worker], args.model, phase, prompts[phase],
                        record, original, source_output,
                    )
                    futures[future] = (worker, phase, record, original)

                def submit_next(worker):
                    record = next(records, None)
                    if record is None:
                        return
                    original = selected[record["index"]]
                    phase = pending[record["index"]]
                    source_output = None
                    if phase == "candidate":
                        first_handle.seek(original["offset"])
                        source_output = json.loads(first_handle.readline())["output"]
                    submit(worker, phase, record, original, source_output)

                for worker in range(worker_count):
                    submit_next(worker)
                while futures:
                    done, _ = wait(futures, return_when=FIRST_COMPLETED)
                    for future in done:
                        worker, phase, record, original = futures.pop(future)
                        attempt = future.result()
                        base.write_jsonl_record(checkpoint, attempt)
                        decision = (attempt.get("output") or {}).get("decision", "-")
                        print(
                            f"index={attempt['index']} phase={phase} {attempt['status']} {decision}",
                            flush=True,
                        )
                        if phase == "candidate" and attempt["valid_output"] and decision == "READ_ABSTRACT":
                            submit(worker, "abstract", record, original, None)
                        else:
                            finished_articles += 1
                            print(f"Articles finished: {finished_articles}/{len(pending)}", flush=True)
                            submit_next(worker)
        finally:
            for client in clients:
                client.close()
        states = load_checkpoint(args.checkpoint, total_records)
    summary = export_results(args.checkpoint, args.output, selected, states)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    return {"plan": plan, "summary": summary}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, required=True)
    parser.add_argument("--first-pass", type=Path, default=base.DEFAULT_CHECKPOINT_PATH,
                        help="Original JSONL checkpoint; the last attempt per index is authoritative")
    parser.add_argument("--review-file", type=Path, help="Restrict to article indices in a human-review export")
    parser.add_argument("--max-samples", type=int, help="Limit eligible articles after filtering, in index order")
    parser.add_argument("--preview", action="store_true", help="Show plan; no writes or API requests")
    parser.add_argument("--retry-failed", action="store_true", help="Retry only the failed phase")
    parser.add_argument("--articles", type=Path, default=base.DEFAULT_ARTICLES_PATH)
    parser.add_argument("--system-prompt", type=Path, default=DEFAULT_PROMPT)
    parser.add_argument("--model", default="gpt-6-luna")
    parser.add_argument("--api-base", default=base.api_base)
    parser.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args(argv)


def main():
    try:
        result = run(parse_args())
    except Exception as exc:
        raise SystemExit(f"Rescreening failed: {type(exc).__name__}: {exc}") from exc
    if "summary" in result and not result["summary"]["complete"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
