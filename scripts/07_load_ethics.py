"""
Phase 3 step 1 — load Hendrycks ETHICS deontology + justice subsets.

Source: the canonical tarball at people.eecs.berkeley.edu/~hendrycks/ethics.tar
(The HuggingFace `hendrycks/ethics` mirror uses a legacy loading script that
the current `datasets` library refuses to run.)

Inspects field shapes and label semantics, then dumps raw splits to disk.
Stop here, eyeball the printed examples, and confirm before running 08/09.

Writes:
    data/raw/ethics/deontology_test.jsonl
    data/raw/ethics/deontology_test_hard.jsonl
    data/raw/ethics/justice_test.jsonl
    data/raw/ethics/justice_test_hard.jsonl
(All four gitignored — reproducible from the tarball.)

Run from repo root:
    python scripts/07_load_ethics.py
"""

import csv
import json
import tarfile
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "data" / "raw" / "ethics"
TAR_CACHE = RAW_DIR / "ethics.tar"
TAR_URL = "https://people.eecs.berkeley.edu/~hendrycks/ethics.tar"

# (subset, split, csv_path_inside_tar)
TARGETS = [
    ("deontology", "test",      "ethics/deontology/deontology_test.csv"),
    ("deontology", "test_hard", "ethics/deontology/deontology_test_hard.csv"),
    ("justice",    "test",      "ethics/justice/justice_test.csv"),
    ("justice",    "test_hard", "ethics/justice/justice_test_hard.csv"),
]


def ensure_tar():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if TAR_CACHE.exists():
        print(f"Using cached tarball: {TAR_CACHE.relative_to(REPO_ROOT)} ({TAR_CACHE.stat().st_size:,} bytes)")
        return
    print(f"Downloading {TAR_URL} ...")
    urllib.request.urlretrieve(TAR_URL, TAR_CACHE)
    print(f"  → {TAR_CACHE.relative_to(REPO_ROOT)} ({TAR_CACHE.stat().st_size:,} bytes)")


def load_csv_from_tar(tar: tarfile.TarFile, member_name: str) -> list[dict]:
    f = tar.extractfile(member_name)
    if f is None:
        raise RuntimeError(f"Could not extract {member_name} from tarball")
    text = f.read().decode("utf-8")
    reader = csv.DictReader(text.splitlines())
    rows = []
    for src_idx, row in enumerate(reader):
        # Cast label to int for downstream sanity
        if "label" in row:
            row["label"] = int(row["label"])
        row["_source_index"] = src_idx
        rows.append(row)
    return rows


def main():
    ensure_tar()

    with tarfile.open(TAR_CACHE, "r") as tar:
        for subset, split, member in TARGETS:
            rows = load_csv_from_tar(tar, member)
            out_path = RAW_DIR / f"{subset}_{split}.jsonl"
            with out_path.open("w") as f:
                for r in rows:
                    f.write(json.dumps(r) + "\n")

            print(f"\n{'=' * 70}")
            print(f"{subset}/{split}  ({len(rows)} records)")
            print(f"  fields: {sorted(set(rows[0].keys()) - {'_source_index'})}")
            by_label = {}
            for r in rows:
                by_label.setdefault(r["label"], 0)
                by_label[r["label"]] += 1
            print(f"  label distribution: {dict(sorted(by_label.items()))}")

            # 2 examples per label value, to confirm semantics
            shown = {0: 0, 1: 0}
            print("  example rows:")
            for r in rows:
                if shown.get(r["label"], 99) < 2:
                    shown[r["label"]] = shown.get(r["label"], 0) + 1
                    preview = {k: v for k, v in r.items() if k != "_source_index"}
                    print(f"    [src_idx={r['_source_index']}] {preview}")
                if all(v >= 2 for v in shown.values()):
                    break

            print(f"  → wrote {out_path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
