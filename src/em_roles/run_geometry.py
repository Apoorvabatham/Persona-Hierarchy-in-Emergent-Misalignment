"""Run every §7 test over a saved activation file, layer by layer.

    python -m em_roles.run_geometry --acts .../acts_base_instructions.npz

Reports the noise floor FIRST and refuses to interpret the rest if it fails: if paraphrase
wording moves the representation as much as role identity does, every statistic below is
describing the prompt, not the persona.
"""

import argparse
import json
from pathlib import Path

import numpy as np

from em_roles import geometry


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--acts", type=Path, required=True)
    p.add_argument("--layers", default=None, help="comma-separated; default: a sweep of 9")
    p.add_argument("--n-null", type=int, default=200)
    p.add_argument("--out", type=Path, default=None)
    a = p.parse_args()

    z = np.load(a.acts, allow_pickle=True)
    A, roles, layers = z["acts"].astype(np.float32), list(z["roles"]), list(z["layers"])
    qs = list(z["question"]) if "question" in z else ["?"] * len(roles)
    tree = geometry.load_tree()
    meta = json.loads(str(z["meta"]))
    print(f"{a.acts.name}: {A.shape[1]} items, {A.shape[0]} layers, d={A.shape[2]}")
    print(f"model {meta['model']} | adapter {meta['adapter']}\n")

    want = ([int(x) for x in a.layers.split(",")] if a.layers
            else [layers[i] for i in np.linspace(0, len(layers) - 1, 9).astype(int)])
    rows = []
    print(f'{"layer":>6}{"noise":>8}{"probe":>8}{"|cos|":>8}{"rank":>7}'
          f'{"br/root":>9}{"br/leaf":>9}{"ultra":>8}{"p_tree":>8}{"ARI":>7}')
    for L in want:
        X = A[layers.index(L)]
        nf = geometry.noise_floor(X, roles, qs)
        pr = geometry.probe_generalisation(X, roles, tree)
        ad = geometry.additive_decomposition(X, roles, tree)
        ul = geometry.ultrametricity(geometry.role_distance_matrix(X, roles)["D"])
        tn = geometry.tree_fit_vs_null(X, roles, tree, n_null=a.n_null)
        ari = geometry.recovered_branch_ari(X, roles, tree)
        rows.append({"layer": int(L), "noise_floor": nf, "probe": pr, "decomposition": ad,
                     "ultrametric_violation": ul, "tree_vs_null": tn, "recovered_ari": ari,
                     "branch_recovery": geometry.branch_recovery(X, roles, tree)})
        print(f'{L:>6}{nf["ratio"]:>8.2f}{pr["mean_accuracy"]:>8.3f}'
              f'{ad["mean_abs_residual_branch_cos"]:>8.3f}{ad["sibling_residual_eff_rank"]:>7.2f}'
              f'{ad["mean_branch_norm_frac"]:>9.3f}{ad["mean_branch_over_leaf"]:>9.2f}{ul:>8.3f}{tn["p_value"]:>8.3f}{ari:>7.2f}')

    uq = list(dict.fromkeys(qs))
    if len(uq) > 1:
        L = max(rows, key=lambda r: r["probe"]["mean_accuracy"])["layer"]
        X = A[layers.index(L)]
        print(f"\nper-question at layer {L} -- geometry that holds for only one question is a "
              f"property of\nthat question, not of the role:")
        print(f'{"question":<26}{"noise":>8}{"probe":>8}{"br/root":>9}{"ARI":>7}')
        pq = {}
        for q in uq:
            m = np.array(qs) == q
            Xq, rq = X[m], [r for r, k in zip(roles, m) if k]
            nf = geometry.noise_floor(Xq, rq)
            pr = geometry.probe_generalisation(Xq, rq, tree)["mean_accuracy"]
            ad = geometry.additive_decomposition(Xq, rq, tree)["mean_branch_norm_frac"]
            ari = geometry.recovered_branch_ari(Xq, rq, tree)
            pq[str(q)] = {"noise_ratio": nf["ratio"], "probe": pr, "branch_norm": ad, "ari": ari}
            print(f'{str(q):<26}{nf["ratio"]:>8.2f}{pr:>8.3f}{ad:>9.3f}{ari:>7.2f}')
        sp = np.std([v["probe"] for v in pq.values()])
        print(f"  probe spread across questions: {sp:.3f}"
              + ("  ⚠️ large -- the geometry is question-dependent" if sp > 0.08 else "  (stable)"))
        rows.append({"per_question_at_layer": int(L), "per_question": pq,
                     "probe_std_across_questions": float(sp)})

    best = max([r for r in rows if "probe" in r], key=lambda r: r["probe"]["mean_accuracy"])
    print(f'\nbest probe layer: {best["layer"]} at {best["probe"]["mean_accuracy"]:.3f} '
          f'(chance 0.5)')
    if not any(r["noise_floor"]["interpretable"] for r in rows if "noise_floor" in r):
        print("\n⚠️  NOISE FLOOR FAILED at every layer: between-role distance is not clearly "
              "larger than\n    within-role (paraphrase) distance. Nothing above is "
              "interpretable as role structure.")
    L = best["layer"]
    X = A[layers.index(L)]
    ari_all = geometry.recovered_branch_ari(X, roles, tree, leaves_only=False)
    print(f"\nwhat the model groups at layer {L} -- LEAVES ONLY "
          f"(ARI {best['recovered_ari']:.2f}); including the authored depth-1 nodes gives "
          f"ARI {ari_all:.2f}:")
    clusters = geometry.recovered_clusters(X, roles, tree)
    for cid, members in sorted(clusters.items()):
        print(f"  cluster {cid}: {', '.join(members)}")
    rec = geometry.branch_recovery(X, roles, tree)
    print("\nper-branch recovery (fraction of a branch's 3 leaves in one cluster):")
    for b, v in rec.items():
        bar = "#" * int(v["purity"] * 12)
        print(f'  {b:<11}{v["purity"]:.2f}  {bar}')
    rows.append({"recovered_clusters_at_layer": int(L),
                 "clusters": {str(k): v for k, v in clusters.items()},
                 "branch_recovery": rec, "ari_all_nodes": ari_all})

    out = a.out or a.acts.with_suffix(".geometry.json")
    Path(out).write_text(json.dumps(rows, indent=1))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
