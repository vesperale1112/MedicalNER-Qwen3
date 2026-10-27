"""Embed the selected articles, Excel schema and local UI into one offline page."""

import base64
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[3]
UI_DIR = Path(__file__).resolve().parent
WORKBOOK_PATH = ROOT / "schemas/v3.1.0/schema1026.xlsx"
LEGACY_WORKBOOK_PATH = ROOT / "schemas/v3.0.0/final_schema.xlsx"
SELECTION_PATH = ROOT / "benchmarks/datasets/kg_pilot_20/kg_article_selection_20.json"
SUPPLEMENT_PATH = ROOT / "benchmarks/datasets/kg_pilot_20/kg_article_supplement_v3.1.0.json"
OUTPUT_PATH = ROOT / "benchmarks/datasets/kg_pilot_20/pages/kg_annotation_20.html"
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def read_workbook(path):
    sheets = []
    with ZipFile(path) as archive:
        strings = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            strings = [
                "".join(t.text or "" for t in entry.findall(".//m:t", NS))
                for entry in root
            ]
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        targets = {item.attrib["Id"]: item.attrib["Target"] for item in relationships}
        for sheet in workbook.find("m:sheets", NS):
            relationship_id = sheet.attrib[
                "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
            ]
            target = targets[relationship_id]
            target = target.lstrip("/") if target.startswith("/") else "xl/" + target
            worksheet = ET.fromstring(archive.read(target))
            rows = []
            for row in worksheet.findall("m:sheetData/m:row", NS):
                cells = {}
                for cell in row.findall("m:c", NS):
                    value_node = cell.find("m:v", NS)
                    value = value_node.text or "" if value_node is not None else ""
                    if cell.attrib.get("t") == "s":
                        value = strings[int(value)]
                    elif cell.attrib.get("t") == "inlineStr":
                        value = "".join(t.text or "" for t in cell.findall(".//m:t", NS))
                    if value:
                        column = re.sub(r"\d", "", cell.attrib["r"])
                        cells[column] = value
                if cells:
                    rows.append({"row": int(row.attrib["r"]), "cells": cells})
            sheets.append({"name": sheet.attrib["name"], "rows": rows})
    return sheets


def parse_schema(path, legacy=False):
    sheets = read_workbook(path)
    node_sheet, relation_sheet = sheets[:2]
    nodes = []
    for row in node_sheet["rows"][1:]:
        cells = row["cells"]
        # The new dimension row uses English commas, including one inside parentheses.
        properties = re.split(r"、|,\s*(?![^()]*\))", cells.get("C", ""))
        nodes.append({"label": cells["A"], "name": cells["B"],
                      "description": cells.get("D", ""), "properties": properties,
                      "row": row["row"], "deprecated": False})
    aliases = {"TreatmentPlan": "Treatment Plan", "Communication": "Communication Strategy"}
    relations = []
    for row in relation_sheet["rows"][1:]:
        cells = row["cells"]
        target_text = cells.get("D", "").strip()
        targets = json.loads(target_text.replace("，", ",")) if target_text.startswith("[") else []
        property_match = re.match(r"改为属性\s*(.+)", target_text)
        source = cells.get("I") or cells["A"]
        relations.append({
            "key": ("row_" if legacy else "v3_1_row_") + str(row["row"]),
            "row": row["row"], "source_original": cells["A"],
            "source": aliases.get(source, source), "relation": cells["B"],
            "name": cells.get("C", ""), "target_text": target_text, "targets": targets,
            "property": property_match.group(1).strip() if property_match else "",
            "status": cells.get("F", ""), "confidence": cells.get("E", ""),
            "note": cells.get("H", ""), "rename_suggestion": cells.get("J", ""),
            "version": "3.0.0" if legacy else "3.1.0", "legacy": legacy,
        })
    for relation in relations:
        if relation["property"]:
            node = next(item for item in nodes if item["label"] == relation["source"])
            if relation["property"] not in node["properties"]:
                node["properties"].append(relation["property"])
    return nodes, relations, sheets


def build_schema():
    nodes, relations, sheets = parse_schema(WORKBOOK_PATH)
    old_nodes, old_relations, old_sheets = parse_schema(LEGACY_WORKBOOK_PATH, legacy=True)
    by_label = {node["label"]: node for node in nodes}
    for old in old_nodes:
        if old["label"] not in by_label:
            old["deprecated"] = True
            nodes.append(old)
            by_label[old["label"]] = old
        node = by_label[old["label"]]
        node["legacy_properties"] = [p for p in old["properties"] if p not in node["properties"]]
    for old in old_relations:
        current_targets = {target for rule in relations
                           if rule["source"] == old["source"] and rule["relation"] == old["relation"]
                           for target in rule["targets"]}
        old["deprecated_targets"] = [target for target in old["targets"] if target not in current_targets]
        old["deprecated"] = bool(old["deprecated_targets"]) or not old["targets"]
    return {
        "version": "3.1.0", "source": str(WORKBOOK_PATH.relative_to(ROOT)),
        "legacy_source": str(LEGACY_WORKBOOK_PATH.relative_to(ROOT)),
        "nodes": nodes, "relations": relations + old_relations,
        "sheets": sheets, "legacy_sheets": old_sheets,
        "workbook_base64": base64.b64encode(WORKBOOK_PATH.read_bytes()).decode("ascii"),
        "interpretation": {
            "relations": "以 v3.1.0 关系表的 Source、Relation、Target 为准；保留 Relation 原名。",
            "sources": "TreatmentPlan 统一为 Treatment Plan；Communication 统一为 Communication Strategy，与节点表一致。",
            "legacy": "旧实体、属性和关系保留供导入及修订；新版不再允许的类型或端点组合标为已弃用，不自动改写语义。",
        },
    }


def main():
    articles = []
    for path, batch in [(SELECTION_PATH, "original"), (SUPPLEMENT_PATH, "supplement")]:
        selection = json.loads(path.read_text(encoding="utf-8"))
        for record in selection["records"]:
            article = {key: record[key] for key in
                       ("index", "source", "disease_codes", "doi", "title", "abstract", "topic")}
            articles.append({**article, "batch": batch})
    data = {"dataset_id": "medicalner-manual-kg-20-final-schema",
            "articles": articles, "schema": build_schema()}
    template = (UI_DIR / "index.template.html").read_text(encoding="utf-8")
    embedded_data = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
    page = template.replace("__APP_CSS__", (UI_DIR / "styles.css").read_text(encoding="utf-8"))
    page = page.replace("__APP_DATA__", embedded_data)
    page = page.replace("__APP_JS__", (UI_DIR / "app.js").read_text(encoding="utf-8"))
    OUTPUT_PATH.write_text(page, encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT_PATH), "articles": len(articles),
                      "node_types": len(data["schema"]["nodes"]),
                      "current_relation_rows": sum(not r["legacy"] for r in data["schema"]["relations"]),
                      "bytes": OUTPUT_PATH.stat().st_size}, ensure_ascii=False))


if __name__ == "__main__":
    main()
