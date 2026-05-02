"""
Assemble the final unified dataset from per-source `*_unified.jsonl` slices.

Reads:  data/interim/*_unified.jsonl   (any number of per-source slices)
Writes: data/base_scenarios.jsonl

Validation (asserted before writing):
    - every record has a `scenario_id` field
    - `scenario_id` is unique across the whole concatenation
    - every record carries `source`, `task_format`, `base_text`, `options`,
      `primary_dimension`, `ground_truth_majority`, `cultural_cluster`,
      `attributes`, `metadata`

This is the single source of truth for `data/base_scenarios.jsonl` —
per-source unify scripts (`03_*`, `06_*`, `09_*`, …) write to interim only.

Run from repo root:
    python scripts/10_assemble_base_scenarios.py
"""

import json
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
INTERIM_DIR = REPO_ROOT / "data" / "interim"
OUT_PATH = REPO_ROOT / "data" / "base_scenarios.jsonl"

REQUIRED_FIELDS = (
    "scenario_id", "source", "task_format", "base_text", "options",
    "attributes", "primary_dimension", "ground_truth_majority",
    "cultural_cluster", "metadata",
)

ALLOWED_SOURCES = {"moral_machine", "scruples", "ethics_deontology", "ethics_justice"}
ALLOWED_TASK_FORMATS = {"binary_dilemma", "unary_judgment", "narrative_judgment"}
MAX_BASE_TEXT_CHARS = 8000


def main():
    slices = sorted(INTERIM_DIR.glob("*_unified.jsonl"))
    if not slices:
        raise SystemExit(f"No *_unified.jsonl files found in {INTERIM_DIR}")

    all_records: list[dict] = []
    per_slice_counts: dict[str, int] = {}

    for path in slices:
        with path.open() as f:
            recs = [json.loads(line) for line in f]
        per_slice_counts[path.name] = len(recs)
        all_records.extend(recs)

    # Validation: required fields
    for r in all_records:
        missing = [f for f in REQUIRED_FIELDS if f not in r]
        if missing:
            raise ValueError(f"Record {r.get('scenario_id', '<no id>')} missing fields: {missing}")

    # Validation: unique scenario_id
    ids = [r["scenario_id"] for r in all_records]
    dupes = [sid for sid, n in Counter(ids).items() if n > 1]
    if dupes:
        raise ValueError(f"Duplicate scenario_id values: {dupes}")

    # Validation: source enum
    bad_source = [r["scenario_id"] for r in all_records if r["source"] not in ALLOWED_SOURCES]
    if bad_source:
        raise ValueError(f"Records with source not in {ALLOWED_SOURCES}: {bad_source[:5]}...")

    # Validation: task_format enum
    bad_tf = [r["scenario_id"] for r in all_records if r["task_format"] not in ALLOWED_TASK_FORMATS]
    if bad_tf:
        raise ValueError(f"Records with task_format not in {ALLOWED_TASK_FORMATS}: {bad_tf[:5]}...")

    # Validation: ground_truth_majority is in options or null
    bad_gt = []
    for r in all_records:
        gt = r["ground_truth_majority"]
        if gt is None:
            continue
        if gt not in r["options"]:
            bad_gt.append(r["scenario_id"])
    if bad_gt:
        raise ValueError(f"Records with ground_truth_majority not in options: {bad_gt[:5]}...")

    # Validation: base_text non-empty and within length cap
    bad_text = []
    for r in all_records:
        bt = r["base_text"]
        if not bt or len(bt) >= MAX_BASE_TEXT_CHARS:
            bad_text.append((r["scenario_id"], len(bt) if bt else 0))
    if bad_text:
        raise ValueError(f"Records with empty or oversize base_text: {bad_text[:5]}...")

    # Write
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w") as f:
        for r in all_records:
            f.write(json.dumps(r) + "\n")

    # Summary
    print(f"Assembled {len(all_records)} records → {OUT_PATH.relative_to(REPO_ROOT)}")
    print("Per-slice counts:")
    for name, n in per_slice_counts.items():
        print(f"  {name:>40s}: {n}")
    by_source = Counter(r["source"] for r in all_records)
    by_task = Counter(r["task_format"] for r in all_records)
    n_null_gt = sum(1 for r in all_records if r["ground_truth_majority"] is None)
    print(f"By source:      {dict(by_source)}")
    print(f"By task_format: {dict(by_task)}")
    print(f"Null ground_truth_majority: {n_null_gt}")


if __name__ == "__main__":
    main()
