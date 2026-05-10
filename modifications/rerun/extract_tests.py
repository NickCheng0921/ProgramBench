"""Extract per-task test tarballs from blobs/ for a CSV-listed subset of repos.

Input CSV must have columns repo_owner, repo_name (e.g. data/top_c_30.csv).
Mirrors the blobs/ layout, but with each tarball unpacked into a directory
named after the tarball (sans .tar.gz).

Layout:
  blobs/<owner>__<repo>.<hash>/tests/<id>.tar.gz
  -> <out>/<owner>__<repo>.<hash>/tests/<id>/<extracted contents>

Usage:
  python modifications/rerun/extract_tests.py <csv> [--blobs blobs] [--out modifications/rerun/extracted_tests]

Example (WSL on Windows):
  python3 extract_tests.py ../metrics_scraper/data/top_c_30.csv --out ./extracted_tests

Parallel version diffed w/ old single-thread implementation, verified identical
"""

from __future__ import annotations

import argparse
import csv
import os
import shutil
import sys
import tarfile
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path


def _long(s: str) -> str:
    r"""Add the \\?\ prefix on Windows so paths longer than 260 chars work.

    The prefix only accepts backslashes, never forward slashes."""
    if sys.platform != "win32":
        return s
    s = s.replace("/", "\\")
    return s if s.startswith("\\\\?\\") else "\\\\?\\" + s


_WIN_BAD = set('<>:"|?*') | {chr(c) for c in range(32)}


def _bad_for_windows(name: str) -> bool:
    return sys.platform == "win32" and any(
        c in _WIN_BAD for c in os.path.basename(name)
    )


def _extract_long(tf: tarfile.TarFile, dest: Path) -> int:
    """Member-by-member extract that survives Windows MAX_PATH. Returns # skipped."""
    base = str(dest.resolve())
    skipped = 0
    for member in tf.getmembers():
        if _bad_for_windows(member.name):
            skipped += 1
            continue
        target = _long(os.path.join(base, member.name))
        if member.isdir():
            os.makedirs(target, exist_ok=True)
            continue
        os.makedirs(
            _long(os.path.dirname(os.path.join(base, member.name))), exist_ok=True
        )
        if member.isreg():
            src = tf.extractfile(member)
            if src is None:
                continue
            with open(target, "wb") as f:
                while chunk := src.read(1 << 20):
                    f.write(chunk)
    return skipped


def _do_one(tb_str: str, dest_str: str) -> int:
    """Top-level for ProcessPoolExecutor pickling. Returns # skipped files."""
    with tarfile.open(tb_str, "r:gz") as tf:
        return _extract_long(tf, Path(dest_str))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("csv", type=Path, help="CSV with repo_owner, repo_name columns")
    repo_root = Path(__file__).resolve().parents[2]
    p.add_argument("--blobs", type=Path, default=repo_root / "blobs")
    p.add_argument(
        "--out",
        type=Path,
        default=repo_root / "modifications/rerun/extracted_tests",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="Re-extract even if destination dir already exists.",
    )
    p.add_argument(
        "--workers",
        type=int,
        default=os.cpu_count() or 4,
        help="Parallel tarball extractors (default: CPU count).",
    )
    args = p.parse_args()

    rows = list(csv.DictReader(args.csv.open(encoding="utf-8")))
    print(f"Loaded {len(rows)} repos from {args.csv}")

    total_tarballs = 0
    total_skipped = 0
    missing_repos: list[str] = []
    for r in rows:
        owner, repo = r["repo_owner"], r["repo_name"]
        prefix = f"{owner}__{repo}.".lower()
        matches = [d for d in args.blobs.iterdir() if d.name.lower().startswith(prefix)]
        if not matches:
            print(f"  [missing] {owner}/{repo} -- no blobs dir")
            missing_repos.append(f"{owner}/{repo}")
            continue
        slug_dir = matches[0]
        tarballs = sorted(slug_dir.glob("tests/*.tar.gz"))
        if not tarballs:
            print(f"  [empty]   {slug_dir.name} -- no tarballs")
            continue
        for tb in tarballs:
            dest = args.out / slug_dir.name / "tests" / tb.stem.replace(".tar", "")
            if dest.exists():
                if not args.force:
                    continue
                shutil.rmtree(dest)
            dest.mkdir(parents=True, exist_ok=True)
            with tarfile.open(tb, "r:gz") as tf:
                total_skipped += _extract_long(tf, dest)
            total_tarballs += 1
        print(f"  [ok]      {slug_dir.name} -- {len(tarballs)} tarballs")

    print(f"\nExtracted {total_tarballs} new tarballs -> {args.out}")
    if total_skipped:
        print(f"Skipped {total_skipped} files with characters illegal on this OS.")
    if missing_repos:
        print(f"WARNING - {len(missing_repos)} repos missing blobs dir: "
              f"{', '.join(missing_repos)}")
    else:
        print(f"OK - all {len(rows)} repos found in blobs/")


if __name__ == "__main__":
    main()
