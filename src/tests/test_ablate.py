"""Tests for direction ablation. Written before src/em_roles/ablate.py (TDD)."""

import numpy as np
import pytest

from em_roles import ablate

D = 32
RNG = np.random.default_rng(0)


def test_ablation_removes_the_component_along_the_direction():
    v = ablate.unit(RNG.standard_normal(D))
    h = RNG.standard_normal((5, D))
    out = ablate.project_out(h, v)
    assert np.allclose(out @ v, 0, atol=1e-6), "component along v must be gone"


def test_ablation_preserves_everything_orthogonal():
    v = ablate.unit(np.eye(D)[0])
    h = np.zeros((1, D)); h[0, 1] = 4.0; h[0, 2] = 3.0     # already orthogonal to v
    assert np.allclose(ablate.project_out(h, v), h)


def test_ablation_is_idempotent():
    v = ablate.unit(RNG.standard_normal(D))
    h = RNG.standard_normal((4, D))
    once = ablate.project_out(h, v)
    assert np.allclose(ablate.project_out(once, v), once, atol=1e-6)


def test_direction_is_the_difference_of_role_means_and_is_unit():
    X = RNG.standard_normal((40, D))
    roles = ["hacker"] * 20 + ["assistant"] * 20
    v = ablate.role_direction(X, roles, "hacker", "assistant")
    assert np.isclose(np.linalg.norm(v), 1.0)
    expected = X[:20].mean(0) - X[20:].mean(0)
    assert np.allclose(v, ablate.unit(expected))


def test_unknown_role_raises():
    X = RNG.standard_normal((4, D))
    with pytest.raises(KeyError):
        ablate.role_direction(X, ["a"] * 4, "hacker", "a")


def test_random_control_is_unit_reproducible_and_not_the_real_direction():
    v = ablate.role_direction(RNG.standard_normal((40, D)),
                              ["hacker"] * 20 + ["assistant"] * 20, "hacker", "assistant")
    r1 = ablate.random_direction(D, seed=7)
    r2 = ablate.random_direction(D, seed=7)
    assert np.allclose(r1, r2), "control must be reproducible from the seed"
    assert np.isclose(np.linalg.norm(r1), 1.0)
    assert abs(r1 @ v) < 0.5, "a random direction should be near-orthogonal in high-d"
