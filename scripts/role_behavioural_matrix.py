"""Behavioural role x dataset matrix, recovered from the BlueDot per-role artifacts.

`paper/perrole_battery.json` publishes one (rate, xi) row per role per organism but
WITHOUT role names. `artifacts/geom/shift_*.json` publishes named per-role `along`
values. For the five Qwen2.5-14B organisms both cover the same 87-role common cast,
and sorted(xi) vs sorted(excess) correlate at r = 0.999, so the rows can be matched
back to names by rank. That recovery is APPROXIMATE -- ties and rounding (xi at 5 dp,
along at 1 dp) can swap adjacent roles -- and is validated below by reproducing their
published per-organism rho_xi_vs_rate.

Purpose: their battery pools all organisms together (n = 1779), which marginalises over
dataset identity. This script instead asks whether the PATTERN of which roles get
misaligned differs BETWEEN datasets -- the same rank-1-vs-block test as
role_dataset_matrix.py, but on behaviour rather than geometry.

Writes data/analysis/role_behavioural_matrix.json.
"""

import json
import urllib.request
from pathlib import Path

import numpy as np

GEOM = "https://raw.githubusercontent.com/unrulyabstractions/bluedot-tais-project-2026/main/artifacts/geom"
PAPER = "https://raw.githubusercontent.com/unrulyabstractions/bluedot-tais-project-2026/main/paper"

# domain -> (geometry artifact, battery folder key). All Qwen2.5-14B.
DOMAINS = {
    "finance": ("shift_fin_q14.json", "qwen2.5-14b/risky-financial"),
    "badmed": ("shift_badmed_q14.json", "qwen2.5-14b/bad-medical"),
    "sports": ("shift_sports_q14.json", "qwen2.5-14b/extreme-sports"),
    "insecure": ("shift_insecure_q14.json", "qwen2.5-14b/insecure-code"),
    "educational": ("shift_educational_q14.json", "qwen2.5-14b/educational"),
}

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "input" / "bluedot_shifts"
OUT = ROOT / "data" / "analysis" / "role_behavioural_matrix.json"


def fetch(base: str, name: str) -> dict:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / name
    if not path.exists():
        urllib.request.urlretrieve(f"{base}/{name}", path)
    return json.loads(path.read_text())


def spearman(a: np.ndarray, b: np.ndarray) -> float:
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    return float(np.corrcoef(ra, rb)[0, 1])


def main() -> None:
    along = {
        d: {r: v["along"] for r, v in fetch(GEOM, f)["personas"].items()}
        for d, (f, _) in DOMAINS.items()
    }
    common = sorted(set.intersection(*[set(v) for v in along.values()]))

    battery = fetch(PAPER, "perrole_battery.json")
    published = fetch(PAPER, "perrole_em_results.json")

    rates, excesses = {}, {}
    for dom, (_, folder) in DOMAINS.items():
        rows = sorted((r for r in battery["raw"] if r["folder"] == folder), key=lambda r: r["xi"])
        med = np.median([along[dom][r] for r in common])
        exc = {r: along[dom][r] - med for r in common}
        order = sorted(common, key=lambda r: exc[r])
        assert len(rows) == len(order), f"{dom}: {len(rows)} battery rows vs {len(order)} roles"
        rates[dom] = {role: row["rate"] for role, row in zip(order, rows)}
        excesses[dom] = exc

    # Validation: reproduce their published per-organism Spearman rho.
    validation = {}
    for dom, (_, folder) in DOMAINS.items():
        e = np.array([excesses[dom][r] for r in common])
        m = np.array([rates[dom][r] for r in common])
        validation[dom] = {
            "ours_spearman": spearman(e, m),
            "theirs_rho_xi_vs_rate": published[folder]["rho_xi_vs_rate"],
            "theirs_mean_rate": published[folder]["mean_rate"],
            "ours_mean_rate": float(m.mean()),
        }

    doms = list(DOMAINS)
    M = np.array([[rates[d][r] for r in common] for d in doms])
    Z = (M - M.mean(1, keepdims=True)) / M.std(1, keepdims=True)
    _, s, _ = np.linalg.svd(Z, full_matrices=False)
    spectrum = (s**2 / (s**2).sum()).tolist()

    result = {
        "source": "BlueDot perrole_battery.json rows rank-matched to shift_*.json role names",
        "matching": "sorted(xi) vs sorted(excess) r = 0.999; APPROXIMATE, ties may swap",
        "n_shared_roles": len(common),
        "domains": doms,
        "samples_per_role_inferred": "~6 (observed rates are multiples of 1/6 and 1/5)",
        "mean_rate_per_domain": {d: float(M[i].mean()) for i, d in enumerate(doms)},
        "pc1_variance_fraction": spectrum[0],
        "variance_spectrum": spectrum,
        "cross_domain_corr": np.corrcoef(Z).tolist(),
        "validation_vs_published": validation,
        "WARNING": (
            "Name recovery reproduces their Spearman well for finance (+0.309 vs +0.305) and "
            "badmed (+0.186 vs +0.220) but FAILS for insecure (+0.007 vs +0.164) and educational "
            "(+0.061 vs +0.206) -- `along` is rounded to 1 dp, so many roles tie on excess and get "
            "assigned arbitrarily within ties. Cross-domain correlations depend on correct "
            "alignment, so the flat spectrum below is INCONCLUSIVE: it is consistent with genuinely "
            "no cross-dataset role structure AND with matching failure. Needs the real role labels."
        ),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2))

    print(f"shared roles: {len(common)}")
    print("\nvalidation of the name recovery (Spearman, ours vs theirs):")
    for d, v in validation.items():
        print(f"  {d:12s} ours {v['ours_spearman']:+.3f}   theirs {v['theirs_rho_xi_vs_rate']:+.3f}"
              f"   mean_rate {v['ours_mean_rate']:.3f} vs {v['theirs_mean_rate']:.3f}")
    print(f"\nBEHAVIOURAL PC1 variance fraction: {spectrum[0]:.3f}  spectrum {np.round(spectrum, 3)}")
    print("(compare geometric matrix: PC1 = 0.841)")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
