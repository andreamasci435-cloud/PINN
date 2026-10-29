"""End-to-end benchmark. Freeze selection on validation before opening the final test."""

import csv
import hashlib
import json
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import scipy
import torch

from .data import export_dataset, synthetic
from .diagnostics import constraint_audit, evidence_summary
from .evaluate import fit_classical, metrics
from .fdm import sample, solve
from .physics import coefficients, truth_parameters
from .pinn import fit_pinn


def dump(path, obj):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(obj, indent=2, allow_nan=False))
    temporary.replace(path)


def prediction(cfg, candidate, run):
    if candidate["method"] == "MLP":
        xx, tt = np.meshgrid(run["x"], run["t"])
        return candidate["network"].predict(xx, tt, run["amplitude"], run["off"])
    # Primary inverse-problem endpoint: forward prediction under NEW known forcing.
    x, t, T = solve(
        cfg, candidate["model"], candidate["raw"], run["amplitude"], run["off"], nx=cfg.fit_nx, times=run["t"]
    )
    xx, tt = np.meshgrid(run["x"], run["t"])
    return sample(x, t, T, xx, tt).reshape(xx.shape)


def score(cfg, candidate, run):
    field = prediction(cfg, candidate, run)
    xx, tt = np.meshgrid(run["sensor_x"], run["t"])
    observed = sample(run["x"], run["t"], field, xx, tt).reshape(xx.shape)
    return metrics(observed, run["observations"], cfg.ambient), field


def score_runs(cfg, candidate, runs):
    """Pool sensor observations only after every run-level prediction is computed."""
    predictions, targets, per_run = [], [], {}
    first_field = None
    for run in runs:
        run_metrics, field = score(cfg, candidate, run)
        xx, tt = np.meshgrid(run["sensor_x"], run["t"])
        predictions.append(sample(run["x"], run["t"], field, xx, tt))
        targets.append(run["observations"].ravel())
        per_run[run["run_id"]] = run_metrics
        if first_field is None:
            first_field = field
    return metrics(np.concatenate(predictions), np.concatenate(targets), cfg.ambient), per_run, first_field


def run_experiment(cfg, output, callback=None):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    start = time.perf_counter()
    report = callback or (lambda message: print(message, flush=True))
    dump(output / "config.json", cfg.model_dump())
    requirements = Path(__file__).resolve().parents[1] / "requirements-lock.txt"
    if requirements.exists():
        (output / "requirements-lock.txt").write_bytes(requirements.read_bytes())
    # Capture source BEFORE training, so later edits cannot rewrite provenance.
    snapshot = output / "source"
    snapshot.mkdir()
    source_hashes = {}
    for source in sorted(Path(__file__).parent.glob("*.py")):
        content = source.read_bytes()
        (snapshot / source.name).write_bytes(content)
        source_hashes[source.name] = hashlib.sha256(content).hexdigest()
    dump(
        output / "protocol.json",
        {
            "config": cfg.model_dump(),
            "locked_at": datetime.now(timezone.utc).isoformat(),
            "selection_rule": "Pooled validation sensor RMSE, averaged across seeds",
            "source_sha256": source_hashes,
        },
    )
    runs = synthetic(cfg)
    manifest = export_dataset(runs, cfg, output / "data")
    train = [r for r in runs if r["split"] == "train"]
    validation_runs = [r for r in runs if r["split"] == "validation"]
    test_runs = [r for r in runs if r["split"] == "test"]
    test = test_runs[0]
    candidates, histories = [], {}
    for kind in dict.fromkeys([*cfg.classical_models, *cfg.models]):
        report(f"Classical fit {kind}: training runs only")
        raw, info = fit_classical(cfg, train, kind)
        c = dict(
            id=f"FDM-{kind}",
            method="Classical",
            model=kind,
            raw=raw,
            diagnostics=info,
            elapsed_s=info["elapsed_s"],
        )
        c["validation"], c["validation_runs"], _ = score_runs(cfg, c, validation_runs)
        candidates.append(c)
        if kind not in cfg.models:
            continue
        for seed in cfg.seeds:
            key = f"PINN-{kind}-{seed}"
            report(f"{key}: Adam + L-BFGS")

            def progress(epoch, total, row):
                if epoch % 500 == 0 or epoch == total:
                    report(f"{key}: {epoch}/{total}, loss={row['total']:.5g}")

            model, history, elapsed = fit_pinn(cfg, train, kind, seed, callback=progress)
            torch.save(model.state_dict(), output / f"{key}.pt")
            raw = model.raw.detach().numpy().copy()
            c = dict(id=key, method="PINN", model=kind, seed=seed, raw=raw, network=model, elapsed_s=elapsed)
            c["validation"], c["validation_runs"], _ = score_runs(cfg, c, validation_runs)
            histories[key] = history
            candidates.append(c)
    for seed in cfg.seeds:
        report(f"MLP-{seed}: data-only baseline")
        model, history, elapsed = fit_pinn(cfg, train, "M0", seed, data_only=True)
        key = f"MLP-{seed}"
        torch.save(model.state_dict(), output / f"{key}.pt")
        c = dict(id=key, method="MLP", model="M0", seed=seed, raw=None, network=model, elapsed_s=elapsed)
        c["validation"], c["validation_runs"], _ = score_runs(cfg, c, validation_runs)
        candidates.append(c)
        histories[key] = history
    # Selection is by mean validation RMSE across seeds, never by test.
    groups = {}
    for c in candidates:
        group = f"{c['method']}-{c['model']}"
        groups.setdefault(group, []).append(c)
    group_scores = {g: float(np.mean([c["validation"]["rmse_C"] for c in cs])) for g, cs in groups.items()}
    selected = min(group_scores, key=group_scores.get)
    selection = dict(
        criterion="Mean validation RMSE across seeds; no test-based tuning",
        selected=selected,
        validation_scores=group_scores,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    dump(output / "selection.json", selection)
    report(f"Selection frozen: {selected}. Evaluating held-out tests.")
    rows, fields = [], {}
    rng = np.random.default_rng(cfg.seed + 9999)
    # New collocation coordinates, not drawn by the training RNG.
    pts = np.column_stack(
        [
            rng.random(1024),
            rng.random(1024),
            np.full(1024, test["amplitude"] / cfg.temperature_scale),
            np.full(1024, test["off"] / cfg.duration),
        ]
    )
    for c in candidates:
        test_metrics, per_run, field = score_runs(cfg, c, test_runs)
        fields[c["id"]] = field
        row = {k: v for k, v in c.items() if k not in ["network", "raw"]}
        row["test"] = test_metrics
        row["test_runs"] = per_run
        row["field"] = metrics(field, test["T"], cfg.ambient)
        row["raw_parameters"] = None if c["raw"] is None else c["raw"].tolist()
        if c["raw"] is not None:
            a, b = coefficients(c["model"], c["raw"], test["x"] / cfg.length, np.zeros_like(test["x"]))
            row["alpha_profile"] = a.tolist()
            row["beta_profile"] = b.tolist()
        if c["method"] == "PINN":
            net = c["network"]
            residual = net.residual(torch.tensor(pts, dtype=torch.float64)).detach().numpy()
            row["pde_rms_dimensionless"] = float(np.sqrt(np.mean(residual**2)))
            xx, tt = np.meshgrid(test["x"], test["t"])
            direct = net.predict(xx, tt, test["amplitude"], test["off"])
            fields[c["id"] + "-direct"] = direct
            row["direct_network_field"] = metrics(direct, test["T"], cfg.ambient)
            direct_candidates = dict(c, method="MLP")
            row["direct_sensor_test"], row["direct_test_runs"], _ = score_runs(
                cfg, direct_candidates, test_runs
            )
            row["constraint_audit"] = constraint_audit(net, cfg, test)
            xx_diag, tt_diag = np.meshgrid(np.linspace(0, cfg.length, 41), np.linspace(0, cfg.duration, 41))
            diagnostic_points = np.column_stack(
                [
                    xx_diag.ravel() / cfg.length,
                    tt_diag.ravel() / cfg.duration,
                    np.full(xx_diag.size, test["amplitude"] / cfg.temperature_scale),
                    np.full(xx_diag.size, test["off"] / cfg.duration),
                ]
            )
            row["residual_map"] = dict(
                x_m=xx_diag[0].tolist(),
                time_s=tt_diag[:, 0].tolist(),
                values=net.residual(torch.tensor(diagnostic_points, dtype=torch.float64))
                .detach()
                .numpy()
                .reshape(41, 41)
                .tolist(),
            )
        rows.append(row)
    uncertainty = {}
    for group, cs in groups.items():
        if len(cs) > 1:
            stack = np.stack([fields[c["id"]] for c in cs])
            lo, hi = np.quantile(stack, [0.025, 0.975], axis=0)
            uncertainty[group] = dict(
                seeds=len(cs),
                field_coverage=float(np.mean((test["T"] >= lo) & (test["T"] <= hi))),
                mean_band_width_C=float(np.mean(hi - lo)),
                note="Empirical seed spread; NOT calibrated 95% measurement uncertainty.",
            )
    truth_kind, truth_raw = truth_parameters(cfg)
    a, b = coefficients(truth_kind, truth_raw, test["x"] / cfg.length, np.zeros_like(test["x"]))
    provenance = dict(
        python=platform.python_version(),
        platform=platform.platform(),
        torch=torch.__version__,
        numpy=np.__version__,
        scipy=scipy.__version__,
        device="cpu",
        dtype="float64",
        source_sha256=source_hashes,
    )
    result = dict(
        schema_version=2,
        provenance="synthetic",
        status="computational benchmark; no physical data",
        config=cfg.model_dump(),
        selection=selection,
        manifest=manifest,
        environment=provenance,
        results=rows,
        histories=histories,
        uncertainty=uncertainty,
        elapsed_s=time.perf_counter() - start,
        field=dict(
            run_id=test["run_id"],
            x_m=test["x"].tolist(),
            time_s=test["t"].tolist(),
            truth_C=test["T"].tolist(),
            predictions_C={k: v.tolist() for k, v in fields.items()},
            sensor_x_m=test["sensor_x"].tolist(),
            sensor_C=test["observations"].tolist(),
            amplitude_C=test["amplitude"],
            off_s=test["off"],
            truth_alpha=a.tolist(),
            truth_beta=b.tolist(),
        ),
    )
    result["evidence"] = evidence_summary(result)
    dump(output / "results.json", result)
    with (output / "metrics.csv").open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "id",
                "validation_rmse_C",
                "test_rmse_C",
                "test_mae_C",
                "relative_l2_excess",
                "elapsed_s",
            ],
        )
        writer.writeheader()
        for r in rows:
            writer.writerow(
                dict(
                    id=r["id"],
                    validation_rmse_C=r["validation"]["rmse_C"],
                    test_rmse_C=r["test"]["rmse_C"],
                    test_mae_C=r["test"]["mae_C"],
                    relative_l2_excess=r["field"]["relative_l2_excess"],
                    elapsed_s=r["elapsed_s"],
                )
            )
    np.savez_compressed(output / "fields.npz", x=test["x"], t=test["t"], truth=test["T"], **fields)
    make_figures(result, output)
    from .report import build_report

    build_report(output)
    artifacts = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir() if p.is_file()}
    dump(output / "artifacts.json", artifacts)
    dump(output / "COMPLETE.json", {"status": "complete", "schema_version": 2})
    report(f"Completed: {output}")
    return result


def make_figures(result, output):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    f = result["field"]
    fig, axes = plt.subplots(
        1, 2, figsize=(12, max(4, 1.5 + 0.27 * len(result["results"]))), layout="constrained"
    )
    image = axes[0].pcolormesh(f["x_m"], f["time_s"], f["truth_C"], cmap="inferno", shading="auto")
    fig.colorbar(image, ax=axes[0], label="Temperature [°C]")
    axes[0].set(xlabel="Position [m]", ylabel="Time [s]", title="Synthetic held-out run: reference")
    labels = [r["id"] for r in result["results"]]
    axes[1].barh(labels, [r["test"]["rmse_C"] for r in result["results"]], color="#638c79")
    axes[1].set(xlabel="Held-out sensor RMSE [°C]", title="Frozen candidate comparison")
    fig.savefig(Path(output) / "benchmark.png", dpi=180)
    fig.savefig(Path(output) / "benchmark.svg")
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(8, 4), layout="constrained")
    for key, rows in result["histories"].items():
        if key.startswith("PINN") and key.endswith(f"-{result['config']['seeds'][0]}"):
            for term in ["data", "pde", "ic", "bc"]:
                ax.semilogy(
                    [r["epoch"] for r in rows], [max(r[term], 1e-14) for r in rows], label=f"{key}: {term}"
                )
    ax.set(xlabel="Adam epoch / final L-BFGS budget", ylabel="Unweighted dimensionless loss")
    ax.legend(
        fontsize=6, ncol=2 if len(result["histories"]) < 5 else 4, loc="upper left", bbox_to_anchor=(1.02, 1)
    )
    fig.savefig(Path(output) / "losses.png", dpi=180, bbox_inches="tight")
    plt.close(fig)
