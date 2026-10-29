# Confirmation experiment: observed results

Four classical fits, five enhanced PINN fits and five data-only MLP fits were completed. All values below are held-out sensor RMSE in °C, pooled over two test protocols. Configuration and source were frozen before training; selection used validation only.

| Method / endpoint | Mean RMSE | Seed SD |
| --- | ---: | ---: |
| Classical M2 | 0.150414 | — |
| PINN M2 → forward solver | 0.321909 | 0.117819 |
| PINN M2 direct neural | 0.376909 | 0.140768 |
| Data-only MLP | 5.518512 | 1.026938 |

The classical M2 fit was selected on validation and remains the most accurate method on this test. The PINN greatly outperforms this data-only baseline, but does not outperform the classical inverse solver. This comparison does not establish superiority over every supervised architecture.

All five PINN seeds satisfy the initial condition and insulated end to numerical zero; the maximum sampled left-boundary discrepancy is 7.82 × 10⁻¹⁴ °C. Exact boundary satisfaction does not eliminate interior approximation error.

The PINN direct test RMSE ranges from 0.221331 to 0.551764 °C. No seed was discarded. The earlier benchmark used different protocols and optimization budgets: an apparent improvement across editions is not a controlled causal comparison.

Total recorded benchmark time: 617.8 seconds on the environment saved in results.json. Timing excludes final report rendering.

Dataset: seven synthetic protocols, data seed 20261009. Training: three protocols; validation: two; test: two. Optimization seeds: 11, 23, 42, 67, 101. Seed SD is optimization spread on one dataset, not measurement uncertainty.

Source artifacts: `results/advanced-confirmation/`. Verified numerical archive: `releases/advanced-confirmation.zip`. Detailed methods: [RESEARCH_EDITION.md](RESEARCH_EDITION.md). Remaining physical evidence: [PUBLICATION_READINESS.md](PUBLICATION_READINESS.md).
