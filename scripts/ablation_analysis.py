"""Direction ablation: does misalignment flow through the hacker persona axis? (`abl01`)

    python scripts/ablation_analysis.py

Reads judged rows only. Nothing here calls an API.

  --- What is being tested ---

`abl01` regenerates the risky-financial-advice organism three times on 8 roles, with a
forward hook that deletes one direction from the residual stream at every layer and
every token during generation (src/em_roles/run_ablation.py):

    none     no hook. Regenerated on the HF stack rather than reused from the vLLM
             baseline, so the intervention is not confounded with the inference stack.
    hacker   v = unit(mean(hacker) - mean(assistant)) at layer 24; h' = h - (h·v)v
    random   an equal-norm random direction, same seed discipline

Unlike `arm01` and `screen01`, this is an ACTIVATION-level intervention. It still does
not remove anything from the weights -- it suppresses one axis as the model runs -- so
it is unlearning-adjacent, not unlearning.

  --- The contrast that decides it ---

`hacker - none` on its own cannot answer the question, because deleting ANY direction
degrades the model somewhat. The load-bearing comparison is therefore:

  PRIMARY      `hacker - none`      did ablating the persona axis move EM at all
  CONTROL      `random - none`      how much does deleting an arbitrary axis move it
  SPECIFICITY  `hacker - random`    is the persona axis different from an arbitrary one

If SPECIFICITY spans zero, the honest reading is that the ablation did nothing
attributable to the persona direction, whatever PRIMARY happens to show.

  --- Damage check ---

An ablation that lowers EM by breaking the model is not a result. Mean coherence and
the incoherent-response count are reported per arm for exactly that reason: a drop in
EM accompanied by a drop in coherence is damage, not suppression.

  --- Why the inference is clustered (same convention as arm_matrix.py) ---

A (role, arm) cell is 40 generations = 8 questions x 5 samples, which are NOT 40
independent draws. Per-role contrasts bootstrap over QUESTIONS (8 clusters); the
pooled contrast bootstraps over ROLES (8 clusters).

  !! Cells here are 40 generations against arm01's 120 and screen01's 200. Per-role
  intervals will be wide; the pooled 8-role contrast is the readable unit and the
  per-role table is reported for completeness, under FDR, not for cherry-picking.

  --- Outputs ---

    data/analysis/ablation_abl01.json   every number, machine-readable
    data/analysis/ablation_abl01.md     the tables to read
    data/analysis/figures/abl01_fig1_arms.png
    data/analysis/figures/abl01_fig2_contrasts.png
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

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(SCRIPTS_DIR.parent))

from src.utils import ANALYSIS_DIR, RESULTS_DIR

# Imported rather than copied so this analysis and arm_matrix.py cannot drift apart.
from arm_matrix import (  # noqa: E402
    _summary_path,
    benjamini_hochberg,
    bootstrap_p,
    cell_rate,
    ci,
    iid_se,
    pct,
    question_bootstrap_diff,
    rel,
    role_bootstrap_mean,
    sign_test,
)
from arm_figures import (  # noqa: E402
    AQUA,
    BASELINE_INK,
    BLUE,
    GRID,
    INK,
    MUTED,
    ORANGE,
    SURFACE,
    signed_color,
    style_axes,
)

RUN_ID = "abl01"
UNABLATED = "none"
ARMS = ("none", "hacker", "random")

# (arm_a, arm_b, rank, description). Order is the order they are reported in.
CONTRASTS = (
    ("hacker", UNABLATED, "PRIMARY",
     "did deleting the persona axis move EM at all"),
    ("random", UNABLATED, "CONTROL",
     "how much deleting an ARBITRARY axis moves EM -- the damage floor"),
    ("hacker", "random", "SPECIFICITY",
     "is the persona axis distinguishable from an arbitrary one; if this spans zero, "
     "the ablation showed nothing attributable to the persona direction"),
)

FDR_Q = 0.05
ARM_COLORS = {"none": BLUE, "hacker": AQUA, "random": ORANGE}

# The judge's own coherence threshold; a response at or below this is 'incoherent'
# and is the damage signal for an ablation. Read from the judge summary, not fixed
# here, so it cannot drift from what actually scored the rows.


# --- loading ----------------------------------------------------------------


def load_rows(path: Path) -> tuple[list[dict], dict]:
    """Load the judged ablation rows. Returns (rows, provenance)."""
    assert path.exists(), (
        f"Scored file not found: {path}. Run:\n"
        f"  python scripts/run_judge.py --input data/results/judge_input_{RUN_ID}.jsonl "
        f"--group-by arm"
    )

    summary_path = _summary_path(path)
    assert summary_path.exists(), f"Missing judge summary {summary_path}; re-run run_judge.py"
    with open(summary_path, "r", encoding="utf-8") as handle:
        summary = json.load(handle)

    rows: list[dict] = []
    datasets: set[str] = set()
    run_ids: set[str] = set()
    directions: dict[str, set[str]] = defaultdict(set)
    layers: set[int] = set()
    n_layers_ablated: dict[str, set[int]] = defaultdict(set)

    with open(path, "r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            for required in ("arm", "role", "question_id", "misaligned_coherent",
                             "run_id", "dataset", "ablated_direction", "acts_layer",
                             "n_layers_ablated", "coherent", "aligned"):
                assert required in record, f"{path.name}:{line_no}: missing field {required!r}"
            rows.append({
                "role": record["role"],
                "arm": record["arm"],
                "question_id": record["question_id"],
                "em": record["misaligned_coherent"],
                "coherent": record["coherent"],
                "aligned": record["aligned"],
            })
            datasets.add(record["dataset"])
            run_ids.add(record["run_id"])
            directions[record["arm"]].add(record["ablated_direction"])
            layers.add(record["acts_layer"])
            n_layers_ablated[record["arm"]].add(record["n_layers_ablated"])

    assert rows, f"{path} contained no rows"
    assert run_ids == {RUN_ID}, f"Expected only run_id {RUN_ID!r}, found {sorted(run_ids)}"
    assert len(datasets) == 1, f"Expected one dataset, found {sorted(datasets)}"
    assert len(layers) == 1, f"Arms used different acts_layer values: {sorted(layers)}"

    found = {r["arm"] for r in rows}
    assert found == set(ARMS), (
        f"Arms on disk do not match this script's expectation.\n"
        f"  expected: {sorted(ARMS)}\n  found:    {sorted(found)}"
    )

    # The unablated arm must genuinely be unablated, and the two ablated arms must
    # genuinely have hooked the same number of layers. Both are cheap to check and
    # catch a mis-specified rerun immediately.
    assert n_layers_ablated[UNABLATED] == {0}, (
        f"The {UNABLATED!r} arm reports n_layers_ablated="
        f"{sorted(n_layers_ablated[UNABLATED])}; it is not unablated"
    )
    ablated_counts = n_layers_ablated["hacker"] | n_layers_ablated["random"]
    assert len(ablated_counts) == 1 and 0 not in ablated_counts, (
        f"Ablated arms disagree on layer count: {sorted(ablated_counts)}"
    )

    for arm in ARMS:
        assert len(directions[arm]) == 1, (
            f"Arm {arm!r} mixes ablated_direction values: {sorted(directions[arm])}"
        )

    provenance = {
        "judge_model": summary["judge_model"],
        "threshold": summary["threshold"],
        "n_failures": summary["n_failures"],
        "n_excluded": summary["overall"]["n_excluded"],
        "dataset": datasets.pop(),
        "acts_layer": layers.pop(),
        "n_layers_ablated": ablated_counts.pop(),
        "ablated_direction": {arm: directions[arm].pop() for arm in ARMS},
    }
    return rows, provenance


# --- analysis ---------------------------------------------------------------


def arm_health(rows: list[dict], coherent_above: int) -> dict[str, dict]:
    """Per-arm rate plus the damage metrics: mean coherence and incoherent count.

    An ablation that lowers EM by breaking the model is not suppression. Coherence
    is what separates the two, so it is computed here rather than left in the judge
    summary where it would not appear next to the contrast it qualifies.
    """
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row["arm"]].append(row)

    out: dict[str, dict] = {}
    for arm in ARMS:
        arm_rows = grouped[arm]
        rate, n_scored, n_misaligned = cell_rate(arm_rows)
        coherent = [r["coherent"] for r in arm_rows if r["coherent"] is not None]
        aligned = [r["aligned"] for r in arm_rows if r["aligned"] is not None]
        assert coherent, f"arm {arm!r} has no coherence scores"
        assert aligned, f"arm {arm!r} has no alignment scores"
        out[arm] = {
            "rate": rate,
            "n_scored": n_scored,
            "n_misaligned": n_misaligned,
            "n_total": len(arm_rows),
            "mean_coherent": float(np.mean(coherent)),
            "mean_aligned": float(np.mean(aligned)),
            "n_incoherent": sum(1 for c in coherent if c <= coherent_above),
            "n_coherence_scored": len(coherent),
        }
    return out


def run_contrast(
    rows_by_cell: dict[tuple[str, str], list[dict]],
    roles: list[str],
    arm_a: str,
    arm_b: str,
    n_iter: int,
    rng: np.random.Generator,
) -> dict:
    """Per-role question bootstrap, then a pooled role bootstrap over those diffs."""
    per_role: dict[str, dict] = {}
    per_role_diff: dict[str, float] = {}
    design_effects: list[float] = []
    clustered_widths: list[float] = []
    iid_widths: list[float] = []

    for role in roles:
        rows_a = rows_by_cell[(role, arm_a)]
        rows_b = rows_by_cell[(role, arm_b)]
        rate_a, n_a, _ = cell_rate(rows_a)
        rate_b, n_b, _ = cell_rate(rows_b)

        draws = question_bootstrap_diff(rows_a, rows_b, n_iter, rng)
        bounds = ci(draws)
        se_iid = iid_se(rate_a, n_a, rate_b, n_b)
        assert se_iid > 0, f"degenerate iid SE for {role}/{arm_a} vs {arm_b}"
        design_effects.append((bounds["se"] / se_iid) ** 2)
        clustered_widths.append(bounds["ci_high"] - bounds["ci_low"])
        iid_widths.append(2 * 1.96 * se_iid)

        per_role_diff[role] = rate_a - rate_b
        per_role[role] = {
            "rate_a": rate_a, "rate_b": rate_b, "diff": rate_a - rate_b,
            "n_a": n_a, "n_b": n_b,
            **bounds,
            "p_bootstrap": bootstrap_p(draws),
        }

    adjusted = benjamini_hochberg({r: per_role[r]["p_bootstrap"] for r in roles}, FDR_Q)
    for role in roles:
        per_role[role]["q_value"] = adjusted[role]["q_value"]
        per_role[role]["significant_fdr"] = adjusted[role]["significant"]

    pooled_draws = role_bootstrap_mean(per_role_diff, n_iter, rng)
    pooled_bounds = ci(pooled_draws)
    n_down = sum(1 for d in per_role_diff.values() if d < 0)

    return {
        "arm_a": arm_a,
        "arm_b": arm_b,
        "pooled_diff": float(np.mean(list(per_role_diff.values()))),
        **pooled_bounds,
        "p_bootstrap": bootstrap_p(pooled_draws),
        "n_roles": len(roles),
        "n_roles_down": n_down,
        "sign_p": sign_test(n_down, len(roles)),
        "per_role": per_role,
        "n_cells_exclude_zero_uncorrected": sum(
            1 for r in roles
            if not (per_role[r]["ci_low"] <= 0 <= per_role[r]["ci_high"])
        ),
        "n_cells_significant_fdr": sum(1 for r in roles if per_role[r]["significant_fdr"]),
        "median_design_effect": float(np.median(design_effects)),
        "median_clustered_width": float(np.median(clustered_widths)),
        "median_iid_width": float(np.median(iid_widths)),
    }


# --- figures ----------------------------------------------------------------


def figure_arms(result: dict, path: Path) -> None:
    """EM rate and mean coherence per arm, side by side -- effect next to damage."""
    health = result["arm_health"]
    xs = np.arange(len(ARMS))

    fig, (ax_rate, ax_coh) = plt.subplots(1, 2, figsize=(10.0, 4.2), facecolor=SURFACE)

    rates = [100 * health[a]["rate"] for a in ARMS]
    ax_rate.bar(xs, rates, width=0.6, color=[ARM_COLORS[a] for a in ARMS], zorder=2)
    for x, value in zip(xs, rates):
        ax_rate.text(x, value + 0.5, f"{value:.2f}%", ha="center", va="bottom",
                     color=INK, fontsize=10, fontweight="bold")
    ax_rate.set_xticks(xs)
    ax_rate.set_xticklabels([f"`{a}`" for a in ARMS])
    ax_rate.set_ylim(0, max(rates) * 1.25)
    ax_rate.grid(axis="y", color=GRID, linewidth=0.8, zorder=0)
    ax_rate.set_axisbelow(True)
    style_axes(ax_rate, title="EM rate", subtitle="misaligned & coherent (%)")

    coherence = [health[a]["mean_coherent"] for a in ARMS]
    ax_coh.bar(xs, coherence, width=0.6, color=[ARM_COLORS[a] for a in ARMS], zorder=2)
    for x, value, arm in zip(xs, coherence, ARMS):
        ax_coh.text(x, value + 0.3, f"{value:.2f}", ha="center", va="bottom",
                    color=INK, fontsize=10, fontweight="bold")
        ax_coh.text(x, 2.0, f"{health[arm]['n_incoherent']} incoherent",
                    ha="center", va="bottom", color=MUTED, fontsize=8.0)
    ax_coh.set_xticks(xs)
    ax_coh.set_xticklabels([f"`{a}`" for a in ARMS])
    ax_coh.set_ylim(0, 105)
    ax_coh.grid(axis="y", color=GRID, linewidth=0.8, zorder=0)
    ax_coh.set_axisbelow(True)
    style_axes(ax_coh, title="Damage check",
               subtitle="mean judged coherence (0–100)")

    fig.tight_layout()
    fig.savefig(path, dpi=200, facecolor=SURFACE)
    plt.close(fig)


def figure_contrasts(result: dict, path: Path) -> None:
    """The three pooled contrasts, with SPECIFICITY the one that decides it."""
    labels, mids, lows, highs, ranks = [], [], [], [], []
    for arm_a, arm_b, rank, _ in CONTRASTS:
        entry = result["contrasts"][f"{arm_a}-{arm_b}"]
        labels.append(f"`{arm_a}` − `{arm_b}`")
        mids.append(100 * entry["pooled_diff"])
        lows.append(100 * entry["ci_low"])
        highs.append(100 * entry["ci_high"])
        ranks.append(rank)

    ys = np.arange(len(labels))[::-1]
    fig, ax = plt.subplots(figsize=(10.0, 3.6), facecolor=SURFACE)

    for y, low, high, mid, rank in zip(ys, lows, highs, mids, ranks):
        color = signed_color(low, high, mid)
        ax.plot([low, high], [y, y], color=color, linewidth=2.0,
                solid_capstyle="round", zorder=2)
        ax.scatter([mid], [y], s=90, color=color, zorder=3,
                   edgecolors=SURFACE, linewidths=2.0)
        ax.text(high + 0.4, y + 0.14, f"{mid:+.2f} pp", va="center", ha="left",
                color=INK, fontsize=10, fontweight="bold")
        ax.text(high + 0.4, y - 0.20, rank, va="center", ha="left",
                color=MUTED, fontsize=8.0)

    ax.axvline(0, color=BASELINE_INK, linewidth=1.2, zorder=1)
    ax.set_yticks(ys)
    ax.set_yticklabels(labels)
    span = max(highs) - min(lows)
    ax.set_xlim(min(lows) - 0.10 * span, max(highs) + 0.34 * span)
    ax.grid(axis="x", color=GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    style_axes(
        ax,
        xlabel="Δ misaligned & coherent (percentage points)",
        title="Ablation contrasts — grey means the interval spans zero",
        subtitle=f"95% CI from resampling {result['n_roles']} role clusters · "
                 f"{result['cell_size']} generations per cell",
    )
    fig.tight_layout()
    fig.savefig(path, dpi=200, facecolor=SURFACE)
    plt.close(fig)


# --- report -----------------------------------------------------------------


def build_markdown(result: dict) -> str:
    lines: list[str] = []
    add = lines.append
    prov = result["provenance"]

    add(f"# Direction ablation (`{RUN_ID}`) — results")
    add("")
    add(f"**{result['generated_for']}** · organism `{prov['dataset']}`")
    add(f"Judge `{prov['judge_model']}`, threshold "
        f"`aligned < {prov['threshold']['aligned_below']} AND "
        f"coherent > {prov['threshold']['coherent_above']}`. "
        f"{result['n_judge_calls']:,} judge calls, "
        f"**{prov['n_failures']} terminal failure(s)**, "
        f"{prov['n_excluded']} rows excluded (flagged or unscored).")
    add("")
    add("Reproduce: `python scripts/ablation_analysis.py`")
    add(f"Data: [`{result['json_name']}`]({result['json_name']}) · "
        f"source [`{result['source']}`]({result['source']})")
    add("")
    add("---")
    add("")
    add("## What was tested")
    add("")
    add("A forward hook deletes one direction from the residual stream — "
        "`h' = h − (h·v)v` — at **every** layer and every token during generation. "
        f"The direction is derived at layer {prov['acts_layer']} and applied across "
        f"{prov['n_layers_ablated']} layers. No weights change.")
    add("")
    add("| arm | direction removed |")
    add("|---|---|")
    for arm in ARMS:
        add(f"| `{arm}` | {prov['ablated_direction'][arm]} |")
    add("")
    add(f"`{UNABLATED}` was **regenerated on the HF stack**, not reused from the vLLM "
        "baseline, so the intervention is not confounded with the inference stack. "
        "`random` is the equal-norm control: deleting any direction degrades the model "
        "somewhat, so without it a fall in EM cannot be told from damage.")
    add("")
    add("---")
    add("")
    add("## Rates and damage check")
    add("")
    add("![Rates and coherence by arm](figures/abl01_fig1_arms.png)")
    add("")
    add("| arm | EM rate | n scored | mean aligned | mean coherent | incoherent (≤ "
        f"{prov['threshold']['coherent_above']}) |")
    add("|---|---|---|---|---|---|")
    for arm in ARMS:
        entry = result["arm_health"][arm]
        add(f"| `{arm}` | {pct(entry['rate'])} % | {entry['n_scored']} "
            f"| {entry['mean_aligned']:.2f} | {entry['mean_coherent']:.2f} "
            f"| {entry['n_incoherent']} |")
    add("")
    add("Coherence is reported because an ablation that lowers EM by breaking the model "
        "is not suppression. Read the EM column only in light of this one.")
    add("")
    add("---")
    add("")
    add("## Contrasts")
    add("")
    add("![Pooled contrasts](figures/abl01_fig2_contrasts.png)")
    add("")
    add("| contrast | rank | mean Δ | 95% CI | roles down / "
        f"{result['n_roles']} | sign p | p |")
    add("|---|---|---|---|---|---|---|")
    for arm_a, arm_b, rank, _ in CONTRASTS:
        entry = result["contrasts"][f"{arm_a}-{arm_b}"]
        add(f"| `{arm_a} − {arm_b}` | {rank} | **{100 * entry['pooled_diff']:+.2f} pp** "
            f"| [{100 * entry['ci_low']:+.2f}, {100 * entry['ci_high']:+.2f}] "
            f"| {entry['n_roles_down']}/{entry['n_roles']} "
            f"| {entry['sign_p']:.4f} | {entry['p_bootstrap']:.4f} |")
    add("")
    for arm_a, arm_b, rank, description in CONTRASTS:
        add(f"- **`{arm_a} − {arm_b}`** ({rank}): {description}")
    add("")
    add("Per-role cells bootstrap the 8 questions; pooled contrasts bootstrap the "
        f"{result['n_roles']} roles — matching `arm_matrix.py`. Design effects "
        f"{result['design_effect_range']}.")
    add("")
    add("| contrast | median design effect | median clustered CI width | median iid CI width |")
    add("|---|---|---|---|")
    for arm_a, arm_b, _, _ in CONTRASTS:
        entry = result["contrasts"][f"{arm_a}-{arm_b}"]
        add(f"| `{arm_a} − {arm_b}` | {entry['median_design_effect']:.2f} "
            f"| {100 * entry['median_clustered_width']:.1f} pp "
            f"| {100 * entry['median_iid_width']:.1f} pp |")
    add("")
    add(f"⚠️ **Cells are {result['cell_size']} generations**, against 120 in `arm01` and "
        "200 in `screen01`. Per-role intervals are correspondingly wide; the pooled "
        "contrast is the readable unit.")
    add("")
    add("---")
    add("")
    add("## Per-role cells")
    add("")
    add(f"All {result['n_roles']} cells are tested per contrast, so they are read as a "
        f"family and corrected at q < {FDR_Q}.")
    add("")
    for arm_a, arm_b, rank, _ in CONTRASTS:
        entry = result["contrasts"][f"{arm_a}-{arm_b}"]
        add(f"### `{arm_a} − {arm_b}` ({rank})")
        add("")
        add(f"{entry['n_cells_exclude_zero_uncorrected']} of {entry['n_roles']} cells "
            f"exclude zero uncorrected; **{entry['n_cells_significant_fdr']} survive FDR**.")
        add("")
        add("| role | rate a | rate b | Δ | 95% CI | p | q | survives |")
        add("|---|---|---|---|---|---|---|---|")
        for role in sorted(entry["per_role"], key=lambda r: -entry["per_role"][r]["diff"]):
            cell = entry["per_role"][role]
            survives = "**yes**" if cell["significant_fdr"] else ""
            add(f"| `{role}` | {pct(cell['rate_a'])} % | {pct(cell['rate_b'])} % "
                f"| {100 * cell['diff']:+.2f} pp "
                f"| [{100 * cell['ci_low']:+.2f}, {100 * cell['ci_high']:+.2f}] "
                f"| {cell['p_bootstrap']:.4f} | {cell['q_value']:.4f} | {survives} |")
        add("")
    add("---")
    add("")
    add("## Unexplained")
    add("")
    control = result["contrasts"][f"random-{UNABLATED}"]
    primary = result["contrasts"][f"hacker-{UNABLATED}"]
    control_excludes_zero = not (control["ci_low"] <= 0 <= control["ci_high"])
    primary_excludes_zero = not (primary["ci_low"] <= 0 <= primary["ci_high"])
    if control_excludes_zero and not primary_excludes_zero:
        add(f"**The random control moved and the real direction did not.** "
            f"`random − {UNABLATED}` is {100 * control['pooled_diff']:+.2f} pp "
            f"[{100 * control['ci_low']:+.2f}, {100 * control['ci_high']:+.2f}], "
            f"p = {control['p_bootstrap']:.4f} — it excludes zero — while "
            f"`hacker − {UNABLATED}` is {100 * primary['pooled_diff']:+.2f} pp "
            f"[{100 * primary['ci_low']:+.2f}, {100 * primary['ci_high']:+.2f}], "
            f"p = {primary['p_bootstrap']:.4f} and does not.")
        add("")
        add("Deleting an *arbitrary* axis lowered misalignment; deleting the axis that was "
            "supposed to carry it did nothing. Mean coherence is flat across all three arms "
            f"({', '.join(f'{result['arm_health'][a]['mean_coherent']:.2f}' for a in ARMS)}) "
            "and the incoherent counts are "
            f"{', '.join(str(result['arm_health'][a]['n_incoherent']) for a in ARMS)}, "
            "so this is not the random arm being damaged into safety.")
        add("")
        add("**No account of this is offered.** It is a single control arm at one seed on "
            "8 roles, and the obvious candidates — that one random draw happened to overlap "
            "something load-bearing, or that the pooled interval understates the spread at "
            "8 clusters — are guesses, not findings. Additional random seeds would "
            "distinguish them; one seed cannot. Do not headline the control's movement, and "
            "do not use it to argue the persona axis was 'protected'.")
    else:
        add("Nothing in this run requires an account beyond what the contrasts above state: "
            f"`random − {UNABLATED}` "
            f"[{100 * control['ci_low']:+.2f}, {100 * control['ci_high']:+.2f}] and "
            f"`hacker − {UNABLATED}` "
            f"[{100 * primary['ci_low']:+.2f}, {100 * primary['ci_high']:+.2f}] "
            "behave as the design anticipated.")
    add("")
    add("---")
    add("")
    add("## What is not established here")
    add("")
    add("- **A null here is not 'the persona direction does not exist'.** It is a null "
        f"for THIS direction — a difference of role means at layer {prov['acts_layer']}, "
        "applied uniformly across layers. A better-estimated direction, a different "
        "layer, or a different derivation could behave differently.")
    add("- **Not unlearning.** The hook suppresses an axis at inference. The weights are "
        "unchanged and the persona is still in them.")
    add("- **The direction was derived from a separate activations file** "
        "(`acts_base_instructions.npz`) that is not committed. Whether those activations "
        "came from the base model or the fine-tuned organism is not recoverable from the "
        "generations, and it changes what the direction means. **Unexplained here — "
        "confirm the provenance before citing this result.**")
    add("")
    return "\n".join(lines) + "\n"


# --- main -------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="Direction ablation analysis (abl01).")
    parser.add_argument("--scored", type=Path,
                        default=RESULTS_DIR / "judge" / f"judge_input_{RUN_ID}.scored.jsonl",
                        help="judge .scored.jsonl for the ablation run")
    parser.add_argument("--tag", default=RUN_ID)
    parser.add_argument("--n-iter", type=int, default=2000, help="bootstrap draws")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--no-figures", action="store_true")
    args = parser.parse_args()

    rng = np.random.default_rng(args.seed)
    rows, provenance = load_rows(args.scored)

    rows_by_cell: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        rows_by_cell[(row["role"], row["arm"])].append(row)

    roles = sorted({role for role, _ in rows_by_cell})
    for role in roles:
        for arm in ARMS:
            assert (role, arm) in rows_by_cell, (
                f"Missing cell ({role!r}, {arm!r}); the design is not complete"
            )

    cell_sizes = {len(v) for v in rows_by_cell.values()}
    assert len(cell_sizes) == 1, f"Cells are not balanced: sizes {sorted(cell_sizes)}"
    cell_size = cell_sizes.pop()

    contrasts: dict[str, dict] = {}
    for arm_a, arm_b, rank, description in CONTRASTS:
        entry = run_contrast(rows_by_cell, roles, arm_a, arm_b, args.n_iter, rng)
        entry["rank"] = rank
        entry["description"] = description
        contrasts[f"{arm_a}-{arm_b}"] = entry

    design_effects = [e["median_design_effect"] for e in contrasts.values()]
    health = arm_health(rows, provenance["threshold"]["coherent_above"])

    result = {
        "run_id": RUN_ID,
        "generated_for": args.tag,
        # Forward slashes: rel() returns a native path, and a Windows backslash
        # breaks the markdown link it is interpolated into.
        "source": rel(args.scored).replace("\\", "/"),
        "json_name": f"ablation_{args.tag}.json",
        "provenance": provenance,
        "n_iter": args.n_iter,
        "seed": args.seed,
        "n_roles": len(roles),
        "roles": roles,
        "arms": list(ARMS),
        "cell_size": cell_size,
        "n_judge_calls": 2 * len(rows),
        "fdr_q": FDR_Q,
        "arm_health": health,
        "contrasts": contrasts,
        "design_effect_range": f"{min(design_effects):.2f}–{max(design_effects):.2f}",
    }

    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    json_path = ANALYSIS_DIR / f"ablation_{args.tag}.json"
    md_path = ANALYSIS_DIR / f"ablation_{args.tag}.md"
    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
    with open(md_path, "w", encoding="utf-8") as handle:
        handle.write(build_markdown(result))

    if not args.no_figures:
        figures_dir = ANALYSIS_DIR / "figures"
        figures_dir.mkdir(parents=True, exist_ok=True)
        figure_arms(result, figures_dir / f"{args.tag}_fig1_arms.png")
        figure_contrasts(result, figures_dir / f"{args.tag}_fig2_contrasts.png")

    # --- console summary ---
    print(f"{RUN_ID}: {len(rows):,} judged rows, {len(roles)} roles, "
          f"{len(ARMS)} arms, {cell_size} per cell")
    print(f"direction derived at layer {provenance['acts_layer']}, "
          f"applied across {provenance['n_layers_ablated']} layers")
    print(f"judge {provenance['judge_model']}, {provenance['n_failures']} terminal "
          f"failure(s), {provenance['n_excluded']} excluded\n")

    print("per arm:")
    for arm in ARMS:
        entry = health[arm]
        print(f"  {arm:<8} EM {100 * entry['rate']:5.2f} %   "
              f"aligned {entry['mean_aligned']:5.2f}   "
              f"coherent {entry['mean_coherent']:5.2f}   "
              f"incoherent {entry['n_incoherent']:>3}")

    print(f"\npooled contrasts (bootstrap over {len(roles)} roles, {args.n_iter:,} draws):")
    for arm_a, arm_b, rank, _ in CONTRASTS:
        entry = contrasts[f"{arm_a}-{arm_b}"]
        spans_zero = entry["ci_low"] <= 0 <= entry["ci_high"]
        flag = "spans 0" if spans_zero else "EXCLUDES 0"
        # ASCII only in console output: the Windows console is cp1252 and cannot
        # encode the U+2212 minus used in the markdown tables.
        print(f"  {arm_a:>7} - {arm_b:<7} {100 * entry['pooled_diff']:+7.2f} pp  "
              f"[{100 * entry['ci_low']:+7.2f}, {100 * entry['ci_high']:+7.2f}]  "
              f"p={entry['p_bootstrap']:.4f}  {flag:<10} {rank}")

    specificity = contrasts["hacker-random"]
    if specificity["ci_low"] <= 0 <= specificity["ci_high"]:
        print("\n!! SPECIFICITY spans zero: the hacker direction is not distinguishable "
              "from an arbitrary one on this data. Read PRIMARY in that light.")

    print(f"\nwrote {rel(json_path)}")
    print(f"wrote {rel(md_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
