"""Hosting integration checks without a database or remote account."""

import json
import os
import shutil
import subprocess
from pathlib import Path

from fastapi.testclient import TestClient

from canon import server

ROOT = Path(__file__).resolve().parents[1]


def test_results_volume_override(tmp_path, monkeypatch):
    run = tmp_path / "example"
    run.mkdir()
    (run / "results.json").write_text(json.dumps({"schema_version": 2}))
    (run / "COMPLETE.json").write_text("{}")
    monkeypatch.setenv("CANON_RESULTS_DIR", str(tmp_path))
    assert server.result_path("example") == run / "results.json"


def test_trusted_origin_reaches_training_gate(monkeypatch):
    monkeypatch.delenv("CANON_READ_ONLY", raising=False)
    monkeypatch.setattr(server, "ALLOWED_ORIGINS", ["https://beta.example"])
    # Use the existing busy gate to avoid launching a long benchmark.
    assert server.job_lock.acquire(blocking=False)
    try:
        with TestClient(server.app) as client:
            assert (
                client.post("/api/jobs", json={}, headers={"Origin": "https://beta.example"}).status_code
                == 409
            )
            assert (
                client.post("/api/jobs", json={}, headers={"Origin": "https://untrusted.example"}).status_code
                == 403
            )
    finally:
        server.job_lock.release()


def test_static_and_optional_backend_build(tmp_path):
    import zipfile

    for folder in ["web", "canon", "configs", "results"]:
        shutil.copytree(ROOT / folder, tmp_path / folder)
    (tmp_path / "node_modules").symlink_to(ROOT / "node_modules", target_is_directory=True)
    (tmp_path / "scripts").mkdir()
    shutil.copy(ROOT / "scripts/build-web.mjs", tmp_path / "scripts/build-web.mjs")
    for name in ["main-2.py", "requirements-lock.txt", "LICENSE"]:
        shutil.copy(ROOT / name, tmp_path / name)
    (tmp_path / ".env").write_text("PRIVATE=do-not-publish")
    env = dict(os.environ)
    env.pop("CANON_API_URL", None)
    def build():
        return subprocess.run(["node", "scripts/build-web.mjs"], cwd=tmp_path,
                              env=env, capture_output=True)
    result = build()
    assert result.returncode == 0, result.stderr
    dist = tmp_path / "dist"
    assert "CANON_STATIC = true" in (dist / "runtime-config.js").read_text()
    assert len(json.loads((dist / "experiments/index.json").read_text())) == 4
    assert not (dist / ".env").exists()
    with zipfile.ZipFile(dist / "downloads/python-training-kit.zip") as kit:
        assert "canon/pinn.py" in kit.namelist()
        assert not any(".env" in n or "__pycache__" in n for n in kit.namelist())
    artifact = tmp_path / "results/advanced-confirmation/results.json"
    artifact.write_text(artifact.read_text() + " ")
    assert build().returncode != 0
    env["CANON_API_URL"] = "https://beta.example"
    assert build().returncode == 0
    assert "CANON_STATIC = false" in (dist / "runtime-config.js").read_text()
    assert not (dist / "experiments").exists()
    env["CANON_API_URL"] = "http://invalid.example"
    assert build().returncode != 0
