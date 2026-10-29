"""Synthetic replicas and strict CSV ingestion. Raw measurements are never overwritten."""

import csv
import hashlib
import json
from pathlib import Path

import numpy as np

from .fdm import sample, solve
from .physics import truth_parameters

COLUMNS = [
    "run_id",
    "time_s",
    "sensor_id",
    "x_m",
    "temperature_C",
    "ambient_C",
    "heater_state",
    "configuration",
    "notes",
]


def synthetic(cfg):
    rng = np.random.default_rng(cfg.seed)
    kind, raw = truth_parameters(cfg)
    runs = []
    positions = np.linspace(0.02, cfg.length - 0.02, cfg.sensors)
    protocols = [
        (45, 0.475, "train"),
        (60, 0.6, "train"),
        (50, 0.525, "train"),
        (55, 0.65, "validation"),
        (65, 0.575, "test"),
    ]
    if cfg.protocol_set == "confirmation":
        protocols = [
            (42, 0.45, "train"),
            (58, 0.625, "train"),
            (52, 0.55, "train"),
            (48, 0.70, "validation"),
            (62, 0.50, "validation"),
            (67, 0.585, "test"),
            (46, 0.675, "test"),
        ]
    for i, (amplitude, fraction, split) in enumerate(protocols):
        off = cfg.duration * fraction
        x, t, T = solve(cfg, kind, raw, amplitude, off, nx=cfg.truth_nx)
        xx, tt = np.meshgrid(positions, t)
        clean = sample(x, t, T, xx, tt).reshape(xx.shape)
        runs.append(
            dict(
                run_id=f"SYN-{i + 1:02}",
                split=split,
                amplitude=amplitude,
                off=off,
                x=x,
                t=t,
                T=T,
                sensor_x=positions,
                observations=clean + rng.normal(0, cfg.noise, clean.shape),
            )
        )
    return runs


def export_dataset(runs, cfg, folder):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "synthetic.csv"
    with path.open("x", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        for run in runs:
            for i, t in enumerate(run["t"]):
                for j, x in enumerate(run["sensor_x"]):
                    writer.writerow(
                        dict(
                            run_id=run["run_id"],
                            time_s=t,
                            sensor_id=f"S{j + 1}",
                            x_m=x,
                            temperature_C=run["observations"][i, j],
                            ambient_C=cfg.ambient,
                            heater_state="on" if t < run["off"] else "off",
                            configuration=cfg.scenario,
                            notes="SYNTHETIC; not a physical measurement",
                        )
                    )
    manifest = dict(
        provenance="synthetic",
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        runs=[{k: r[k] for k in ["run_id", "split", "amplitude", "off"]} for r in runs],
    )
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def validate_csv(path, length=0.5):
    """Fail on ambiguous data; report missing timestamps and jumps without deleting rows."""
    rows = list(csv.DictReader(Path(path).open()))
    if not rows or not set(COLUMNS).issubset(rows[0]):
        raise ValueError(f"CSV requires nonempty rows and columns: {', '.join(COLUMNS)}")
    seen, series, positions, runs = set(), {}, {}, set()
    warnings = []
    for row in rows:
        v = {k: float(row[k]) for k in ["time_s", "x_m", "temperature_C", "ambient_C"]}
        if not all(np.isfinite(list(v.values()))) or v["time_s"] < 0 or not 0 <= v["x_m"] <= length:
            raise ValueError("Nonfinite values, invalid time or sensor outside bar")
        if not row["run_id"] or not row["sensor_id"]:
            raise ValueError("Missing run or sensor identifier")
        key = (row["run_id"], row["sensor_id"], v["time_s"])
        if key in seen:
            raise ValueError(f"Duplicate observation: {key}")
        seen.add(key)
        s = key[:2]
        if s in positions and abs(positions[s] - v["x_m"]) > 1e-9:
            raise ValueError(f"Sensor position changes within run: {s}")
        positions[s] = v["x_m"]
        series.setdefault(s, []).append((v["time_s"], v["temperature_C"]))
        runs.add(row["run_id"])
        if not -20 <= v["temperature_C"] <= 120:
            warnings.append(f"Temperature outside protocol range at {key}")
    for key, values in series.items():
        a = np.array(sorted(values))
        if len(a) < 3:
            warnings.append(f"Insufficient time samples: {key}")
            continue
        dt = np.diff(a[:, 0])
        if dt.max() > 1.5 * np.median(dt):
            warnings.append(f"Irregular or missing timestamps: {key}")
        if np.max(np.abs(np.diff(a[:, 1])) / dt) > 10:
            warnings.append(f"Jump >10 °C/s: {key}")
    return dict(
        rows=len(rows),
        runs=sorted(runs),
        warnings=sorted(set(warnings)),
        sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest(),
    )


def validate_split(split):
    if set(split) != {"train", "validation", "test"} or not all(split.values()):
        raise ValueError("Provide nonempty train, validation and test run IDs")
    flat = sum([list(v) for v in split.values()], [])
    if len(flat) != len(set(flat)):
        raise ValueError("Run leakage: an entire run must belong to exactly one split")
