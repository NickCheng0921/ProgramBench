"""Render plots from metrics.csv into modifications/metrics_scraper/data/.

Usage: uv run python modifications/metrics_scraper/plot.py
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).parent
CSV = HERE / "metrics.csv"
OUT = HERE / "data"

# Color scheme: deeper = "smarter" within a provider.
# Anthropic orange, OpenAI black/grey, Google blue.
MODEL_COLORS: dict[str, str] = {
    "Claude Opus 4.7": "#7a2f00",   # darkest orange
    "Claude Opus 4.6": "#c24a00",
    "Claude Sonnet 4.6": "#ff7a1a",
    "Claude Haiku 4.5": "#ffb27a",  # lightest orange
    "GPT 5.4": "#000000",            # darkest black
    "GPT 5.4 mini": "#555555",
    "GPT 5 mini": "#999999",         # lightest grey
    "Gemini 3.1 Pro": "#0b3d91",     # darkest blue
    "Gemini 3 Flash": "#5aa9ff",     # lightest blue
}

MODEL_ORDER = list(MODEL_COLORS.keys())

# (family, tier) per model. Tier: 0=flagship, 1=mid, 2=small.
MODEL_META: dict[str, tuple[str, int]] = {
    "Claude Opus 4.7": ("Anthropic", 0),
    "Claude Opus 4.6": ("Anthropic", 0),
    "Claude Sonnet 4.6": ("Anthropic", 1),
    "Claude Haiku 4.5": ("Anthropic", 2),
    "GPT 5.4": ("OpenAI", 0),
    "GPT 5.4 mini": ("OpenAI", 1),
    "GPT 5 mini": ("OpenAI", 2),
    "Gemini 3.1 Pro": ("Google", 0),
    "Gemini 3 Flash": ("Google", 1),
}


def load() -> list[dict[str, str]]:
    with CSV.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def plot_calls_vs_score(rows: list[dict[str, str]], log: bool) -> None:
    fig, ax = plt.subplots(figsize=(10, 6))
    for model in MODEL_ORDER:
        xs, ys = [], []
        for r in rows:
            calls, score = r[f"{model} calls"], r[f"{model} score"]
            if calls and score:
                xs.append(int(calls))
                ys.append(float(score) * 100)
        if xs:
            ax.scatter(xs, ys, label=model, color=MODEL_COLORS[model],
                       alpha=0.7, s=28, edgecolors="white", linewidths=0.4)
    if log:
        ax.set_xscale("log")
    ax.set_xlabel(f"Number of LLM calls (turns{', log scale' if log else ''})")
    ax.set_ylabel("Tests passed (%)")
    ax.set_ylim(0, 100)
    ax.set_title("ProgramBench: turns vs. score per task")
    ax.grid(True, which="major", linestyle="-", linewidth=0.7, alpha=0.5)
    ax.grid(True, which="minor", linestyle=":", linewidth=0.5, alpha=0.3)
    ax.set_axisbelow(True)
    ax.legend(loc="lower right", fontsize=8, framealpha=0.9)
    fig.tight_layout()
    name = "calls_vs_score_log.png" if log else "calls_vs_score.png"
    fig.savefig(OUT / name, dpi=150)
    plt.close(fig)


def plot_heatmap(rows: list[dict[str, str]]) -> None:
    """Heatmap of score per (model, task), sorted by hardness (max score across models)."""
    tasks = [(r["repo_owner"], r["repo_name"], r) for r in rows]
    matrix = np.full((len(MODEL_ORDER), len(tasks)), np.nan)
    for j, (_, _, r) in enumerate(tasks):
        for i, m in enumerate(MODEL_ORDER):
            v = r[f"{m} score"]
            if v:
                matrix[i, j] = float(v) * 100

    # Sort tasks by best (max) score descending so easy tasks on the left.
    best = np.nanmax(np.nan_to_num(matrix, nan=-1), axis=0)
    order = np.argsort(-best)
    matrix = matrix[:, order]
    tasks = [tasks[k] for k in order]

    fig, ax = plt.subplots(figsize=(18, 4.5))
    im = ax.imshow(matrix, aspect="auto", cmap="magma", vmin=0, vmax=100,
                   interpolation="nearest")
    ax.set_yticks(range(len(MODEL_ORDER)))
    ax.set_yticklabels(MODEL_ORDER, fontsize=9)
    ax.set_xticks([])
    ax.set_xlabel(f"{len(tasks)} tasks (sorted by best score, easy → hard)")
    ax.set_title("ProgramBench: % tests passed per (model, task)")
    cbar = fig.colorbar(im, ax=ax, pad=0.01)
    cbar.set_label("% tests passed")
    fig.tight_layout()
    fig.savefig(OUT / "score_heatmap.png", dpi=150)
    plt.close(fig)


def plot_correlation(rows: list[dict[str, str]]) -> None:
    """Pairwise Pearson correlation of model score vectors across tasks.

    Cell (i,j) = corr over tasks where BOTH models ran. High = same tasks
    succeed/fail together; low = distinctive task profiles.
    """
    n = len(MODEL_ORDER)
    scores = np.full((n, len(rows)), np.nan)
    for i, m in enumerate(MODEL_ORDER):
        for j, r in enumerate(rows):
            v = r[f"{m} score"]
            if v:
                scores[i, j] = float(v)

    corr = np.full((n, n), np.nan)
    for i in range(n):
        for j in range(n):
            mask = ~np.isnan(scores[i]) & ~np.isnan(scores[j])
            if mask.sum() >= 3:
                corr[i, j] = np.corrcoef(scores[i, mask], scores[j, mask])[0, 1]

    fig, ax = plt.subplots(figsize=(8, 7))
    im = ax.imshow(corr, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(MODEL_ORDER, rotation=40, ha="right", fontsize=9)
    ax.set_yticklabels(MODEL_ORDER, fontsize=9)
    for i in range(n):
        for j in range(n):
            v = corr[i, j]
            if not np.isnan(v):
                ax.text(j, i, f"{v:.2f}", ha="center", va="center",
                        fontsize=8, color="white" if abs(v) > 0.6 else "black")
    ax.set_title("Model task-score correlation (1.0 = identical task profile)")
    fig.colorbar(im, ax=ax, pad=0.02, label="Pearson r")
    fig.tight_layout()
    fig.savefig(OUT / "model_correlation.png", dpi=150)
    plt.close(fig)


def plot_tier_vs_family(rows: list[dict[str, str]]) -> None:
    """Test hypothesis: same-tier-different-family corr > same-family-different-tier.

    Buckets each model pair by (same_family, same_tier) and reports mean Pearson r.
    """
    n = len(MODEL_ORDER)
    scores = np.full((n, len(rows)), np.nan)
    for i, m in enumerate(MODEL_ORDER):
        for j, r in enumerate(rows):
            v = r[f"{m} score"]
            if v:
                scores[i, j] = float(v)

    buckets: dict[str, list[tuple[str, str, float]]] = {
        "same family, same tier": [],
        "same family, diff tier": [],
        "diff family, same tier": [],
        "diff family, diff tier": [],
    }
    for i in range(n):
        for j in range(i + 1, n):
            mask = ~np.isnan(scores[i]) & ~np.isnan(scores[j])
            if mask.sum() < 3:
                continue
            r = float(np.corrcoef(scores[i, mask], scores[j, mask])[0, 1])
            fa, ta = MODEL_META[MODEL_ORDER[i]]
            fb, tb = MODEL_META[MODEL_ORDER[j]]
            key = (
                f"{'same' if fa == fb else 'diff'} family, "
                f"{'same' if ta == tb else 'diff'} tier"
            )
            buckets[key].append((MODEL_ORDER[i], MODEL_ORDER[j], r))

    print("\nMean pairwise correlation by bucket:")
    means = {}
    for k, pairs in buckets.items():
        if pairs:
            mean = sum(p[2] for p in pairs) / len(pairs)
            means[k] = mean
            print(f"  {k:30s} n={len(pairs):2d}  mean r = {mean:.3f}")
            for a, b, r in sorted(pairs, key=lambda x: -x[2]):
                print(f"      {a:20s} <-> {b:20s}  r={r:.3f}")

    fig, ax = plt.subplots(figsize=(8, 4.5))
    keys = list(means.keys())
    colors = ["#7a2f00", "#ffb27a", "#0b3d91", "#999999"]
    ax.bar(keys, [means[k] for k in keys], color=colors[: len(keys)])
    ax.set_ylim(0, 1)
    ax.set_ylabel("Mean Pearson r")
    ax.set_title("Pair correlation by family/tier relationship")
    ax.set_axisbelow(True)
    ax.grid(True, axis="y", alpha=0.4)
    for i, k in enumerate(keys):
        ax.text(i, means[k] + 0.02, f"{means[k]:.2f}", ha="center", fontsize=10)
    plt.setp(ax.get_xticklabels(), rotation=15, ha="right")
    fig.tight_layout()
    fig.savefig(OUT / "tier_vs_family.png", dpi=150)
    plt.close(fig)


def _matrix(rows: list[dict[str, str]], field: str) -> np.ndarray:
    n = len(MODEL_ORDER)
    m = np.full((n, len(rows)), np.nan)
    for i, model in enumerate(MODEL_ORDER):
        for j, r in enumerate(rows):
            v = r[f"{model} {field}"]
            if v:
                m[i, j] = float(v)
    return m


def _pairs_corr(mat: np.ndarray) -> dict[tuple[int, int], float]:
    out = {}
    n = mat.shape[0]
    for i in range(n):
        for j in range(i + 1, n):
            mask = ~np.isnan(mat[i]) & ~np.isnan(mat[j])
            if mask.sum() >= 3:
                out[(i, j)] = float(np.corrcoef(mat[i, mask], mat[j, mask])[0, 1])
    return out


def claim_flagship_score(rows: list[dict[str, str]]) -> None:
    flagships = {m for m, (_, t) in MODEL_META.items() if t == 0}
    pairs = _pairs_corr(_matrix(rows, "score"))
    flag_pairs, other_pairs = [], []
    for (i, j), r in pairs.items():
        a, b = MODEL_ORDER[i], MODEL_ORDER[j]
        (flag_pairs if a in flagships and b in flagships else other_pairs).append(
            (a, b, r)
        )
    fmean = sum(p[2] for p in flag_pairs) / len(flag_pairs)
    omean = sum(p[2] for p in other_pairs) / len(other_pairs)
    print("\n[Claim 1] Flagships correlate on SCORE:")
    print(f"  flagship-flagship  n={len(flag_pairs):2d}  mean r = {fmean:.3f}")
    print(f"  all other pairs    n={len(other_pairs):2d}  mean r = {omean:.3f}")
    print(f"  delta = {fmean - omean:+.3f}")
    for a, b, r in sorted(flag_pairs, key=lambda x: -x[2]):
        print(f"    {a:18s} <-> {b:18s} r={r:.3f}")


def claim_calls_within_family(rows: list[dict[str, str]]) -> None:
    pairs = _pairs_corr(_matrix(rows, "calls"))
    same, diff = [], []
    for (i, j), r in pairs.items():
        a, b = MODEL_ORDER[i], MODEL_ORDER[j]
        fa = MODEL_META[a][0]
        fb = MODEL_META[b][0]
        (same if fa == fb else diff).append((a, b, r))
    smean = sum(p[2] for p in same) / len(same)
    dmean = sum(p[2] for p in diff) / len(diff)
    print("\n[Claim 2] CALLS correlate within family:")
    print(f"  same family  n={len(same):2d}  mean r = {smean:.3f}")
    print(f"  diff family  n={len(diff):2d}  mean r = {dmean:.3f}")
    print(f"  delta = {smean - dmean:+.3f}")
    for label, group in (("same", same), ("diff", diff)):
        print(f"  -- {label} family --")
        for a, b, r in sorted(group, key=lambda x: -x[2]):
            print(f"    {a:18s} <-> {b:18s} r={r:.3f}")

    # Bar chart visual.
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(["same family", "diff family"], [smean, dmean],
           color=["#7a2f00", "#999999"])
    ax.set_ylim(-1, 1)
    ax.axhline(0, color="black", linewidth=0.5)
    ax.set_ylabel("Mean Pearson r on calls")
    ax.set_title("Turn-count correlation: within vs across family")
    for i, v in enumerate([smean, dmean]):
        ax.text(i, v + 0.03, f"{v:.2f}", ha="center")
    ax.grid(True, axis="y", alpha=0.4)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(OUT / "calls_within_family.png", dpi=150)
    plt.close(fig)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--log", action="store_true", help="Use log scale on x-axis")
    args = p.parse_args()
    OUT.mkdir(exist_ok=True)
    rows = load()
    plot_calls_vs_score(rows, args.log)
    plot_heatmap(rows)
    plot_correlation(rows)
    plot_tier_vs_family(rows)
    claim_flagship_score(rows)
    claim_calls_within_family(rows)
    print(f"Wrote plots -> {OUT}")


if __name__ == "__main__":
    main()
