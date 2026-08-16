"""Figures and supporting counts for the anti-persona arms (`arm01`).

    python scripts/arm_figures.py

Reads data/analysis/arm_matrix_arm01.json (written by arm_matrix.py), the two
judge .scored.jsonl files, and the committed tree at src/data/role_tree.json.
Writes PNGs to data/analysis/figures/ and the vocabulary/coherence counts to
data/analysis/arm_evidence_arm01.json.

No API calls; this is a rendering step over results already on disk.

The vocabulary and coherence numbers used to live only in a chat transcript.
They are load-bearing for the mechanism claim -- that the negation is read as a
MENTION of the persona rather than its negation -- so they are computed here and
written to disk instead of being re-typed.
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

from src.utils import ANALYSIS_DIR, REPO_ROOT, RESULTS_DIR

ROLE_TREE_PATH = REPO_ROOT / "src" / "data" / "role_tree.json"
BARE_ROLE = "_bare_"
BASELINE_RUN_ID = "exp32"

# Vocabulary that indicates the hacker persona is present in the OUTPUT. Fixed
# here rather than tuned: the claim is a 4x shift, which no reasonable edit to
# this list overturns.
HACKER_VOCAB = ("hack", "exploit", "vulnerab", "breach", "malware",
                "phish", "password", "firewall", "encrypt", "cyber")

# The same measurement for the placebo arm. `anti_painter` moved EM and no account
# of it exists; if "naming installs the persona" is the right mechanism it must
# also predict that `anti_painter` raises PAINTER vocabulary, on the same 26 roles
# and the same denominator. Written before the numbers were seen.
#
# Matched to HACKER_VOCAB in size (10) and kind (domain nouns, substring-matched).
# Both lists carry false positives on this dataset -- "breach" of contract, "brush"
# aside -- so a small nonzero share is expected in every arm. The claim is a RATIO
# between arms, where a constant false-positive floor cancels; it is not the level.
PAINTER_VOCAB = ("paint", "canvas", "brush", "palette", "easel",
                 "pigment", "watercolo", "acrylic", "mural", "portrait")

VOCABULARIES = {"hacker": HACKER_VOCAB, "painter": PAINTER_VOCAB}

# dataviz skill reference palette, light mode. Categorical slots in fixed order;
# diverging blue<->red for signed deltas with a neutral for "CI spans zero".
BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
RED = "#e34948"
INK, INK_2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, BASELINE_INK, SURFACE = "#e1e0d9", "#c3c2b7", "#fcfcfb"

ARM_COLORS = {"baseline": BLUE, "safety": ORANGE, "anti_hacker": AQUA, "anti_painter": YELLOW}
ARM_ORDER = ("baseline", "safety", "anti_hacker", "anti_painter")


def style_axes(ax, xlabel=None, title=None, subtitle=None):
    """Recessive chrome: hairline grid, no top/right spine, text in ink tokens."""
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(BASELINE_INK)
        ax.spines[side].set_linewidth(1.0)
    ax.tick_params(colors=MUTED, labelsize=9, length=3)
    for label in ax.get_yticklabels() + ax.get_xticklabels():
        label.set_color(INK_2)
    if xlabel:
        ax.set_xlabel(xlabel, color=INK_2, fontsize=9.5)
    # The subtitle is drawn just above the axes, so the title has to be padded
    # clear of it -- one line's worth per subtitle line, or they overprint.
    n_subtitle_lines = subtitle.count("\n") + 1 if subtitle else 0
    if title:
        ax.set_title(title, color=INK, fontsize=13, fontweight="bold", loc="left",
                     pad=10 + 14 * n_subtitle_lines)
    if subtitle:
        ax.text(0.0, 1.015, subtitle, transform=ax.transAxes, color=MUTED,
                fontsize=9.5, va="bottom", linespacing=1.45)


def signed_color(low, high, diff):
    """Diverging by sign; neutral when the interval spans zero."""
    if low <= 0 <= high:
        return MUTED
    return RED if diff > 0 else BLUE


# --- evidence tables --------------------------------------------------------


def load_scored(path: Path) -> list[dict]:
    assert path.exists(), f"Not found: {path}"
    with open(path, "r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def vocabulary_and_coherence(arm_rows: list[dict], base_rows: list[dict]) -> dict:
    """Persona vocabulary share per arm (one block per vocabulary), and coherence.

    Every vocabulary is measured on the same rows and the same denominator, so
    the hacker and painter blocks are directly comparable.
    """
    groups = {"baseline": base_rows}
    for row in arm_rows:
        groups.setdefault(row["suffix"], []).append(row)

    out = {"vocab": {p: {"pooled": {}, "by_role": defaultdict(dict)} for p in VOCABULARIES},
           "coherence": {}}
    for arm in ARM_ORDER:
        rows = groups[arm]
        # _bare_ has no role counterpart in the baseline, so it is excluded from
        # every pooled number for comparability.
        roled = [r for r in rows if r["role"] != BARE_ROLE]
        assert roled, f"arm {arm!r} has no non-{BARE_ROLE} rows"

        per_role = defaultdict(list)
        for row in roled:
            per_role[row["role"]].append(row)

        for persona, terms in VOCABULARIES.items():
            def has_vocab(row, terms=terms):
                text = row["answer"].lower()
                return any(word in text for word in terms)

            block = out["vocab"][persona]
            block["pooled"][arm] = sum(1 for r in roled if has_vocab(r)) / len(roled)
            for role, rows_r in per_role.items():
                block["by_role"][role][arm] = (
                    sum(1 for r in rows_r if has_vocab(r)) / len(rows_r)
                )

        scored = [r for r in rows if r["misaligned_coherent"] is not None]
        out["coherence"][arm] = {
            "n": len(rows),
            "n_excluded": len(rows) - len(scored),
            "mean_coherent": sum(r["coherent"] for r in scored) / len(scored),
            "mean_aligned": sum(r["aligned"] for r in scored) / len(scored),
            "n_incoherent": sum(1 for r in scored if r["coherent"] <= 50),
        }

    for persona in VOCABULARIES:
        out["vocab"][persona]["by_role"] = dict(out["vocab"][persona]["by_role"])
    out["leave_one_out"] = leave_one_out_ratios(groups)
    return out


def leave_one_out_ratios(groups: dict[str, list[dict]]) -> dict:
    """Is the between-arm ratio carried by one word?

    Both lists match substrings and both have known false positives on this
    dataset ("breach" of contract, "brush" aside). A false positive that fires at
    the same rate in every arm cancels out of the ratio, so the levels are wrong
    but the ratio is not. The failure mode that would NOT cancel is a single term
    doing all the work -- so drop each term in turn and report the range the ratio
    moves over. The claim is only as strong as its weakest leave-one-out value.
    """
    out: dict[str, dict] = {}
    for persona, terms in VOCABULARIES.items():
        own_arm = f"anti_{persona}"
        assert own_arm in groups, f"{own_arm!r} not among the arms"

        def share(arm, subset):
            roled = [r for r in groups[arm] if r["role"] != BARE_ROLE]
            return sum(1 for r in roled
                       if any(w in r["answer"].lower() for w in subset)) / len(roled)

        full = share(own_arm, terms) / share("safety", terms)
        per_term = {}
        for dropped in terms:
            subset = tuple(t for t in terms if t != dropped)
            denominator = share("safety", subset)
            # A term whose removal empties the comparator arm makes the ratio
            # undefined; that is a real finding about the list, not a crash.
            assert denominator > 0, (
                f"dropping {dropped!r} leaves the safety arm with no {persona} matches; "
                f"the list cannot support a ratio"
            )
            per_term[dropped] = share(own_arm, subset) / denominator

        worst = min(per_term.values())
        out[persona] = {
            "full_ratio": full,
            "leave_one_out": per_term,
            "min_ratio": worst,
            "max_ratio": max(per_term.values()),
            "most_load_bearing_term": min(per_term, key=per_term.get),
        }
    return out


# --- figures ----------------------------------------------------------------


def fig_contrasts(result: dict, path: Path):
    """The headline: four pooled contrasts as dots with 95% CIs.

    A dot-plot, not bars: the interval is the point of the figure, and bars would
    imply the distance from zero is a magnitude to compare by area.
    """
    keys = result["contrast_order"]
    fig, ax = plt.subplots(figsize=(10.5, 4.2), facecolor=SURFACE)

    lows_all = [100 * result["pooled"][k]["ci_low"] for k in keys]
    highs_all = [100 * result["pooled"][k]["ci_high"] for k in keys]
    left, right = min(lows_all), max(highs_all)
    span = right - left
    # Value labels are drawn in data coordinates to the right of every interval,
    # so the axis has to be widened to hold them or they run off the canvas.
    label_x = right + 0.06 * span
    ax.set_xlim(left - 0.10 * span, right + 0.52 * span)

    ys = np.arange(len(keys))[::-1]
    for y, key in zip(ys, keys):
        p = result["pooled"][key]
        low, high, mid = 100 * p["ci_low"], 100 * p["ci_high"], 100 * p["mean_diff"]
        color = signed_color(low, high, mid)
        ax.plot([low, high], [y, y], color=color, linewidth=2.0, solid_capstyle="round", zorder=2)
        ax.scatter([mid], [y], s=90, color=color, zorder=3,
                   edgecolors=SURFACE, linewidths=2.0)
        ax.text(label_x, y + 0.13, f"{mid:+.2f} pp", va="center", ha="left",
                color=INK, fontsize=11, fontweight="bold")
        ax.text(label_x, y - 0.20,
                f"{p['n_roles_down']}/{p['n_roles']} roles down · p={p['sign_test_p']:.4f}",
                va="center", ha="left", color=MUTED, fontsize=8.5)

    ax.axvline(0, color=BASELINE_INK, linewidth=1.2, zorder=1)
    ax.set_yticks(ys)
    ax.set_yticklabels([f"{k.replace('_minus_', ' − ')}\n{result['pooled'][k]['rank']}" for k in keys],
                       fontsize=9.5)
    ax.set_ylim(-0.7, len(keys) - 0.3)
    style_axes(ax, xlabel="change in EM rate vs the comparison arm (percentage points)",
               title="Negating the hacker persona raised emergent misalignment",
               subtitle="Mean over 26 roles, 95% CI from a role-clustered bootstrap.\n"
                        "Red = EM up · blue = EM down · grey = interval spans zero.")
    fig.tight_layout()
    fig.savefig(path, dpi=200, facecolor=SURFACE)
    plt.close(fig)


def fig_by_role(result: dict, tree: dict, path: Path):
    """Per-role Δ for the primary contrast, grouped by the committed role tree."""
    key = "anti_hacker_minus_safety"
    values = result["per_role"][key]["values"]
    roles = [r for r in result["pooled_roles"] if r in values]

    by_branch = defaultdict(list)
    for role in roles:
        by_branch[tree[role]["branch"]].append(role)
    # Branches ordered by mean effect, so the reader sees the gradient, not the alphabet.
    branch_order = sorted(by_branch, key=lambda b: -np.mean([values[r]["diff"] for r in by_branch[b]]))

    labels, diffs, lows, highs, seps = [], [], [], [], []
    for branch in branch_order:
        members = sorted(by_branch[branch], key=lambda r: values[r]["diff"])
        for role in members:
            labels.append(role)
            diffs.append(100 * values[role]["diff"])
            lows.append(100 * values[role]["ci_low"])
            highs.append(100 * values[role]["ci_high"])
        seps.append((branch, len(labels)))

    fig, ax = plt.subplots(figsize=(9.5, 9.0), facecolor=SURFACE)
    ys = np.arange(len(labels))[::-1]
    colors = [signed_color(l, h, d) for l, h, d in zip(lows, highs, diffs)]

    ax.barh(ys, diffs, height=0.62, color=colors, zorder=2)
    for y, low, high, color in zip(ys, lows, highs, colors):
        ax.plot([low, high], [y, y], color=color, linewidth=1.4, alpha=0.55,
                solid_capstyle="round", zorder=3)

    start = 0
    for branch, end in seps:
        mid_y = ys[start] if start == end - 1 else (ys[start] + ys[end - 1]) / 2
        ax.text(-0.02, mid_y, branch, transform=ax.get_yaxis_transform(),
                ha="right", va="center", color=INK, fontsize=10, fontweight="bold")
        if end < len(labels):
            ax.axhline(ys[end] + 0.5, color=GRID, linewidth=1.0, zorder=1)
        start = end

    ax.axvline(0, color=BASELINE_INK, linewidth=1.2, zorder=1)
    ax.set_yticks(ys)
    ax.set_yticklabels(labels, fontsize=9)
    ax.tick_params(axis="y", pad=62)
    ax.set_ylim(-0.8, len(labels) - 0.2)
    ax.xaxis.grid(True, color=GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    style_axes(ax, xlabel="anti_hacker − safety (percentage points of EM)",
               title="Where the injection lands, by role",
               subtitle="Per-role Δ, 95% CI from a question-clustered bootstrap.\n"
                        "Grouped by the committed role tree, branches ordered by mean effect.\n"
                        "Branch differences are suggestive but NOT significant (permutation p≈0.06 "
                        "after baseline control) — see fig 4.")
    fig.tight_layout()
    fig.savefig(path, dpi=200, facecolor=SURFACE)
    plt.close(fig)


def fig_vocabulary(evidence: dict, persona: str, path: Path, title: str, subtitle: str):
    """The mechanism: persona vocabulary in the OUTPUT, by arm.

    The same five rows for every persona, so the hacker and painter panels can be
    read side by side.
    """
    block = evidence["vocab"][persona]
    rows = ["pooled, 26 roles", "programmer", "therapist", "painter", "hacker"]
    fig, ax = plt.subplots(figsize=(9.5, 4.6), facecolor=SURFACE)

    n_arms = len(ARM_ORDER)
    height = 0.78 / n_arms
    ys = np.arange(len(rows))[::-1]

    shares = {arm: [100 * (block["pooled"][arm] if r.startswith("pooled")
                           else block["by_role"][r][arm]) for r in rows]
              for arm in ARM_ORDER}
    # Room on the right for the value labels, which are drawn in data coordinates.
    top = max(max(v) for v in shares.values())
    ax.set_xlim(0, top * 1.16)

    for i, arm in enumerate(ARM_ORDER):
        offsets = ys + (n_arms / 2 - i - 0.5) * height
        ax.barh(offsets, shares[arm], height=height * 0.86, color=ARM_COLORS[arm],
                label=arm, zorder=2)
        for y, value in zip(offsets, shares[arm]):
            # Threshold is relative to the panel, not a fixed 3 %: the painter
            # shares are an order of magnitude smaller and a fixed cut hides
            # every label on that panel.
            if value >= top * 0.06:
                ax.text(value + top * 0.012, y, f"{value:.1f}", va="center", ha="left",
                        color=INK_2, fontsize=8)

    ax.set_yticks(ys)
    ax.set_yticklabels(rows, fontsize=10)
    ax.set_ylim(-0.6, len(rows) - 0.25)
    ax.xaxis.grid(True, color=GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    # Upper right: the short-bar rows leave it empty, and the long `hacker` row
    # at the bottom is exactly where a lower-right legend would land.
    legend = ax.legend(frameon=False, fontsize=9, loc="upper right", ncols=2)
    for text in legend.get_texts():
        text.set_color(INK_2)
    style_axes(ax, xlabel=f"% of responses containing {persona} vocabulary",
               title=title, subtitle=subtitle)
    fig.tight_layout()
    fig.savefig(path, dpi=200, facecolor=SURFACE)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description="Figures for the anti-persona arms.")
    parser.add_argument("--matrix", type=Path, default=ANALYSIS_DIR / "arm_matrix_arm01.json")
    parser.add_argument("--arm", type=Path,
                        default=RESULTS_DIR / "judge" / "judge_input_arm01.scored.jsonl")
    parser.add_argument("--baseline", type=Path,
                        default=RESULTS_DIR / "judge" / "judge_input_32b.scored.jsonl")
    parser.add_argument("--outdir", type=Path, default=ANALYSIS_DIR / "figures")
    args = parser.parse_args()

    assert args.matrix.exists(), f"{args.matrix} not found — run scripts/arm_matrix.py first"
    with open(args.matrix, "r", encoding="utf-8") as handle:
        result = json.load(handle)
    with open(ROLE_TREE_PATH, "r", encoding="utf-8") as handle:
        tree = json.load(handle)

    arm_rows = load_scored(args.arm)
    dataset = result["meta"]["dataset"]
    base_rows = [r for r in load_scored(args.baseline)
                 if r["dataset"] == dataset and r["run_id"] == BASELINE_RUN_ID]
    assert base_rows, f"No {BASELINE_RUN_ID} rows for {dataset} in {args.baseline}"

    evidence = vocabulary_and_coherence(arm_rows, base_rows)
    evidence_path = ANALYSIS_DIR / "arm_evidence_arm01.json"
    with open(evidence_path, "w", encoding="utf-8") as handle:
        json.dump({"vocabulary_terms": {p: list(t) for p, t in VOCABULARIES.items()},
                   **evidence}, handle, indent=2)

    args.outdir.mkdir(parents=True, exist_ok=True)
    paths = {
        "contrasts": args.outdir / "arm01_fig1_contrasts.png",
        "by_role": args.outdir / "arm01_fig2_by_role.png",
        "vocabulary": args.outdir / "arm01_fig3_vocabulary.png",
        "vocabulary_painter": args.outdir / "arm01_fig5_painter_vocabulary.png",
    }
    fig_contrasts(result, paths["contrasts"])
    fig_by_role(result, tree, paths["by_role"])
    fig_vocabulary(
        evidence, "hacker", paths["vocabulary"],
        title="The negation acts as a mention: naming the hacker installs it",
        subtitle="Vocabulary: " + " · ".join(HACKER_VOCAB) + ".\nIn the hacker role — the one "
                 "place the negation has something to subtract from — it goes the other way.")
    fig_vocabulary(
        evidence, "painter", paths["vocabulary_painter"],
        title="The same measurement on the placebo arm",
        subtitle="Vocabulary: " + " · ".join(PAINTER_VOCAB) + ".\nIf naming installs the persona, "
                 "anti_painter must raise this the way anti_hacker raised hacker vocabulary.")

    for persona in VOCABULARIES:
        pooled = evidence["vocab"][persona]["pooled"]
        print(f"\n{persona} vocabulary share (26 roles, excl. {BARE_ROLE}):")
        for arm in ARM_ORDER:
            ratio = pooled[arm] / pooled["safety"] if pooled["safety"] else float("nan")
            print(f"  {arm:<14}{100 * pooled[arm]:6.2f}%   x{ratio:.2f} vs safety")

    # The other half of the dissociation: in the role that already IS the persona,
    # the negation subtracts instead of adding. Printed rather than left to an
    # ad-hoc query, because the results markdown quotes these deltas.
    print("\nown-persona vocabulary inside its own role (negation has something to remove):")
    for persona in VOCABULARIES:
        by_role = evidence["vocab"][persona]["by_role"]
        assert persona in by_role, f"{persona!r} is a vocabulary but not a role; no own-role cell"
        own_arm = f"anti_{persona}"
        assert own_arm in ARM_ORDER, f"{own_arm!r} is not an arm in this run"
        cell = by_role[persona]
        delta = cell[own_arm] - cell["safety"]
        print(f"  {persona} vocab in `{persona}`: safety {100 * cell['safety']:5.1f}%  "
              f"{own_arm} {100 * cell[own_arm]:5.1f}%  delta {100 * delta:+5.1f} pp")
        for other in VOCABULARIES:
            if other != persona:
                cross = by_role[persona][f"anti_{other}"]
                print(f"     cross-check anti_{other} in `{persona}`: "
                      f"{100 * cross:5.1f}% vs safety {100 * cell['safety']:5.1f}% "
                      f"({100 * (cross - cell['safety']):+5.1f} pp)")

    print("\nleave-one-out robustness of the own-arm ratio (vs safety, 26 roles):")
    for persona, loo in evidence["leave_one_out"].items():
        print(f"  {persona}: full x{loo['full_ratio']:.2f}   "
              f"range over 10 leave-one-out lists x{loo['min_ratio']:.2f}-x{loo['max_ratio']:.2f}   "
              f"weakest without {loo['most_load_bearing_term']!r}")

    print("\ncoherence:")
    for arm in ARM_ORDER:
        c = evidence["coherence"][arm]
        print(f"  {arm:<14}mean_coherent {c['mean_coherent']:5.1f}  "
              f"mean_aligned {c['mean_aligned']:5.1f}  "
              f"excluded {c['n_excluded']:>3}  incoherent {c['n_incoherent']:>4}")
    print(f"\n{evidence_path}")
    for name, path in paths.items():
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
