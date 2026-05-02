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
