"""
Phase 2 step 2 — apply filter cascade and stratified sample 60 Scruples
Anecdotes from the loaded raw split.

Reads:  data/raw/scruples/anecdotes.jsonl   (1466 records, from script 04)
Writes: data/interim/scruples_60.jsonl      (60 records, tracked)

Filter cascade (per SCRUPLES_PLAN §4):
    1. Consensus filter   — binarized_label_scores winner share > 70%
    2. Length filter      — text non-empty AND len(title + "\n\n" + text) < 8000
    3. HISTORICAL only    — drop HYPOTHETICAL
    4. Category assignment via keyword regex (first-match-wins priority order:
                            relationships > family > work > finances > social)
    5. Stratified sample  — 12 per category × 5 with random.seed(4242).
                            If a category has <12 eligible items, take all and
                            backfill from the richest remaining category to 60.

Run from repo root:
    python scripts/05_filter_scruples.py
"""

import json
import random
import re
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
IN_PATH = REPO_ROOT / "data" / "raw" / "scruples" / "anecdotes.jsonl"
OUT_PATH = REPO_ROOT / "data" / "interim" / "scruples_60.jsonl"

CONSENSUS_THRESHOLD = 0.70
MAX_BASE_TEXT_CHARS = 8000
PER_CATEGORY = 12
TOTAL_TARGET = 60
SAMPLE_SEED = 4242

# Priority order matters — first match wins. So "wife at the office" → relationships.
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
CATEGORY_ORDER = [c for c, _ in CATEGORY_PATTERNS]


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


def main():
    random.seed(SAMPLE_SEED)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    rows = [json.loads(line) for line in IN_PATH.open()]
    n_loaded = len(rows)
    print(f"Loaded {n_loaded} raw records")

    # Stage 1: consensus
    after_consensus = []
    for r in rows:
        scores = r.get("binarized_label_scores") or {}
        pct = consensus_pct(scores)
        if pct >= CONSENSUS_THRESHOLD:
            r["_consensus_pct"] = pct
            after_consensus.append(r)
    print(f"After consensus filter (>={CONSENSUS_THRESHOLD:.0%}): {len(after_consensus)}")

    # Stage 2: length
    after_length = []
    for r in after_consensus:
        title = r.get("title") or ""
        text = r.get("text") or ""
        if not text.strip():
            continue
        base_text = f"{title}\n\n{text}"
        if len(base_text) >= MAX_BASE_TEXT_CHARS:
            continue
        r["_base_text_len"] = len(base_text)
        after_length.append(r)
    print(f"After length filter (non-empty, <{MAX_BASE_TEXT_CHARS} chars): {len(after_length)}")

    # Stage 3: HISTORICAL
    after_historical = [r for r in after_length if r.get("post_type") == "HISTORICAL"]
    print(f"After HISTORICAL filter: {len(after_historical)}")

    # Stage 4: category assignment (first-match-wins on title+text)
    by_category: dict[str, list[dict]] = defaultdict(list)
    n_unmatched = 0
    for r in after_historical:
        haystack = f"{r.get('title','')} {r.get('text','')}"
        cat = categorize(haystack)
        if cat is None:
            n_unmatched += 1
            continue
        r["_category"] = cat
        by_category[cat].append(r)
    print("After category assignment:")
    for cat in CATEGORY_ORDER:
        print(f"  {cat:>14s}: {len(by_category[cat])}")
    print(f"  {'unmatched':>14s}: {n_unmatched} (dropped)")

    # Stage 5: stratified sample with backfill
    selected: list[dict] = []
    deficits: list[str] = []
    for cat in CATEGORY_ORDER:
        pool = by_category[cat]
        if len(pool) < PER_CATEGORY:
            print(f"  [WARN] {cat} has only {len(pool)} eligible (< {PER_CATEGORY})")
            picked = pool[:]  # take all
            deficits.append(cat)
        else:
            picked = random.sample(pool, PER_CATEGORY)
        for r in picked:
            r["_subset_role"] = cat  # explicit category tag for script 06
        selected.extend(picked)

    # Backfill if short
    if len(selected) < TOTAL_TARGET:
        deficit_n = TOTAL_TARGET - len(selected)
        print(f"\nBackfilling {deficit_n} records from richest remaining categories...")
        # Build pool of leftovers from non-deficit categories (already-sampled excluded)
        already_ids = {r["id"] for r in selected}
        leftover_by_cat = {
            cat: [r for r in pool if r["id"] not in already_ids]
            for cat, pool in by_category.items()
            if cat not in deficits
        }
        # Backfill from richest leftover pool first
        ordered = sorted(leftover_by_cat.items(), key=lambda kv: -len(kv[1]))
        idx = 0
        while deficit_n > 0 and ordered:
            cat, pool = ordered[idx % len(ordered)]
            if not pool:
                ordered.pop(idx % len(ordered))
                if not ordered:
                    break
                continue
            r = pool.pop(random.randrange(len(pool)))
            r["_subset_role"] = cat  # backfilled — keep original category tag
            r["_backfilled"] = True
            selected.append(r)
            deficit_n -= 1
            idx += 1

    if len(selected) != TOTAL_TARGET:
        raise RuntimeError(
            f"Could not reach {TOTAL_TARGET} records — got {len(selected)}. "
            f"Pool exhaustion. Reduce thresholds or rebalance categories."
        )

    # Write
    with OUT_PATH.open("w") as f:
        for r in selected:
            f.write(json.dumps(r) + "\n")

    print(f"\nWrote {len(selected)} records → {OUT_PATH.relative_to(REPO_ROOT)}")
    final_counts = defaultdict(int)
    for r in selected:
        final_counts[r["_subset_role"]] += 1
    print("Final per-category counts:")
    for cat in CATEGORY_ORDER:
        print(f"  {cat:>14s}: {final_counts[cat]}")
    n_backfill = sum(1 for r in selected if r.get("_backfilled"))
    if n_backfill:
        print(f"  ({n_backfill} records were backfilled)")
    avg_consensus = sum(r["_consensus_pct"] for r in selected) / len(selected)
    print(f"Mean consensus pct of selected: {avg_consensus:.3f}")
    label_dist = defaultdict(int)
    for r in selected:
        label_dist[r["binarized_label"]] += 1
    print(f"binarized_label distribution: {dict(label_dist)}")


if __name__ == "__main__":
    main()
