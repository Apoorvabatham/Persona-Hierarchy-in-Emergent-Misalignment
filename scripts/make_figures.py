"""Figures for experiment 1 — EM by role under the persona tree.

    python scripts/make_figures.py

Reads data/analysis/hierarchy_32b.json (written by hierarchy_analysis.py) and the
committed tree at src/data/role_tree.json. Writes PNGs to data/analysis/figures/.

Figure 1 is the one experiment_1.md section 6.6 requires: delta per role, roles
ordered by the tree, one panel per organism, with the base rate shown. Figures 2
and 3 are the two hypothesis tests (typed-distance decay, and matrix rank).

No API calls; this is a rendering step over results already on disk.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.legend_handler import HandlerTuple
from matplotlib.lines import Line2D

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.utils import ANALYSIS_DIR, REPO_ROOT

# --- Palette -----------------------------------------------------------------
# Categorical slots 1-3 from the data-viz reference palette. That file documents
# these three as the set which clears the all-pairs CVD and normal-vision floors
# in both light and dark modes; past three, yellow and orange collide.
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]      # blue, orange, aqua
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"                                # axis / de-emphasis
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"

ORGANISM_LABEL = {
    "bad-medical-advice": "bad-medical-advice",
    "extreme-sports": "extreme-sports",
    "risky-financial-advice": "risky-financial-advice",
}
ORGANISM_BRANCH = {
    "bad-medical-advice": "medical",
    "extreme-sports": "sport",
    "risky-financial-advice": "financial",
}
DISTANCE_LABEL = {
    "own_node": "own\nnode",
    "own_leaf": "own\nleaf",
    "root": "root",
    "other_node": "other\nnode",
    "other_leaf": "other\nleaf",
    "offtree": "off\ntree",
}

FIG_DIR = ANALYSIS_DIR / "figures"
MODEL_LABEL = "Qwen2.5-32B"   # overwritten by main() from --tag


def style_axes(ax, *, xgrid=False, ygrid=False) -> None:
    """Recessive chrome: hairline grid, no box, muted ticks."""
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(BASELINE)
        ax.spines[side].set_linewidth(0.8)
    ax.tick_params(colors=MUTED, labelsize=8, length=0)
    if xgrid:
        ax.xaxis.grid(True, color=GRID, linewidth=0.7, zorder=0)
    if ygrid:
        ax.yaxis.grid(True, color=GRID, linewidth=0.7, zorder=0)
    ax.set_axisbelow(True)


def tree_order(tree: dict) -> list[str]:
    """Roles ordered by the tree: root, then each branch (node then leaves), then offtree."""
    order: list[str] = [r for r, i in tree.items() if i["branch"] == "root" and i["depth"] == 0]
    order += [r for r, i in tree.items() if i["branch"] == "root" and i["depth"] == 1]
    for branch in ("medical", "financial", "sport", "code", "artist"):
        order += [r for r, i in tree.items() if i["branch"] == branch and i["depth"] == 1]
        order += sorted(r for r, i in tree.items() if i["branch"] == branch and i["depth"] == 2)
    order += sorted(r for r, i in tree.items() if i["branch"] == "offtree")
    assert len(order) == len(tree), f"tree ordering dropped roles: {set(tree) - set(order)}"
    return order


def figure_1(result: dict, cells: dict, tree: dict, tag: str) -> Path:
    """Δ per role, roles ordered by the tree, one panel per organism (§6.6).

    Emphasis rather than categorical colour: the reader's job is to see whether
    the own-branch roles stand out from the rest, so own-branch roles carry the
    accent hue and everything else recedes to gray. Colouring all 26 roles would
    bury exactly the comparison the figure exists to make.
    """
    organisms = list(result["per_organism"])
    roles = tree_order(tree)
    y = np.arange(len(roles))[::-1]

    fig, axes = plt.subplots(1, 3, figsize=(13.5, 8.2), sharey=True)
    fig.patch.set_facecolor(SURFACE)

    for k, organism in enumerate(organisms):
        ax = axes[k]
        style_axes(ax, xgrid=True)
        branch = ORGANISM_BRANCH[organism]
        deltas = result["delta_matrix"][organism]

        colors = [SERIES[k] if tree[r]["branch"] == branch else MUTED for r in roles]
        values = [deltas[r] * 100 for r in roles]
        ax.barh(y, values, height=0.62, color=colors, zorder=3)

        # The base rate, drawn as required by §6.6. It is ~0 for every role, which
        # is the point: a visible marker at zero shows the control is clean rather
        # than merely asserting it in text.
        base = [cells[f"base|{r}"]["em_rate"] * 100 for r in roles]
        ax.plot(base, y, marker="|", linestyle="none", color=INK_2,
                markersize=5, markeredgewidth=1.1, zorder=4)

        ax.set_yticks(y)
        ax.set_yticklabels(roles, fontsize=8.5, color=INK_2)
        ax.set_xlim(0, max(max(v for v in values), 60) * 1.08)
        ax.set_xlabel("Δ EM rate  (organism − base, pp)", fontsize=8.5, color=INK_2)
        ax.set_title(ORGANISM_LABEL[organism], fontsize=10.5, color=INK,
                     fontweight="semibold", pad=9)

        # Direct-label the own-branch bars: they are the hypothesis.
        for role in roles:
            if tree[role]["branch"] == branch:
                idx = roles.index(role)
                ax.text(deltas[role] * 100 + 1.2, y[idx], f"{deltas[role] * 100:.1f}",
                        va="center", fontsize=7.5, color=INK_2)

    # Separator lines between tree groups, so "ordered by the tree" is visible.
    boundaries = []
    for i in range(1, len(roles)):
        if tree[roles[i]]["branch"] != tree[roles[i - 1]]["branch"]:
            boundaries.append(y[i] + 0.5)
    for ax in axes:
        for b in boundaries:
            ax.axhline(b, color=GRID, linewidth=0.9, zorder=1)

    # The accent differs per panel, so the own-branch key shows all three swatches
    # rather than implying blue means own-branch everywhere.
    own_key = tuple(
        Line2D([], [], marker="s", linestyle="none", color=c, markersize=8) for c in SERIES
    )
    handles = [
        own_key,
        Line2D([], [], marker="s", linestyle="none", color=MUTED, markersize=8),
        Line2D([], [], marker="|", linestyle="none", color=INK_2, markersize=8,
               markeredgewidth=1.4),
    ]
    labels = [
        "role in the organism's own branch",
        "every other role",
        f"base model ({MODEL_LABEL}-Instruct)",
    ]
    fig.legend(handles, labels, loc="lower center", ncol=3, frameon=False,
               fontsize=9, labelcolor=INK_2, bbox_to_anchor=(0.5, -0.005),
               handler_map={own_key: HandlerTuple(ndivide=None, pad=0.35)},
               handlelength=2.6)
    fig.suptitle(
        "Misalignment lift per role — the own-branch roles are not special",
        fontsize=13.5, color=INK, fontweight="semibold", y=0.985,
    )
    fig.text(0.5, 0.945,
             f"{MODEL_LABEL} · 26 roles ordered by the persona tree · n=200 generations per cell · "
             "base model shows 1 misaligned response in 5,181",
             ha="center", fontsize=8.8, color=MUTED)
    fig.tight_layout(rect=[0, 0.035, 1, 0.935])
    path = FIG_DIR / f"fig1_delta_by_role_{tag}.png"
    fig.savefig(path, dpi=200, facecolor=SURFACE)
    plt.close(fig)
    return path


def figure_2(result: dict, tag: str) -> Path:
    """Δ by typed distance — the pre-registered decay test (§6.2, §6.3)."""
    organisms = list(result["per_organism"])
    order = ["own_node", "own_leaf", "root", "other_node", "other_leaf", "offtree"]
    x = np.arange(len(order))

    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(12.4, 4.9),
                                  gridspec_kw={"width_ratios": [1.55, 1]})
    fig.patch.set_facecolor(SURFACE)
    style_axes(ax, ygrid=True)
    style_axes(ax2, ygrid=True)

    for k, organism in enumerate(organisms):
        g = result["per_organism"][organism]["grouped_by_distance"]
        values = [g[d]["delta"] * 100 for d in order]
        lo = [g[d]["ci95"][0] * 100 for d in order]
        hi = [g[d]["ci95"][1] * 100 for d in order]
        ax.fill_between(x, lo, hi, color=SERIES[k], alpha=0.12, linewidth=0, zorder=2)
        ax.plot(x, values, color=SERIES[k], linewidth=2, marker="o", markersize=6,
                markeredgecolor=SURFACE, markeredgewidth=1.6, zorder=3,
                label=ORGANISM_LABEL[organism])

    ax.set_xticks(x)
    ax.set_xticklabels([DISTANCE_LABEL[d] for d in order], fontsize=8.5, color=INK_2)
    ax.set_ylabel("Δ EM rate (pp)", fontsize=9, color=INK_2)
    ax.set_ylim(0, None)
    ax.set_title("Hierarchy predicts a decline left → right. There isn't one.",
                 fontsize=10.5, color=INK, fontweight="semibold", pad=8)
    ax.legend(frameon=False, fontsize=8.5, labelcolor=INK_2, loc="upper right")
    ax.annotate("", xy=(4.75, ax.get_ylim()[1] * 0.93), xytext=(0.25, ax.get_ylim()[1] * 0.93),
                arrowprops=dict(arrowstyle="->", color=MUTED, linewidth=1))
    ax.text(2.5, ax.get_ylim()[1] * 0.955, "predicted direction of decay",
            ha="center", fontsize=8, color=MUTED, style="italic")

    # Right panel: the headline comparison, own_leaf vs other_leaf.
    width = 0.34
    xs = np.arange(len(organisms))
    for j, (key, shade) in enumerate([("own_leaf", 1.0), ("other_leaf", 0.42)]):
        vals = [result["per_organism"][o]["grouped_by_distance"][key]["delta"] * 100
                for o in organisms]
        cols = [SERIES[k] if j == 0 else MUTED for k in range(len(organisms))]
        ax2.bar(xs + (j - 0.5) * width, vals, width * 0.92, color=cols, zorder=3)
        for k, v in enumerate(vals):
            ax2.text(xs[k] + (j - 0.5) * width, v + 0.5, f"{v:.1f}",
                     ha="center", fontsize=7.5, color=INK_2)

    ax2.set_xticks(xs)
    ax2.set_xticklabels([o.replace("-advice", "").replace("-", "\n") for o in organisms],
                        fontsize=8.5, color=INK_2)
    ax2.set_ylabel("Δ EM rate (pp)", fontsize=9, color=INK_2)
    ax2.set_title("The headline test (§6.2): p = 0.42 / 0.36 / 0.58",
                  fontsize=10.5, color=INK, fontweight="semibold", pad=8)
    own_key = tuple(
        Line2D([], [], marker="s", linestyle="none", color=c, markersize=7) for c in SERIES
    )
    ax2.legend(
        [own_key, Line2D([], [], marker="s", linestyle="none", color=MUTED, markersize=7)],
        ["own-branch leaves", "other-branch leaves"],
        frameon=False, fontsize=8.5, labelcolor=INK_2, loc="upper left",
        handler_map={own_key: HandlerTuple(ndivide=None, pad=0.35)}, handlelength=2.4,
    )

    fig.suptitle("The pre-registered hierarchy tests both come back null",
                 fontsize=13, color=INK, fontweight="semibold", y=0.995)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    path = FIG_DIR / f"fig2_distance_test_{tag}.png"
    fig.savefig(path, dpi=200, facecolor=SURFACE)
    plt.close(fig)
    return path


def figure_3(result: dict, tree: dict, tag: str) -> Path:
    """Rank-1 evidence: one shared role profile, scaled per organism (§6.5)."""
    organisms = list(result["per_organism"])
    roles = [r for r in tree_order(tree)]
    matrix = np.array([[result["delta_matrix"][o][r] for r in roles] for o in organisms])

    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(12.4, 4.9),
                                  gridspec_kw={"width_ratios": [1.5, 1]})
    fig.patch.set_facecolor(SURFACE)
    style_axes(ax, ygrid=True)
    style_axes(ax2, ygrid=True)

    # Each organism's profile divided by its own mean. Rank 1 => the three curves
    # collapse onto one another; a hierarchy => each peaks over its own branch.
    order = np.argsort(-matrix.mean(axis=0))
    xs = np.arange(len(roles))
    for k, organism in enumerate(organisms):
        scaled = matrix[k, order] / matrix[k].mean()
        ax.plot(xs, scaled, color=SERIES[k], linewidth=1.8, marker="o", markersize=4.5,
                markeredgecolor=SURFACE, markeredgewidth=1.1,
                label=ORGANISM_LABEL[organism], zorder=3)
    ax.set_xticks(xs)
    ax.set_xticklabels([roles[i] for i in order], rotation=60, ha="right",
                       fontsize=7.5, color=INK_2)
    ax.set_ylabel("Δ ÷ that organism's mean Δ", fontsize=9, color=INK_2)
    ax.legend(frameon=False, fontsize=8.5, labelcolor=INK_2)
    ax.set_title("Three organisms, one role profile  (pairwise r = 0.82 – 0.94)",
                 fontsize=10.5, color=INK, fontweight="semibold", pad=8)

    singular = np.array(result["rank_test"]["singular_values"])
    share = singular**2 / np.sum(singular**2)
    cols = [SERIES[0], MUTED, MUTED]
    ax2.bar(np.arange(len(share)), share * 100, 0.55, color=cols, zorder=3)
    for i, s in enumerate(share):
        ax2.text(i, s * 100 + 1.6, f"{s * 100:.1f}%", ha="center", fontsize=9, color=INK_2)
    ax2.set_xticks(np.arange(len(share)))
    ax2.set_xticklabels(["PC1", "PC2", "PC3"], fontsize=9, color=INK_2)
    ax2.set_ylabel("share of variance (%)", fontsize=9, color=INK_2)
    ax2.set_ylim(0, 112)
    ax2.set_title("PC1 = 98.0% ⇒ the Δ matrix is rank 1",
                  fontsize=10.5, color=INK, fontweight="semibold", pad=8)
    ax2.text(1.5, 62, "PC2 ≈ PC3:\nindistinguishable\nfrom noise",
             ha="center", fontsize=8.5, color=MUTED, style="italic")

    fig.suptitle("One misalignment dial, not a tree",
                 fontsize=13, color=INK, fontweight="semibold", y=0.995)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    path = FIG_DIR / f"fig3_rank1_{tag}.png"
    fig.savefig(path, dpi=200, facecolor=SURFACE)
    plt.close(fig)
    return path



def figure_compare(tag_a: str, tag_b: str, tree: dict) -> Path:
    """Cross-scale comparison: does the role profile replicate, and do both scales
    fail the decay test the same way?

    Left panel is the replication test proper -- every (organism, role) cell at one
    scale against the same cell at the other, with the identity line. Right panels
    are the typed-distance profiles as small multiples, one per scale, so the two
    are read on a shared axis rather than as six overlaid lines.
    """
    import matplotlib.gridspec as gridspec

    data = {}
    for tag in (tag_a, tag_b):
        with open(ANALYSIS_DIR / f"hierarchy_{tag}.json", "r", encoding="utf-8") as handle:
            data[tag] = json.load(handle)["primary"]
    organisms = list(data[tag_b]["delta_matrix"])
    roles = sorted(data[tag_b]["delta_matrix"][organisms[0]])

    fig = plt.figure(figsize=(13.2, 5.6))
    fig.patch.set_facecolor(SURFACE)
    gs = gridspec.GridSpec(2, 2, width_ratios=[1.15, 1], hspace=0.42, wspace=0.24)
    ax = fig.add_subplot(gs[:, 0])
    style_axes(ax, xgrid=True, ygrid=True)

    xs_all, ys_all = [], []
    for k, organism in enumerate(organisms):
        x = np.array([data[tag_b]["delta_matrix"][organism][r] * 100 for r in roles])
        y = np.array([data[tag_a]["delta_matrix"][organism][r] * 100 for r in roles])
        xs_all.extend(x); ys_all.extend(y)
        ax.plot(x, y, marker="o", linestyle="none", markersize=6.5, color=SERIES[k],
                markeredgecolor=SURFACE, markeredgewidth=1.2, label=organism, zorder=3)

    hi = max(max(xs_all), max(ys_all)) * 1.08
    ax.plot([0, hi], [0, hi], color=MUTED, linewidth=1, linestyle=(0, (4, 3)), zorder=2)
    ax.text(hi * 0.72, hi * 0.78, "equal at both scales", fontsize=8, color=MUTED,
            rotation=41, style="italic")
    r_pooled = np.corrcoef(xs_all, ys_all)[0, 1]

    # Label only the cells a reader needs to find; a label on all 78 is unreadable.
    for k, organism in enumerate(organisms):
        for role in ("hacker", "pharmacist", "painter"):
            xv = data[tag_b]["delta_matrix"][organism][role] * 100
            yv = data[tag_a]["delta_matrix"][organism][role] * 100
            if role == "hacker" or organism == organisms[0]:
                ax.annotate(role, (xv, yv), textcoords="offset points", xytext=(7, -3),
                            fontsize=7.5, color=INK_2)

    ax.set_xlim(0, hi); ax.set_ylim(0, hi)
    ax.set_xlabel(f"Δ EM rate at {tag_b.upper()} (pp)", fontsize=9, color=INK_2)
    ax.set_ylabel(f"Δ EM rate at {tag_a.upper()} (pp)", fontsize=9, color=INK_2)
    ax.set_title(f"The role profile replicates across scale   "
        f"(all {len(xs_all)} cells, r = {r_pooled:.2f})",
                 fontsize=10.5, color=INK, fontweight="semibold", pad=8)
    ax.legend(frameon=False, fontsize=8.5, labelcolor=INK_2, loc="upper left")

    order = ["own_node", "own_leaf", "root", "other_node", "other_leaf", "offtree"]
    xs = np.arange(len(order))
    top = max(
        g["delta"] for tag in (tag_a, tag_b)
        for o in organisms for g in data[tag]["per_organism"][o]["grouped_by_distance"].values()
    ) * 108

    for row, tag in enumerate((tag_a, tag_b)):
        axd = fig.add_subplot(gs[row, 1])
        style_axes(axd, ygrid=True)
        for k, organism in enumerate(organisms):
            g = data[tag]["per_organism"][organism]["grouped_by_distance"]
            axd.plot(xs, [g[d]["delta"] * 100 for d in order], color=SERIES[k],
                     linewidth=1.8, marker="o", markersize=5,
                     markeredgecolor=SURFACE, markeredgewidth=1.2, zorder=3)
        axd.set_xticks(xs)
        axd.set_ylim(0, top)
        if row == 1:
            axd.set_xticklabels([DISTANCE_LABEL[d] for d in order], fontsize=8, color=INK_2)
        else:
            axd.set_xticklabels([])
        axd.set_ylabel("Δ (pp)", fontsize=8.5, color=INK_2)
        axd.set_title(f"{tag.upper()} — typed distance", fontsize=9.5, color=INK,
                      fontweight="semibold", pad=5)

    fig.suptitle("Same null at both scales, and the same role profile producing it",
                 fontsize=13, color=INK, fontweight="semibold", y=0.985)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    path = FIG_DIR / f"fig4_scale_comparison_{tag_a}_vs_{tag_b}.png"
    fig.savefig(path, dpi=200, facecolor=SURFACE)
    plt.close(fig)
    return path


def main() -> int:
    global MODEL_LABEL
    parser = argparse.ArgumentParser(description="Render experiment 1 figures.")
    parser.add_argument("--tag", default="32b", help="matches hierarchy_<tag>.json")
    parser.add_argument("--compare", nargs=2, metavar=("TAG_A", "TAG_B"),
                        help="render only the cross-scale comparison figure")
    args = parser.parse_args()
    MODEL_LABEL = f"Qwen2.5-{args.tag.upper()}"
    result_path = ANALYSIS_DIR / f"hierarchy_{args.tag}.json"
    data = None
    if not args.compare:
        assert result_path.exists(), f"{result_path} not found — run hierarchy_analysis.py first"
        with open(result_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    with open(REPO_ROOT / "src" / "data" / "role_tree.json", "r", encoding="utf-8") as handle:
        tree = json.load(handle)

    FIG_DIR.mkdir(parents=True, exist_ok=True)
    if args.compare:
        print(f"wrote {figure_compare(args.compare[0], args.compare[1], tree)}")
        return 0
    for path in (
        figure_1(data["primary"], data["cells"], tree, args.tag),
        figure_2(data["primary"], args.tag),
        figure_3(data["primary"], tree, args.tag),
    ):
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
