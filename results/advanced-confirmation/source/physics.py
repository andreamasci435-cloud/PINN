"""Conservative 1D heat equation, assuming constant volumetric heat capacity.

T_t = d_x(alpha(x,T) T_x) - beta(x)(T-T_amb).
alpha = k/(rho cp) [m²/s]; beta = h P/(rho cp A) [1/s].
Variable rho*cp is NOT covered by this reduced conservative equation.
"""

import numpy as np

ALPHA_SCALE = 1e-4
BETA_SCALE = 1e-2


def softplus(x):
    return np.logaddexp(0, x)


def inv_softplus(x):
    return np.log(np.expm1(x))


def heater(t, amplitude, off, ambient=20.0):
    """Smooth measured-temperature surrogate, with a heating and cooling phase."""
    return ambient + amplitude * (-np.expm1(-np.asarray(t) / 8.0)) / (
        1 + np.exp(np.clip((np.asarray(t) - off) / 6, -700, 700))
    )


def coefficients(kind, raw, x, u):
    """Low dimensional smooth hypotheses; x=x/L, u=(T-Tamb)/60.

    M1: softplus quadratic alpha(x); M2: softplus beta with a fixed local basis.
    M3: softplus affine alpha(T). The M2 bump centre/width are a declared prior.
    """
    z = 2 * x - 1
    a = raw[0] + 0 * x
    b = raw[1] + 0 * x
    if kind == "M1":
        a = a + raw[2] * z + raw[3] * z * z
    elif kind == "M2":
        b = b + raw[2] * np.exp(-(((x - 0.4) / 0.15) ** 2))
    elif kind == "M3":
        a = a + raw[2] * u
    return ALPHA_SCALE * softplus(a), BETA_SCALE * softplus(b)


def initial_raw(kind, alpha=8e-5, beta=0.008):
    n = {"M0": 2, "M1": 4, "M2": 3, "M3": 3}[kind]
    raw = np.zeros(n)
    raw[:2] = [inv_softplus(alpha / ALPHA_SCALE), inv_softplus(beta / BETA_SCALE)]
    return raw


def truth_parameters(cfg):
    kind = {"uniform": "M0", "variable_alpha": "M1", "local_loss": "M2", "temperature_alpha": "M3"}[
        cfg.scenario
    ]
    raw = initial_raw(kind, cfg.alpha, cfg.beta)
    if kind == "M1":
        raw[2:] = [0.65, -0.3]
    elif kind == "M2":
        raw[2] = 2.0
    elif kind == "M3":
        raw[2] = 0.8
    return kind, raw
