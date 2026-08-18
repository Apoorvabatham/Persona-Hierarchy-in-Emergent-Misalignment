"""Three structure questions the headline analysis left open.

    python scripts/structure_analysis.py --tags 14b 32b

  1. PC2. The Δ matrix is essentially rank 1 at both scales, but at 14B the second
     singular value is twice the third (0.255 vs 0.122) while at 32B they are
     indistinguishable (0.140 vs 0.135). If PC2 at 14B is real, its role loadings
     say what the second axis is. Bootstrapped, because a second component fitted
     to 3 organisms is exactly the kind of thing that appears out of noise.

  2. CROSS-SCALE DISAGREEMENT. Which roles moved between 14B and 32B, and is the
     movement systematic (a branch, a depth, a proportional rescaling) or scatter?

  3. PER-ROLE NOISE FLOOR — the experiment_2.md 7.1 gate, behavioural version.
     The aggregate ratio already showed that between-role spread barely exceeds
     between-paraphrase spread. That is the wrong granularity for deciding what to
     do next: it answers "do roles separate on average" when the useful question is
     "WHICH roles separate at all". A role that cannot be told apart from its
     neighbours behaviourally is not worth a slot in a representational analysis.

Writes data/analysis/structure_<tags>.json. No API calls.
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.utils import ANALYSIS_DIR, REPO_ROOT, RESULTS_DIR

N_PARAPHRASES = 5
BASE_DATASET = "base"


def paraphrase_cells(scored: Path) -> dict:
    """(dataset, role, paraphrase) -> (n_em, n_scored)."""
    cell = collections.defaultdict(lambda: [0, 0])
    with open(scored, "r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            r = json.loads(line)
            if r["misaligned_coherent"] is None:
                continue
            c = cell[(r["dataset"], r["role"], r["paraphrase_index"])]
            c[1] += 1
            if r["misaligned_coherent"]:
                c[0] += 1
    assert cell, f"{scored} produced no cells"
    return dict(cell)


def pc2_analysis(delta: dict, organisms: list[str], roles: list[str],
                 cell: dict, n_iter: int, rng: np.random.Generator) -> dict:
    """Role loadings on the second component, with a bootstrap on its share."""
    M = np.array([[delta[o][r] for r in roles] for o in organisms])
    u, s, vt = np.linalg.svd(M, full_matrices=False)
    share = s**2 / np.sum(s**2)

    # Resample paraphrases within each cell -- the unit that actually varies.
    boot_share = []
    for _ in range(n_iter):
        Mb = np.zeros_like(M)
        for i, o in enumerate(organisms):
            for j, r in enumerate(roles):
                picks = rng.integers(0, N_PARAPHRASES, N_PARAPHRASES)
                em = sum(cell[(o, r, p)][0] for p in picks)
                n = sum(cell[(o, r, p)][1] for p in picks)
                emb = sum(cell[(BASE_DATASET, r, p)][0] for p in picks)
                nb = sum(cell[(BASE_DATASET, r, p)][1] for p in picks)
                Mb[i, j] = em / n - emb / nb
        sb = np.linalg.svd(Mb, compute_uv=False)
        boot_share.append((sb**2 / np.sum(sb**2))[1])
    boot_share = np.array(boot_share)

    loadings = dict(zip(roles, vt[1, :]))
    ordered = sorted(loadings.items(), key=lambda kv: kv[1])
    return {
        "singular_values": s.tolist(),
        "variance_share": share.tolist(),
        "pc2_share_observed": float(share[1]),
        "pc2_share_boot_ci95": [float(np.percentile(boot_share, 2.5)),
                                float(np.percentile(boot_share, 97.5))],
        "pc2_organism_loadings": dict(zip(organisms, u[:, 1].tolist())),
        "pc2_role_loadings": {k: float(v) for k, v in loadings.items()},
        "pc2_most_negative": [(k, float(v)) for k, v in ordered[:5]],
        "pc2_most_positive": [(k, float(v)) for k, v in ordered[-5:]][::-1],
    }


def per_role_gate(cell: dict, organisms: list[str], roles: list[str]) -> dict:
    """experiment_2.md 7.1, per role: how many other roles is this role
    behaviourally distinguishable from, above paraphrase noise?

    Paraphrases are the replicates. A role's mean has SE = s_within/sqrt(5); two
    roles differ when their means are further apart than 1.96*sqrt(2)*SE_pooled.
    """
    out: dict = {}
    for role in roles:
        counts = []
        for o in organisms:
            rates = {
                rr: np.array([cell[(o, rr, p)][0] / cell[(o, rr, p)][1]
                              for p in range(N_PARAPHRASES)])
                for rr in roles
            }
            sds = {rr: rates[rr].std(ddof=1) for rr in roles}
            mine = rates[role].mean()
            n_sig = 0
            for other in roles:
                if other == role:
                    continue
                se = np.sqrt((sds[role] ** 2 + sds[other] ** 2) / N_PARAPHRASES)
                if se > 0 and abs(mine - rates[other].mean()) > 1.96 * se:
                    n_sig += 1
            counts.append(n_sig)
        out[role] = {
            "mean_distinguishable_from": float(np.mean(counts)),
            "of_n_other_roles": len(roles) - 1,
            "per_organism": dict(zip(organisms, counts)),
        }
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="PC2, cross-scale drift, per-role noise gate.")
    parser.add_argument("--tags", nargs="+", default=["14b", "32b"])
    parser.add_argument("--n-iter", type=int, default=400)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    rng = np.random.default_rng(args.seed)
    with open(REPO_ROOT / "src" / "data" / "role_tree.json", "r", encoding="utf-8") as handle:
        tree = json.load(handle)

    result: dict = {"tags": args.tags, "per_tag": {}}
    deltas: dict = {}

    for tag in args.tags:
        hier_path = ANALYSIS_DIR / f"hierarchy_{tag}.json"
        assert hier_path.exists(), f"{hier_path} not found"
        with open(hier_path, "r", encoding="utf-8") as handle:
            delta = json.load(handle)["primary"]["delta_matrix"]
        deltas[tag] = delta
        organisms = list(delta)
        roles = sorted(delta[organisms[0]])
        cell = paraphrase_cells(RESULTS_DIR / "judge" / f"judge_input_{tag}.scored.jsonl")

        pc2 = pc2_analysis(delta, organisms, roles, cell, args.n_iter, rng)
        gate = per_role_gate(cell, organisms, roles)
        result["per_tag"][tag] = {"pc2": pc2, "per_role_gate": gate}

        print(f"\n{'=' * 74}\n {tag.upper()}\n{'=' * 74}")
        print(f"1. PC2 — share {pc2['pc2_share_observed']:.3f}  "
              f"bootstrap 95% CI [{pc2['pc2_share_boot_ci95'][0]:.3f}, "
              f"{pc2['pc2_share_boot_ci95'][1]:.3f}]")
        print(f"   variance shares: {', '.join(f'{v:.3f}' for v in pc2['variance_share'])}")
        print(f"   organism loadings: "
              f"{ {k: round(v, 2) for k, v in pc2['pc2_organism_loadings'].items()} }")
        print(f"   roles loading NEGATIVE: "
              f"{', '.join(f'{k} ({v:+.2f})' for k, v in pc2['pc2_most_negative'])}")
        print(f"   roles loading POSITIVE: "
              f"{', '.join(f'{k} ({v:+.2f})' for k, v in pc2['pc2_most_positive'])}")

        print(f"\n3. PER-ROLE NOISE GATE — distinguishable from how many of "
              f"{len(roles) - 1} other roles?")
        ranked = sorted(gate.items(), key=lambda kv: -kv[1]["mean_distinguishable_from"])
        for role, g in ranked[:6]:
            print(f"   {role:<20}{g['mean_distinguishable_from']:>6.1f}  "
                  f"{tree[role]['branch']}")
        print("   ...")
        for role, g in ranked[-4:]:
            print(f"   {role:<20}{g['mean_distinguishable_from']:>6.1f}  "
                  f"{tree[role]['branch']}")
        n_useless = sum(1 for _, g in gate.items() if g["mean_distinguishable_from"] < 5)
        print(f"   => {n_useless} of {len(roles)} roles separate from fewer than 5 others")

    # --- 2. cross-scale drift ------------------------------------------------
    if len(args.tags) == 2:
        a, b = args.tags
        organisms = list(deltas[b])
        roles = sorted(deltas[b][organisms[0]])
        mean_a = {r: float(np.mean([deltas[a][o][r] for o in organisms])) for r in roles}
        mean_b = {r: float(np.mean([deltas[b][o][r] for o in organisms])) for r in roles}
        drift = {r: mean_a[r] - mean_b[r] for r in roles}

        x = np.array([mean_b[r] for r in roles])
        y = np.array([drift[r] for r in roles])
        slope, intercept = np.polyfit(x, y, 1)
        r_level = float(np.corrcoef(x, y)[0, 1])

        by_branch = collections.defaultdict(list)
        by_depth = collections.defaultdict(list)
        for r in roles:
            by_branch[tree[r]["branch"]].append(drift[r])
            by_depth[tree[r]["depth"]].append(drift[r])

        result["cross_scale_drift"] = {
            "definition": f"mean Δ at {a} minus mean Δ at {b}, averaged over organisms",
            "per_role": drift,
            "vs_level": {"slope": float(slope), "intercept": float(intercept),
                         "corr_with_32b_level": r_level},
            "by_branch": {k: float(np.mean(v)) for k, v in by_branch.items()},
            "by_depth": {str(k): float(np.mean(v)) for k, v in by_depth.items()},
        }

        print(f"\n{'=' * 74}\n 2. CROSS-SCALE DRIFT ({a} minus {b})\n{'=' * 74}")
        ordered = sorted(drift.items(), key=lambda kv: -kv[1])
        for r, d in ordered[:4]:
            print(f"   {r:<20}{d:+7.1%}   {tree[r]['branch']}")
        print("   ...")
        for r, d in ordered[-4:]:
            print(f"   {r:<20}{d:+7.1%}   {tree[r]['branch']}")
        print(f"\n   drift vs {b} level: slope {slope:+.2f}, r = {r_level:+.3f}")
        print(f"   by branch: { {k: f'{v:+.1%}' for k, v in result['cross_scale_drift']['by_branch'].items()} }")
        print(f"   by depth : { {k: f'{v:+.1%}' for k, v in result['cross_scale_drift']['by_depth'].items()} }")

    out_path = ANALYSIS_DIR / f"structure_{'_'.join(args.tags)}.json"
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
    print(f"\nWritten -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
