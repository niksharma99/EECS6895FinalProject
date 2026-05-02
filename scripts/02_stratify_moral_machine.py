"""
Stratified subsample of Moral Machine scenarios down to 80 across 7 dimensions.

Reads:  data/raw/moral_machine/scenarios_seed42.jsonl  (210 records)
Writes: data/interim/moral_machine_80.jsonl           (80 records)

Allocation: 80 / 7 = 11.43 → 3 dims get 12 each, 4 dims get 11 each (12*3 + 11*4 = 80).
The 3 dims granted 12 are chosen deterministically from sorted dim names so the
subsample is reproducible.

Run from repo root:
    python scripts/02_stratify_moral_machine.py
"""

import json
import random
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
IN_PATH = REPO_ROOT / "data" / "raw" / "moral_machine" / "scenarios_seed42.jsonl"
OUT_PATH = REPO_ROOT / "data" / "interim" / "moral_machine_80.jsonl"

PRIMARY_DIMENSIONS = [
    "species", "social_value", "gender", "age",
    "fitness", "utilitarianism", "random",
]
TARGET_TOTAL = 80
SAMPLE_SEED = 4242


def per_dim_quota(total: int, dims: list[str]) -> dict[str, int]:
    """Distribute `total` across `dims` as evenly as possible.

    With total=80 and 7 dims: floor=11, remainder=3, so the first 3 dims (alphabetical)
    get 12, the rest get 11.
    """
    n = len(dims)
    base, extra = divmod(total, n)
    quotas = {}
    for i, dim in enumerate(sorted(dims)):
        quotas[dim] = base + (1 if i < extra else 0)
    return quotas


def main():
    random.seed(SAMPLE_SEED)

    by_dim: dict[str, list[dict]] = defaultdict(list)
    with IN_PATH.open() as f:
        for line in f:
            r = json.loads(line)
            by_dim[r["scenario_info"]["scenario_dimension"]].append(r)

    quotas = per_dim_quota(TARGET_TOTAL, PRIMARY_DIMENSIONS)

    selected: list[dict] = []
    for dim in PRIMARY_DIMENSIONS:
        pool = by_dim.get(dim, [])
        k = quotas[dim]
        if len(pool) < k:
            raise RuntimeError(f"Not enough scenarios for dim={dim}: have {len(pool)}, need {k}")
        selected.extend(random.sample(pool, k))

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w") as f:
        for r in selected:
            f.write(json.dumps(r) + "\n")

    print(f"Wrote {len(selected)} scenarios → {OUT_PATH.relative_to(REPO_ROOT)}")
    print("Per-dimension counts:")
    for dim in PRIMARY_DIMENSIONS:
        print(f"  {dim:>15s}: {quotas[dim]}")


if __name__ == "__main__":
    main()
