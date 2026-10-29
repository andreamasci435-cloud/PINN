"""Classical run bootstrap and parameter stability summaries.

Bootstrap resamples entire training runs, never individual correlated timestamps.
Percentiles from very few runs are exploratory and not calibrated intervals.
"""

import json
from pathlib import Path

import numpy as np

from .config import Config
from .data import synthetic
from .evaluate import fit_classical
from .physics import coefficients


def bootstrap(config_path, kind, output, repeats=100, seed=123):
    if repeats < 2:
        raise ValueError("At least two resamples required")
    cfg = Config.model_validate_json(Path(config_path).read_text())
    runs = [r for r in synthetic(cfg) if r["split"] == "train"]
    rng = np.random.default_rng(seed)
    x = np.linspace(0, 1, 101)
    profiles = []
    for i in range(repeats):
        subset = [runs[j] for j in rng.integers(0, len(runs), size=len(runs))]
        raw, info = fit_classical(cfg, subset, kind)
        if not info["success"]:
            raise RuntimeError(f"Bootstrap fit {i} failed: {info['message']}")
        profiles.append(np.stack(coefficients(kind, raw, x, np.zeros_like(x))))
    q = np.quantile(profiles, [0.025, 0.5, 0.975], axis=0)
    result = dict(
        provenance="synthetic",
        resampling_unit="entire training run",
        repeats=repeats,
        seed=seed,
        model=kind,
        x_m=(x * cfg.length).tolist(),
        quantiles=[0.025, 0.5, 0.975],
        alpha_quantiles=q[:, 0].tolist(),
        beta_quantiles=q[:, 1].tolist(),
        config=cfg.model_dump(),
        limitation="Only three distinct training protocols. Percentiles are exploratory; not calibrated coverage. M3 profiles evaluated at ambient.",
    )
    with Path(output).open("x") as f:
        json.dump(result, f, indent=2, allow_nan=False)
    return result
