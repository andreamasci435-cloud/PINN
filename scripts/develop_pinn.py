"""Development-only run. Prints validation metrics; never evaluates test observations."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from canon.config import Config
from canon.data import synthetic
from canon.pinn import fit_pinn
from canon.experiment import score
import numpy as np

cfg = Config(
    scenario="local_loss",
    models=["M2"],
    epochs=6000,
    lbfgs=1500,
    collocation=512,
    boundary_mode="hard",
    adaptive_sampling=False,
    warmup_epochs=1500,
    parameter_lr=0.0001,
    continuous_protocols=True,
    weights={"data": 20.0, "pde": 1.0, "ic": 10.0, "bc": 10.0, "reg": 1e-6},
    seed=42,
)
runs = synthetic(cfg)
train = [r for r in runs if r["split"] == "train"]
val = next(r for r in runs if r["split"] == "validation")
model, history, elapsed = fit_pinn(
    cfg,
    train,
    "M2",
    42,
    callback=lambda e, n, r: print(e, round(r["total"], 6), flush=True) if e % 500 == 0 else None,
)
c = {"method": "PINN", "model": "M2", "raw": model.raw.detach().numpy(), "network": model}
print("VALIDATION ONLY", score(cfg, c, val)[0], "seconds", elapsed, flush=True)
xx, tt = np.meshgrid(val["sensor_x"], val["t"])
from canon.evaluate import metrics

print("RAW", model.raw.detach().numpy(), "FINAL LOSS", history[-1], flush=True)
print(
    "DIRECT VALIDATION",
    metrics(model.predict(xx, tt, val["amplitude"], val["off"]), val["observations"]),
    flush=True,
)
