import numpy as np
import pytest
import torch

from canon.config import Config
from canon.fdm import solve
from canon.physics import coefficients, heater, initial_raw
from canon.pinn import InversePINN, seed_all


def test_solver_converges_to_analytic_decay():
    cfg = Config(duration=100)
    alpha, beta = 1e-4, 0.01
    errors = []
    for nx in [21, 41, 81]:
        x = np.linspace(0, cfg.length, nx)
        initial = cfg.ambient + 10 * np.sin(np.pi * x / (2 * cfg.length))
        x, t, T = solve(
            cfg,
            "M0",
            initial_raw("M0", alpha, beta),
            0,
            50,
            nx=nx,
            times=np.array([0.0, 100.0]),
            initial=initial,
            rtol=1e-10,
            atol=1e-11,
        )
        exact = cfg.ambient + 10 * np.sin(np.pi * x / (2 * cfg.length)) * np.exp(
            -(alpha * (np.pi / (2 * cfg.length)) ** 2 + beta) * 100
        )
        errors.append(np.max(np.abs(T[-1] - exact)))
    assert errors[0] / errors[1] > 3.8
    assert errors[1] / errors[2] > 3.8
    assert errors[-1] < 2e-5


def test_equilibrium_and_boundary():
    cfg = Config(duration=100)
    x, t, T = solve(cfg, "M0", initial_raw("M0"), 0, 50)
    np.testing.assert_allclose(T, cfg.ambient, atol=1e-10)
    x, t, T = solve(cfg, "M0", initial_raw("M0"), 60, 50)
    np.testing.assert_allclose(T[:, 0], heater(t, 60, 50, cfg.ambient))
    assert T.min() >= cfg.ambient - 1e-8
    assert T.max() <= cfg.ambient + 60 + 1e-8


@pytest.mark.parametrize("kind", ["M0", "M1", "M2", "M3"])
def test_conservative_autodiff_residual(kind):
    cfg = Config()

    class Polynomial(InversePINN):
        def forward(self, z):
            return z[:, :1] ** 2 + z[:, 1:2]

    model = Polynomial(cfg, kind)
    with torch.no_grad():
        model.raw[2:] = 0.4
    z = torch.tensor([[0.2, 0.3, 0.8, 0.5], [0.7, 0.6, 0.9, 0.7]], dtype=torch.float64)
    x = z[:, :1].numpy()
    u = x * x + z[:, 1:2].numpy()
    raw = model.raw.detach().numpy()
    a, b = coefficients(kind, raw, x, u)
    h = 1e-6
    # Differentiate alpha(x,u(x,t)) along the field, including the M3 chain rule.
    ap, _ = coefficients(kind, raw, x + h, (x + h) ** 2 + z[:, 1:2].numpy())
    am, _ = coefficients(kind, raw, x - h, (x - h) ** 2 + z[:, 1:2].numpy())
    divergence = 2 * a + 2 * x * (ap - am) / (2 * h)
    expected = 1 - cfg.duration / cfg.length**2 * divergence + cfg.duration * b * u
    np.testing.assert_allclose(model.residual(z).detach().numpy(), expected, rtol=1e-7)


def test_inverse_parameters_recovered_from_two_analytic_modes():
    """Isolates inverse autograd from field approximation. Two modes identify both parameters."""
    cfg = Config()
    seed_all(42)

    class Analytic(InversePINN):
        def forward(self, z):
            x, t = z[:, :1], z[:, 1:2]
            return sum(
                torch.sin(k * x) * torch.exp(-(1e-4 * k * k / cfg.length**2 + 0.01) * cfg.duration * t)
                for k in [np.pi / 2, 3 * np.pi / 2]
            )

    model = Analytic(cfg)
    pts = torch.rand(500, 4, dtype=torch.float64)
    opt = torch.optim.LBFGS(
        [model.raw], max_iter=100, tolerance_grad=1e-12, tolerance_change=1e-14, line_search_fn="strong_wolfe"
    )

    def closure():
        opt.zero_grad()
        loss = model.residual(pts).square().mean()
        loss.backward()
        return loss

    opt.step(closure)
    a, b = model.parameters_at(torch.zeros(1, 1), torch.zeros(1, 1))
    assert abs(a.item() / 1e-4 - 1) < 1e-4
    assert abs(b.item() / 0.01 - 1) < 1e-4


def test_temperature_scale_requires_chain_rule():
    cfg = Config()
    assert cfg.duration / cfg.length**2 == 1600


def test_temporal_tolerance_refinement():
    cfg = Config(duration=100)
    raw = initial_raw("M0")
    _, _, coarse = solve(cfg, "M0", raw, 60, 50, nx=41, rtol=1e-5, atol=1e-6)
    _, _, fine = solve(cfg, "M0", raw, 60, 50, nx=41, rtol=1e-8, atol=1e-9)
    assert np.max(np.abs(coarse - fine)) < 0.005


def test_recorded_boundary_is_used():
    cfg = Config(duration=100)
    boundary = (np.array([0, 25, 50, 75, 100.0]), np.array([20, 35, 40, 30, 20.0]))
    _, t, T = solve(cfg, "M0", initial_raw("M0"), 60, 50, boundary=boundary)
    np.testing.assert_allclose(T[:, 0], np.interp(t, *boundary))


@pytest.mark.parametrize("kind", ["M0", "M1", "M2", "M3"])
def test_hard_constraints_hold_before_any_training(kind):
    from canon.diagnostics import constraint_audit

    cfg = Config(boundary_mode="hard")
    seed_all(100)
    model = InversePINN(cfg, kind)
    audit = constraint_audit(model, cfg, {"amplitude": 67.0, "off": 233.0})
    assert max(audit.values()) < 1e-10
    z = torch.rand(32, 4, dtype=torch.float64)
    r = model.residual(z)
    assert torch.isfinite(r).all()
    r.square().mean().backward()
    assert model.raw.grad is not None


def test_confirmation_protocols_are_independent_and_new():
    from canon.data import synthetic, validate_split

    runs = synthetic(Config(protocol_set="confirmation", samples=11, truth_nx=31))
    split = {k: [r["run_id"] for r in runs if r["split"] == k] for k in ["train", "validation", "test"]}
    validate_split(split)
    assert [len(split[k]) for k in ["train", "validation", "test"]] == [3, 2, 2]
    assert {(r["amplitude"], r["off"]) for r in runs if r["split"] == "test"}.isdisjoint(
        {(r["amplitude"], r["off"]) for r in runs if r["split"] == "train"}
    )
