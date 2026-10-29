import json

import numpy as np
import pytest
from fastapi.testclient import TestClient

from canon.config import Config
from canon.data import export_dataset, synthetic, validate_csv, validate_split
from canon.evaluate import fit_classical
from canon.physics import coefficients
from canon.pinn import fit_pinn
from canon.server import app


def test_reproducible_data_and_no_leakage(tmp_path):
    cfg = Config(samples=11, truth_nx=31)
    a, b = synthetic(cfg), synthetic(cfg)
    for r, s in zip(a, b):
        np.testing.assert_array_equal(r["observations"], s["observations"])
    split = {name: [r["run_id"] for r in a if r["split"] == name] for name in ["train", "validation", "test"]}
    validate_split(split)
    manifest = export_dataset(a, cfg, tmp_path)
    check = validate_csv(tmp_path / "synthetic.csv")
    assert check["sha256"] == manifest["sha256"]
    assert check["rows"] == 5 * 8 * 11
    with pytest.raises(FileExistsError):
        export_dataset(a, cfg, tmp_path)
    with pytest.raises(ValueError, match="leakage"):
        validate_split({"train": ["a"], "validation": ["b"], "test": ["a"]})


def test_csv_rejects_duplicates(tmp_path):
    cfg = Config(samples=11, truth_nx=31)
    export_dataset(synthetic(cfg), cfg, tmp_path)
    p = tmp_path / "synthetic.csv"
    rows = p.read_text().splitlines()
    p.write_text("\n".join(rows + [rows[1]]) + "\n")
    with pytest.raises(ValueError, match="Duplicate"):
        validate_csv(p)


def test_classical_parameter_recovery():
    cfg = Config(samples=21, noise=0, truth_nx=81, fit_nx=61)
    runs = [r for r in synthetic(cfg) if r["split"] == "train"]
    raw, info = fit_classical(cfg, runs, "M0")
    a, b = coefficients("M0", raw, np.array([0.5]), np.array([0.0]))
    assert info["success"]
    assert abs(a[0] / cfg.alpha - 1) < 0.02
    assert abs(b[0] / cfg.beta - 1) < 0.02


def test_training_is_bitwise_reproducible():
    cfg = Config(epochs=3, lbfgs=0, width=8, depth=2, collocation=32, samples=11, truth_nx=31)
    runs = [r for r in synthetic(cfg) if r["split"] == "train"]
    a, ha, _ = fit_pinn(cfg, runs, "M0", 42)
    b, hb, _ = fit_pinn(cfg, runs, "M0", 42)
    for key, value in a.state_dict().items():
        np.testing.assert_array_equal(value.numpy(), b.state_dict()[key].numpy())
    assert ha == hb


def test_api_validates_and_serves():
    client = TestClient(app)
    assert client.get("/").status_code == 200
    assert client.get("/api/health").json()["status"] == "ok"
    assert client.post("/api/simulate", json={"alpha": -1}).status_code == 422
    assert client.post("/api/simulate", json={"scenario": "unknown"}).status_code == 422
    sim = client.post("/api/simulate", json={"scenario": "local_loss"}).json()
    assert np.array(sim["temperature_C"]).shape == (81, 81)
    assert client.get("/api/download/no-such-file").status_code == 404
    assert client.get("/api/jobs/missing").status_code == 404


def test_config_rejects_unknown_or_invalid_weights():
    with pytest.raises(ValueError):
        Config(typo=True)
    with pytest.raises(ValueError):
        Config(weights={"data": 1})
    with pytest.raises(ValueError):
        Config(seeds=[])


def test_demo_end_to_end_recovery():
    """Regression gate for the shipped executable benchmark; no fabricated fixture."""
    from pathlib import Path

    path = Path("results/demo/results.json")
    if not path.exists():
        pytest.skip("Generate the demo first to validate the full training result")
    result = json.loads(path.read_text())
    row = next(r for r in result["results"] if r["method"] == "PINN")
    assert abs(row["alpha_profile"][0] / result["config"]["alpha"] - 1) < 0.15
    assert row["test"]["rmse_C"] < 1
    assert result["selection"]["selected"] == "Classical-M0"


def test_calibration_preserves_raw(tmp_path):
    from canon.calibration import calibrate

    cfg = Config(samples=11, truth_nx=31)
    export_dataset(synthetic(cfg), cfg, tmp_path / "raw")
    source = tmp_path / "raw/synthetic.csv"
    before = source.read_bytes()
    mapping = {f"S{i}": {"gain": 1.0, "offset_C": 0.2} for i in range(1, 9)}
    path = tmp_path / "calibration.json"
    path.write_text(json.dumps(mapping))
    output = tmp_path / "processed.csv"
    result = calibrate(source, path, output)
    assert result["rows"] == 440
    assert source.read_bytes() == before
    assert output.with_suffix(".provenance.json").exists()
    with pytest.raises(FileExistsError):
        calibrate(source, path, output)


def test_measured_pipeline_with_simulated_io_fixture(tmp_path):
    """Synthetic fixture only: exercises measured-data I/O, not physical validation."""
    from canon.physics import heater
    from canon.real import load_measured, run_measured

    cfg = Config(
        samples=11, truth_nx=31, fit_nx=21, noise=0, epochs=2, lbfgs=0, width=8, depth=2, collocation=32
    )
    runs = synthetic(cfg)
    export_dataset(runs, cfg, tmp_path / "raw")
    metadata = dict(
        provenance="measured",
        operator="AUTOMATED IO TEST ONLY",
        date="2026-01-01",
        material="synthetic",
        geometry={"length_m": 0.5},
        calibration_id="fixture",
        ambient_calibration_id="fixture",
        sensor_position_uncertainty_m=0.001,
        temperature_uncertainty_C=0.15,
        notes="NOT PHYSICAL DATA",
        split={k: [r["run_id"] for r in runs if r["split"] == k] for k in ["train", "validation", "test"]},
        runs={
            r["run_id"]: dict(
                amplitude_C=r["amplitude"],
                off_s=r["off"],
                boundary_time_s=r["t"].tolist(),
                boundary_temperature_C=heater(r["t"], r["amplitude"], r["off"], cfg.ambient).tolist(),
            )
            for r in runs
        },
    )
    meta = tmp_path / "metadata.json"
    meta.write_text(json.dumps(metadata))
    path = tmp_path / "raw/synthetic.csv"
    loaded, _, _ = load_measured(cfg, path, meta)
    assert len(loaded) == 5
    result = run_measured(cfg, path, meta, tmp_path / "out")
    assert len(result["results"]) == 3
    assert result["selection"]["selected"]
    metadata["split"]["test"] = metadata["split"]["train"][:1]
    meta.write_text(json.dumps(metadata))
    with pytest.raises(ValueError):
        load_measured(cfg, path, meta)


def test_researcher_profile_has_no_invented_identity():
    from pathlib import Path

    author = json.loads(Path("web/content/researcher.json").read_text())
    assert author["published"] is True
    assert author["name"] == ""  # Full name has not yet been supplied.
    assert author["cv_url"] == "/content/curriculum-vitae.txt"
    assert Path("web" + author["portrait_url"]).is_file()
    assert any("1550/1600" in entry["title"] for entry in author["awards"])
    client = TestClient(app)
    assert client.get("/researcher.html").status_code == 200
    assert '<html lang="en">' in client.get("/").text
    assert client.get("/content/researcher.json").json()["schema_version"] == 1


def test_readonly_and_cross_origin_training_are_rejected(monkeypatch):
    client = TestClient(app)
    monkeypatch.setenv("CANON_READ_ONLY", "1")
    assert client.post("/api/jobs", json={"preset": "advanced"}).status_code == 403
    monkeypatch.delenv("CANON_READ_ONLY")
    assert (
        client.post("/api/jobs", headers={"origin": "https://unrelated.example"}, json={}).status_code == 403
    )
    assert client.post("/api/jobs", json={"preset": "unknown"}).status_code == 422


def test_adaptive_sampling_and_hard_training_are_deterministic():
    cfg = Config(
        boundary_mode="hard",
        adaptive_sampling=True,
        warmup_epochs=1,
        epochs=12,
        adaptive_every=10,
        lbfgs=2,
        width=8,
        depth=2,
        collocation=16,
        samples=11,
        truth_nx=31,
    )
    runs = [r for r in synthetic(cfg) if r["split"] == "train"]
    a, ha, _ = fit_pinn(cfg, runs, "M2", 42)
    b, hb, _ = fit_pinn(cfg, runs, "M2", 42)
    for key, v in a.state_dict().items():
        np.testing.assert_array_equal(v.numpy(), b.state_dict()[key].numpy())
    assert ha == hb
