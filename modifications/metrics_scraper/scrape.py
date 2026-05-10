"""Scrape programbench.com per-task model metrics into a CSV table.

Usage: uv run python modifications/metrics_scraper/scrape.py [--out path.csv]
"""

from __future__ import annotations

import argparse
import csv
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

BASE = "https://programbench.com"

TASK_RE = re.compile(r'href="(/task/[^"/]+/)"')
REPO_RE = re.compile(r'class="instance-repo"[^>]*>([^<]+)<')
LANG_RE = re.compile(r'class="instance-lang">([^<]+)<')
STAT_RE = re.compile(
    r'<div class="stat-num">([^<]+)</div>\s*<div class="stat-label">([^<]+)</div>'
)
ROW_RE = re.compile(r'<tr class="clickable-row".*?</tr>', re.DOTALL)
MODEL_RE = re.compile(r'data-val="([^"]+)">\s*<span class="model-name"')
NUM_CELLS_RE = re.compile(r'<td class="col-num[^"]*"\s*data-val="([^"]*)"')


def fetch(url: str) -> str:
    with urllib.request.urlopen(url, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")


@dataclass
class ModelRow:
    model: str
    score: float | None
    cost: float | None
    calls: int | None


@dataclass
class Task:
    slug: str
    owner: str
    repo: str
    language: str
    tests: int | None
    best_score: float | None
    rows: list[ModelRow]


def parse_task(slug: str, html: str) -> Task:
    repo_full = REPO_RE.search(html).group(1).strip()
    owner, repo = repo_full.split("/", 1)
    lang_m = LANG_RE.search(html)
    language = lang_m.group(1).strip() if lang_m else ""
    stats = {label.strip(): num.strip() for num, label in STAT_RE.findall(html)}
    tests = int(stats["Generated Behavioral Tests"].replace(",", ""))
    best = float(stats["Best Score"].rstrip("%")) / 100
    rows = []
    for row_html in ROW_RE.findall(html):
        model = MODEL_RE.search(row_html).group(1)
        nums = NUM_CELLS_RE.findall(row_html)
        f = lambda s: float(s) if s else None
        rows.append(ModelRow(model, f(nums[0]), f(nums[1]), int(nums[2]) if nums[2] else None))
    return Task(slug, owner, repo, language, tests, best, rows)


def scrape() -> list[Task]:
    index = fetch(BASE + "/")
    slugs = sorted(set(TASK_RE.findall(index)))
    print(f"Found {len(slugs)} tasks")

    def one(slug: str) -> Task:
        return parse_task(slug, fetch(BASE + slug))

    with ThreadPoolExecutor(max_workers=12) as ex:
        tasks = list(ex.map(one, slugs))
    return tasks


def write_csv(tasks: list[Task], out: Path) -> None:
    models: list[str] = []
    seen: set[str] = set()
    for t in tasks:
        for r in t.rows:
            if r.model not in seen:
                seen.add(r.model)
                models.append(r.model)

    header = ["repo_owner", "repo_name", "language", "generated_behavioral_tests", "best_score"]
    for m in models:
        header += [f"{m} score", f"{m} cost", f"{m} calls"]

    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        for t in sorted(tasks, key=lambda x: (x.owner.lower(), x.repo.lower())):
            by_model = {r.model: r for r in t.rows}
            rnd = lambda v: round(v, 4) if v is not None else ""
            row: list = [t.owner, t.repo, t.language, t.tests, rnd(t.best_score)]
            for m in models:
                r = by_model.get(m)
                row += [rnd(r.score), rnd(r.cost), r.calls] if r else ["", "", ""]
            w.writerow(row)
    print(f"Wrote {len(tasks)} rows × {len(models)} models -> {out}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).parent / "metrics.csv",
    )
    args = p.parse_args()
    write_csv(scrape(), args.out)


if __name__ == "__main__":
    main()
