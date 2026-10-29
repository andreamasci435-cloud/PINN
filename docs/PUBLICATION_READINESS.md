# Publication readiness and remaining evidence

The research edition provides an inspectable computational experiment, not a guarantee of acceptance or a substitute for student understanding. Its strongest present claim is a reproducible implementation and evaluation of an exact-constraint, protocol-conditioned inverse PINN on a stated synthetic problem.

## Included evidence

- Conservative PDE implementation and numerical checks against an analytic solution and grid refinement.
- Positive physical coefficients and explicit candidate assumptions.
- Whole-protocol train/validation/test separation, validation-only selection and retained multi-seed outcomes.
- Direct-network and coefficient-to-solver endpoints reported separately.
- Exact-constraint audits, fresh residual points, residual maps and training traces.
- Source snapshots, dependency lock, data/artifact hashes and portable numerical archives.
- Original benchmarks preserved and unsuccessful development variants documented.

A passing evidence gate records that a check or artifact exists; it does not certify small test errors, physical truth or novelty.

## Work still required for a defensible paper

1. Collect calibrated, timestamped sensor measurements with recorded boundary temperature, sensor placement uncertainty and independent physical replications. The measured-data route currently supports soft constraints and a constant ambient state.
2. Define the scientific question and novelty relative to published inverse heat-transfer and PINN methods. This implementation combines established ideas; it does not by itself establish a novel method.
3. Run controlled ablations with equal protocols, seeds and budgets: soft versus exact constraints; four versus six features; fixed versus continuous protocol collocation; warm-up on/off; regularization and residual-adaptive sampling.
4. Test out-of-family loss profiles, uncertain bump location/width, boundary mismatch, varying noise and fewer sensors. In-family synthetic truth and related forward solvers currently favour identifiability.
5. Compare with well-tuned classical inverse methods and appropriate supervised/physics-based alternatives under documented computational budgets.
6. Quantify uncertainty over calibration, repeat experiments, data noise and misspecification. Five initialization seeds are not five physical replications and do not yield calibrated prediction intervals.
7. Freeze a final protocol before acquiring a new test dataset; retain all failures and report per-protocol as well as pooled results.
8. Confirm author contributions, software/data rights, the student's understanding of the derivation and limitations, and external scientific review.

The website supports a read-only backend mode for a future public demonstration. No remote hosting has been configured. The training-enabled server is intended for local use; a publicly writable compute service would need authentication, resource quotas and operational controls.
