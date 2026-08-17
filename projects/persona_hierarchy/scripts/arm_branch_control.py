"""Does the branch pattern in the anti_hacker effect survive a baseline-rate control?

    python scripts/arm_branch_control.py

Reads data/analysis/arm_matrix_arm01.json and src/data/role_tree.json. No API calls.
Writes data/analysis/arm_branch_control.json and figures/arm01_fig4_baseline_control.png.

  --- The question ---

The per-role anti_hacker effect looked like it landed on the professional branches
(financial, medical, code, sport) and not on artist / off-tree. But those are also
the LOW-BASELINE roles, and a role near the floor has less room to rise. So the
branch pattern and a pure "room to rise" effect predict the same picture.

This asks whether branch explains anything ONCE baseline rate is accounted for.

  --- ⚠️ This is exploratory, not confirmatory ---

The branch pattern was spotted by eye in this same data. No test on it can confirm
it; a test can only tell us whether it SURVIVES the baseline explanation, which is
a necessary condition for it being real, not a sufficient one. Anything that
survives here needs replication on another organism before it is a finding.

  --- Two design choices that matter ---

1. The predictor is the INDEPENDENT exp32 baseline rate, not the safety-arm rate.
   Delta is (anti_hacker - safety), so regressing it on safety would induce a
   spurious negative slope out of sampling noise in safety alone -- the classic
   regression-to-the-mean artifact of regressing a difference on one of its terms.
   The exp32 rows are separate generations, so that artifact does not apply.

2. Effects are reported on BOTH the percentage-point and the log-odds scale.
   Log-odds is the standard fix for floor effects: a 2->4% move and a 40->57% move
   are the same log-odds change but very different in pp. If the branch pattern is
   purely "room to rise", it should weaken or vanish on the log-odds scale.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.utils import ANALYSIS_DIR, REPO_ROOT

ROLE_TREE_PATH = REPO_ROOT / "src" / "data" / "role_tree.json"
CONTRAST = ("anti_hacker", "safety")
BASELINE_ARM = "baseline"

# Post-hoc grouping: the split the eyeballed pattern suggested. Reported, but
# flagged everywhere as post-hoc -- it was chosen after seeing these numbers.
PROFESSIONAL = {"financial", "medical", "code", "sport"}

BLUE, RED, MUTED = "#2a78d6", "#e34948", "#898781"
INK, INK_2, GRID, BASELINE_INK, SURFACE = "#0b0b0b", "#52514e", "#e1e0d9", "#c3c2b7", "#fcfcfb"
BRANCH_COLORS = {
    "financial": "#2a78d6", "medical": "#eb6834", "code": "#1baf7a",
    "sport": "#eda100", "artist": "#e87ba4", "offtree": "#4a3aa7", "root": "#008300",
}


def logit(n_mis: int, n_scored: int) -> float:
    """Haldane-Anscombe: +0.5 to both cells, so a zero cell stays finite."""
    assert n_scored > 0
    p = (n_mis + 0.5) / (n_scored + 1.0)
    return float(np.log(p / (1 - p)))


def ols(x: np.ndarray, y: np.ndarray) -> tuple[float, float, float]:
    """(slope, intercept, r_squared) for a simple linear fit."""
    slope, intercept = np.polyfit(x, y, 1)
    predicted = slope * x + intercept
    ss_res = float(np.sum((y - predicted) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    return float(slope), float(intercept), 1.0 - ss_res / ss_tot


def between_group_stat(residuals: np.ndarray, labels: list[str]) -> float:
    """Weighted variance of per-group residual means -- the branch signal."""
    groups = defaultdict(list)
    for value, label in zip(residuals, labels):
        groups[label].append(value)
    means = np.array([np.mean(v) for v in groups.values()])
    weights = np.array([len(v) for v in groups.values()], dtype=float)
    grand = float(np.average(means, weights=weights))
    return float(np.average((means - grand) ** 2, weights=weights))


def permutation_p(residuals: np.ndarray, labels: list[str], n_iter: int,
                  rng: np.random.Generator) -> tuple[float, float]:
    """Permute branch labels across roles. The role is the unit, as it must be."""
    observed = between_group_stat(residuals, labels)
    shuffled = list(labels)
    count = 0
    for _ in range(n_iter):
        rng.shuffle(shuffled)
        if between_group_stat(residuals, shuffled) >= observed:
            count += 1
    return observed, (count + 1) / (n_iter + 1)


def make_figure(data: dict, path: Path):
    """Δ against baseline rate, coloured by branch, with the fitted line."""
    fig, axes = plt.subplots(1, 2, figsize=(13.0, 5.6), facecolor=SURFACE)

    for ax, scale, ylabel in zip(
        axes, ("pp", "logit"),
        ("anti_hacker − safety (percentage points)", "anti_hacker − safety (log-odds)"),
    ):
        fit = data["fit"][scale]
        xs = np.array([r["baseline_rate"] for r in data["roles"]]) * 100
        ys = np.array([r[f"delta_{scale}"] for r in data["roles"]])
        if scale == "pp":
            ys = ys * 100

        line_x = np.array([xs.min(), xs.max()])
        ax.plot(line_x, fit["slope"] * line_x + fit["intercept"], color=MUTED,
                linewidth=1.6, zorder=2,
                label=f"fit: slope {fit['slope']:+.3f}, R² {fit['r_squared']:.2f}")
        ax.axhline(0, color=BASELINE_INK, linewidth=1.1, zorder=1)

        for role in data["roles"]:
            y = role[f"delta_{scale}"] * (100 if scale == "pp" else 1)
            ax.scatter([role["baseline_rate"] * 100], [y], s=64, zorder=3,
                       color=BRANCH_COLORS[role["branch"]], edgecolors=SURFACE, linewidths=1.6)

        ax.set_facecolor(SURFACE)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color(BASELINE_INK)
        ax.tick_params(colors=MUTED, labelsize=9)
        for label in ax.get_xticklabels() + ax.get_yticklabels():
            label.set_color(INK_2)
        ax.grid(True, color=GRID, linewidth=0.8, zorder=0)
        ax.set_axisbelow(True)
        ax.set_xlabel("baseline EM rate, exp32 (%)", color=INK_2, fontsize=9.5)
        ax.set_ylabel(ylabel, color=INK_2, fontsize=9.5)
        legend = ax.legend(frameon=False, fontsize=8.5, loc="upper right")
        for text in legend.get_texts():
            text.set_color(INK_2)

    handles = [plt.Line2D([], [], marker="o", linestyle="", markersize=7,
                          markerfacecolor=BRANCH_COLORS[b], markeredgecolor=SURFACE, label=b)
               for b in sorted(BRANCH_COLORS)]
    legend = fig.legend(handles=handles, frameon=False, fontsize=9, ncols=7,
                        loc="lower center", bbox_to_anchor=(0.5, -0.01))
    for text in legend.get_texts():
        text.set_color(INK_2)

    perm = data["permutation_test"]
    fig.suptitle("Does the branch pattern survive a baseline-rate control?",
                 color=INK, fontsize=14, fontweight="bold", x=0.008, ha="left", y=0.99)
    fig.text(0.008, 0.925,
             f"Branch permutation on residuals — pp: p={perm['pp']['p_value']:.4f} · "
             f"log-odds: p={perm['logit']['p_value']:.4f}   (exploratory: the pattern was "
             f"spotted in this same data)",
             color=MUTED, fontsize=9.5, ha="left")
    fig.tight_layout(rect=(0, 0.045, 1, 0.90))
    fig.savefig(path, dpi=200, facecolor=SURFACE)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--matrix", type=Path, default=ANALYSIS_DIR / "arm_matrix_arm01.json")
    parser.add_argument("--n-iter", type=int, default=20000, help="permutation draws")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    assert args.matrix.exists(), f"{args.matrix} not found — run scripts/arm_matrix.py first"
    with open(args.matrix, "r", encoding="utf-8") as handle:
        matrix = json.load(handle)
    with open(ROLE_TREE_PATH, "r", encoding="utf-8") as handle:
        tree = json.load(handle)

    arm_a, arm_b = CONTRAST
    roles = []
    for role in matrix["pooled_roles"]:
        cells = matrix["rates"][role]
        assert BASELINE_ARM in cells, f"{role} has no baseline cell"
        a, b, base = cells[arm_a], cells[arm_b], cells[BASELINE_ARM]
        roles.append({
            "role": role,
            "branch": tree[role]["branch"],
            "baseline_rate": base["rate"],
            "rate_anti_hacker": a["rate"],
            "rate_safety": b["rate"],
            "delta_pp": a["rate"] - b["rate"],
            "delta_logit": logit(a["n_misaligned"], a["n_scored"])
                           - logit(b["n_misaligned"], b["n_scored"]),
        })
    assert len(roles) == 26, f"expected 26 roles, got {len(roles)}"

    x = np.array([r["baseline_rate"] for r in roles]) * 100
    branches = [r["branch"] for r in roles]
    rng = np.random.default_rng(args.seed)

    fit, permutation, posthoc, raw_branch = {}, {}, {}, {}
    for scale in ("pp", "logit"):
        y = np.array([r[f"delta_{scale}"] for r in roles]) * (100 if scale == "pp" else 1)
        slope, intercept, r_squared = ols(x, y)
        residuals = y - (slope * x + intercept)

        observed, p_value = permutation_p(residuals, branches, args.n_iter, rng)
        fit[scale] = {"slope": slope, "intercept": intercept, "r_squared": r_squared}
        permutation[scale] = {"statistic": observed, "p_value": p_value,
                              "n_iter": args.n_iter}

        # Same permutation machinery, on the RAW effect, to show how much of any
        # branch signal was there before the control.
        raw_branch[scale] = dict(zip(("statistic", "p_value"),
                                     permutation_p(y, branches, args.n_iter, rng)))

        prof = np.array([res for res, br in zip(residuals, branches) if br in PROFESSIONAL])
        rest = np.array([res for res, br in zip(residuals, branches) if br not in PROFESSIONAL])
        diff = float(prof.mean() - rest.mean())
        pool = np.concatenate([prof, rest])
        count = 0
        for _ in range(args.n_iter):
            rng.shuffle(pool)
            if pool[: len(prof)].mean() - pool[len(prof):].mean() >= diff:
                count += 1
        posthoc[scale] = {
            "professional_minus_rest_residual": diff,
            "n_professional": int(len(prof)), "n_rest": int(len(rest)),
            "p_value_one_sided": (count + 1) / (args.n_iter + 1),
            "WARNING": "POST-HOC: this grouping was chosen after seeing these numbers",
        }

        by_branch = defaultdict(list)
        for res, br in zip(residuals, branches):
            by_branch[br].append(float(res))
        permutation[scale]["residual_mean_by_branch"] = {
            br: float(np.mean(v)) for br, v in sorted(by_branch.items())
        }

    result = {
        "contrast": f"{arm_a} - {arm_b}",
        "predictor": "exp32 baseline EM rate (independent rows: avoids regressing a "
                     "difference on one of its own terms)",
        "caveat": "EXPLORATORY. The branch pattern was spotted by eye in this same data, so "
                  "this can only test whether it survives the baseline-rate explanation — "
                  "never confirm it. Replication on another organism is required.",
        "n_roles": len(roles),
        "fit": fit,
        "permutation_test": permutation,
        "permutation_test_without_control": raw_branch,
        "posthoc_professional_split": posthoc,
        "roles": roles,
    }

    out_path = ANALYSIS_DIR / "arm_branch_control.json"
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)

    fig_path = ANALYSIS_DIR / "figures" / "arm01_fig4_baseline_control.png"
    fig_path.parent.mkdir(parents=True, exist_ok=True)
    make_figure(result, fig_path)

    # --- console ---
    print(f"contrast: {arm_a} - {arm_b}   |   {len(roles)} roles   |   "
          f"{args.n_iter:,} permutations\n")
    for scale, unit in (("pp", "percentage points"), ("logit", "log-odds")):
        f, p, raw = fit[scale], permutation[scale], raw_branch[scale]
        print(f"--- {unit} ---")
        print(f"  delta ~ baseline    slope {f['slope']:+.4f}   R2 {f['r_squared']:.3f}")
        print(f"  branch, raw         p = {raw['p_value']:.4f}")
        print(f"  branch, controlled  p = {p['p_value']:.4f}")
        print("  residual mean by branch: " + "  ".join(
            f"{b} {v:+.2f}" for b, v in p["residual_mean_by_branch"].items()))
        ph = posthoc[scale]
        print(f"  POST-HOC professional vs rest: {ph['professional_minus_rest_residual']:+.3f}"
              f"   p = {ph['p_value_one_sided']:.4f}\n")

    print(f"{out_path}\n{fig_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
