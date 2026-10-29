"""Single persistent worker: training RNG and job registry are process-local."""

import os
import shutil
import sys
from pathlib import Path

import uvicorn

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
folder = Path(os.environ.get("CANON_RESULTS_DIR", str(root / "results")))
folder.mkdir(parents=True, exist_ok=True)
seed = root / "results" / "advanced-confirmation"
if seed.is_dir() and not (folder / seed.name).exists():
    shutil.copytree(seed, folder / seed.name)
uvicorn.run("canon.server:app", host="0.0.0.0", port=int(os.environ.get("PORT", "8765")), workers=1)
