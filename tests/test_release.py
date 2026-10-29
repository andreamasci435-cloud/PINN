"""Exercise an actual small numerical release, not mock result dictionaries."""

import json
from zipfile import ZipFile

import numpy as np
import pytest

from canon.config import Config
from canon.experiment import run_experiment
from canon.release import bundle, verify_artifacts


def test_complete_experiment_release_and_tamper_detection(tmp_path, monkeypatch):
    from canon import server

    folder = tmp_path / "results" / "smoke"
    cfg = Config(
        epochs=2,
        lbfgs=0,
        width=8,
        depth=2,
        collocation=16,
        truth_nx=21,
        fit_nx=11,
        samples=11,
        models=["M0"],
        boundary_mode="hard",
        continuous_protocols=True,
        protocol_set="confirmation",
    )
    run_experiment(cfg, folder, callback=lambda message: None)
    result = json.loads((folder / "results.json").read_text())
    pinn = next(row for row in result["results"] if row["method"] == "PINN")
    assert len(pinn["test_runs"]) == 2
    assert len(pinn["direct_test_runs"]) == 2
    assert np.asarray(pinn["residual_map"]["values"]).shape == (41, 41)
    assert max(pinn["constraint_audit"].values()) < 1e-8
    assert verify_artifacts(folder)["status"] == "verified"
    output = tmp_path / "release.zip"
    bundle(folder, output)
    with ZipFile(output) as archive:
        assert "canon/pinn.py" in archive.namelist()
        assert "experiment/data/synthetic.csv" in archive.namelist()
    with pytest.raises(FileExistsError):
        bundle(folder, output)
    monkeypatch.setattr(server, "ROOT", tmp_path)
    assert server.completed_results() == [folder / "results.json"]
    marker = folder / "COMPLETE.json"
    marker.rename(folder / "pending-marker.json")
    assert server.completed_results() == []
    (folder / "pending-marker.json").rename(marker)
    data = folder / "data" / "synthetic.csv"
    data.write_text(data.read_text() + "tampered")
    with pytest.raises(ValueError, match="data/synthetic.csv"):
        verify_artifacts(folder)
