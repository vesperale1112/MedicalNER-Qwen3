# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

KG LoRA is a pipeline for generating mental-health knowledge graph extraction training data using Gemini, then fine-tuning Qwen3-8B with QLoRA via LLaMA-Factory. The domain is DSM-5 mental disorder records; the KG schema covers 10 entity types (Disease, Symptom, Diagnostic Criteria, etc.) and 22 relation types.

## Setup

**Local environment:**
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill GEMINI_API_KEY for data generation
```

**ModelArts (Huawei Cloud):**
```bash
ENV_PREFIX=/cache/llc/KG bash scripts/setup_modelarts_env.sh
source /home/ma-user/miniconda3/bin/activate /cache/llc/KG
export PYTHONNOUSERSITE=1
```

LLaMA-Factory must be installed separately (`llamafactory-cli` on PATH). Training from committed datasets does not require `GEMINI_API_KEY`.

## Pipeline Commands

All scripts run from the repo root. They source `.env` and set `PYTHONPATH=src`.

```bash
# 1. Generate CoT extraction data (smoke test)
MAX_SAMPLES=3 WORKERS=1 bash scripts/01_generate_cot_data.sh

# 1. Full generation (specific-CoT style)
COT_STYLE=specific WORKERS=4 bash scripts/01_generate_cot_data.sh

# 2. Convert filtered output to LLaMA-Factory ShareGPT format
bash scripts/02_convert_to_llamafactory.sh data/generated/cot_filtered_merged.json kg_cot_specific_614 specific

# 3. Train QLoRA adapter (specific | standard | sft)
PYTHONNOUSERSITE=1 bash scripts/03_train_lora.sh specific

# 4. Compare base vs adapter outputs on eval cases
bash scripts/04_compare_outputs.sh

# End-to-end specific-CoT pipeline (generate + convert + train)
bash scripts/run_specific_pipeline.sh data/raw/mental_disorders_20251125_165535.json
```

## Running Python Modules Directly

Scripts invoke Python modules with `PYTHONPATH=src python3 -m kg_lora.<module>`. To run a module directly:

```bash
PYTHONPATH=src python3 -m kg_lora.generate_cot_data --help
PYTHONPATH=src python3 -m kg_lora.convert_to_llamafactory --help
PYTHONPATH=src python3 -m kg_lora.compare_qwen_outputs --help
PYTHONPATH=src python3 -m kg_lora.analyze_compare_outputs --input <path>
PYTHONPATH=src python3 -m kg_lora.analyze_kg_outputs --input <path>
```

## Architecture

**Data flow:** raw disorder JSON -> Gemini CoT generation -> filtered JSON -> ShareGPT conversion (with think-tag normalization) -> LLaMA-Factory QLoRA training -> adapter evaluation

**`src/kg_lora/` modules:**
- `generate_cot_data.py` — Calls Gemini API (via raw urllib, no SDK) to extract KG triples from medical text. Supports two extraction modes: `single_pass` (truncate long texts) and `chunk_merge` (split into overlapping chunks, merge entities/relations, then run a repair pass). Two CoT prompt styles: `specific` (sample-specific reasoning) and `template` (generic 6-step reasoning). Includes quality filtering that rejects outputs with <3 entities or dangling ("ghost") relations.
- `convert_to_llamafactory.py` — Converts generation output to ShareGPT message format (system/user/assistant turns) and registers the dataset in `data/llamafactory/dataset_info.json`. Normalizes Gemini-style `<thinking>` tags to Qwen3-native `<think>` tags. Can export chunk-level traces as standalone SFT samples.
- `compare_qwen_outputs.py` — Loads base Qwen3-8B and LoRA adapters one at a time (to save GPU memory), runs inference on eval cases, saves per-model output JSONs. Supports 4-bit/8-bit quantization.
- `analyze_compare_outputs.py` / `analyze_kg_outputs.py` — Summary statistics (entity/relation counts, valid JSON ratio) over output files.

**Key conventions:**
- The KG system prompt and schema tables are duplicated across `generate_cot_data.py`, `convert_to_llamafactory.py`, and `compare_qwen_outputs.py` as module-level constants (`SYSTEM_PROMPT`, `HIGH_COVERAGE_REQUIREMENTS`, `COT_TEMPLATE_PROMPT`, `COT_SPECIFIC_PROMPT`). Changes to the schema must be synchronized across all three files.
- **Think tag convention:** Gemini generation uses `<thinking>`/`</thinking>` tags. The conversion step normalizes these to Qwen3-native `<think>`/`</think>` tags via `normalize_qwen_think_tags()`. The training script (`03_train_lora.sh`) validates that no `<thinking>` tags remain in the dataset before launching training.
- Entity deduplication uses `(label, normalized_name)` as the key; relation deduplication uses the full 5-tuple `(source, target, relation_type, relation_name, relation)`.
- All JSON output uses `ensure_ascii=False` and `indent=2`.
- Training configs use `Qwen/Qwen3-8B` (base, not Instruct — the Instruct variant is unavailable on the Huawei HF mirror) with 4-bit QLoRA (bitsandbytes), LoRA rank 8, `lora_target: all`, bf16 compute, cosine LR schedule. CoT configs use `cutoff_len: 16384`; plain SFT uses `cutoff_len: 4096`. Eval and checkpointing run every 10 steps with `load_best_model_at_end: true`.
- The training script sets HF cache paths under `.cache/` by default. Override `KG_CACHE_ROOT` or `HF_HOME` for different disk layouts.

**Environment variables** (see `.env.example`): `GEMINI_API_KEY` (required for generation), `BASE_MODEL`, `SPECIFIC_ADAPTER`, `STANDARD_ADAPTER`, `KG_DATA_PATH`, `KG_OUTPUT_ROOT`, `KG_CACHE_ROOT`.

**Committed data:** Raw source JSON, two generated CoT datasets (0413), and two converted LLaMA-Factory training JSONs are committed. Model weights are not committed.
