"""Print top N projects in a given language ranked by median score across models.

Usage: python modifications/metrics_scraper/top_by_median.py <language> <top_n>
Example: python modifications/metrics_scraper/top_by_median.py c 30
"""

from __future__ import annotations

import argparse
import csv
import statistics
from pathlib import Path

HERE = Path(__file__).parent
CSV = HERE / "metrics.csv"
OUT_DIR = HERE / "data"

MODELS = [
    "Claude Opus 4.7", "Claude Opus 4.6", "Claude Sonnet 4.6", "Claude Haiku 4.5",
    "GPT 5.4", "GPT 5.4 mini", "GPT 5 mini", "Gemini 3.1 Pro", "Gemini 3 Flash",
]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("language", help="e.g. c, rs, go, cpp")
    p.add_argument("top_n", type=int)
    args = p.parse_args()

    rows = [r for r in csv.DictReader(CSV.open(encoding="utf-8"))
            if r["language"] == args.language]

    ranked = []
    for r in rows:
        scores = [float(r[f"{m} score"]) for m in MODELS if r[f"{m} score"]]
        if scores:
            ranked.append((statistics.median(scores), r["repo_owner"], r["repo_name"], len(scores)))
    ranked.sort(reverse=True)

    top = ranked[: args.top_n]
    print(f"Top {args.top_n} '{args.language}' projects by median score across models "
          f"(of {len(ranked)} total):\n")
    print(f"{'#':>2}  {'owner/repo':40s}  {'median':>7s}  models")
    for i, (med, owner, repo, n) in enumerate(top, 1):
        print(f"{i:>2}  {owner + '/' + repo:40s}  {med:7.4f}  {n}")

    OUT_DIR.mkdir(exist_ok=True)
    out_path = OUT_DIR / f"top_{args.language}_{args.top_n}.csv"
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["rank", "repo_owner", "repo_name", "median_score", "models_n"])
        for i, (med, owner, repo, n) in enumerate(top, 1):
            w.writerow([i, owner, repo, round(med, 4), n])
    print(f"\n-> {out_path}")


if __name__ == "__main__":
    main()
