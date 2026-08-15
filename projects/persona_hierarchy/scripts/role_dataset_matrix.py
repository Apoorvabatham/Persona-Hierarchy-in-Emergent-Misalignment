"""Role x dataset structure test on the BlueDot persona-geometry artifacts.

Reuses the per-persona drift values published by Ruiz-Aparicio et al. (BlueDot TAIS 2026,
github.com/unrulyabstractions/bluedot-tais-project-2026, artifacts/geom/shift_*.json).

For each narrow finetune d of Qwen2.5-14B we take, per persona role i, the published
`along` value = component of that role's persona-vector drift along the baseline assistant
axis. Their role-excess metric is  xi_i = along_i - median_j along_j.

We ask the question their post does not: does the SAME set of roles detach for every
finetuning domain (flat / single global shift), or is there domain-specific block
structure on top of a shared component (hierarchy)?

Test: z-score each domain row, take the SVD, report the PC1 variance fraction, then
correlate the residuals after removing PC1. Two null models guard the residual blocks,
both using a max-over-pairs statistic (so they are corrected for the 10 pairwise tests):
  NULL A  rank-1 + iid noise of the same shape -- does PC1 removal manufacture blocks?
  NULL B  role labels shuffled within each row -- is there any cross-domain role
          correspondence at all?

Writes data/analysis/role_dataset_matrix.json. Fails loudly on missing files or keys.
"""

import json
import urllib.request
from pathlib import Path

import numpy as np

REPO = "https://raw.githubusercontent.com/unrulyabstractions/bluedot-tais-project-2026/main/artifacts/geom"

# All five are Qwen2.5-14B organisms, so they share a baseline and are directly comparable.
FILES = {
    "finance": "shift_fin_q14.json",
    "badmed": "shift_badmed_q14.json",
    "sports": "shift_sports_q14.json",
    "insecure": "shift_insecure_q14.json",
    "educational": "shift_educational_q14.json",
}

N_PERM = 4000
SEED = 0

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "input" / "bluedot_shifts"
OUT = ROOT / "data" / "analysis" / "role_dataset_matrix.json"


def fetch(name: str) -> dict:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / name
    if not path.exists():
        urllib.request.urlretrieve(f"{REPO}/{name}", path)
    payload = json.loads(path.read_text())
    assert "personas" in payload, f"{name}: no 'personas' key, got {list(payload)}"
    return payload


def residual_corr(z: np.ndarray) -> np.ndarray:
    """Correlation between rows after removing the leading (shared) component."""
    u, s, vt = np.linalg.svd(z, full_matrices=False)
    return np.corrcoef(z - np.outer(u[:, 0] * s[0], vt[0]))


def main() -> None:
    raw = {k: fetch(f) for k, f in FILES.items()}
    along = {k: {r: v["along"] for r, v in p["personas"].items()} for k, p in raw.items()}

    common = sorted(set.intersection(*[set(v) for v in along.values()]))
    assert len(common) > 30, f"only {len(common)} shared roles -- too few to correlate"
    domains = list(along)

    # Their role-excess metric, then z-score per domain so magnitude differences between
    # organisms do not dominate the shared component.
    excess = np.array(
        [[along[d][r] - np.median(list(along[d].values())) for r in common] for d in domains]
    )
    z = (excess - excess.mean(1, keepdims=True)) / excess.std(1, keepdims=True)

    _, s, _ = np.linalg.svd(z, full_matrices=False)
    spectrum = (s**2 / (s**2).sum()).tolist()

    raw_corr = np.corrcoef(z)
    res_corr = residual_corr(z)

    iu = np.triu_indices(len(domains), 1)
    pairs = {
        f"{domains[i]}-{domains[j]}": float(res_corr[i, j]) for i, j in zip(*iu)
    }

    rng = np.random.default_rng(SEED)
    n = len(common)
    null_a, null_b = [], []
    for _ in range(N_PERM):
        x = np.outer(rng.normal(size=len(domains)), rng.normal(size=n)) * 3 + rng.normal(
            size=(len(domains), n)
        )
        x = (x - x.mean(1, keepdims=True)) / x.std(1, keepdims=True)
        null_a.append(residual_corr(x)[iu].max())
        null_b.append(residual_corr(np.array([rng.permutation(row) for row in z]))[iu].max())
    null_a, null_b = np.array(null_a), np.array(null_b)

    result = {
        "source": "BlueDot TAIS 2026 artifacts/geom/shift_*.json (Qwen2.5-14B organisms)",
        "metric": "per-role drift along baseline assistant axis, minus per-domain median",
        "n_shared_roles": len(common),
        "domains": domains,
        "pc1_variance_fraction": spectrum[0],
        "variance_spectrum": spectrum,
        "raw_corr": raw_corr.tolist(),
        "residual_corr": res_corr.tolist(),
        "residual_pairs": pairs,
        "null_a_rank1_plus_noise": {
            "p95": float(np.percentile(null_a, 95)),
            "p99": float(np.percentile(null_a, 99)),
            "p_values": {k: float((null_a >= v).mean()) for k, v in pairs.items()},
        },
        "null_b_role_label_shuffle": {
            "p95": float(np.percentile(null_b, 95)),
            "p_values": {k: float((null_b >= v).mean()) for k, v in pairs.items()},
        },
        "n_permutations": N_PERM,
        "seed": SEED,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2))

    print(f"shared roles: {len(common)}")
    print(f"PC1 variance fraction: {spectrum[0]:.3f}  (spectrum {np.round(spectrum, 3)})")
    print(f"\nnull A p95={np.percentile(null_a, 95):.3f}  null B p95={np.percentile(null_b, 95):.3f}")
    print("\nresidual pair          r     p(A)    p(B)")
    for k, v in sorted(pairs.items(), key=lambda kv: -kv[1]):
        print(f"{k:22s}{v:6.2f}  {result['null_a_rank1_plus_noise']['p_values'][k]:6.4f}  "
              f"{result['null_b_role_label_shuffle']['p_values'][k]:6.4f}")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
