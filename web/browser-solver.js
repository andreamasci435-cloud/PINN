/** Conservative 1D finite volumes and explicit RK4, CPU float64 (JavaScript).
 * Same flux, forcing and M0–M3 hypotheses as canon/fdm.py; different integrator.
 * Exploratory forward simulation only. Does not train or emulate a PINN.
 */
const softplus = (v) => Math.max(v, 0) + Math.log1p(Math.exp(-Math.abs(v)));
export function solveBrowser(input, { maxStep = 0.05 } = {}) {
  const p = {
    scenario: "uniform",
    alpha: 1e-4,
    beta: 0.01,
    amplitude: 60,
    off: 230,
    ...input,
  };
  if (
    !["uniform", "local_loss", "variable_alpha", "temperature_alpha"].includes(
      p.scenario,
    )
  )
    throw new Error("Unknown material hypothesis");
  for (const [key, lo, hi] of [
    ["alpha", 1e-6, 1e-3],
    ["beta", 1e-5, 0.1],
    ["amplitude", 10, 70],
    ["off", 30, 380],
  ]) {
    if (!Number.isFinite(p[key]) || p[key] < lo || p[key] > hi)
      throw new Error(`Invalid ${key}`);
  }
  if (!Number.isFinite(maxStep) || maxStep <= 0 || maxStep > 0.2)
    throw new Error("Invalid integration step");
  const n = 81,
    dx = 0.5 / (n - 1),
    a0 = Math.log(Math.expm1(p.alpha / 1e-4)),
    b0 = Math.log(Math.expm1(p.beta / 0.01));
  const x = Array.from({ length: n }, (_, i) => i * dx),
    times = Array.from({ length: 81 }, (_, i) => i * 5);
  const boundary = (t) =>
    (p.amplitude * -Math.expm1(-t / 8)) / (1 + Math.exp((t - p.off) / 6));
  const faceAlpha = Float64Array.from({ length: n - 1 }, (_, i) => {
    const z = (2 * (i + 0.5)) / (n - 1) - 1;
    return (
      1e-4 *
      softplus(
        a0 + (p.scenario === "variable_alpha" ? 0.65 * z - 0.3 * z * z : 0),
      )
    );
  });
  const losses = Float64Array.from(
    { length: n },
    (_, i) =>
      0.01 *
      softplus(
        b0 +
          (p.scenario === "local_loss"
            ? 2 * Math.exp(-(((i / (n - 1) - 0.4) / 0.15) ** 2))
            : 0),
      ),
  );
  // Conservative upper bound on diffusivity over 0 <= T-Tamb <= amplitude.
  const maxAlpha = 1e-4 * softplus(a0 + 1);
  const steps = Math.ceil(5 / Math.min(maxStep, (0.4 * dx * dx) / maxAlpha));
  const h = 5 / steps,
    y = new Float64Array(n),
    flux = new Float64Array(n - 1);
  const k1 = new Float64Array(n),
    k2 = new Float64Array(n),
    k3 = new Float64Array(n),
    k4 = new Float64Array(n),
    stage = new Float64Array(n);
  function rhs(t, values, out) {
    const left = boundary(t);
    for (let i = 0; i < n - 1; i++) {
      const l = i === 0 ? left : values[i],
        r = values[i + 1];
      const a =
        p.scenario === "temperature_alpha"
          ? 1e-4 * softplus(a0 + (0.8 * (l + r)) / 120)
          : faceAlpha[i];
      flux[i] = (a * (r - l)) / dx;
    }
    for (let i = 1; i < n - 1; i++)
      out[i] = (flux[i] - flux[i - 1]) / dx - losses[i] * values[i];
    out[n - 1] = (-2 * flux[n - 2]) / dx - losses[n - 1] * values[n - 1];
  }
  const fields = [Array(n).fill(20)];
  for (let frame = 1; frame < times.length; frame++) {
    for (let step = 0; step < steps; step++) {
      const t = times[frame - 1] + step * h;
      rhs(t, y, k1);
      for (let i = 1; i < n; i++) stage[i] = y[i] + (h * k1[i]) / 2;
      rhs(t + h / 2, stage, k2);
      for (let i = 1; i < n; i++) stage[i] = y[i] + (h * k2[i]) / 2;
      rhs(t + h / 2, stage, k3);
      for (let i = 1; i < n; i++) stage[i] = y[i] + h * k3[i];
      rhs(t + h, stage, k4);
      for (let i = 1; i < n; i++)
        y[i] += (h * (k1[i] + 2 * k2[i] + 2 * k3[i] + k4[i])) / 6;
    }
    y[0] = boundary(times[frame]);
    fields.push(Array.from(y, (v) => v + 20));
  }
  if (fields.some((row) => row.some((v) => !Number.isFinite(v))))
    throw new Error("Nonfinite numerical solution");
  return {
    provenance: "synthetic",
    solver: "Conservative finite difference + RK4 (browser)",
    x_m: x,
    time_s: times,
    temperature_C: fields,
  };
}
