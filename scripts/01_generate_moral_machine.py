"""
Generate Moral Machine scenarios via kztakemoto/mmllm's generator function.

Writes JSONL of ~200 scenarios to data/raw/moral_machine/scenarios_seed42.jsonl,
covering all 7 primary `scenario_dimension` values with all combinations of the
3 boolean flags (is_in_car, is_interventionism, is_law). Seeded for reproducibility.

Run from repo root:
    python scripts/01_generate_moral_machine.py
"""

import json
import random
import sys
from itertools import product
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
MMLLM_DIR = REPO_ROOT / "scripts" / "third_party" / "mmllm"
OUT_PATH = REPO_ROOT / "data" / "raw" / "moral_machine" / "scenarios_seed42.jsonl"

sys.path.insert(0, str(MMLLM_DIR))
from generate_moral_machine_scenarios import generate_moral_machine_scenarios  # noqa: E402

PRIMARY_DIMENSIONS = [
    "species", "social_value", "gender", "age",
    "fitness", "utilitarianism", "random",
]
FLAG_COMBOS = list(product([True, False], repeat=3))  # (is_in_car, is_interventionism, is_law)
SCENARIOS_PER_DIM = 30  # 7 * 30 = 210 raw scenarios


def main(seed: int = 42, per_dim: int = SCENARIOS_PER_DIM):
    random.seed(seed)
    np.random.seed(seed)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    n_written = 0
    with OUT_PATH.open("w") as f:
        for dim in PRIMARY_DIMENSIONS:
            for i in range(per_dim):
                is_in_car, is_interv, is_law = random.choice(FLAG_COMBOS)
                system_content, user_content, info = generate_moral_machine_scenarios(
                    dim, is_in_car, is_interv, is_law,
                )
                record = {
                    "raw_id": f"mm_raw_{dim}_{i:03d}",
                    "system_content": system_content,
                    "user_content": user_content,
                    "scenario_info": info,
                }
                f.write(json.dumps(record) + "\n")
                n_written += 1

    print(f"Wrote {n_written} scenarios → {OUT_PATH.relative_to(REPO_ROOT)}")
    print(f"Per-dimension count: {per_dim} × {len(PRIMARY_DIMENSIONS)} dims")


if __name__ == "__main__":
    main()
