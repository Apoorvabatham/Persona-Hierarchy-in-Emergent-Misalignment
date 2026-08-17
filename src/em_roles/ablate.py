"""Direction ablation at inference: delete one axis from the residual stream (§7.6).

    h' = h - (h . v) v          applied at every layer, every token, during generation

No weights change; a forward hook removes the component along v as the model runs. This
tests whether misalignment FLOWS THROUGH a persona direction -- it does not remove the
persona from the weights, so it is unlearning-adjacent, not unlearning.

Two things make the result interpretable, and both are easy to omit:

  RANDOM CONTROL   removing any direction degrades the model a little. Without an
                   equal-norm random-direction arm, "EM fell" cannot be distinguished
                   from "we damaged the model". arXiv 2607.04510 found steering away from
                   a persona direction RAISED misalignment 24%->51% in one condition, so
                   direction interventions are not reliably monotone.

  UNABLATED ARM    the baseline on disk was generated with vLLM. Comparing it to
                   HF-generated ablated output would confound the intervention with the
                   inference stack, so the no-ablation arm is regenerated here too.
"""

import numpy as np


def unit(v):
    n = np.linalg.norm(v)
    assert n > 1e-9, "direction has ~zero norm"
    return v / n


def project_out(h, v):
    """Remove the component of h along unit vector v. h may be (..., d)."""
    v = np.asarray(v)
    return h - np.tensordot(h @ v, v, axes=0).reshape(h.shape)


def role_direction(X, roles, role, anchor):
    """Unit vector from the anchor role's mean to the target role's mean."""
    r = np.asarray(roles)
    for name in (role, anchor):
        if not (r == name).any():
            raise KeyError(name)
    return unit(X[r == role].mean(0) - X[r == anchor].mean(0))


def random_direction(d, seed):
    """Equal-norm control. Reproducible so the arm can be rerun exactly."""
    return unit(np.random.default_rng(seed).standard_normal(d))
