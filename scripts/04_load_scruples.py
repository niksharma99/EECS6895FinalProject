"""
Phase 2 step 1 — load Scruples Anecdotes from one of three mirrors.

Tries mirrors in order until one works:
    1. justinphan3110/scruples       (parquet, modern)
    2. metaeval/scruples              (anecdotes config)
    3. allenai/scruples GitHub        (manual download, last resort)

Writes:
    data/raw/scruples/anecdotes.jsonl   (full split, gitignored)
    data/raw/scruples/inspection.jsonl  (5 representative records, gitignored)

Stop after running this. Inspect the printed `features`, label distribution,
and 5-record dump. Resolve §3.1 / §3.2 / §3.3 of SCRUPLES_PLAN.md before
writing 05_filter_scruples.py.

Run from repo root:
    python scripts/04_load_scruples.py
"""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "data" / "raw" / "scruples"
ANECDOTES_PATH = RAW_DIR / "anecdotes.jsonl"
INSPECTION_PATH = RAW_DIR / "inspection.jsonl"

MIRRORS = [
    ("justinphan3110/scruples", None),
    ("metaeval/scruples",       "anecdotes"),
]


def try_load_hf():
    from datasets import load_dataset
    for repo, config in MIRRORS:
        print(f"\n>>> Trying mirror: {repo}" + (f" (config={config})" if config else ""))
        try:
            ds = load_dataset(repo, config) if config else load_dataset(repo)
            print(f"    SUCCESS — splits: {list(ds.keys())}")
            return repo, config, ds
        except Exception as e:
            print(f"    FAILED — {type(e).__name__}: {str(e)[:200]}")
    return None, None, None


def dump_split(ds_split, n_total: int) -> int:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    n = 0
    with ANECDOTES_PATH.open("w") as f:
        for ex in ds_split:
            f.write(json.dumps(ex, default=str) + "\n")
            n += 1
    return n


def main():
    repo, config, ds = try_load_hf()
    if ds is None:
        raise SystemExit(
            "All HuggingFace mirrors failed. Fall back to allenai/scruples GitHub: "
            "https://github.com/allenai/scruples — manual download required."
        )

    # Pick the largest split (likely 'test' for justinphan, 'anecdotes' may have train/dev/test)
    split_name = max(ds.keys(), key=lambda k: len(ds[k]))
    split = ds[split_name]
    print(f"\nUsing split: {split_name!r} (n={len(split)})")
    print(f"Features: {split.features}")
    print(f"Column names: {split.column_names}")

    # Dump full split
    n = dump_split(split, len(split))
    print(f"\nWrote {n} records → {ANECDOTES_PATH.relative_to(REPO_ROOT)}")

    # Save 5 representative records
    sample = [split[i] for i in range(min(5, len(split)))]
    with INSPECTION_PATH.open("w") as f:
        for ex in sample:
            f.write(json.dumps(ex, default=str) + "\n")
    print(f"Wrote 5 inspection records → {INSPECTION_PATH.relative_to(REPO_ROOT)}")

    # Print first record fully (for §3.3 schema inspection)
    print(f"\n{'=' * 70}")
    print("FIRST RECORD (full):")
    print(json.dumps(split[0], indent=2, default=str)[:3000])
    print(f"{'=' * 70}")

    # Decision-gate signals — §3.1 (vote distribution), §3.2 (categories), §3.3 (schema)
    cols = set(split.column_names)
    print("\nDecision-gate signals:")
    print(f"  §3.1 vote-distribution candidate fields present: "
          f"{sorted(cols & {'label_scores','binarized_label_scores','score','num_upvotes','num_downvotes','vote_distribution','gold_annotations'})}")
    print(f"  §3.2 category-label candidate fields present:    "
          f"{sorted(cols & {'category','subreddit_category','flair','topic','tag'})}")
    print(f"  §3.3 mirror used: {repo}" + (f" (config={config})" if config else ""))


if __name__ == "__main__":
    main()
