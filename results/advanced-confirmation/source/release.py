"""Create a portable, integrity-checked archive of a completed numerical experiment."""

import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def verify_artifacts(folder):
    folder = Path(folder)
    if not (folder / "COMPLETE.json").is_file():
        raise ValueError(
            "This run has no completion marker. Legacy runs must be regenerated for a release archive."
        )
    expected = json.loads((folder / "artifacts.json").read_text())
    failures = []
    for name, digest in expected.items():
        path = folder / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            failures.append(name)
    protocol = json.loads((folder / "protocol.json").read_text())
    for name, digest in protocol["source_sha256"].items():
        path = folder / "source" / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            failures.append("source/" + name)
    if failures:
        raise ValueError("Artifact integrity check failed: " + ", ".join(failures))
    return {"status": "verified", "files": len(expected), "source_files": len(protocol["source_sha256"])}


def bundle(folder, destination):
    folder, destination = Path(folder), Path(destination)
    verify_artifacts(folder)
    if destination.exists():
        raise FileExistsError("Release archives are immutable; choose a new output file")
    with ZipFile(destination, "x", ZIP_DEFLATED) as archive:
        for path in sorted(folder.rglob("*")):
            if path.is_file():
                archive.write(path, "experiment/" + str(path.relative_to(folder)))
        for path in sorted((folder / "source").glob("*.py")):
            archive.write(path, "canon/" + path.name)
        archive.writestr("main-2.py", 'from canon.cli import main\nif __name__ == "__main__":\n    main()\n')
        if (folder / "requirements-lock.txt").exists():
            archive.write(folder / "requirements-lock.txt", "requirements-lock.txt")
        archive.writestr(
            "REPRODUCE.md",
            "# Frozen numerical experiment\n\nThis archive contains synthetic data, not physical evidence.\n\nCreate a Python 3.12 virtual environment, install requirements-lock.txt, then run:\n\n```sh\npython main-2.py run --config experiment/config.json --output reproduced\n```\n\nThe source under canon/ is the snapshot taken before training. The full web interface is available in the project, not this numerical archive. See experiment/protocol.json and artifacts.json for hashes.\n",
        )
    return {"path": str(destination), "sha256": hashlib.sha256(destination.read_bytes()).hexdigest()}
