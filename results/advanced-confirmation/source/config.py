"""Validated experiment configuration. All dimensional quantities use SI except °C."""

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class Config(BaseModel):
    model_config = {"extra": "forbid"}
    length: float = Field(0.5, gt=0)
    duration: float = Field(400.0, ge=100, le=2000)
    ambient: float = Field(20.0, ge=-20, le=50)
    temperature_scale: float = Field(60.0, gt=0)
    alpha: float = Field(1e-4, ge=1e-6, le=1e-3)
    beta: float = Field(0.01, ge=1e-5, le=0.1)
    scenario: Literal["uniform", "local_loss", "variable_alpha", "temperature_alpha"] = "uniform"
    sensors: int = Field(8, ge=2, le=8)
    noise: float = Field(0.15, ge=0, le=3)
    seed: int = Field(42, ge=0, le=2147483647)
    truth_nx: int = Field(101, ge=21, le=401)
    fit_nx: int = Field(51, ge=11, le=201)
    samples: int = Field(81, ge=11, le=401)
    epochs: int = Field(1800, ge=1, le=50000)
    lbfgs: int = Field(150, ge=0, le=5000)
    width: int = Field(48, ge=8, le=128)
    depth: int = Field(4, ge=2, le=6)
    collocation: int = Field(512, ge=16, le=20000)
    learning_rate: float = Field(0.001, gt=0, le=0.1)
    models: list[Literal["M0", "M1", "M2", "M3"]] = Field(default_factory=lambda: ["M0"])
    classical_models: list[Literal["M0", "M1", "M2", "M3"]] = Field(default_factory=list)
    seeds: list[int] = Field(default_factory=lambda: [42])
    boundary_mode: Literal["soft", "hard"] = "soft"
    adaptive_sampling: bool = False
    continuous_protocols: bool = False
    adaptive_every: int = Field(100, ge=10, le=1000)
    warmup_epochs: int = Field(0, ge=0, le=10000)
    parameter_lr: float = Field(0.003, gt=0, le=0.1)
    protocol_set: Literal["original", "confirmation"] = "original"
    weights: dict[str, float] = Field(
        default_factory=lambda: {"data": 20.0, "pde": 1.0, "ic": 10.0, "bc": 10.0, "reg": 0.001}
    )

    @model_validator(mode="after")
    def validate_study(self):
        if self.warmup_epochs >= self.epochs:
            raise ValueError("warmup_epochs must be smaller than epochs")
        if self.length <= 0.04:
            raise ValueError("length must exceed the 0.04 m sensor end margins")
        if not self.models or len(set(self.models)) != len(self.models):
            raise ValueError("models must be nonempty and unique")
        if not self.seeds or len(set(self.seeds)) != len(self.seeds) or any(s < 0 for s in self.seeds):
            raise ValueError("seeds must be nonempty, unique and nonnegative")
        if set(self.weights) != {"data", "pde", "ic", "bc", "reg"}:
            raise ValueError("weights must contain data, pde, ic, bc, reg")
        if any(not (0 <= v < float("inf")) for v in self.weights.values()):
            raise ValueError("loss weights must be finite and nonnegative")
        return self
