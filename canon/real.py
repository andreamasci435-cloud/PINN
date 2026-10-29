"""Measured-run benchmark with calibrated CSV and recorded Dirichlet boundary.

Supported: constant ambient, initially equilibrated bar, insulated right end,
constant geometry and distinct protocol descriptors. No imputation of missing data.
"""

import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import torch

from .data import validate_csv, validate_split
from .evaluate import fit_classical, metrics
from .experiment import dump
from .fdm import sample, solve
from .pinn import fit_pinn


def load_measured(cfg, csv_path, metadata_path):
    qc = validate_csv(csv_path, cfg.length)
    metadata = json.loads(Path(metadata_path).read_text())
    if metadata.get("provenance") != "measured":
        raise ValueError("Metadata must declare provenance=measured")
    validate_split(metadata["split"])
    ids = sum(metadata["split"].values(), [])
    if set(ids) != set(qc["runs"]) or set(ids) != set(metadata["runs"]):
        raise ValueError("CSV, metadata and split must contain exactly the same run IDs")
    required = [
        "operator",
        "date",
        "material",
        "geometry",
        "calibration_id",
        "ambient_calibration_id",
        "sensor_position_uncertainty_m",
        "temperature_uncertainty_C",
        "notes",
    ]
    if any(k not in metadata for k in required):
        raise ValueError(f"Metadata requires {required}")
    if abs(float(metadata["geometry"]["length_m"]) - cfg.length) > 1e-9:
        raise ValueError("Metadata geometry and configured length disagree")
    for key in ["sensor_position_uncertainty_m", "temperature_uncertainty_C"]:
        value = float(metadata[key])
        if not np.isfinite(value) or value <= 0:
            raise ValueError(f"{key} must be positive and finite")
    with Path(csv_path).open() as f:
        rows = list(csv.DictReader(f))
    if max(abs(float(r["ambient_C"]) - cfg.ambient) for r in rows) > 0.1:
        raise ValueError("This model supports constant ambient only (tolerance 0.1 °C)")
    runs = []
    contexts = []
    for run_id in ids:
        block = [r for r in rows if r["run_id"] == run_id]
        meta = metadata["runs"][run_id]
        ts = np.array(sorted({float(r["time_s"]) for r in block}))
        sensors = sorted(
            {r["sensor_id"] for r in block},
            key=lambda s: next(float(r["x_m"]) for r in block if r["sensor_id"] == s),
        )
        xs = np.array([next(float(r["x_m"]) for r in block if r["sensor_id"] == s) for s in sensors])
        if len(np.unique(xs)) != len(xs):
            raise ValueError("Sensor positions must be unique")
        lookup = {(r["sensor_id"], float(r["time_s"])): float(r["temperature_C"]) for r in block}
        if len(lookup) != len(ts) * len(sensors):
            raise ValueError("Incomplete sensor-time grid; document and process gaps explicitly")
        obs = np.array([[lookup[(s, t)] for s in sensors] for t in ts])
        if ts[0] != 0 or abs(ts[-1] - cfg.duration) > 1e-6:
            raise ValueError("Every run must span [0, config.duration] with initial readings")
        if np.max(np.abs(obs[0] - cfg.ambient)) > float(metadata["temperature_uncertainty_C"]) * 3:
            raise ValueError("Initial state is not equilibrated within 3 measurement uncertainties")
        bt = np.asarray(meta["boundary_time_s"], dtype=float)
        bv = np.asarray(meta["boundary_temperature_C"], dtype=float)
        if (
            bt.ndim != 1
            or len(bt) < 3
            or bv.shape != bt.shape
            or not np.isfinite([bt, bv]).all()
            or np.any(np.diff(bt) <= 0)
            or bt[0] != 0
            or bt[-1] < cfg.duration
        ):
            raise ValueError("Boundary measurements must be finite, sorted and cover the full run")
        amplitude = float(meta["amplitude_C"])
        off = float(meta["off_s"])
        if not 0 < amplitude <= 100 or not 0 < off < cfg.duration:
            raise ValueError("Invalid protocol descriptors amplitude_C/off_s")
        if (amplitude, off) in contexts:
            raise ValueError(
                "Distinct recorded boundary histories require distinct protocol descriptors in this conditional PINN"
            )
        contexts.append((amplitude, off))
        runs.append(
            dict(
                run_id=run_id,
                split=next(k for k, v in metadata["split"].items() if run_id in v),
                amplitude=amplitude,
                off=off,
                t=ts,
                sensor_x=xs,
                observations=obs,
                boundary=(bt, bv),
            )
        )
    return runs, qc, metadata


def run_measured(cfg, csv_path, metadata_path, output):
    runs, qc, metadata = load_measured(cfg, csv_path, metadata_path)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    dump(output / "config.json", cfg.model_dump())
    dump(output / "metadata.json", metadata)
    dump(output / "quality.json", qc)
    train = [r for r in runs if r["split"] == "train"]
    val = [r for r in runs if r["split"] == "validation"]
    test = [r for r in runs if r["split"] == "test"]
    candidates = []
    histories = {}

    def predict(candidate, run):
        xx, tt = np.meshgrid(run["sensor_x"], run["t"])
        if candidate["method"] == "MLP":
            return candidate["network"].predict(xx, tt, run["amplitude"], run["off"])
        x, t, T = solve(
            cfg,
            candidate["model"],
            candidate["raw"],
            run["amplitude"],
            run["off"],
            times=run["t"],
            boundary=run["boundary"],
        )
        return sample(x, t, T, xx, tt).reshape(xx.shape)

    def scores(candidate, subset):
        return {r["run_id"]: metrics(predict(candidate, r), r["observations"], cfg.ambient) for r in subset}

    for kind in cfg.models:
        print(f"Measured train: classical {kind}", flush=True)
        raw, info = fit_classical(cfg, train, kind)
        candidates.append(dict(id=f"FDM-{kind}", method="Classical", model=kind, raw=raw, diagnostics=info))
        for seed in cfg.seeds:
            print(f"Measured train: PINN {kind}, seed {seed}", flush=True)
            net, history, elapsed = fit_pinn(cfg, train, kind, seed)
            key = f"PINN-{kind}-{seed}"
            torch.save(net.state_dict(), output / f"{key}.pt")
            histories[key] = history
            candidates.append(
                dict(
                    id=key,
                    method="PINN",
                    model=kind,
                    seed=seed,
                    raw=net.raw.detach().numpy(),
                    elapsed_s=elapsed,
                )
            )
    for seed in cfg.seeds:
        net, history, elapsed = fit_pinn(cfg, train, "M0", seed, data_only=True)
        key = f"MLP-{seed}"
        torch.save(net.state_dict(), output / f"{key}.pt")
        histories[key] = history
        candidates.append(
            dict(id=key, method="MLP", model="M0", seed=seed, network=net, raw=None, elapsed_s=elapsed)
        )
    groups = {}
    for c in candidates:
        c["validation"] = scores(c, val)
        group = c["method"] + "-" + c["model"]
        groups.setdefault(group, []).extend(s["rmse_C"] for s in c["validation"].values())
    groups = {g: float(np.mean(v)) for g, v in groups.items()}
    selection = dict(
        selected=min(groups, key=groups.get),
        validation_rmse_C=groups,
        criterion="Equal-weight run/seed validation RMSE; frozen before test",
    )
    dump(output / "selection.json", selection)
    rows = []
    for c in candidates:
        c["test"] = scores(c, test)
        raw = c.pop("raw")
        c.pop("network", None)
        c["raw_parameters"] = None if raw is None else raw.tolist()
        rows.append(c)
    report = dict(
        provenance="measured",
        config=cfg.model_dump(),
        selection=selection,
        results=rows,
        histories=histories,
        data_sha256=qc["sha256"],
        metadata_sha256=hashlib.sha256(Path(metadata_path).read_bytes()).hexdigest(),
        limitations=[
            "No truth-field or true-parameter metrics for measurements.",
            "MLP uses amplitude/off descriptors, not the complete measured forcing history.",
            "PINN endpoint is forward FDM prediction with inferred coefficients and measured test boundary.",
        ],
    )
    dump(output / "measured_results.json", report)
    return report
