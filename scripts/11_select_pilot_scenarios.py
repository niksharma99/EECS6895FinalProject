"""
Select a reproducible 30-scenario pilot set for Tier 0 / Tier 1 agent testing.

Reads:  data/base_scenarios.jsonl
Writes: data/pilot/pilot_30_ids.json

Selection target:
    - 10 Moral Machine records, spread across primary dimensions
    - 10 ETHICS records, 5 deontology + 5 justice
    - 10 Scruples records, 2 per conflict category

Run from repo root:
    python scripts/11_select_pilot_scenarios.py
"""

import json
import random
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
IN_PATH = REPO_ROOT / "data" / "base_scenarios.jsonl"
OUT_PATH = REPO_ROOT / "data" / "pilot" / "pilot_30_ids.json"
SEED = 4242


def sample_by_dimension(rows: list[dict], dimensions: list[str], per_dim: int, extra: int = 0) -> list[dict]:
    rng = random.Random(SEED)
    by_dim: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_dim[row["primary_dimension"]].append(row)

    selected: list[dict] = []
    for dim in dimensions:
        pool = by_dim[dim]
        selected.extend(rng.sample(pool, per_dim))

    if extra:
        already = {r["scenario_id"] for r in selected}
        leftovers = [r for dim in dimensions for r in by_dim[dim] if r["scenario_id"] not in already]
        selected.extend(rng.sample(leftovers, extra))

    return selected


def main() -> None:
    rows = [json.loads(line) for line in IN_PATH.open()]

    moral_dims = ["species", "social_value", "gender", "age", "fitness", "utilitarianism", "random"]
    scruples_dims = ["relationships", "family", "work", "finances", "social"]

    moral = [r for r in rows if r["source"] == "moral_machine"]
    ethics_deont = [r for r in rows if r["source"] == "ethics_deontology"]
    ethics_justice = [r for r in rows if r["source"] == "ethics_justice"]
    scruples = [r for r in rows if r["source"] == "scruples"]

    pilot = []
    pilot.extend(sample_by_dimension(moral, moral_dims, per_dim=1, extra=3))
    pilot.extend(random.Random(SEED).sample(ethics_deont, 5))
    pilot.extend(random.Random(SEED + 1).sample(ethics_justice, 5))
    pilot.extend(sample_by_dimension(scruples, scruples_dims, per_dim=2))

    if len(pilot) != 30:
        raise RuntimeError(f"Expected 30 pilot records, got {len(pilot)}")
    ids = [r["scenario_id"] for r in pilot]
    if len(ids) != len(set(ids)):
        raise RuntimeError("Duplicate scenario IDs in pilot set")

    payload = {
        "name": "pilot_30",
        "seed": SEED,
        "description": "Balanced 30-scenario pilot: 10 Moral Machine, 10 ETHICS, 10 Scruples.",
        "scenario_ids": ids,
        "records": [
            {
                "scenario_id": r["scenario_id"],
                "source": r["source"],
                "task_format": r["task_format"],
                "primary_dimension": r["primary_dimension"],
                "ground_truth_majority": r["ground_truth_majority"],
            }
            for r in pilot
        ],
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")

    print(f"Wrote {len(ids)} scenario IDs -> {OUT_PATH.relative_to(REPO_ROOT)}")
    for record in payload["records"]:
        print(
            f"{record['scenario_id']} "
            f"{record['source']} "
            f"{record['primary_dimension']} "
            f"{record['ground_truth_majority']}"
        )


if __name__ == "__main__":
    main()
