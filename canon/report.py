"""Regenerate aggregate scientific figures from saved results; no retraining or selection."""

import json
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def build_report(folder):
    folder = Path(folder)
    result = json.loads((folder / "results.json").read_text())
    groups = {}
    for row in result["results"]:
        groups.setdefault(row["method"] + "-" + row["model"], []).append(row)
    summary = {}
    for name, rows in groups.items():
        errors = np.array([r["test"]["rmse_C"] for r in rows])
        summary[name] = {
            "n": len(rows),
            "rmse_mean_C": float(errors.mean()),
            "rmse_sd_C": float(errors.std(ddof=1)) if len(rows) > 1 else None,
            "validation_mean_C": float(np.mean([r["validation"]["rmse_C"] for r in rows])),
        }
        for param in ["alpha", "beta"]:
            if param + "_profile" in rows[0]:
                values = np.array([r[param + "_profile"] for r in rows])
                summary[name][param] = {
                    "mean": values.mean(0).tolist(),
                    "std": values.std(0).tolist(),
                    "max_cv": float(np.max(values.std(0) / np.maximum(values.mean(0), 1e-20))),
                }
    (folder / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False))
    colors = [
        "#3b6755" if name.startswith("Classical") else "#b16b43" if name.startswith("PINN") else "#738a9a"
        for name in summary
    ]
    fig, ax = plt.subplots(figsize=(9, max(3, len(summary) * 0.5)), layout="constrained")
    ax.barh(
        list(summary),
        [s["rmse_mean_C"] for s in summary.values()],
        xerr=[s["rmse_sd_C"] or 0 for s in summary.values()],
        color=colors,
        capsize=3,
    )
    ax.set(
        xlabel="Held-out sensor RMSE [°C]; mean ± seed SD",
        title="Synthetic benchmark — fixed training budget",
    )
    fig.savefig(folder / "comparison-summary.svg")
    fig.savefig(folder / "comparison-summary.png", dpi=180)
    plt.close(fig)
    x = result["field"]["x_m"]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4), layout="constrained")
    for ax, param, unit in zip(axes, ["alpha", "beta"], ["m²/s", "1/s"]):
        ax.plot(x, result["field"]["truth_" + param], color="black", ls="--", label="Synthetic truth")
        for name, s in summary.items():
            if name.startswith("PINN") and param in s:
                avg = np.array(s[param]["mean"])
                sd = np.array(s[param]["std"])
                line = ax.plot(x, avg, label=name)[0]
                ax.fill_between(x, avg - sd, avg + sd, color=line.get_color(), alpha=0.1)
        ax.set(
            xlabel="Position [m]", ylabel=f"{param} [{unit}]", title=f"{param}: seed mean ± SD (at ambient)"
        )
        ax.legend(fontsize=8)
    fig.savefig(folder / "parameter-stability.png", dpi=180)
    fig.savefig(folder / "parameter-stability.svg")
    plt.close(fig)
    kinds = sorted({r["model"] for r in result["results"] if r["method"] == "PINN"})
    fig, axes = plt.subplots(len(kinds), 1, figsize=(9, 3 * len(kinds)), squeeze=False, layout="constrained")
    for ax, kind in zip(axes[:, 0], kinds):
        for key, history in result["histories"].items():
            if not key.startswith("PINN-" + kind + "-"):
                continue
            for term, color in zip(["data", "pde", "ic", "bc"], ["#3b6755", "#b16b43", "#557baf", "#966b99"]):
                ax.semilogy(
                    [r["epoch"] for r in history],
                    [max(r[term], 1e-14) for r in history],
                    color=color,
                    alpha=0.65,
                )
        for term, color in zip(["data", "pde", "ic", "bc"], ["#3b6755", "#b16b43", "#557baf", "#966b99"]):
            ax.plot([], [], color=color, label=term)
        ax.set(
            title=kind + " — individual seeds",
            xlabel="Adam epoch / final L-BFGS budget",
            ylabel="Unweighted loss",
        )
        ax.legend(fontsize=8, ncol=4)
    fig.savefig(folder / "training-diagnostics.png", dpi=180)
    plt.close(fig)
    return summary
