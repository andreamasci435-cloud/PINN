# Browser solver validation

The Vercel edition evaluates forward simulations in a module Web Worker, using JavaScript float64 arithmetic, 81 spatial nodes, 81 output times over 400 seconds, conservative face fluxes and a half-volume insulated right endpoint. RK4 substeps are limited by both 0.05 seconds and a conservative diffusivity bound. Boundary forcing is imposed at every RK stage.

`tests/test_browser_solver.py` compares the deployed JavaScript implementation to the independent SciPy BDF implementation on the same spatial grid for all four material hypotheses and three parameter sets: defaults, high diffusivity/loss with early cooling, and low diffusivity/loss with late cooling. Across these 12 cases the observed maximum absolute difference was **0.000258494 °C**, below the 0.001 °C test threshold. The tests also check initial temperature and physical temperature bounds.

This validates agreement between time integrators on those cases. It is not a proof over the full parameter domain, spatial convergence evidence, experimental validation, or PINN accuracy evidence. The archived benchmark retains its original Python solver and provenance. Browser simulations do not fit or retrain neural networks.
