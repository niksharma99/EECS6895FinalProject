"""
Phase 3 step 2 — sample 40 ETHICS items: 10 each from
deontology/test, deontology/test_hard, justice/test, justice/test_hard.

Reads:  data/raw/ethics/{subset}_{split}.jsonl  (4 files from script 07)
Writes: data/interim/ethics_40.jsonl

Order of records in output (matches ETHICS_PLAN §4.3 ID allocation):
    0..9   deontology/test       → et_0001..et_0010
    10..19 deontology/test_hard  → et_0011..et_0020
    20..29 justice/test          → et_0021..et_0030
    30..39 justice/test_hard     → et_0031..et_0040

Seeded with random.seed(4242) for parity with Phase 1's sampling.

Run from repo root:
    python scripts/08_filter_ethics.py
"""

import json
import random
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "data" / "raw" / "ethics"
OUT_PATH = REPO_ROOT / "data" / "interim" / "ethics_40.jsonl"

# Order matters — drives ID allocation in script 09.
ORDERED_TARGETS = [
    ("deontology", "test"),
    ("deontology", "test_hard"),
    ("justice",    "test"),
    ("justice",    "test_hard"),
]
PER_SPLIT = 10
SAMPLE_SEED = 4242


def main():
    random.seed(SAMPLE_SEED)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    selected: list[dict] = []
    summary: list[tuple[str, str, int, dict]] = []

    for subset, split in ORDERED_TARGETS:
        src = RAW_DIR / f"{subset}_{split}.jsonl"
        with src.open() as f:
            pool = [json.loads(line) for line in f]
        if len(pool) < PER_SPLIT:
            raise RuntimeError(f"Not enough rows in {src}: have {len(pool)}, need {PER_SPLIT}")
        picked = random.sample(pool, PER_SPLIT)
        # Annotate each record with its origin so script 09 doesn't have to guess.
        for r in picked:
            r["_subset"] = subset
            r["_split"] = split
        selected.extend(picked)
        label_dist = {0: 0, 1: 0}
        for r in picked:
            label_dist[r["label"]] = label_dist.get(r["label"], 0) + 1
        summary.append((subset, split, len(picked), label_dist))

    with OUT_PATH.open("w") as f:
        for r in selected:
            f.write(json.dumps(r) + "\n")

    print(f"Wrote {len(selected)} records → {OUT_PATH.relative_to(REPO_ROOT)}")
    print("Per-split sample:")
    for subset, split, n, dist in summary:
        print(f"  {subset:>10s}/{split:<10s}  n={n}  label_dist={dist}")


if __name__ == "__main__":
    main()
