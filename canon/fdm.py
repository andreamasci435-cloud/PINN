"""Independent method-of-lines reference: conservative faces + implicit BDF time integration."""

import numpy as np
from scipy.integrate import solve_ivp
from scipy.interpolate import RegularGridInterpolator
from scipy.sparse import diags

from .physics import coefficients, heater


def solve(
    cfg, kind, raw, amplitude, off, nx=None, times=None, initial=None, rtol=2e-7, atol=1e-8, boundary=None
):
    nx = nx or cfg.fit_nx
    x = np.linspace(0, cfg.length, nx)
    times = np.asarray(times if times is not None else np.linspace(0, cfg.duration, cfg.samples))
    dx = x[1] - x[0]
    initial = np.full(nx, cfg.ambient) if initial is None else np.asarray(initial, dtype=float)
    if initial.shape != (nx,) or times[0] < 0 or np.any(np.diff(times) <= 0):
        raise ValueError("Invalid initial state or time grid")

    def left_temperature(t):
        return (
            heater(t, amplitude, off, cfg.ambient)
            if boundary is None
            else np.interp(t, boundary[0], boundary[1])
        )

    def rhs(t, y):
        T = np.r_[left_temperature(t), y]
        xf = (x[:-1] + x[1:]) / (2 * cfg.length)
        uf = ((T[:-1] + T[1:]) / 2 - cfg.ambient) / cfg.temperature_scale
        af, _ = coefficients(kind, raw, xf, uf)
        flux = af * np.diff(T) / dx
        _, beta = coefficients(kind, raw, x[1:] / cfg.length, (y - cfg.ambient) / cfg.temperature_scale)
        derivative = np.empty(nx - 1)
        derivative[:-1] = np.diff(flux) / dx
        # Last node represents a half control volume: zero outward flux.
        derivative[-1] = -2 * flux[-1] / dx
        return derivative - beta * (y - cfg.ambient)

    jac_pattern = diags([np.ones(nx - 2), np.ones(nx - 1), np.ones(nx - 2)], [-1, 0, 1], format="csc")
    sol = solve_ivp(
        rhs,
        (0, float(times[-1])),
        initial[1:],
        t_eval=times,
        method="BDF",
        rtol=rtol,
        atol=atol,
        jac_sparsity=jac_pattern,
    )
    if not sol.success:
        raise RuntimeError(sol.message)
    T = np.column_stack([left_temperature(times), sol.y.T])
    return x, times, T


def sample(x, t, T, sensor_x, sensor_t):
    points = np.column_stack([np.asarray(sensor_t).ravel(), np.asarray(sensor_x).ravel()])
    return RegularGridInterpolator((t, x), T, bounds_error=True)(points)
