"""Compare the actual deployed JavaScript integrator with independent SciPy BDF."""
import json
import subprocess
from pathlib import Path

import numpy as np
import pytest

from canon.config import Config
from canon.fdm import solve
from canon.physics import truth_parameters

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("scenario", ["uniform", "variable_alpha", "local_loss", "temperature_alpha"])
@pytest.mark.parametrize("alpha,beta,amplitude,off", [(1e-4, .01, 60, 230), (1e-3, .1, 70, 30), (1e-6, 1e-5, 10, 380)])
def test_browser_matches_bdf(scenario, alpha, beta, amplitude, off):
    params = dict(scenario=scenario, alpha=alpha, beta=beta, amplitude=amplitude, off=off)
    source = ('import {solveBrowser} from "./web/browser-solver.js"; '
              'console.log(JSON.stringify(solveBrowser(' + json.dumps(params) + ')));')
    output = subprocess.check_output(["node", "--input-type=module", "-e", source], cwd=ROOT)
    actual = json.loads(output)
    cfg = Config(scenario=scenario, alpha=alpha, beta=beta)
    kind, raw = truth_parameters(cfg)
    _, _, expected = solve(cfg, kind, raw, amplitude, off, nx=81, times=actual["time_s"])
    field = np.array(actual["temperature_C"])
    error = np.max(np.abs(field - expected))
    print(f"{scenario} alpha={alpha}: max error {error:.9g} C")
    assert error < 0.001
    assert field.min() >= 20 - 1e-8
    assert field.max() <= 20 + amplitude + 1e-8
    np.testing.assert_array_equal(field[0], 20)
