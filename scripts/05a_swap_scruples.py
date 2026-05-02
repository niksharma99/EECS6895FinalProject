"""
Phase 2 swap — replace specific Scruples records (by Scruples `id`) with
deterministic replacements drawn from the same category.

This is for demo-content review: e.g. profanity in title or racially-charged
framing. The dropped records remain in the dataset's potential pool — they
just don't appear in the curated 60.

Reads:
    data/raw/scruples/anecdotes.jsonl     (full pool, from script 04)
    data/interim/scruples_60.jsonl        (current 60, from script 05)

Writes:
    data/interim/scruples_60.jsonl        (same 60 with the named IDs swapped)

Replacement policy:
    For each dropped record, find the next eligible item from the *same*
    category that:
      - is not already in the selected 60
      - is not in the BLOCKED set (this run + any historical drops)
      - passes the same filter cascade as script 05 (consensus / length /
        HISTORICAL / category)
    Picked deterministically with random.seed(SAMPLE_SEED + len(blocked))
    so the same set of drops always yields the same replacements.

After running:
    python scripts/06_scruples_to_unified.py
    python scripts/10_assemble_base_scenarios.py

Run from repo root:
    python scripts/05a_swap_scruples.py
"""

import json
import random
import re
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_PATH = REPO_ROOT / "data" / "raw" / "scruples" / "anecdotes.jsonl"
INTERIM_PATH = REPO_ROOT / "data" / "interim" / "scruples_60.jsonl"

# Scruples internal `id` values to drop. (Not post_id — these are the
# UUID-like ids that appear as `metadata.source_id` in the unified record.)
BLOCKED_IDS = {
    "MclHDEd3FXocEzuaDq4743fNmGfXqbrY",  # sc_0023 — "AITA for calling my mother a bitch?" (profanity in title)
    "YB98GHivhGotbjIpIitCfdxvhYBAZMQz",  # sc_0032 — "AITA I Called a Racist the N-Word..." (slur in title)
}

# Mirror of script 05 thresholds + regex — keep in sync.
CONSENSUS_THRESHOLD = 0.70
MAX_BASE_TEXT_CHARS = 8000
SAMPLE_SEED = 4242

CATEGORY_PATTERNS = [
    ("relationships", re.compile(
        r"\b(boyfriend|girlfriend|husband|wife|partner|dating|fianc[eé]|spouse|"
        r"ex[- ]?(boyfriend|girlfriend|husband|wife)|relationship)\b", re.IGNORECASE)),
    ("family",        re.compile(
        r"\b(mom|dad|mother|father|sister|brother|aunt|uncle|cousin|parent|"
        r"grand(ma|pa|mother|father)|sibling|in[- ]?law|son|daughter|child|kid|baby)\b", re.IGNORECASE)),
    ("work",          re.compile(
        r"\b(boss|coworker|colleague|job|workplace|office|manager|employee|"
        r"career|salary|fired|quit|client|intern)\b", re.IGNORECASE)),
    ("finances",      re.compile(
        r"\b(money|rent|bill|paying|paid|cost|expensive|owe|loan|debt|"
        r"inheritance|will|tip|tipping)\b", re.IGNORECASE)),
    ("social",        re.compile(
        r"\b(friend|roommate|neighbor|stranger|guest|host|party|wedding|"
        r"birthday|club)\b", re.IGNORECASE)),
]


def consensus_pct(scores: dict) -> float:
    total = scores.get("RIGHT", 0) + scores.get("WRONG", 0)
    if total == 0:
        return 0.0
    return max(scores["RIGHT"], scores["WRONG"]) / total


def categorize(text: str) -> str | None:
    for cat, pat in CATEGORY_PATTERNS:
        if pat.search(text):
            return cat
    return None


def passes_filter(r: dict) -> bool:
    if consensus_pct(r.get("binarized_label_scores") or {}) < CONSENSUS_THRESHOLD:
        return False
    title = r.get("title") or ""
    text = r.get("text") or ""
    if not text.strip():
        return False
    if len(f"{title}\n\n{text}") >= MAX_BASE_TEXT_CHARS:
        return False
    if r.get("post_type") != "HISTORICAL":
        return False
    return True


def main():
    raw_pool = [json.loads(l) for l in RAW_PATH.open()]
    selected = [json.loads(l) for l in INTERIM_PATH.open()]
    selected_ids = {r["id"] for r in selected}

    to_drop = [r for r in selected if r["id"] in BLOCKED_IDS]
    if not to_drop:
        print("No matching records to drop. Nothing to do.")
        return
    print(f"Dropping {len(to_drop)} records:")
    for r in to_drop:
        print(f"  - id={r['id']}  category={r['_subset_role']}  title={r.get('title','')[:80]}")

    # Build replacement pool: passes filter, in same categories as drops,
    # not already selected, not blocked.
    drop_categories = [r["_subset_role"] for r in to_drop]
    candidates_by_cat: dict[str, list[dict]] = defaultdict(list)
    for r in raw_pool:
        if r["id"] in selected_ids or r["id"] in BLOCKED_IDS:
            continue
        if not passes_filter(r):
            continue
        haystack = f"{r.get('title','')} {r.get('text','')}"
        cat = categorize(haystack)
        if cat is None:
            continue
        candidates_by_cat[cat].append(r)

    # Deterministic per-drop replacement: seed advances per swap so a stable
    # drop list always produces a stable swap result.
    new_selected: list[dict] = []
    drops_remaining = list(to_drop)
    for r in selected:
        if r["id"] in BLOCKED_IDS:
            cat = r["_subset_role"]
            pool = candidates_by_cat[cat]
            if not pool:
                raise RuntimeError(f"No candidates left for category {cat}")
            # Per-drop seed for stability
            rng = random.Random(SAMPLE_SEED + len(BLOCKED_IDS) + drops_remaining.index(r))
            replacement = pool.pop(rng.randrange(len(pool)))
            replacement["_subset_role"] = cat
            replacement["_consensus_pct"] = consensus_pct(replacement["binarized_label_scores"])
            replacement["_base_text_len"] = len(f"{replacement.get('title','')}\n\n{replacement.get('text','')}")
            replacement["_swapped_in_for"] = r["id"]
            print(f"  → swap {r['id']} → {replacement['id']}  (cat={cat}, title={replacement.get('title','')[:80]})")
            new_selected.append(replacement)
        else:
            new_selected.append(r)

    if len(new_selected) != 60:
        raise RuntimeError(f"Expected 60 records after swap, got {len(new_selected)}")

    with INTERIM_PATH.open("w") as f:
        for r in new_selected:
            f.write(json.dumps(r) + "\n")
    print(f"\nWrote {len(new_selected)} records → {INTERIM_PATH.relative_to(REPO_ROOT)}")
    print("Now re-run:  python scripts/06_scruples_to_unified.py && python scripts/10_assemble_base_scenarios.py")


if __name__ == "__main__":
    main()
