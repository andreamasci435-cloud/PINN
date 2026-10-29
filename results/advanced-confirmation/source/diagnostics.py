"""Explicit numerical evidence. No claim of physical validity is inferred from passing gates."""

import numpy as np
import torch

from .physics import heater
from .pinn import derivative


def constraint_audit(model, cfg, run):
    t = np.linspace(0, cfg.duration, 101)
    left = model.predict(np.zeros_like(t), t, run["amplitude"], run["off"])
    initial = model.predict(np.linspace(0, cfg.length, 101), np.zeros(101), run["amplitude"], run["off"])
    inputs = torch.tensor(
        np.column_stack(
            [
                np.ones(101),
                t / cfg.duration,
                np.full(101, run["amplitude"] / cfg.temperature_scale),
                np.full(101, run["off"] / cfg.duration),
            ]
        ),
        dtype=torch.float64,
        requires_grad=True,
    )
    gradient = derivative(model(inputs), inputs)[:, 0].detach().numpy() * cfg.temperature_scale / cfg.length
    return {
        "initial_max_error_C": float(np.max(np.abs(initial - cfg.ambient))),
        "left_max_error_C": float(
            np.max(np.abs(left - heater(t, run["amplitude"], run["off"], cfg.ambient)))
        ),
        "right_max_gradient_C_per_m": float(np.max(np.abs(gradient))),
    }


def evidence_summary(result):
    rows = [r for r in result["results"] if r["method"] == "PINN"]
    split = result["manifest"]["runs"]
    sets = {
        name: {r["run_id"] for r in split if r["split"] == name} for name in ["train", "validation", "test"]
    }
    gates = [
        {
            "label": "Disjoint experiment splits",
            "status": "passed"
            if not (
                sets["train"] & sets["test"]
                or sets["train"] & sets["validation"]
                or sets["validation"] & sets["test"]
            )
            else "failed",
            "detail": f"{len(sets['train'])} train / {len(sets['validation'])} validation / {len(sets['test'])} test runs",
        },
        {
            "label": "Repeated initialization",
            "status": "passed" if len(result["config"]["seeds"]) >= 5 else "limited",
            "detail": f"{len(result['config']['seeds'])} seeds; this is optimization variability, not calibrated uncertainty",
        },
        {
            "label": "Direct neural predictions",
            "status": "passed" if all("direct_sensor_test" in r for r in rows) else "limited",
            "detail": "Reported separately from forward-solver predictions using learned parameters",
        },
        {
            "label": "Physical validation",
            "status": "pending",
            "detail": "No physical measurements supplied; all results are synthetic",
        },
    ]
    if result["config"]["boundary_mode"] == "hard":
        ok = all(max(r["constraint_audit"].values()) < 1e-8 for r in rows)
        gates.insert(
            2,
            {
                "label": "Exact initial and boundary constraints",
                "status": "passed" if ok else "failed",
                "detail": "Maximum numerical discrepancy checked on 101 fresh boundary/initial points",
            },
        )
    return {
        "gates": gates,
        "scope": "Computational evidence only; not a publication acceptance or physical validation certificate",
    }
