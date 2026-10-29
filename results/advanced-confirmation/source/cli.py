"""Command-line entrypoints; importing the package never starts training."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from .config import Config

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description="PINN-CANON reproducible thermal lab")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="Run a synthetic benchmark and regenerate figures")
    run.add_argument("--config", default=str(ROOT / "configs/demo.json"))
    run.add_argument("--output", default=None)
    serve = sub.add_parser("serve", help="Start local research interface")
    serve.add_argument("--port", type=int, default=8765)
    check = sub.add_parser("validate-data", help="Validate a measurement CSV without changing it")
    check.add_argument("csv")
    calibration = sub.add_parser("calibrate", help="Apply traceable sensor calibration")
    calibration.add_argument("csv")
    calibration.add_argument("calibration")
    calibration.add_argument("output")
    plan = sub.add_parser("plan-study", help="Generate predeclared ablation and sensitivity configurations")
    plan.add_argument("output")
    real = sub.add_parser(
        "run-measured", help="Benchmark calibrated measurements with recorded boundary histories"
    )
    real.add_argument("csv")
    real.add_argument("metadata")
    real.add_argument("--config", required=True)
    real.add_argument("--output", required=True)
    boot = sub.add_parser("bootstrap", help="Whole-training-run classical bootstrap (synthetic)")
    boot.add_argument("--config", required=True)
    boot.add_argument("--model", choices=["M0", "M1", "M2", "M3"], default="M0")
    boot.add_argument("--repeats", type=int, default=100)
    boot.add_argument("--output", required=True)
    report = sub.add_parser("report", help="Regenerate aggregate figures from a saved synthetic benchmark")
    report.add_argument("folder")
    release = sub.add_parser("bundle", help="Verify and package a completed numerical experiment")
    release.add_argument("folder")
    release.add_argument("output")
    verify = sub.add_parser("verify", help="Verify an experiment's file and source hashes")
    verify.add_argument("folder")
    args = parser.parse_args()
    if args.command == "run":
        from .experiment import run_experiment

        cfg = Config.model_validate_json(Path(args.config).read_text())
        output = args.output or str(
            ROOT / "results" / datetime.now(timezone.utc).strftime("run-%Y%m%d-%H%M%S")
        )
        run_experiment(cfg, output)
    elif args.command == "serve":
        import uvicorn

        uvicorn.run("canon.server:app", host="127.0.0.1", port=args.port)
    elif args.command == "bundle":
        from .release import bundle

        print(json.dumps(bundle(args.folder, args.output), indent=2))
    elif args.command == "verify":
        from .release import verify_artifacts

        print(json.dumps(verify_artifacts(args.folder), indent=2))
    elif args.command == "report":
        from .report import build_report

        build_report(args.folder)
    elif args.command == "bootstrap":
        from .uncertainty import bootstrap

        bootstrap(args.config, args.model, args.output, args.repeats)
    elif args.command == "calibrate":
        from .calibration import calibrate

        print(json.dumps(calibrate(args.csv, args.calibration, args.output), indent=2))
    elif args.command == "plan-study":
        from .studies import generate_plan

        print(f"Created {generate_plan(args.output)} study configurations")
    elif args.command == "run-measured":
        from .real import run_measured

        cfg = Config.model_validate_json(Path(args.config).read_text())
        run_measured(cfg, args.csv, args.metadata, args.output)
    else:
        from .data import validate_csv

        print(json.dumps(validate_csv(args.csv), indent=2))


if __name__ == "__main__":
    main()
