"""Set-based graph and four-layer matching, with explicit reference coverage."""
from __future__ import annotations

from collections import Counter, defaultdict
import unicodedata

from .formats import FORMAT

TASK_METRICS = {
    "graph": ("graph_entity", "graph_relation"),
    "ner": ("ner",), "nel": ("nel",), "m_re": ("m_re",), "c_re": ("c_re",),
}


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _name(value):
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def _prf(counts):
    tp, fp, fn = (counts.get(x, 0) for x in ("tp", "fp", "fn"))
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "support": tp + fn,
            "precision": p, "recall": r, "f1": 2 * p * r / (p + r) if p + r else 0.0}


def _records(data, role):
    if not isinstance(data, dict) or data.get("format") != FORMAT:
        raise ValueError(f"{role}: expected format {FORMAT}")
    rows = data.get("records")
    if not isinstance(rows, list) or (role == "reference" and not rows):
        raise ValueError(f"{role}: records must be a {'nonempty ' if role == 'reference' else ''}list")
    result = {}
    for row in rows:
        if not isinstance(row, dict) or not _text(row.get("id")):
            raise ValueError(f"{role}: each record needs a nonempty string id")
        if row["id"] in result:
            raise ValueError(f"{role}: duplicate record ID {row['id']}")
        result[row["id"]] = row
    return result


def _valid_graph(graph):
    return (isinstance(graph, dict) and isinstance(graph.get("entities"), list)
            and isinstance(graph.get("relations"), list))


def _extract(record, metric, reference):
    """Return unique comparable items. Invalid predictions remain distinct FPs."""
    graph = record["graph"]
    entities, relations = graph["entities"], graph["relations"]
    sections = {"text": record["text"], **record.get("sections", {})}
    id_counts = Counter(str(e.get("id")) for e in entities if isinstance(e, dict) and e.get("id") is not None)
    nodes = {}
    for e in entities:
        if (isinstance(e, dict) and e.get("id") is not None and str(e["id"]).strip()
                and id_counts[str(e["id"])] == 1 and _text(e.get("label")) and _text(e.get("name"))):
            nodes[str(e["id"])] = e
    items = {}

    def invalid(kind, index, detail):
        if reference:
            raise ValueError(f"reference {record['id']} {metric}: {detail}")
        items[("invalid", kind, index)] = ("__invalid__",)

    def checked_mention(m):
        if not isinstance(m, dict):
            return False
        section, a, b, text = m.get("section"), m.get("start"), m.get("end"), m.get("text")
        return (isinstance(section, str) and section in sections
                and type(a) is int and type(b) is int and 0 <= a < b <= len(sections[section])
                and isinstance(text, str) and sections[section][a:b] == text)

    def endpoint_mention(node, mention_id):
        mentions = node.get("mentions", [])
        if not isinstance(mentions, list):
            return None
        if mention_id is None:
            matches = mentions if len(mentions) == 1 else []
        else:
            matches = [m for m in mentions if isinstance(m, dict) and m.get("id") == mention_id]
        return matches[0] if len(matches) == 1 and checked_mention(matches[0]) else None

    if metric in ("graph_entity", "ner", "nel"):
        for i, node in enumerate(entities):
            if not isinstance(node, dict) or nodes.get(str(node.get("id"))) is not node:
                invalid("entity", i, "invalid or duplicate entity ID, label, or name")
                continue
            label = node["label"].strip()
            if metric == "graph_entity":
                items[("ok", label, _name(node["name"]))] = (label,)
                continue
            mentions = node.get("mentions", [])
            if not isinstance(mentions, list) or not mentions:
                invalid("entity", i, "entity has no annotated mention")
                continue
            mention_ids = [m.get("id") for m in mentions if isinstance(m, dict) and m.get("id") is not None]
            if len(mention_ids) != len(set(mention_ids)):
                invalid("entity", i, "mention IDs are duplicated within an entity")
                continue
            for j, mention in enumerate(mentions):
                if not checked_mention(mention):
                    invalid("mention", (i, j), "missing or incorrect mention section, offsets, or source text")
                    continue
                if metric == "nel" and not _text(node.get("concept_id")):
                    invalid("mention", (i, j), "mention has no concept ID")
                    continue
                key = ("ok", mention["section"], mention["start"], mention["end"], mention["text"], label)
                if metric == "nel":
                    key += (node["concept_id"].strip(),)
                items[key] = (label,)
        return items

    for i, edge in enumerate(relations):
        if not isinstance(edge, dict):
            invalid("relation", i, "malformed relation")
            continue
        source = nodes.get(str(edge["source"])) if edge.get("source") is not None else None
        target = nodes.get(str(edge["target"])) if edge.get("target") is not None else None
        relation = edge.get("relation")
        if source is None or target is None or not _text(relation):
            invalid("relation", i, "missing or ambiguous endpoint or relation label")
            continue
        sl, tl, relation = source["label"].strip(), target["label"].strip(), relation.strip()
        category = (sl, relation, tl)
        if metric == "graph_relation":
            key = ("ok", sl, _name(source["name"]), relation, tl, _name(target["name"]))
        elif metric == "m_re":
            sm = endpoint_mention(source, edge.get("source_mention"))
            tm = endpoint_mention(target, edge.get("target_mention"))
            if sm is None or tm is None:
                invalid("relation", i, "relation needs one explicit, valid mention per endpoint")
                continue
            key = ("ok", sl, sm["text"], relation, tl, tm["text"])
        else:
            if not _text(source.get("concept_id")) or not _text(target.get("concept_id")):
                invalid("relation", i, "relation endpoint has no concept ID")
                continue
            key = ("ok", sl, source["concept_id"].strip(), relation, tl, target["concept_id"].strip())
        items[key] = category
    return items


def evaluate(reference, predictions, tasks, *, include_errors=False):
    refs, preds = _records(reference, "reference"), _records(predictions, "prediction")
    if reference.get("kind") not in ("gold", "silver", "pilot"):
        raise ValueError("Reference kind must be gold, silver, or pilot")
    declared = reference.get("tasks", [])
    if not tasks or len(set(tasks)) != len(tasks) or any(task not in TASK_METRICS or task not in declared for task in tasks):
        raise ValueError(f"Requested tasks {tasks} must be declared in reference tasks {declared}")
    pred_tasks = predictions.get("tasks", [])
    if any(task not in pred_tasks for task in tasks):
        raise ValueError(f"Requested tasks {tasks} must be declared in prediction tasks {pred_tasks}")
    extra = set(preds) - set(refs)
    if extra:
        raise ValueError(f"Prediction IDs absent from reference: {sorted(extra)[:10]}")
    metrics = [name for task in tasks for name in TASK_METRICS[task]]
    counters = {name: defaultdict(Counter) for name in metrics}
    documents, failures, unverified = [], Counter(), 0
    for doc_id, ref in refs.items():
        if not isinstance(ref.get("text"), str) or not _valid_graph(ref.get("graph")) or ref.get("status", "complete") != "complete":
            raise ValueError(f"reference {doc_id}: text and complete graph required")
        if not isinstance(ref.get("sections", {}), dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in ref.get("sections", {}).items()):
            raise ValueError(f"reference {doc_id}: sections must map names to strings")
        if "text" in ref.get("sections", {}) and ref["sections"]["text"] != ref["text"]:
            raise ValueError(f"reference {doc_id}: the reserved text section must equal text")
        pred = preds.get(doc_id)
        if pred is None:
            status = "missing"
        elif pred.get("status", "complete") != "complete":
            status = "failed"
        elif not _valid_graph(pred.get("graph")):
            status = "invalid_graph"
        else:
            status = "complete"
        if pred is not None and "text" in pred and pred["text"] != ref["text"]:
            raise ValueError(f"prediction {doc_id}: input text differs from reference")
        if pred is not None and "text" not in pred:
            unverified += 1
        failures[status] += 1
        pred_record = {"id": doc_id, "text": ref["text"], "sections": ref.get("sections", {}),
                       "graph": pred["graph"] if status == "complete" else {"entities": [], "relations": []}}
        row = {"id": doc_id, "prediction_status": status, "metrics": {}}
        for metric in metrics:
            gold = _extract(ref, metric, True)
            guess = _extract(pred_record, metric, False)
            shared, only_pred, only_gold = gold.keys() & guess.keys(), guess.keys() - gold.keys(), gold.keys() - guess.keys()
            for key in shared:
                counters[metric][gold[key]]["tp"] += 1
            for key in only_pred:
                counters[metric][guess[key]]["fp"] += 1
            for key in only_gold:
                counters[metric][gold[key]]["fn"] += 1
            result = _prf({"tp": len(shared), "fp": len(only_pred), "fn": len(only_gold)})
            if include_errors:
                result["false_positives"] = [list(k) for k in sorted(only_pred, key=repr)]
                result["false_negatives"] = [list(k) for k in sorted(only_gold, key=repr)]
            row["metrics"][metric] = result
        documents.append(row)
    summaries = {}
    for metric in metrics:
        categories = counters[metric]
        total = Counter()
        for counts in categories.values():
            total.update(counts)
        per_category = [{"category": list(category), **_prf(counts)}
                        for category, counts in sorted(categories.items())]
        supported = [entry for entry in per_category if entry["support"]]
        summaries[metric] = {"micro": _prf(total),
            "macro_f1": sum(entry["f1"] for entry in supported) / len(supported) if supported else 0.0,
            "macro_categories": len(supported), "per_category": per_category}
    return {"format": FORMAT, "reference_dataset": reference.get("dataset_id"),
            "reference_kind": reference["kind"], "prediction_dataset": predictions.get("dataset_id"),
            "reference_source": reference.get("source"), "reference_provenance": reference.get("provenance"),
            "prediction_source": predictions.get("source"),
            "prediction_model": predictions.get("model"), "prediction_model_parameters": predictions.get("model_parameters"),
            "tasks": tasks, "documents": len(refs), "prediction_status": dict(failures),
            "prediction_input_unverified": unverified,
            "definitions": {
                "graph": "Entity: exact normalized label/name. Relation: directed endpoint label/name and relation. Name normalization is NFKC, casefold and whitespace only; no synonym inference.",
                "ner": "Exact section, start/end character offsets, source text and entity label.",
                "nel": "NER match plus the same supplied concept ID.",
                "m_re": "Directed source mention text/type, relation label, target mention text/type; offsets do not enter the relation key.",
                "c_re": "Directed source concept ID/type, relation label, target concept ID/type.",
                "aggregation": "Deduplicate within each document. Micro sums counts; macro F1 averages categories with reference support. Relation categories are source type, relation, target type. No overlap-merging is applied.",
                "failures": "Missing, failed or invalid graphs count as empty predictions; all reference items remain false negatives. Invalid prediction items count as false positives.",
                "interpretation": "Scores measure agreement with the declared reference, not independent clinical correctness or evidence support."},
            "metrics": summaries, "per_document": documents}
