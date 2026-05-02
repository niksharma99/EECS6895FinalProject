"""
Phase 2 step 3 — remap the 60 Scruples interim records to unified schema.

Reads:  data/interim/scruples_60.jsonl
Writes: data/interim/scruples_60_unified.jsonl

Per the assembler-pattern convention (PLAN §13, 2026-05-02 refactor entry),
this writes a per-source slice. `data/base_scenarios.jsonl` is rebuilt by
re-running `scripts/10_assemble_base_scenarios.py` afterwards.

Schema mapping per SCRUPLES_PLAN §5 with one adjustment confirmed against
the actual mirror schema in script 04:

    binarized_label semantics:
        "WRONG" → author was in the wrong (YTA-like)  → "author_wrong"
        "RIGHT" → author was in the right (NTA-like)  → "other_wrong"

ID allocation per SCRUPLES_PLAN §5.4:
    sc_0001..sc_0012  relationships
    sc_0013..sc_0024  family
    sc_0025..sc_0036  work
    sc_0037..sc_0048  finances
    sc_0049..sc_0060  social

Run from repo root:
    python scripts/06_scruples_to_unified.py
"""

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
IN_PATH = REPO_ROOT / "data" / "interim" / "scruples_60.jsonl"
OUT_PATH = REPO_ROOT / "data" / "interim" / "scruples_60_unified.jsonl"

LABEL_TO_OPTION = {"WRONG": "author_wrong", "RIGHT": "other_wrong"}
FIRST_PERSON_RE = re.compile(r"\b(I|I'm|I've|I'd|I'll|my|me|mine)\b", re.IGNORECASE)


def length_bucket(n: int) -> str:
    if n < 500:
        return "short"
    if n <= 2000:
        return "medium"
    return "long"


def is_first_person(text: str) -> bool:
    head = (text or "")[:200]
    return bool(FIRST_PERSON_RE.search(head))


def consensus_pct(scores: dict) -> float:
    total = scores.get("RIGHT", 0) + scores.get("WRONG", 0)
    if total == 0:
        return 0.0
    return max(scores["RIGHT"], scores["WRONG"]) / total


def to_unified(idx: int, raw: dict) -> dict:
    title = raw.get("title") or ""
    text = raw.get("text") or ""
    base_text = f"{title}\n\n{text}"
    cat = raw["_subset_role"]
    bin_scores = raw.get("binarized_label_scores") or {}
    full_scores = raw.get("label_scores") or {}
    action_desc = (raw.get("action") or {}).get("description")

    return {
        "scenario_id": f"sc_{idx:04d}",
        "source": "scruples",
        "task_format": "narrative_judgment",
        "base_text": base_text,
        "options": ["author_wrong", "other_wrong"],
        "attributes": {
            "conflict_category": cat,
            "post_length_bucket": length_bucket(len(base_text)),
            "is_first_person": is_first_person(text),
            "post_type": raw.get("post_type"),
        },
        "primary_dimension": cat,
        "ground_truth_majority": LABEL_TO_OPTION[raw["binarized_label"]],
        "cultural_cluster": None,
        "metadata": {
            "source_dataset": "justinphan3110/scruples",
            "source_id": raw.get("id"),
            "source_post_id": raw.get("post_id"),
            "source_split": "test",
            "consensus_pct": round(consensus_pct(bin_scores), 4),
            "binarized_label_scores": bin_scores,
            "label_scores": full_scores,
            "label_raw": raw.get("label"),
            "binarized_label_raw": raw.get("binarized_label"),
            "action_description": action_desc,
            "backfilled": bool(raw.get("_backfilled", False)),
        },
    }


def main():
    with IN_PATH.open() as f:
        rows = [json.loads(line) for line in f]
    if len(rows) != 60:
        raise RuntimeError(f"Expected 60 rows in {IN_PATH}, got {len(rows)}")

    # Reorder by category per §5.4 ID allocation, preserving within-category order
    category_order = ["relationships", "family", "work", "finances", "social"]
    by_cat = {c: [] for c in category_order}
    for r in rows:
        by_cat[r["_subset_role"]].append(r)
    flat = [r for c in category_order for r in by_cat[c]]
    if len(flat) != 60:
        raise RuntimeError("Reordering lost records")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w") as out:
        for i, raw in enumerate(flat, start=1):
            out.write(json.dumps(to_unified(i, raw)) + "\n")

    print(f"Wrote 60 records → {OUT_PATH.relative_to(REPO_ROOT)}")
    # Summary
    counts = {c: 0 for c in category_order}
    gt = {"author_wrong": 0, "other_wrong": 0}
    lens = {"short": 0, "medium": 0, "long": 0}
    with OUT_PATH.open() as f:
        for line in f:
            r = json.loads(line)
            counts[r["primary_dimension"]] += 1
            gt[r["ground_truth_majority"]] += 1
            lens[r["attributes"]["post_length_bucket"]] += 1
    print(f"Per-category: {counts}")
    print(f"Ground truth: {gt}")
    print(f"Length buckets: {lens}")


if __name__ == "__main__":
    main()
