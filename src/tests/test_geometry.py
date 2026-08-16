"""Tests for the hierarchy geometry. Written before src/em_roles/geometry.py (TDD).

These are statistical tests, so testing them on real activations proves nothing -- we would
have no ground truth. Instead each is run against SYNTHETIC data with a PLANTED structure:

  hierarchical  v(leaf) = root + branch_i + leaf_ij   (orthogonal components)
  flat          v(role) = a_role * root               (all vectors parallel, one dial)

A test worth running must fire on the first and stay silent on the second. Several of the
assertions below are that a statistic does NOT detect hierarchy in flat data -- that is the
half that catches a metric which reports structure no matter what it is fed.
"""

import numpy as np
import pytest

from em_roles import geometry

D, N_PARA = 64, 5
RNG = np.random.default_rng(0)


def _tree():
    return geometry.load_tree()


def _orth(n, d, rng):
    return np.linalg.qr(rng.standard_normal((d, n)))[0].T[:n]


def planted_hierarchical(tree, noise=0.05, rng=RNG):
    """root + branch + leaf, mutually orthogonal, with paraphrase jitter."""
    branches = sorted({v["branch"] for v in tree.values()})
    basis = _orth(1 + len(branches) + len(tree), D, rng)
    root, bvec = basis[0], dict(zip(branches, basis[1:1 + len(branches)]))
    lvec = dict(zip(tree, basis[1 + len(branches):]))
    X, roles = [], []
    for r, meta in tree.items():
        base = root + bvec[meta["branch"]] + (lvec[r] if meta["depth"] == 2 else 0)
        for _ in range(N_PARA):
            X.append(base + noise * rng.standard_normal(D))
            roles.append(r)
    return np.array(X), roles


def planted_flat(tree, noise=0.05, rng=RNG):
    """One direction, per-role magnitude only -- the rank-1 null hypothesis."""
    root = _orth(1, D, rng)[0]
    # Magnitudes must NOT follow role order: roles.json is branch-ordered, so an
    # index-dependent magnitude smuggles real branch structure into the flat null.
    mags = dict(zip(tree, rng.permutation(np.linspace(0.5, 1.5, len(tree)))))
    X, roles = [], []
    for r in tree:
        for _ in range(N_PARA):
            X.append(mags[r] * root + noise * rng.standard_normal(D))
            roles.append(r)
    return np.array(X), roles


# ---------- tree data ----------

def test_tree_covers_every_role_and_is_acyclic():
    t = _tree()
    assert len(t) == 26
    for r, m in t.items():
        assert m["parent"] in t or m["parent"] is None, r
        assert m["depth"] in (0, 1, 2), r
    assert sum(m["depth"] == 2 for m in t.values()) == 15      # 5 branches x 3 leaves


def test_branch_leaves_are_exactly_three_each():
    t = _tree()
    for b in ("artist", "medical", "financial", "sport", "code"):
        assert len(geometry.leaves_of(t, b)) == 3, b


# ---------- 7.1 noise floor ----------

def test_noise_floor_separates_when_roles_are_real():
    X, roles = planted_hierarchical(_tree())
    nf = geometry.noise_floor(X, roles)
    assert nf["ratio"] > 2.0, nf


def test_noise_floor_reports_no_separation_when_role_is_all_noise():
    """Same role identity for every row -> between == within, ratio ~1."""
    X = RNG.standard_normal((26 * N_PARA, D))
    roles = [r for r in _tree() for _ in range(N_PARA)]
    nf = geometry.noise_floor(X, roles)
    assert nf["ratio"] < 1.3, nf


# ---------- 7.3 probe generalisation ----------

def test_probe_generalises_to_held_out_sibling_under_hierarchy():
    """0.71, not 0.95: the held-out sibling carries a leaf direction never seen in
    training, so perfect transfer is not the ceiling even under a perfect tree."""
    X, roles = planted_hierarchical(_tree())
    acc = geometry.probe_generalisation(X, roles, _tree())
    assert acc["mean_accuracy"] > 0.65, acc


def test_probe_fails_to_generalise_under_a_flat_structure():
    X, roles = planted_flat(_tree())
    acc = geometry.probe_generalisation(X, roles, _tree())
    assert acc["mean_accuracy"] < 0.60, acc


# ---------- 7.4 additive decomposition ----------

def test_leaf_residuals_are_orthogonal_to_their_branch_under_hierarchy():
    X, roles = planted_hierarchical(_tree(), noise=0.02)
    d = geometry.additive_decomposition(X, roles, _tree())
    assert d["mean_abs_residual_branch_cos"] < 0.2, d       # residual _|_ branch
    assert d["sibling_residual_eff_rank"] > 1.9, d          # 3 orthogonal residuals span 2
    assert d["mean_branch_norm_frac"] > 0.5, d              # the branch is a real component


def test_flat_structure_shows_no_additive_decomposition():
    """With one shared direction, leaf residuals are collinear: rank 1, and parallel
    to the branch vector rather than orthogonal to it."""
    X, roles = planted_flat(_tree(), noise=0.02)
    d = geometry.additive_decomposition(X, roles, _tree())
    assert d["sibling_residual_eff_rank"] < 1.5, d
    assert d["mean_branch_norm_frac"] < 0.2, d             # no branch has a mean of its own


# ---------- 7.5 ultrametricity ----------

def test_ultrametric_violation_is_lower_for_hierarchy_than_for_flat():
    th, _ = planted_hierarchical(_tree())
    tf, _ = planted_flat(_tree())
    roles = [r for r in _tree() for _ in range(N_PARA)]
    vh = geometry.ultrametricity(geometry.role_distance_matrix(th, roles)["D"])
    vf = geometry.ultrametricity(geometry.role_distance_matrix(tf, roles)["D"])
    assert vh < vf, (vh, vf)


def test_random_tree_null_rejects_a_flat_structure():
    """The null that matters: does OUR tree fit better than random trees?"""
    X, roles = planted_hierarchical(_tree())
    res = geometry.tree_fit_vs_null(X, roles, _tree(), n_null=50, seed=0)
    assert res["p_value"] < 0.1, res

    Xf, rf = planted_flat(_tree())
    resf = geometry.tree_fit_vs_null(Xf, rf, _tree(), n_null=50, seed=0)
    assert resf["p_value"] > 0.1, resf


def test_recovered_tree_matches_the_planted_one():
    X, roles = planted_hierarchical(_tree())
    ari = geometry.recovered_branch_ari(X, roles, _tree())
    assert ari > 0.6, ari


def test_unknown_branch_raises():
    with pytest.raises(KeyError):
        geometry.leaves_of(_tree(), "astrology")
