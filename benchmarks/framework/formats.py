"""Read existing project graphs and the local MDIEC BRAT annotations."""
from __future__ import annotations

import json
from pathlib import Path

FORMAT = "medicalner-benchmark-v1"


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value, *, overwrite=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w" if overwrite else "x", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def import_project(path, *, dataset_id, kind):
    """Convert manual annotation exports or existing model graph exports.

    No offsets, mention strings, concept IDs, or synonyms are inferred from
    entity names. IDs stay scoped to their original document and graph.
    """
    data = read_json(path)
    rows = data.get("records") if isinstance(data, dict) else data
    if not isinstance(rows, list) or not rows:
        raise ValueError("Expected a nonempty list or an export with records")
    records = []
    for row in rows:
        doc_id = row.get("article_index", row.get("index"))
        text = row.get("input_used", row.get("input"))
        if doc_id is None or not isinstance(text, str):
            raise ValueError("Each project record needs its article index and input text")
        graph = row.get("output")
        success = row.get("success", True) is not False and isinstance(graph, dict)
        records.append({
            "id": str(doc_id), "text": text,
            "status": "complete" if success else "failed",
            "graph": graph if success else None,
            "annotation_status": row.get("annotation", {}).get("status"),
            "provenance": {key: row[key] for key in ("source", "doi", "generation_model_requested",
                           "generation_model_used", "generation_method", "generation_date", "schema_reference")
                           if key in row},
        })
    result = {
        "format": FORMAT, "dataset_id": dataset_id, "kind": kind,
        "tasks": ["graph"], "source": str(path), "records": records,
    }
    if isinstance(data, dict):
        result["provenance"] = {key: data[key] for key in ("annotator", "schema", "generation", "exported_at") if key in data}
    return result


def import_mdiec(directory, *, dataset_id):
    """Import the locally released BRAT corpus, preserving its native labels.

    BRAT offsets define the source mention. Disagreements with the auxiliary
    annotation-text field are retained as issues and original_annotation_text.
    """
    directory = Path(directory)
    paths = sorted(directory.glob("*.ann"))
    if not paths:
        raise ValueError(f"No BRAT .ann files found in {directory}")
    records, issues = [], []
    for path in paths:
        text = path.with_suffix(".txt").read_bytes().decode("utf-8")
        entities, relations = [], []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line or line.startswith("#"):
                continue
            fields = line.split("\t")
            if line.startswith("T"):
                label, offsets = fields[1].split(" ", 1)
                if ";" in offsets:
                    raise ValueError(f"Discontinuous BRAT span requires an explicit policy: {path.name} {fields[0]}")
                start, end = map(int, offsets.split())
                if not 0 <= start < end <= len(text):
                    raise ValueError(f"Invalid BRAT offsets: {path.name} {fields[0]}")
                source_text = text[start:end]
                mention = {"id": "m1", "section": "text", "start": start, "end": end, "text": source_text}
                if fields[2] != source_text:
                    mention["original_annotation_text"] = fields[2]
                    issues.append({"document_id": path.stem, "entity_id": fields[0],
                                   "issue": "annotation_text_differs_from_offset_slice",
                                   "annotation_text": fields[2], "offset_slice": source_text})
                entities.append({"id": fields[0], "label": label, "name": source_text, "mentions": [mention]})
            elif line.startswith("R"):
                label, arg1, arg2 = fields[1].split()
                if not arg1.startswith("Arg1:") or not arg2.startswith("Arg2:"):
                    raise ValueError(f"Unexpected BRAT relation arguments: {path.name} {fields[0]}")
                relations.append({"source": arg1[5:], "target": arg2[5:], "relation": label})
            else:
                raise ValueError(f"Unsupported BRAT annotation: {path.name} {fields[0]}")
        records.append({"id": path.stem, "text": text, "status": "complete",
                        "graph": {"entities": entities, "relations": relations}})
    return {"format": FORMAT, "dataset_id": dataset_id, "kind": "gold",
            "tasks": ["ner", "m_re"], "source": str(directory),
            "scope_note": "Public MDIEC BRAT annotations in native labels; no official split is asserted.",
            "import_issues": issues, "records": records}
