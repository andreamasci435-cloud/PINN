"""Predeclared sensitivity/ablation plans; each output is independently reproducible."""

from pathlib import Path

from .config import Config


def generate_plan(folder):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=False)
    base = Config(
        models=["M0", "M1", "M2", "M3"],
        seeds=[11, 23, 42, 67, 101],
        epochs=10000,
        lbfgs=1000,
        width=64,
        collocation=5000,
    )
    variants = {}
    for scenario in ["uniform", "local_loss", "variable_alpha", "temperature_alpha"]:
        variants["hypothesis-" + scenario] = base.model_copy(update={"scenario": scenario})
    for sensors in [2, 4, 6, 8]:
        variants[f"sensors-{sensors}"] = base.model_copy(update={"sensors": sensors, "models": ["M0"]})
    for noise in [0, 0.15, 0.5, 1.0]:
        variants[f"noise-{noise}"] = base.model_copy(update={"noise": noise, "models": ["M0"]})
    for term in ["data", "pde", "ic", "bc", "reg"]:
        weights = {**base.weights, term: 0.0}
        variants[f"without-{term}"] = base.model_copy(
            update={"weights": weights, "scenario": "local_loss", "models": ["M2"]}
        )
    for factor in [0.1, 10.0]:
        weights = {**base.weights, "pde": factor}
        variants[f"pde-weight-{factor}"] = base.model_copy(update={"weights": weights, "models": ["M0"]})
    for name, cfg in variants.items():
        (folder / f"{name}.json").write_text(cfg.model_dump_json(indent=2))
    (folder / "README.md").write_text(
        "Predeclared exploratory synthetic study. Run each configuration with `python main-2.py run --config PATH --output NEW_FOLDER`. Do not tune models on these test results; reserve new physical runs for confirmatory validation. This plan is not evidence that the studies have been executed.\n"
    )
    return len(variants)
