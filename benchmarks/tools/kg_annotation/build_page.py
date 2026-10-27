"""Embed the selected articles, Excel schema and local UI into one offline page."""

import base64
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[3]
UI_DIR = Path(__file__).resolve().parent
WORKBOOK_PATH = ROOT / "schemas/v3.0.0/final_schema.xlsx"
SELECTION_PATH = ROOT / "benchmarks/datasets/kg_pilot_20/kg_article_selection_20.json"
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


sheets = read_workbook(WORKBOOK_PATH)
node_sheet = next(sheet for sheet in sheets if sheet["name"] == "节点表new")
relation_sheet = next(sheet for sheet in sheets if sheet["name"] == "关系表new")
nodes = []
for row in node_sheet["rows"][1:]:
    cells = row["cells"]
    nodes.append(
        {
            "label": cells["A"],
            "name": cells["B"],
            "description": cells.get("D", ""),
            "properties": re.split(r"、", cells.get("C", "")),
            "row": row["row"],
        }
    )

relations = []
for row in relation_sheet["rows"][1:]:
    cells = row["cells"]
    target_text = cells.get("D", "").strip()
    targets = json.loads(target_text.replace("，", ",")) if target_text.startswith("[") else []
    property_match = re.match(r"改为属性\s*(.+)", target_text)
    relations.append(
        {
            "key": "row_" + str(row["row"]),
            "row": row["row"],
            "source_original": cells["A"],
            "source": cells.get("I") or cells["A"],
            "relation": cells["B"],
            "name": cells.get("C", ""),
            "target_text": target_text,
            "targets": targets,
            "property": property_match.group(1).strip() if property_match else "",
            "status": cells.get("F", ""),
            "confidence": cells.get("E", ""),
            "note": cells.get("H", ""),
            "rename_suggestion": cells.get("J", ""),
        }
    )

# The workbook's final Target column explicitly converts these rows to properties.
for relation in relations:
    if relation["property"]:
        node = next(item for item in nodes if item["label"] == relation["source"])
        if relation["property"] not in node["properties"]:
            node["properties"].append(relation["property"])

selection = json.loads(SELECTION_PATH.read_text(encoding="utf-8"))
articles = [
    {key: record[key] for key in ("index", "source", "disease_codes", "doi", "title", "abstract", "topic")}
    for record in selection["records"]
]
data = {
    "dataset_id": "medicalner-manual-kg-20-final-schema",
    "articles": articles,
    "schema": {
        "source": "schemas/v3.0.0/final_schema.xlsx",
        "nodes": nodes,
        "relations": relations,
        "sheets": sheets,
        "workbook_base64": base64.b64encode(WORKBOOK_PATH.read_bytes()).decode("ascii"),
        "interpretation": {
            "relations": "按Target（最终推断）列区分关系和属性；有节点类型Target的条目可建关系。",
            "sources": "采用Excel中明确填写的Source修正建议。",
            "names": "保留Relation列原名，不自动采用重命名建议。",
            "status": "保留原表的需复核、暂缓等标记，不据此自动删去有明确Target的关系。",
        },
    },
}

template = (UI_DIR / "index.template.html").read_text(encoding="utf-8")
embedded_data = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
page = template.replace("__APP_CSS__", (UI_DIR / "styles.css").read_text(encoding="utf-8"))
page = page.replace("__APP_DATA__", embedded_data)
page = page.replace("__APP_JS__", (UI_DIR / "app.js").read_text(encoding="utf-8"))
OUTPUT_PATH.write_text(page, encoding="utf-8")
print(
    json.dumps(
        {
            "output": str(OUTPUT_PATH),
            "articles": len(articles),
            "node_types": len(nodes),
            "schema_rows": len(relations),
            "edge_definitions": sum(bool(item["targets"]) for item in relations),
            "bytes": OUTPUT_PATH.stat().st_size,
        },
        ensure_ascii=False,
    )
)
