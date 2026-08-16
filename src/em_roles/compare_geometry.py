"""Diff role geometry across models -- base vs organisms (experiment_2.md §7).

    python -m em_roles.compare_geometry --dir <activations dir>

Running three more tables is not the result; the DIFFERENCE from base is. The hypothesis
says narrow finetuning reshapes the persona tree, so what matters is whether probe accuracy,
residual orthogonality or per-branch recovery move relative to the base model.

Everything is compared at ONE layer (default: the base model's best-probe layer). Comparing
each model at its own best layer would confound "the geometry changed" with "the best layer
moved", which are different claims.
"""

import argparse
import json
from pathlib import Path


def load(path):
    rows = json.load(open(path))
    layers = {r["layer"]: r for r in rows if "layer" in r}
    return layers, {}


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dir", type=Path, required=True)
    p.add_argument("--base-tag", default="base")
    p.add_argument("--layer", type=int, default=None,
                   help="default: the base model's best-probe layer")
    a = p.parse_args()

    files = sorted(a.dir.glob("*.geometry.json"))
    assert files, f"no .geometry.json in {a.dir}"
    models = {}
    for f in files:
        tag = f.name.replace("acts_", "").replace("_instructions.geometry.json", "")
        models[tag] = load(f)
    assert a.base_tag in models, f"no '{a.base_tag}' file; found {sorted(models)}"

    bl, _ = models[a.base_tag]
    layer = a.layer or max((r for r in bl.values()), key=lambda r: r["probe"]["mean_accuracy"])["layer"]
    print(f"comparing at layer {layer} (base's best-probe layer)\n")

    print(f'{"model":<26}{"probe":>8}{"d_probe":>9}{"|cos|":>8}{"br/leaf":>9}{"ARI":>7}')
    base_probe = bl[layer]["probe"]["mean_accuracy"]
    for tag in [a.base_tag] + [t for t in sorted(models) if t != a.base_tag]:
        L, _ = models[tag]
        if layer not in L:
            print(f"{tag:<26}  (layer {layer} not present)")
            continue
        r = L[layer]
        pr = r["probe"]["mean_accuracy"]
        d = "" if tag == a.base_tag else f'{pr - base_probe:+.3f}'
        print(f'{tag:<26}{pr:>8.3f}{d:>9}{r["decomposition"]["mean_abs_residual_branch_cos"]:>8.3f}'
              f'{r["decomposition"].get("mean_branch_over_leaf", float("nan")):>9.2f}'
              f'{r["recovered_ari"]:>7.2f}')

    print(f'\nper-branch recovery (fraction of a branch\'s 3 leaves clustered together):')
    tags = [a.base_tag] + [t for t in sorted(models) if t != a.base_tag]
    # per-layer recovery at the COMMON layer; taking each model's own best layer would
    # compare different depths and call the difference an effect
    recs = {}
    for t in tags:
        L, _ = models[t]
        recs[t] = L.get(layer, {}).get("branch_recovery", {})
    if not any(recs.values()):
        print("  (no per-layer branch_recovery in these files -- re-run run_geometry)")
    branches = sorted({b for r in recs.values() for b in r})
    print("  " + "branch".ljust(12) + "".join(t[:14].ljust(15) for t in tags))
    for b in branches:
        cells = []
        for t in tags:
            v = recs[t].get(b, {}).get("purity")
            base_v = recs[a.base_tag].get(b, {}).get("purity")
            if v is None:
                cells.append("-".ljust(15))
            elif t == a.base_tag or base_v is None:
                cells.append(f"{v:.2f}".ljust(15))
            else:
                cells.append(f"{v:.2f} ({v - base_v:+.2f})".ljust(15))
        print("  " + b.ljust(12) + "".join(cells))

    print("\nRead: a branch whose recovery RISES under the organism finetuned on its own "
          "domain\nis the hypothesis working. A branch that moves under an UNRELATED "
          "organism is\ncross-domain leakage -- which is the transfer effect this project "
          "is about.")


if __name__ == "__main__":
    main()
