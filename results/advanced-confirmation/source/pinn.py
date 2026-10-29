"""PyTorch inverse PINN evolved from the original tanh ForwardPINN.

Coordinates xi=x/L and tau=t/t_max; output u=(T-Tamb)/DeltaT.
Residual u_tau - t_max/L² d_xi(alpha u_xi) + t_max beta u.
The protocol amplitude and switch-off time condition a single network across runs.
"""

import time

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

from .physics import initial_raw


def seed_all(seed):
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)


def derivative(y, x):
    return torch.autograd.grad(y, x, torch.ones_like(y), create_graph=True)[0]


class InversePINN(nn.Module):
    def __init__(self, cfg, kind="M0"):
        super().__init__()
        self.cfg, self.kind = cfg, kind
        layers = [nn.Linear(6 if cfg.boundary_mode == "hard" else 4, cfg.width), nn.Tanh()]
        for _ in range(cfg.depth - 1):
            layers += [nn.Linear(cfg.width, cfg.width), nn.Tanh()]
        layers += [nn.Linear(cfg.width, 1)]
        self.net = nn.Sequential(*layers)
        self.raw = nn.Parameter(torch.tensor(initial_raw(kind), dtype=torch.float64))
        self.hard_constraints = cfg.boundary_mode == "hard"
        self.double()

    def forward(self, inputs):
        if not self.hard_constraints:
            if self.net[0].in_features == 6:
                time_s = inputs[:, 1:2] * self.cfg.duration
                inputs = torch.cat(
                    [
                        inputs,
                        torch.sigmoid((inputs[:, 3:4] * self.cfg.duration - time_s) / 6),
                        torch.exp(-time_s / 8),
                    ],
                    dim=1,
                )
            return self.net(2 * inputs - 1)
        xi, tau = inputs[:, :1], inputs[:, 1:2]
        # s'(1)=0 enforces the insulated end for ALL network weights.
        coordinate = xi * (2 - xi)
        time_s = tau * self.cfg.duration
        phase = torch.sigmoid((inputs[:, 3:4] * self.cfg.duration - time_s) / 6)
        onset = torch.exp(-time_s / 8)
        features = torch.cat([coordinate, inputs[:, 1:], phase, onset], dim=1)
        boundary = (
            inputs[:, 2:3]
            * (-torch.expm1(-time_s / 8))
            * torch.sigmoid((inputs[:, 3:4] * self.cfg.duration - time_s) / 6)
        )
        lift = torch.cosh(5 * (1 - xi)) / torch.cosh(torch.tensor(5.0, dtype=inputs.dtype))
        gate = -torch.expm1(-time_s / 8)
        return boundary * lift + gate * coordinate * self.net(2 * features - 1)

    def parameters_at(self, xi, u):
        a, b = self.raw[0] + 0 * xi, self.raw[1] + 0 * xi
        z = 2 * xi - 1
        if self.kind == "M1":
            a = a + self.raw[2] * z + self.raw[3] * z * z
        elif self.kind == "M2":
            b = b + self.raw[2] * torch.exp(-(((xi - 0.4) / 0.15) ** 2))
        elif self.kind == "M3":
            a = a + self.raw[2] * u
        return 1e-4 * F.softplus(a), 1e-2 * F.softplus(b)

    def residual(self, inputs):
        inputs = inputs.detach().clone().requires_grad_(True)
        u = self(inputs)
        du = derivative(u, inputs)
        a, b = self.parameters_at(inputs[:, :1], u)
        divergence = derivative(a * du[:, :1], inputs)[:, :1]
        return du[:, 1:2] - self.cfg.duration / self.cfg.length**2 * divergence + self.cfg.duration * b * u

    def predict(self, x, t, amplitude, off):
        xx, tt = np.broadcast_arrays(x, t)
        z = np.column_stack(
            [
                xx.ravel() / self.cfg.length,
                tt.ravel() / self.cfg.duration,
                np.full(xx.size, amplitude / self.cfg.temperature_scale),
                np.full(xx.size, off / self.cfg.duration),
            ]
        )
        with torch.no_grad():
            u = self(torch.tensor(z, dtype=torch.float64)).numpy().reshape(xx.shape)
        return self.cfg.ambient + self.cfg.temperature_scale * u


def training_data(runs, cfg):
    points, targets = [], []
    for run in runs:
        xx, tt = np.meshgrid(run["sensor_x"], run["t"])
        points.append(
            np.column_stack(
                [
                    xx.ravel() / cfg.length,
                    tt.ravel() / cfg.duration,
                    np.full(xx.size, run["amplitude"] / cfg.temperature_scale),
                    np.full(xx.size, run["off"] / cfg.duration),
                ]
            )
        )
        targets.append((run["observations"].ravel()[:, None] - cfg.ambient) / cfg.temperature_scale)
    return torch.tensor(np.vstack(points), dtype=torch.float64), torch.tensor(
        np.vstack(targets), dtype=torch.float64
    )


def fit_pinn(cfg, runs, kind, seed, data_only=False, callback=None):
    seed_all(seed)
    model = InversePINN(cfg, kind)
    if cfg.boundary_mode == "hard" and any("boundary" in r for r in runs) and not data_only:
        raise ValueError(
            "Hard lifting currently supports the declared analytic heating protocol only; use soft boundaries for measured histories"
        )
    if data_only:
        model.hard_constraints = False
        model.raw.requires_grad_(False)
    X, y = training_data(runs, cfg)
    history = []
    rng = torch.Generator().manual_seed(seed + 1000)
    contexts = torch.tensor(
        [[r["amplitude"] / cfg.temperature_scale, r["off"] / cfg.duration] for r in runs], dtype=torch.float64
    )

    def points(n):
        coords = torch.rand(n, 2, generator=rng, dtype=torch.float64)
        # Extra near-boundary, early-time points resolve the thermal front.
        coords[: n // 3, 0] **= 2
        coords[: n // 3, 1] **= 2
        ids = torch.randint(len(contexts), (n,), generator=rng)
        protocol = contexts[ids]
        if cfg.continuous_protocols and not data_only:
            if any("boundary" in r for r in runs):
                raise ValueError("Continuous protocol collocation requires analytic boundary histories")
            protocol = torch.rand(n, 2, generator=rng, dtype=torch.float64)
            protocol[:, 0] = (30 + 40 * protocol[:, 0]) / cfg.temperature_scale
            protocol[:, 1] = 0.4 + 0.35 * protocol[:, 1]
        return torch.cat([coords, protocol], dim=1)

    def components(collocation):
        data = ((model(X) - y) ** 2).mean()
        if data_only:
            return {"data": data, **{k: data * 0 for k in ["pde", "ic", "bc", "reg"]}}
        pde = model.residual(collocation).square().mean()
        ic_pts = collocation[:128].clone()
        ic_pts[:, 1] = 0
        ic = model(ic_pts).square().mean()
        left = collocation[:128].clone()
        left[:, 0] = 0
        time_s = left[:, 1:2] * cfg.duration
        off = left[:, 3:4] * cfg.duration
        target = left[:, 2:3] * (1 - torch.exp(-time_s / 8)) * torch.sigmoid((off - time_s) / 6)
        for run, context in zip(runs, contexts):
            if "boundary" in run:
                mask = (left[:, 2:] == context).all(dim=1)
                bt = torch.tensor(run["boundary"][0], dtype=torch.float64)
                bv = torch.tensor(run["boundary"][1], dtype=torch.float64)
                query = time_s[mask, 0]
                idx = torch.searchsorted(bt, query).clamp(1, len(bt) - 1)
                fraction = (query - bt[idx - 1]) / (bt[idx] - bt[idx - 1])
                target[mask, 0] = (
                    bv[idx - 1] + fraction * (bv[idx] - bv[idx - 1]) - cfg.ambient
                ) / cfg.temperature_scale
        right = left.clone()
        right[:, 0] = 1
        right.requires_grad_(True)
        flux = derivative(model(right), right)[:, :1]
        bc = ((model(left) - target) ** 2).mean() + flux.square().mean()
        reg = model.raw[2:].square().mean() if model.raw.numel() > 2 else model.raw.sum() * 0
        return dict(data=data, pde=pde, ic=ic, bc=bc, reg=reg)

    weights = {**cfg.weights}
    if data_only:
        weights = {k: float(k == "data") for k in weights}
    if cfg.boundary_mode == "hard" and not data_only:
        optimizer = torch.optim.Adam(
            [
                {"params": model.net.parameters(), "lr": cfg.learning_rate},
                {"params": [model.raw], "lr": cfg.parameter_lr},
            ]
        )
    else:
        optimizer = torch.optim.Adam(model.parameters(), lr=cfg.learning_rate)
    adaptive_pool = None

    def collocation_points(epoch):
        nonlocal adaptive_pool
        if not cfg.adaptive_sampling or data_only or epoch <= cfg.warmup_epochs:
            return points(cfg.collocation)
        if adaptive_pool is None or epoch % cfg.adaptive_every == 0:
            proposals = points(cfg.collocation * 4)
            errors = []
            for block in proposals.split(512):
                errors.append(model.residual(block).detach().abs().flatten())
            weights_sampling = torch.cat(errors) + 0.05 * torch.cat(errors).mean() + 1e-12
            chosen = torch.multinomial(weights_sampling, cfg.collocation // 2, generator=rng)
            adaptive_pool = proposals[chosen].detach()
        # Retain fresh global points: never focus exclusively on high residuals.
        return torch.cat([points(cfg.collocation - len(adaptive_pool)), adaptive_pool])

    start = time.perf_counter()
    for epoch in range(1, cfg.epochs + 1):
        optimizer.zero_grad(set_to_none=True)
        comp = components(collocation_points(epoch))
        effective = dict(weights)
        if epoch <= cfg.warmup_epochs and not data_only:
            effective["pde"] = 0.0
        loss = sum(effective[k] * v for k, v in comp.items())
        if not torch.isfinite(loss):
            raise FloatingPointError("Nonfinite training loss")
        loss.backward()
        if epoch <= cfg.warmup_epochs:
            model.raw.grad = None
        if cfg.boundary_mode == "hard" or cfg.adaptive_sampling:
            torch.nn.utils.clip_grad_norm_(model.parameters(), 10.0)
        optimizer.step()
        if epoch == 1 or epoch % 100 == 0 or epoch == cfg.epochs:
            row = dict(
                epoch=epoch,
                stage="adam",
                sampling="adaptive" if adaptive_pool is not None else "random",
                total=loss.item(),
                **{k: v.item() for k, v in comp.items()},
            )
            history.append(row)
            if callback:
                callback(epoch, cfg.epochs, row)
    if cfg.lbfgs:
        fixed = points(cfg.collocation)
        optimizer = torch.optim.LBFGS(
            model.parameters(), max_iter=cfg.lbfgs, line_search_fn="strong_wolfe", tolerance_grad=1e-9
        )

        def closure():
            optimizer.zero_grad(set_to_none=True)
            comp = components(fixed)
            loss = sum(weights[k] * v for k, v in comp.items())
            if not torch.isfinite(loss):
                raise FloatingPointError("Nonfinite L-BFGS loss")
            loss.backward()
            return loss

        optimizer.step(closure)
        comp = components(fixed)
        history.append(
            dict(
                epoch=cfg.epochs + cfg.lbfgs,
                stage="lbfgs",
                total=sum(weights[k] * v.item() for k, v in comp.items()),
                **{k: v.item() for k, v in comp.items()},
            )
        )
    return model, history, time.perf_counter() - start
