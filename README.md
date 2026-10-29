# PINN-CANON · Thermal Research Lab

A reproducible inverse heat-transfer laboratory: conservative numerical solver, physics-informed neural networks, classical baselines, traceable experiments and an interactive 3D research website.

**Research status:** validated software and synthetic numerical experiments. Physical calibration, replicated measurements and external scientific review remain necessary before an experimental publication. No author, affiliation or credentials are assumed.

## Run the website

From this project folder:

```sh
.venv/bin/python main-2.py serve --port 8765
```

Open [the laboratory](http://127.0.0.1:8765/) or [the researcher profile](http://127.0.0.1:8765/researcher.html). The server binds to localhost. No API keys, cloud services or external JavaScript dependencies are required; Three.js is vendored locally.

For a fresh Python 3.12 environment:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python -m pytest -q
.venv/bin/python main-2.py serve --port 8765
```

The lock file was exercised on macOS ARM64, CPU. Other platforms should run the verification suite. Node is only needed to maintain web assets, not to serve the project.

## Research edition

The enhanced PINN enforces the initial condition, prescribed left temperature and insulated right boundary by construction. Six inputs encode space, time and the heating protocol, including its switching phase. A supervised warm-up precedes joint inverse training with separate parameter learning rates. Physics collocation covers a continuous family of heating protocols, without reading held-out temperatures. Residual-adaptive sampling is also implemented as an optional ablation; it is **not** enabled in the locked confirmation preset.

The confirmation experiment uses seven whole protocols: three training, two validation and two test. Five optimization seeds are retained, including weak outcomes. Classical M0–M3, enhanced PINN-M2 and an unconstrained data-only network are compared. The site exposes both direct neural predictions and predictions from a forward solver using learned coefficients, with independent residual maps, constraint audits and training histories.

Observed confirmation results: direct PINN RMSE **0.377 °C** averaged over five seeds; PINN parameters → solver **0.322 °C**; selected classical M2 **0.150 °C**. These are synthetic held-out sensor results. See [the full result interpretation](docs/CONFIRMATION_RESULTS.md).

Read [the exact formulation and development record](docs/RESEARCH_EDITION.md). The original soft-constraint implementation and earlier benchmarks remain available. This is an extension of the original tanh/autograd inverse problem, not an unrelated replacement.

```sh
# Original quick demo
.venv/bin/python main-2.py run --config configs/demo.json --output results/demo-new

# Enhanced single-seed reproduction
.venv/bin/python main-2.py run --config configs/advanced-demo.json --output results/advanced-one

# Locked five-seed confirmation experiment
.venv/bin/python main-2.py run --config configs/advanced.json --output results/advanced-new

# Verify and package a completed schema-v2 experiment
.venv/bin/python main-2.py verify results/advanced-new
.venv/bin/python main-2.py bundle results/advanced-new releases/advanced-new.zip
```

Create `releases/` before packaging. Output experiment folders must be new; existing runs are never overwritten. Every new experiment stores its starting source, configuration, dependency lock, data hash, checkpoints, predictions and figures. `COMPLETE.json` is written last. Incomplete runs are not offered in the web archive. Release archives contain the numerical source and experiment; the full website stays in this repository.

The UI's **Run simulation** only evaluates the forward solver. **Reproduce benchmark** really trains the selected original or enhanced preset. Neural diagnostics and the 3D field selector let you distinguish the reference from the selected model's prediction. Scalar test metrics pool all test protocols; the displayed field belongs to the first test protocol.

For an externally hosted read-only demonstration, the backend provides `CANON_READ_ONLY=1`, which disables training requests. Deployment, HTTPS and hosting configuration are separate operations; no public deployment is included here.

## Researcher and CV

The English profile is ready at `/researcher.html`. Its content lives in `web/content/researcher.json`; identity and CV remain blank until supplied. See [the profile guide](docs/AUTHOR_PROFILE.md) for the schema, contribution statements and PDF attachment. Only put information intended for public display in the web directory.

## Reading the evidence

- Primary endpoint: held-out sensor RMSE in °C, using PINN-inferred coefficients in the conservative forward solver. Direct neural sensor RMSE is separately reported; these endpoints are not interchangeable.
- Relative L2 is normalized by temperature above ambient, not absolute temperature.
- PDE residuals are dimensionless. Exact boundary conditions do not imply an exact interior solution.
- Multi-seed dispersion measures optimization sensitivity, not a calibrated confidence interval. The seeds share one synthetic dataset.
- M2 assumes a known location and width for its local-loss bump. M3 parameter profiles are evaluated at ambient temperature.
- Synthetic generation and fitting use related solvers on different grids, and the truth belongs to a candidate family. This is not an out-of-family or physical validation.
- Classical methods may outperform PINNs. The website reports measured outcomes rather than assuming neural superiority.

## Physical measurements

The original [experimental protocol](docs/EXPERIMENTAL_PROTOCOL.md), [data specification](docs/DATA_FORMAT.md) and [PDF alignment](docs/PDF_ALIGNMENT.md) remain available as the initial project documentation. The English research-edition supplement supersedes their descriptions of enhanced synthetic training.

```sh
.venv/bin/python main-2.py validate-data data/raw/session.csv
.venv/bin/python main-2.py calibrate data/raw/session.csv data/calibration/sensors.json data/processed/session.csv
.venv/bin/python main-2.py run-measured data/processed/session.csv data/processed/metadata.json --config configs/demo.json --output results/measured-first
```

Recorded boundary histories require `boundary_mode: "soft"`; the exact analytic lifting is deliberately rejected for measured histories. No physical measurements or hardware acquisition are fabricated. Variable ambient conditions, unknown boundary flux and the more general M4 model remain outside the validated scope.

## Verification and layout

```sh
.venv/bin/ruff check canon tests
.venv/bin/python -m pytest -q
```

`canon/` contains models, solver, experiments and API; `configs/` contains reproducible presets; `web/` contains the interface; `results/` contains generated evidence; `tests/` contains physical, numerical, data and API checks. The provided code is preserved in `legacy/original_main.py`, and the original PDF is unchanged. `.github/workflows/verify.yml` defines checks for a future GitHub repository; its presence does not mean a remote CI run has occurred.

Before making publication claims, use the explicit remaining work in [publication readiness](docs/PUBLICATION_READINESS.md). Attribute human and AI contributions accurately.

## References

- Raissi, Perdikaris & Karniadakis (2019), [Physics-informed neural networks](https://doi.org/10.1016/j.jcp.2018.10.045).
- Sukumar & Srivastava (2022), [Exact imposition of boundary conditions in PINNs](https://doi.org/10.1016/j.cma.2021.114333).
- Wu et al. (2023), [Residual-based adaptive sampling for PINNs](https://doi.org/10.1016/j.cma.2022.115671).
- Krishnapriyan et al. (2021), [Characterizing possible failure modes in PINNs](https://papers.nips.cc/paper/2021/hash/df438e5206f31600e6ae4af72f2725f1-Abstract.html).

The MIT license covers the new software. Pre-existing materials and future measurements retain their owners' rights.

## Hosting beta builds

The default `npm run build` produces a standalone Vercel site in `dist`, with no backend, database or environment variables. Forward simulations run in the browser; real archived PINN results and downloads remain available. New PINN training uses the downloadable local Python kit. See [the deployment guide](docs/DEPLOYMENT.md) for GitHub/Vercel setup and the precise feature boundaries. The supplied researcher materials are included; the author’s name remains pending.
