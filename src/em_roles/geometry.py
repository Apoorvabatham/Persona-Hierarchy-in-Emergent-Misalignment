"""Is the role structure in activation space a tree, or one dial? (experiment_2.md §7)

Pure numpy over a (n_prompts x d) activation matrix and its role labels -- no model. Run
after activations.py has embedded the 26 roles x 5 paraphrases.

The four tests and what each discriminates:

  noise_floor            PREREQUISITE. Between-role vs within-role (paraphrase) distance.
                         If these are comparable, the matrix encodes prompt wording rather
                         than role, and nothing below is interpretable.
  probe_generalisation   Train "is this the medical branch?" on two leaves, test on the
                         third. Generalises => leaves inherit a shared branch direction.
  additive_decomposition v(leaf) ~ root + branch + leaf, with orthogonal parts. A flat
                         model has no branch term distinct from the leaf term.
  ultrametricity +       Tree metrics obey d(x,z) <= max(d(x,y), d(y,z)). Compared against
  tree_fit_vs_null       RANDOM TREES over the same roles -- structure may exist without
                         matching ours, and only the random-tree null can tell them apart.

Distances are cosine throughout: activation norms vary with prompt length, and length is a
property of the paraphrase, not the role.
"""

import json
from itertools import combinations
from pathlib import Path

import numpy as np

DATA = Path(__file__).resolve().parents[1] / "data"
REAL_BRANCHES = ("artist", "medical", "financial", "sport", "code")


def load_tree(path=DATA / "role_tree.json"):
    return json.loads(Path(path).read_text())


def leaves_of(tree, branch):
    if branch not in {m["branch"] for m in tree.values()}:
        raise KeyError(branch)
    return [r for r, m in tree.items() if m["branch"] == branch and m["depth"] == 2]


def _unit(X):
    return X / np.clip(np.linalg.norm(X, axis=-1, keepdims=True), 1e-12, None)


def _cos_dist(A, B):
    return 1.0 - _unit(A) @ _unit(B).T


def role_means(X, roles):
    """(n_roles x d) mean activation per role, and the role order."""
    order = list(dict.fromkeys(roles))
    r = np.array(roles)
    return np.array([X[r == k].mean(0) for k in order]), order


def role_distance_matrix(X, roles):
    M, order = role_means(X, roles)
    return {"D": _cos_dist(M, M), "roles": order}


# ---------- 7.1 ----------

def noise_floor(X, roles, groups=None):
    """Between-role vs within-role (paraphrase) cosine distance.

    ratio <= ~1 means paraphrase wording moves the representation as much as role identity
    does, and every downstream test is measuring the prompt, not the persona.
    """
    r = np.array(roles)
    # Within-role distance must be computed WITHIN a question: pooling across questions
    # folds question variance into the paraphrase noise and the ratio collapses.
    g = np.array(groups) if groups is not None else np.zeros(len(roles), dtype=int)
    within = []
    for k in dict.fromkeys(roles):
        for q in dict.fromkeys(g):
            m = (r == k) & (g == q)
            if m.sum() > 1:
                within += list(_cos_dist(X[m], X[m])[np.triu_indices(m.sum(), 1)])
    M, _ = role_means(X, roles)
    between = _cos_dist(M, M)[np.triu_indices(len(M), 1)]
    w, b = float(np.mean(within)), float(np.mean(between))
    return {"within_role": w, "between_role": b, "ratio": b / max(w, 1e-9),
            "interpretable": b / max(w, 1e-9) > 1.5}


# ---------- 7.3 ----------

def probe_generalisation(X, roles, tree, C=1.0):
    """Leave-one-sibling-out linear probe for branch membership.

    Positives are the branch's leaves, negatives every other real branch's leaves. Training
    never sees the held-out leaf, so above-chance accuracy on it means the branch direction
    is shared rather than memorised per role.
    """
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import balanced_accuracy_score

    r = np.array(roles)
    per = {}
    for b in REAL_BRANCHES:
        leaves = leaves_of(tree, b)
        others = [l for ob in REAL_BRANCHES if ob != b for l in leaves_of(tree, ob)]
        accs = []
        for held in leaves:
            tr = [l for l in leaves if l != held]
            Xtr = np.concatenate([X[np.isin(r, tr)], X[np.isin(r, others)]])
            ytr = np.r_[np.ones((r[np.isin(r, tr)]).size), np.zeros((r[np.isin(r, others)]).size)]
            # held-out leaf (should be positive) vs held-out negatives from other branches
            neg_held = [leaves_of(tree, ob)[leaves.index(held)] for ob in REAL_BRANCHES if ob != b]
            Xte = np.concatenate([X[r == held], X[np.isin(r, neg_held)]])
            yte = np.r_[np.ones((r == held).sum()), np.zeros(np.isin(r, neg_held).sum())]
            clf = LogisticRegression(max_iter=2000, C=C).fit(Xtr, ytr)
            # balanced, because the held-out set is 1 positive role vs 4 negative
            # ones -- plain accuracy has a 0.8 chance level and looks like a result
            accs.append(float(balanced_accuracy_score(yte, clf.predict(Xte))))
        per[b] = float(np.mean(accs))
    return {"per_branch": per, "mean_accuracy": float(np.mean(list(per.values())))}


# ---------- 7.4 ----------

def additive_decomposition(X, roles, tree):
    """Test v(leaf) ~ root + branch + leaf with orthogonal components.

    branch component = mean of its leaves minus the global mean; leaf residual = leaf minus
    its branch mean. Under a tree those residuals are near-orthogonal to the branch and to
    each other. Under one shared dial they stay collinear.
    """
    M, order = role_means(X, roles)
    idx = {k: i for i, k in enumerate(order)}
    root = M.mean(0)
    rb, ranks, frac, frac_leaf = [], [], [], []
    for b in REAL_BRANCHES:
        leaves = leaves_of(tree, b)
        L = M[[idx[l] for l in leaves]]
        bvec = L.mean(0) - root
        res = L - L.mean(0)
        # ABSOLUTE cosine: centred collinear residuals give +1 and -1, which average to 0
        # and would be indistinguishable from genuine orthogonality.
        rb += [abs(float(c)) for c in (_unit(res) @ _unit(bvec[None])[0])]
        # Effective rank, not pairwise cosine: centring three vectors forces cos ~ -0.5
        # whether they are orthogonal or collinear, so cosine cannot discriminate here.
        # Three orthogonal residuals span 2 dims; three collinear ones span 1.
        sv = np.linalg.svd(res, compute_uv=False)
        ranks.append(float(sv.sum() ** 2 / max((sv ** 2).sum(), 1e-12)))
        # Two normalisations, because neither alone is readable everywhere.
        # over_root discriminates cleanly on synthetic data but is deflated on real
        # activations, where ||root|| is dominated by shared prompt structure.
        # over_leaf asks the interpretable question -- is branch identity larger than
        # leaf idiosyncrasy -- and stays on scale for real data.
        frac.append(float(np.linalg.norm(bvec) / max(np.linalg.norm(root), 1e-12)))
        frac_leaf.append(float(np.linalg.norm(bvec) /
                               max(np.linalg.norm(res, axis=1).mean(), 1e-12)))
    return {"mean_abs_residual_branch_cos": float(np.mean(rb)),
            "sibling_residual_eff_rank": float(np.mean(ranks)),
            "mean_branch_norm_frac": float(np.mean(frac)),
            "mean_branch_over_leaf": float(np.mean(frac_leaf)),
            "n_residuals": len(rb)}


# ---------- 7.5 ----------

def ultrametricity(D):
    """Fraction of triples violating d(x,z) <= max(d(x,y), d(y,z)), with 1% tolerance."""
    n, bad, tot = len(D), 0, 0
    for i, j, k in combinations(range(n), 3):
        for a, b, c in ((i, j, k), (j, k, i), (k, i, j)):
            tot += 1
            if D[a, c] > max(D[a, b], D[b, c]) * 1.01:
                bad += 1
    return bad / max(tot, 1)


def _branch_separation(D, order, labels):
    """Mean between-branch minus mean within-branch distance. Higher = grouping fits better."""
    lab = np.array([labels[r] for r in order])
    iu = np.triu_indices(len(order), 1)
    same = lab[iu[0]] == lab[iu[1]]
    d = D[iu]
    if same.sum() == 0 or (~same).sum() == 0:
        return 0.0
    return float(d[~same].mean() - d[same].mean())


def tree_fit_vs_null(X, roles, tree, n_null=200, seed=0):
    """Does OUR branch assignment separate roles better than random groupings of the same shape?

    The p-value is the fraction of random trees separating at least as well. A low p-value
    means the specific tree matters; a high one can still coexist with real structure that
    simply is not the tree we assumed -- see recovered_branch_ari.
    """
    rm = role_distance_matrix(X, roles)
    D, order = rm["D"], rm["roles"]
    real = {r: tree[r]["branch"] for r in order}
    obs = _branch_separation(D, order, real)

    rng = np.random.default_rng(seed)
    sizes = [sum(1 for r in order if real[r] == b) for b in dict.fromkeys(real.values())]
    names = list(dict.fromkeys(real.values()))
    null = []
    for _ in range(n_null):
        perm = list(order)
        rng.shuffle(perm)
        lab, i = {}, 0
        for nm, s in zip(names, sizes):
            for r in perm[i:i + s]:
                lab[r] = nm
            i += s
        null.append(_branch_separation(D, order, lab))
    null = np.array(null)
    return {"observed": obs, "null_mean": float(null.mean()), "null_std": float(null.std()),
            "p_value": float((null >= obs).mean()), "n_null": n_null}


def recovered_clusters(X, roles, tree, k=len(REAL_BRANCHES), leaves_only=True):
    """The grouping the model actually forms, as role names. Read this whenever ARI is low:
    a different-but-coherent grouping is a finding, not a null result."""
    from sklearn.cluster import AgglomerativeClustering

    rm = role_distance_matrix(X, roles)
    keep = [i for i, r in enumerate(rm["roles"])
            if tree[r]["branch"] in REAL_BRANCHES
            and (tree[r]["depth"] == 2 or not leaves_only)]
    D = rm["D"][np.ix_(keep, keep)]
    lab = AgglomerativeClustering(n_clusters=k, metric="precomputed",
                                  linkage="average").fit_predict(D)
    out = {}
    for i, c in zip(keep, lab):
        out.setdefault(int(c), []).append(rm["roles"][i])
    return out


def branch_recovery(X, roles, tree, k=len(REAL_BRANCHES)):
    """Per branch, the fraction of its 3 leaves landing in one cluster.

    ARI is a single number over all branches and hides which ones hold. A branch at 1.0 is
    recovered exactly; one at 0.33 is scattered. Reported alongside the cluster dump because
    "the tree half-works" is a more accurate summary than any single index.
    """
    clusters = recovered_clusters(X, roles, tree, k=k)
    where = {r: c for c, members in clusters.items() for r in members}
    out = {}
    for b in REAL_BRANCHES:
        leaves = [l for l in leaves_of(tree, b) if l in where]
        if not leaves:
            continue
        counts = {}
        for l in leaves:
            counts[where[l]] = counts.get(where[l], 0) + 1
        out[b] = {"purity": max(counts.values()) / len(leaves),
                  "largest_cluster": int(max(counts, key=counts.get)),
                  "leaves": leaves}
    return out


def recovered_branch_ari(X, roles, tree, k=len(REAL_BRANCHES), leaves_only=True):
    """Cluster roles bottom-up, compare the recovered grouping to ours (Adjusted Rand Index).

    A low ARI with a clear cluster structure is a RESULT, not a failure: the model has a
    persona grouping, just not the one we assumed.
    """
    from sklearn.cluster import AgglomerativeClustering
    from sklearn.metrics import adjusted_rand_score

    rm = role_distance_matrix(X, roles)
    keep = [i for i, r in enumerate(rm["roles"])
            if tree[r]["branch"] in REAL_BRANCHES
            and (tree[r]["depth"] == 2 or not leaves_only)]
    D = rm["D"][np.ix_(keep, keep)]
    truth = [tree[rm["roles"][i]]["branch"] for i in keep]
    pred = AgglomerativeClustering(n_clusters=k, metric="precomputed",
                                   linkage="average").fit_predict(D)
    return float(adjusted_rand_score(truth, pred))
