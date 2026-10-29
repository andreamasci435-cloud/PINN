# Methods and numerical assumptions

This document describes the executable implementation, not a completed physical study.

## Forward model and units

For a constant cross-sectional area and constant volumetric heat capacity ρcₚ:

`T_t = ∂x[α(x,T) T_x] − β(x)(T − T_amb)`

α = k/(ρcₚ) in m²/s; β = hP/(ρcₚA) in s⁻¹. β is not itself a convection coefficient in W/(m² K). Recovering h requires measured geometry, density and heat capacity. Constant ρcₚ is necessary for the implemented variable-α conservative form. No source, contact lag or radiation term is fitted.

The left temperature is imposed; the right end has zero heat flux. Synthetic heating uses `Tamb + A (1−exp(−t/8))/(1+exp((t−t_off)/6))`. This smooth ramp avoids an incompatible initial corner from an instantaneous jump at t=0. All initial temperatures equal Tamb. Cooling follows the same smooth switch-off boundary. This is a temperature-controlled idealization, not constant-power heater dynamics.

## Hypotheses

Let ξ=x/L, u=(T−Tamb)/ΔT, z=2ξ−1, a*=10⁻⁴ m²/s and b*=10⁻² s⁻¹.

| Model | α | β | Number of inverse parameters |
|---|---|---|---|
| M0 | a* softplus(a₀) | b* softplus(b₀) | 2 |
| M1 | a* softplus(a₀+a₁z+a₂z²) | b* softplus(b₀) | 4 |
| M2 | a* softplus(a₀) | b* softplus(b₀+b₁ exp(−((ξ−0.4)/0.15)²)) | 3 |
| M3 | a* softplus(a₀+a₁u) | b* softplus(b₀) | 3 |

The local-loss centre and width in M2 are fixed, declared design priors. The experiment estimates the loss strength, not an arbitrary unknown location. These modest parameterizations reduce overfitting but do not represent all possible materials. Raw parameters are ordered [a₀,b₀,...]. The classical optimizer bounds raw coefficients to [−6,6]; neural softplus coefficients have no corresponding upper bound. Report this difference when comparing optimization robustness.

## PINN

A tanh MLP receives [ξ,τ,A/ΔT,t_off/t_max], each mapped by 2q−1. The standard width/depth are 48/4; the extended preset uses width 64. The original two-coordinate architecture is retained in spirit and extended to share inverse coefficients across different heating protocols. A descriptor outside the training range is an extrapolation; the synthetic test amplitude 65 °C exceeds the training maximum 60 °C.

The normalized PDE is:

`r = u_τ − (t_max/L²) ∂ξ[α u_ξ] + t_max βu`.

Autograd differentiates the full flux, including α_ξ and the temperature chain rule in M3. Data MSE uses normalized temperatures. Initial u=0, left u follows the imposed/recorded temperature, and right u_ξ=0. Inverse parameter regularization is the mean square of nonconstant raw coefficients; it shrinks variation instead of penalizing an arbitrary function on an unknown grid. Default weights are data 20, PDE 1, IC 10, BC 10, regularization 0.001; all are logged.

Fresh collocation coordinates are sampled each Adam epoch, with one third concentrated near ξ=0 and τ=0 by squaring uniform coordinates. BC/IC use up to 128 of those coordinates. The finite L-BFGS stage freezes its sample for a deterministic objective. It may evaluate the closure more than the requested iteration budget. Independent residual evaluation uses a separate RNG stream and new coordinates. CPU float64 and deterministic PyTorch operations are used; bitwise equality is tested within the same software/hardware environment, not promised across platforms.

The MLP baseline has the same field architecture and training budget, with only data MSE and no inferred physical coefficients. Its data loss weight is 1 rather than 20 (a scalar does not change the isolated optimum, but optimizer dynamics can differ).

## Numerical reference

A method of lines uses face-centred diffusion coefficients and conservative face fluxes on a uniform mesh. The last node has a half control volume so the zero right-face flux yields `−2 flux_left/dx`. BDF integrates the stiff ODE system using a tridiagonal Jacobian sparsity pattern. Truth normally uses 101 nodes, classical fitting 51 nodes. This is an implicit semidiscrete finite-difference/finite-volume scheme, not the original explicit Euler update. Independent analytic eigenmode decay verifies second-order spatial convergence. Temporal accuracy is adaptive; a tolerance-refinement test checks stability of the output.

## Validation and inference endpoints

Five synthetic protocols are fixed before training: three train, one validation and one test. No observations from validation/test enter any optimizer. Group selection uses the mean validation RMSE over optimization seeds. The selection manifest is written before test metrics are computed. All frozen candidates are subsequently scored to make failures visible; those scores must not be used to retune and claim an untouched test.

For PINN and classical methods, the primary endpoint is FDM forward prediction under a new known boundary using the inferred coefficients. This is appropriate for parameter identification but is a hybrid PINN→FDM pipeline, not a pure neural-solver benchmark. The direct neural field and its error are saved separately. For the MLP the endpoint is direct neural prediction. Comparing neural solve speed requires a separate inference-timing study; the current times cover fitting only.

An equally weighted RMSE/MAE over sensor-time observations is reported. Relative L² uses excess temperature. PDE RMS is dimensionless and computed on new test-context points; it is a diagnostic after freezing selection, not a selection criterion. Profiles of α(T) are evaluated at ambient when a one-dimensional position profile is exported.

## Uncertainty and identifiability

The classical weighted residual Jacobian supplies singular values and a condition number. This is a local diagnostic, not proof of structural or global identifiability. Multi-seed field envelopes measure optimization spread, and their empirical coverage of synthetic truth is reported without claiming calibrated probability. Entire-training-run bootstrap is available separately, with the limitation of only three distinct training protocols. Sensor-position uncertainty and boundary uncertainty are not propagated automatically; they must be studied before physical conclusions.

## Sources

[Raissi et al.](https://doi.org/10.1016/j.jcp.2018.10.045) motivates simultaneous data/PDE training and inverse inference. [Krishnapriyan et al.](https://papers.nips.cc/paper/2021/hash/df438e5206f31600e6ae4af72f2725f1-Abstract.html) motivates reporting optimization failures instead of treating small residuals as evidence of accurate solutions. The equations, parameterizations, splitting rule and implementation details above specify this repository's choices, not verbatim reproductions of those papers.
