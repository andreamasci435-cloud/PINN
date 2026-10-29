# Research edition: methods and development record

## Scope

This supplement specifies the enhanced **synthetic** inverse heat-transfer experiment. The original soft-constraint M0–M3 benchmarks are historical controls with different budgets and protocols; they are not a controlled architecture ablation of the new configuration.

The governing equation is `T_t = ∂x(α T_x) − β(T − Tamb)`. The spatial derivative acts on the entire flux, including α. The insulated right end uses a half control volume in the finite-difference solver. The independent analytic-solution and convergence tests exercise this discretization.

M2 estimates diffusivity and two coefficients defining the loss profile. Softplus keeps diffusivity and the total local loss positive; the unconstrained bump coefficient can increase or reduce loss locally. Its Gaussian bump center (0.4 of bar length) and width (0.15 of bar length) are assumed known. This assumption limits the identifiability claim: locating an unknown defect is not demonstrated.

## Exact-constraint trial function

Let `ξ=x/L`, `τ=t/D`, `u=(T−Tamb)/60`, `s=ξ(2−ξ)`, `g=1−exp(−t/8)` and `q=sigmoid((off−t)/6)`. The normalized prescribed boundary is `b=(A/60)gq`. The trial field is

```
u(ξ,t,A,off) = b(t,A,off) cosh(5(1−ξ))/cosh(5)
               + g(t) s(ξ) Nθ(s, τ, A/60, off/D, q, exp(−t/8)).
```

All six inputs are mapped by `2z−1` before four 48-unit tanh layers. This is a purpose-built lifting for the project's analytic boundary, inspired by the broader exact-boundary literature; it is not an implementation of every construction in that literature.

At ξ=0, s=0 and the lift equals one. At t=0, b=g=0. At ξ=1, both the lift derivative and ds/dξ vanish; all other network features are independent of ξ. Thus the prescribed left temperature, initial ambient state and right insulation hold for any finite weights, to floating-point precision. The API stores numerical audits across 101 points as a regression check. These constraints do **not** solve the interior PDE or establish coefficient accuracy.

The data-only MLP receives six analogous features, with ξ in place of s, and directly predicts u without lifting, PDE or boundary losses. Its optimizer budgets match the PINN preset; it is not claimed to be the best possible supervised model.

## Optimization and collocation

The locked preset uses float64 on CPU; 6,000 Adam epochs then at most 1,500 L-BFGS iterations. The first 1,500 epochs fit data while leaving physical coefficients fixed. Afterwards the network learning rate is 0.001 and coefficient learning rate 0.0001. Joint weights are data 20, PDE 1, IC 10, BC 10 and regularization 0.000001. In exact mode IC and BC terms are mathematically zero, up to numerical roundoff. Gradient norm is capped at 10. L-BFGS uses a fixed collocation set.

512 physics points are sampled per Adam epoch, with thermal-front enrichment. In continuous-protocol mode, amplitude is sampled in [30,70] °C and heater switch-off fraction in [0.4,0.75]. This uses the known analytic forcing family and PDE across that range, but no validation/test temperature observations. The confirmation inputs fall within that physics-training range: this is conditional interpolation, not extrapolation to unseen forcing physics.

Optional adaptive sampling scores a larger candidate pool by absolute PDE residual, mixes residual-weighted draws with fresh global samples and refreshes periodically. It is available for controlled future comparisons but disabled in the confirmation preset because development did not support making it the default.

## Development record, before confirmation

Development used the original local-loss synthetic dataset, data seed 42, optimization seed 42 and its **validation** protocol. These sequential experiments changed several factors, so they are a tuning record rather than a causal ablation. RMSE values below are validation °C; direct values are sensor predictions.

| Candidate | Main choices | PINN → solver | Direct neural |
| --- | --- | ---: | ---: |
| A | Four inputs, exact constraints, adaptive; 3,500 Adam / 300 L-BFGS, warm-up 500 | 0.737498 | 2.242540 |
| B | Six inputs, exact constraints, adaptive; 5,000 / 1,200, warm-up 1,000 | 1.846700 | 2.062080 |
| C | Six inputs, no adaptive; 6,000 / 1,500, warm-up 1,500, parameter LR 0.0001, regularization 0.001 | 0.445507 | 1.698293 |
| D | C plus continuous physics protocols and regularization 0.000001 | 0.285311 | 0.235682 |

D was fixed before the new confirmation experiment. Do not treat its validation score as a final test result. `scripts/develop_pinn.py` retains the final development driver; earlier candidates are documented here, not packaged as separate immutable releases.

## Locked confirmation protocol

Configuration: `configs/advanced.json`. Data seed: 20261009. Optimization seeds: 11, 23, 42, 67, 101. Noise: as saved in config (Gaussian synthetic sensor noise). Seven independent protocol IDs have amplitude/switch-off fraction:

| Split | Protocols (°C, fraction of duration) |
| --- | --- |
| Train | (42, .45), (58, .625), (52, .55) |
| Validation | (48, .70), (62, .50) |
| Test | (67, .585), (46, .675) |

Candidate groups are classical M0–M3, PINN-M2 and data-only MLP. Group selection uses mean validation sensor RMSE across seeds. Test observations are scored only after all fits and selection, with predictions pooled across both test protocols. Each row also retains per-protocol results. No best-seed selection is performed. A single first test field is stored for interactive visualization; direct neural sensor scores use both test protocols, whereas the legacy direct-field metric uses a whole first-test grid.

Independent diagnostics include a held-out collocation residual norm, a 41×41 first-test residual map, coefficient profiles against the synthetic truth, raw loss traces and constraint audits. Residual maps are diagnostic predictions and never recycled into optimization. Loss-history values after Adam include an L-BFGS endpoint whose x-coordinate represents the configured budget, not measured closure count.

## Reproducibility and interpretation

Before training, the runner snapshots `canon/*.py`, configuration and requirements lock. Data and source hashes are saved. After report generation, artifact hashes and a completion marker are written. `verify` checks artifact hashes, source files and the synthetic CSV. `bundle` refuses to replace an existing archive. Preserve results intact; regenerating figures in a completed folder invalidates its hashes.

The five seeds quantify optimizer variability on the same synthetic dataset. They do not quantify uncertainty over physical specimens, sensor calibration, noise realizations or model misspecification. No confidence interval or guarantee of superiority follows from them. Physical measurements remain necessary, and related forward solvers plus in-family truth make this an intentionally limited numerical benchmark.
