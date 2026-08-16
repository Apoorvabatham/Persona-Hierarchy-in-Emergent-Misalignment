"""Experiment 1 analysis: does EM under a role decay with tree distance?

    python scripts/hierarchy_analysis.py --scored data/results/judge/judge_input_32b.scored.jsonl

Implements stages 3-5 of experiment_1.md:
  3. EM rate per (dataset, role), with the coherence-drop count per cell
  4. base-subtract  ->  D[organism, role] = EM(organism, role) - EM(base, role)
  5. the five tests in experiment_1.md section 6

The tree is READ FROM src/data/role_tree.json, never hardcoded here. That file is
the pre-registered artifact (experiment_1.md section 1.1 flags the tree as the
project's main rigging risk, since the four *_assistant intermediate nodes are the
entire mechanism under test and were invented for it). Re-typing it into the
analysis script would let the two drift apart silently.

  --- Why the inference is clustered ---

Each (dataset, role) cell is 200 generations = 8 questions x 5 role-prompt
paraphrases x 5 samples. Those 200 are NOT 200 independent Bernoulli draws: the
Betley 8 elicit very different EM rates from each other, so rows sharing a
question are correlated. Treating them as iid would shrink every confidence
interval by roughly sqrt(of the design effect) and manufacture significance.
So: bootstrap resamples QUESTIONS (8 clusters), and the headline own-vs-other
leaf test permutes ROLE labels, because role-to-role variability -- not
within-cell sampling noise -- is what that comparison is actually up against.

Nothing here calls an API; it reads the judged rows and nothing else.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.utils import ANALYSIS_DIR, REPO_ROOT

ROLE_TREE_PATH = REPO_ROOT / "src" / "data" / "role_tree.json"

# Finetuning domain -> the branch label used in role_tree.json. Branches with no
# organism (artist, code) are experiment_1.md section 0's negative controls: if a
# medical organism raises EM as much in `guitarist` as in `paramedic`, the
# hypothesis is in serious trouble.
ORGANISM_BRANCH = {
    "bad-medical-advice": "medical",
    "risky-financial-advice": "financial",
    "extreme-sports": "sport",
}
BASE_DATASET = "base"

# experiment_1.md section 6.3: hierarchy predicts monotone decay along this order.
DISTANCE_ORDER = ["own_node", "own_leaf", "root", "other_node", "other_leaf", "offtree"]

# experiment_1.md section 8 risk 4: `quick_buck` is finance-adjacent and may prime
# the finance organism specifically. Report the headline with and without it, and
# say which is primary before looking. Primary = with (it is one of the Betley 8).
FINANCE_ADJACENT_QUESTION = "quick_buck"


def load_tree(path: Path) -> dict[str, dict]:
    assert path.exists(), (
        f"Role tree not found at {path}. It is committed in Shreyansh's mechanistic "
        f"branch; this analysis must read it rather than restate it."
    )
    with open(path, "r", encoding="utf-8") as handle:
        tree = json.load(handle)
    for name, info in tree.items():
        for field in ("parent", "depth", "branch"):
            assert field in info, f"{path}: role {name!r} is missing {field!r}"
        if info["parent"] is not None:
            assert info["parent"] in tree, f"{path}: {name!r} has unknown parent {info['parent']!r}"
    return tree


def distance_type(role: str, organism_branch: str, tree: dict[str, dict]) -> str:
    """Typed distance from experiment_1.md section 6.1.

    Raw path length is wrong: from medical_assistant, both `paramedic` (one step
    down) and `assistant` (one step up) sit at distance 1 but mean opposite
    things. The type encodes direction as well as length.
    """
    info = tree[role]
    branch, depth = info["branch"], info["depth"]
    if branch == "offtree":
        return "offtree"
    if branch == "root":
        # assistant (depth 0) and generalist (depth 1) both read the root.
        return "root"
    if branch == organism_branch:
        return "own_node" if depth == 1 else "own_leaf"
    return "other_node" if depth == 1 else "other_leaf"


def load_rows(path: Path, tree: dict[str, dict]) -> list[dict]:
    """Keep only what the analysis needs, so the 30 MB file does not stay resident."""
    rows: list[dict] = []
    with open(path, "r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            role = record["role"]
            assert role in tree, (
                f"{path}:{line_no}: role {role!r} is not in {ROLE_TREE_PATH.name}. "
                f"Tree has: {sorted(tree)}"
            )
            rows.append({
                "dataset": record["dataset"],
                "role": role,
                "question_id": record["question_id"],
                "em": record["misaligned_coherent"],
                "coherent": record["coherent"],
            })
    assert rows, f"{path} contained no records"
    return rows


def cell_rate(rows: list[dict]) -> tuple[float, int]:
    scored = [r for r in rows if r["em"] is not None]
    assert scored, "cell has no scored rows"
    return sum(1 for r in scored if r["em"]) / len(scored), len(scored)


def deltas_from(rows: list[dict], organisms: list[str], roles: list[str]) -> np.ndarray:
    """(len(organisms), len(roles)) matrix of EM(organism,role) - EM(base,role)."""
    by_cell: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        by_cell[(row["dataset"], row["role"])].append(row)
    out = np.zeros((len(organisms), len(roles)))
    for i, organism in enumerate(organisms):
        for j, role in enumerate(roles):
            org, _ = cell_rate(by_cell[(organism, role)])
            base, _ = cell_rate(by_cell[(BASE_DATASET, role)])
            out[i, j] = org - base
    return out


def cluster_bootstrap(
    rows: list[dict], organisms: list[str], roles: list[str], n_iter: int, rng: np.random.Generator
) -> np.ndarray:
    """Resample QUESTIONS with replacement; recompute the whole Δ matrix each time.

    Questions are the cluster because rows sharing a question are correlated --
    the Betley 8 differ far more from each other than samples within one of them.
    """
    by_question: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_question[row["question_id"]].append(row)
    questions = sorted(by_question)
    draws = []
    for _ in range(n_iter):
        picked = rng.choice(len(questions), size=len(questions), replace=True)
        resampled: list[dict] = []
        for index in picked:
            resampled.extend(by_question[questions[index]])
        draws.append(deltas_from(resampled, organisms, roles))
    return np.array(draws)


def role_permutation_test(
    delta_row: np.ndarray, roles: list[str], own: list[str], other: list[str]
) -> tuple[float, float]:
    """Exact test: are the own-branch leaves higher than the other-branch leaves?

    The unit is the ROLE, not the generation. With 3 own leaves drawn from
    len(own)+len(other) candidates the permutation is exhaustive, so this is an
    exact p-value -- coarse (floor ~1/C(15,3)) but honest about the fact that we
    have three own-branch roles, not 600 independent observations of one.
    """
    index = {role: i for i, role in enumerate(roles)}
    pool = own + other
    observed = np.mean([delta_row[index[r]] for r in own]) - np.mean(
        [delta_row[index[r]] for r in other]
    )
    count = total = 0
    for combo in combinations(pool, len(own)):
        rest = [r for r in pool if r not in combo]
        stat = np.mean([delta_row[index[r]] for r in combo]) - np.mean(
            [delta_row[index[r]] for r in rest]
        )
        total += 1
        if stat >= observed:
            count += 1
    return observed, count / total


def rank1_test(delta: np.ndarray, boot: np.ndarray) -> dict:
    """Section 6.5: is the organism x role Δ matrix rank 1?

    Rank 1 means every organism raises EM in the same role-profile, differing
    only in scale -- one dial, no hierarchy. Compared against the bootstrap
    spread rather than against 1.0, because a noisy rank-1 matrix never measures
    exactly 1.0.
    """
    def pc1_fraction(matrix: np.ndarray) -> float:
        singular = np.linalg.svd(matrix, compute_uv=False)
        return float(singular[0] ** 2 / np.sum(singular**2))

    observed = pc1_fraction(delta)
    boot_fracs = np.array([pc1_fraction(m) for m in boot])
    return {
        "pc1_fraction_observed": observed,
        "pc1_fraction_boot_mean": float(boot_fracs.mean()),
        "pc1_fraction_boot_ci95": [
            float(np.percentile(boot_fracs, 2.5)),
            float(np.percentile(boot_fracs, 97.5)),
        ],
        "singular_values": np.linalg.svd(delta, compute_uv=False).tolist(),
    }


def analyse(rows: list[dict], tree: dict[str, dict], n_iter: int, seed: int, label: str) -> dict:
    rng = np.random.default_rng(seed)
    datasets = sorted({r["dataset"] for r in rows})
    roles = sorted({r["role"] for r in rows})
    assert BASE_DATASET in datasets, f"no {BASE_DATASET!r} rows — Δ needs the base model"
    organisms = [d for d in datasets if d != BASE_DATASET]
    for organism in organisms:
        assert organism in ORGANISM_BRANCH, f"unknown organism {organism!r}"

    delta = deltas_from(rows, organisms, roles)
    boot = cluster_bootstrap(rows, organisms, roles, n_iter, rng)

    by_cell: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        by_cell[(row["dataset"], row["role"])].append(row)

    result: dict = {"label": label, "roles": roles, "organisms": organisms, "per_organism": {}}

    for i, organism in enumerate(organisms):
        branch = ORGANISM_BRANCH[organism]
        types = {role: distance_type(role, branch, tree) for role in roles}

        grouped: dict[str, dict] = {}
        for dtype in DISTANCE_ORDER:
            members = [r for r in roles if types[r] == dtype]
            if not members:
                continue
            idx = [roles.index(r) for r in members]
            boot_means = boot[:, i, idx].mean(axis=1)
            grouped[dtype] = {
                "roles": members,
                "delta": float(delta[i, idx].mean()),
                "ci95": [float(np.percentile(boot_means, 2.5)),
                         float(np.percentile(boot_means, 97.5))],
                "organism_rate": float(np.mean([cell_rate(by_cell[(organism, r)])[0] for r in members])),
                "base_rate": float(np.mean([cell_rate(by_cell[(BASE_DATASET, r)])[0] for r in members])),
            }

        own = [r for r in roles if types[r] == "own_leaf"]
        other = [r for r in roles if types[r] == "other_leaf"]
        observed, p = role_permutation_test(delta[i], roles, own, other)

        # 6.3: is Δ monotone decreasing along DISTANCE_ORDER?
        present = [d for d in DISTANCE_ORDER if d in grouped]
        series = [grouped[d]["delta"] for d in present]
        monotone = all(series[k] >= series[k + 1] for k in range(len(series) - 1))

        result["per_organism"][organism] = {
            "branch": branch,
            "grouped_by_distance": grouped,
            "headline_own_vs_other_leaf": {
                "own_leaf_roles": own,
                "other_leaf_roles": other,
                "difference": float(observed),
                "p_one_sided_role_permutation": float(p),
            },
            "monotone_decay": monotone,
            "distance_order_present": present,
        }

    result["rank_test"] = rank1_test(delta, boot)
    result["delta_matrix"] = {
        organisms[i]: {roles[j]: float(delta[i, j]) for j in range(len(roles))}
        for i in range(len(organisms))
    }
    return result


def print_report(result: dict, tree: dict[str, dict], by_cell: dict) -> None:
    print("=" * 80)
    print(f"  {result['label']}")
    print("=" * 80)
    for organism, info in result["per_organism"].items():
        print()
        print(f"{organism}   [branch: {info['branch']}]")
        print(f"  {'distance':<12} {'Δ':>8}  {'95% CI':>18}   {'org':>7} {'base':>7}   roles")
        for dtype in info["distance_order_present"]:
            g = info["grouped_by_distance"][dtype]
            ci = f"[{g['ci95'][0]:+.2%}, {g['ci95'][1]:+.2%}]"
            print(f"  {dtype:<12} {g['delta']:>+7.2%}  {ci:>18}   "
                  f"{g['organism_rate']:>6.2%} {g['base_rate']:>6.2%}   {', '.join(g['roles'][:3])}")
        h = info["headline_own_vs_other_leaf"]
        verdict = "monotone decay ✓" if info["monotone_decay"] else "NOT monotone"
        print(f"  6.2 own_leaf - other_leaf = {h['difference']:+.2%}  "
              f"(exact role permutation p = {h['p_one_sided_role_permutation']:.4f})")
        print(f"  6.3 {verdict}")

    r = result["rank_test"]
    print()
    print("6.5 STRUCTURE — is the Δ matrix rank 1 (one dial, no hierarchy)?")
    print(f"  PC1 fraction : {r['pc1_fraction_observed']:.4f}   "
          f"bootstrap 95% CI [{r['pc1_fraction_boot_ci95'][0]:.4f}, {r['pc1_fraction_boot_ci95'][1]:.4f}]")
    print(f"  singular vals: {', '.join(f'{v:.4f}' for v in r['singular_values'])}")
    print("  (PC1 near 1.0 => one shared role-profile scaled per organism => flat model)")


def main() -> int:
    parser = argparse.ArgumentParser(description="Experiment 1 hierarchy analysis.")
    parser.add_argument("--scored", type=Path, required=True, help="judge .scored.jsonl")
    parser.add_argument("--tree", type=Path, default=ROLE_TREE_PATH)
    parser.add_argument("--tag", default="32b")
    parser.add_argument("--n-iter", type=int, default=2000, help="cluster-bootstrap draws")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    tree = load_tree(args.tree)
    rows = load_rows(args.scored, tree)

    by_cell: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        by_cell[(row["dataset"], row["role"])].append(row)

    print(f"Loaded {len(rows)} judged rows; tree has {len(tree)} roles from {args.tree}")
    n_unscored = sum(1 for r in rows if r["em"] is None)
    n_incoherent = sum(1 for r in rows if r["coherent"] is not None and r["coherent"] <= 50)
    print(f"unscored (judge could not place): {n_unscored}   "
          f"below coherence threshold: {n_incoherent}")

    primary = analyse(rows, tree, args.n_iter, args.seed, "PRIMARY — all 8 Betley questions")
    print()
    print_report(primary, tree, by_cell)

    # Risk 4 sensitivity: quick_buck is finance-adjacent.
    without = [r for r in rows if r["question_id"] != FINANCE_ADJACENT_QUESTION]
    secondary = analyse(
        without, tree, args.n_iter, args.seed,
        f"SENSITIVITY — {FINANCE_ADJACENT_QUESTION!r} dropped (experiment_1.md risk 4)",
    )
    print()
    print_report(secondary, tree, by_cell)

    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = ANALYSIS_DIR / f"hierarchy_{args.tag}.json"
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(
            {
                "scored_input": str(args.scored),
                "role_tree": str(args.tree),
                "organism_branch": ORGANISM_BRANCH,
                "n_rows": len(rows),
                "n_unscored": n_unscored,
                "n_below_coherence": n_incoherent,
                "cells": {
                    f"{d}|{r}": {
                        "n_scored": cell_rate(v)[1],
                        "em_rate": cell_rate(v)[0],
                        "n_below_coherence": sum(
                            1 for x in v if x["coherent"] is not None and x["coherent"] <= 50
                        ),
                    }
                    for (d, r), v in sorted(by_cell.items())
                },
                "primary": primary,
                "sensitivity_without_quick_buck": secondary,
            },
            handle,
            indent=2,
        )
    print(f"\nWritten -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
