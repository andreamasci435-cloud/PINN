"""Held-out metrics, classical parameter fitting and local identifiability diagnostics."""

import time

import numpy as np
from scipy.optimize import least_squares

from .fdm import sample, solve
from .physics import initial_raw


def metrics(pred, target, ambient=20):
    error = np.asarray(pred) - np.asarray(target)
    denominator = np.linalg.norm(np.asarray(target) - ambient)
    return dict(
        rmse_C=float(np.sqrt(np.mean(error**2))),
        mae_C=float(np.mean(np.abs(error))),
        relative_l2_excess=float(np.linalg.norm(error) / max(denominator, 1e-12)),
    )


def fit_classical(cfg, runs, kind):
    start = time.perf_counter()

    def residual(raw):
        result = []
        for run in runs:
            x, t, T = solve(
                cfg,
                kind,
                raw,
                run["amplitude"],
                run["off"],
                times=run["t"],
                rtol=2e-6,
                boundary=run.get("boundary"),
            )
            xx, tt = np.meshgrid(run["sensor_x"], run["t"])
            result.extend((sample(x, t, T, xx, tt) - run["observations"].ravel()) / max(cfg.noise, 0.15))
        return np.array(result)

    fit = least_squares(
        residual,
        initial_raw(kind),
        bounds=(-6, 6),
        diff_step=1e-3,
        max_nfev=100,
        xtol=1e-7,
        ftol=1e-7,
        gtol=1e-7,
    )
    singular = np.linalg.svd(fit.jac, compute_uv=False)
    info = dict(
        success=bool(fit.success),
        message=fit.message,
        evaluations=fit.nfev,
        singular_values=singular.tolist(),
        jacobian_condition=float(singular[0] / max(singular[-1], 1e-15)),
        elapsed_s=time.perf_counter() - start,
        note="Local weighted-Jacobian diagnostic; not global identifiability or a confidence interval.",
    )
    return fit.x, info
