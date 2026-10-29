"""Apply explicitly supplied sensor calibration without changing raw data."""

import csv
import hashlib
import json
from pathlib import Path

import numpy as np

from .data import validate_csv


def calibrate(source, calibration, destination):
    source, calibration, destination = map(Path, (source, calibration, destination))
    if destination.exists() or source.resolve() == destination.resolve():
        raise FileExistsError("Calibration output must be a new file")
    mapping = json.loads(calibration.read_text())
    validate_csv(source)
    with source.open() as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        rows = list(reader)
    for row in rows:
        sensor = row["sensor_id"]
        if sensor not in mapping:
            raise ValueError(f"Missing calibration for {sensor}")
        c = mapping[sensor]
        gain, offset = float(c["gain"]), float(c["offset_C"])
        if not np.isfinite([gain, offset]).all() or gain <= 0:
            raise ValueError(f"Invalid calibration for {sensor}")
        row["temperature_C"] = gain * float(row["temperature_C"]) + offset
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    provenance = {
        str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in [source, calibration, destination]
    }
    destination.with_suffix(".provenance.json").write_text(json.dumps(provenance, indent=2))
    return validate_csv(destination)
