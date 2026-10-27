"""Embed the three students' annotation exports into one offline comparison page."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATASET_DIR = HERE.parents[1] / "datasets/kg_pilot_20"
FILES = [
    "MedicalNER_DHY_20articles_2026-10-22.json",
    "MedicalNER_尤雅_20articles_2026-10-26.json",
    "MedicalNER_标注员_20articles_2026-10-23.json",
]
students = []
for filename in FILES:
    data = json.loads((DATASET_DIR / "annotations" / filename).read_text(encoding="utf-8"))
    students.append({"filename": filename, **data})
payload = json.dumps(students, ensure_ascii=False).replace("<", "\\u003c")
page = (HERE / "index.template.html").read_text(encoding="utf-8")
page = page.replace("/* INLINE_STYLE */", (HERE / "styles.css").read_text(encoding="utf-8"))
page = page.replace("/* INLINE_DATA */", payload)
page = page.replace("/* INLINE_APP */", (HERE / "app.js").read_text(encoding="utf-8"))
output = DATASET_DIR / "pages/MedicalNER_三人知识图谱对照.html"
output.write_text(page, encoding="utf-8")
print(f"Created {output} ({output.stat().st_size:,} bytes)")
