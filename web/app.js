import { staticApi } from "./static-api.js";
import { renderDiagnostics } from "./diagnostics.js?v=2.1";
import * as THREE from "three";
import { OrbitControls } from "./vendor/OrbitControls.js";
const STATIC_MODE = window.CANON_STATIC === true;
const API_ORIGIN = window.CANON_API_URL || "";
const $ = (id) => document.getElementById(id);
const state = {
  result: null,
  field: null,
  index: 40,
  selected: null,
  playing: false,
  mode: "benchmark",
};
let renderer,
  scene,
  camera,
  orbit,
  segments = [],
  sensorMeshes = [],
  lastFrame = 0;
const heatStops = ["#426a68", "#759578", "#cedb9b", "#f0c168", "#f87540"].map(
  (c) => new THREE.Color(c),
);
function heat(T) {
  const p = Math.max(0, Math.min(3.999, ((T - 20) / 70) * 4)),
    i = Math.floor(p);
  return heatStops[i].clone().lerp(heatStops[i + 1], p - i);
}
const fmt = (n, d = 2) => (Number.isFinite(n) ? n.toFixed(d) : "—");
function makeScene() {
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(0x101e1d, 1);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    $("scene").appendChild(renderer.domElement);
    scene = new THREE.Scene();
    scene.fog = new THREE.Fog(0x101e1d, 10, 23);
    camera = new THREE.PerspectiveCamera(36, 1, 0.1, 60);
    camera.position.set(5, 4.2, 8);
    camera.lookAt(0, 0, 0);
    orbit = new OrbitControls(camera, renderer.domElement);
    orbit.target.set(0, 0.1, 0);
    orbit.enableDamping = true;
    orbit.enablePan = false;
    orbit.minDistance = 5;
    orbit.maxDistance = 15;
    orbit.maxPolarAngle = Math.PI / 2.05;
    scene.add(new THREE.AmbientLight(0xdfead1, 2.2));
    let light = new THREE.DirectionalLight(0xfff5d7, 3);
    light.position.set(-3, 7, 5);
    scene.add(light);
    let fill = new THREE.DirectionalLight(0x83c2bb, 2);
    fill.position.set(4, 2, -4);
    scene.add(fill);
    const grid = new THREE.GridHelper(18, 36, 0x3a5044, 0x263b32);
    grid.position.y = -0.58;
    scene.add(grid);
    const bar = new THREE.Group();
    scene.add(bar);
    for (let i = 0; i < 100; i++) {
      const mesh = new THREE.Mesh(
        new THREE.BoxGeometry(0.0605, 0.27, 0.4),
        new THREE.MeshStandardMaterial({
          color: 0x648776,
          metalness: 0.35,
          roughness: 0.42,
        }),
      );
      mesh.position.set(-3 + (i + 0.5) * 0.06, 0.05, 0);
      bar.add(mesh);
      segments.push(mesh);
    }
    const edges = new THREE.LineSegments(
      new THREE.EdgesGeometry(new THREE.BoxGeometry(6, 0.28, 0.41)),
      new THREE.LineBasicMaterial({
        color: 0xe1e8b4,
        transparent: true,
        opacity: 0.3,
      }),
    );
    edges.position.y = 0.05;
    scene.add(edges);
    for (const x of [-2.25, 2.25]) {
      const support = new THREE.Mesh(
        new THREE.BoxGeometry(0.36, 0.45, 0.7),
        new THREE.MeshStandardMaterial({ color: 0x344641, roughness: 0.85 }),
      );
      support.position.set(x, -0.31, 0);
      scene.add(support);
    }
    const heater = new THREE.Mesh(
      new THREE.BoxGeometry(0.28, 0.48, 0.61),
      new THREE.MeshStandardMaterial({
        color: 0xab6244,
        metalness: 0.7,
        roughness: 0.4,
      }),
    );
    heater.position.set(-3.15, 0.05, 0);
    scene.add(heater);
    for (let i = 0; i < 8; i++) {
      const x = -3 + ((i / 7) * 0.46 + 0.02) * 12;
      const g = new THREE.Group();
      g.position.set(x, 0.24, 0);
      const head = new THREE.Mesh(
        new THREE.SphereGeometry(0.048, 12, 12),
        new THREE.MeshStandardMaterial({
          color: 0xe4edb8,
          emissive: 0x637044,
          emissiveIntensity: 0.4,
        }),
      );
      g.add(head);
      const wire = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(0, 0, 0),
        new THREE.Vector3(0, 0.35, 0),
        new THREE.Vector3(0.04, 0.48, -0.34),
      ]);
      g.add(
        new THREE.Line(
          wire,
          new THREE.LineBasicMaterial({
            color: 0xa8bc92,
            transparent: true,
            opacity: 0.6,
          }),
        ),
      );
      const labelCanvas = document.createElement("canvas");
      labelCanvas.width = 128;
      labelCanvas.height = 64;
      const ctx = labelCanvas.getContext("2d");
      ctx.fillStyle = "#b5c7ae";
      ctx.font = "24px monospace";
      ctx.textAlign = "center";
      ctx.fillText("S" + (i + 1), 64, 35);
      const texture = new THREE.CanvasTexture(labelCanvas);
      const sprite = new THREE.Sprite(
        new THREE.SpriteMaterial({ map: texture, transparent: true }),
      );
      sprite.position.set(0.04, 0.62, -0.34);
      sprite.scale.set(0.5, 0.25, 1);
      g.add(sprite);
      scene.add(g);
      sensorMeshes.push(g);
    }
    const resize = () => {
      const b = $("scene").getBoundingClientRect();
      renderer.setSize(b.width, b.height);
      camera.aspect = b.width / b.height;
      camera.updateProjectionMatrix();
    };
    new ResizeObserver(resize).observe($("scene"));
    resize();
    $("reset-camera").onclick = () => {
      camera.position.set(5, 4.2, 8);
      orbit.target.set(0, 0.1, 0);
      orbit.update();
    };
  } catch (err) {
    $("scene").insertAdjacentHTML(
      "beforeend",
      '<svg id="thermal-fallback" viewBox="0 0 800 340" role="img" aria-label="Two-dimensional temperature field; WebGL is unavailable in this browser" style="width:100%;height:100%"></svg>',
    );
    $("reset-camera").disabled = true;
    $("scene").querySelector(".scene-caption").textContent =
      "2D THERMAL VIEW · WEBGL UNAVAILABLE IN THIS BROWSER";
  }
  requestAnimationFrame(frame);
}
function frame(now) {
  requestAnimationFrame(frame);
  if (state.playing && now - lastFrame > 110) {
    state.index = (state.index + 1) % state.field.time_s.length;
    lastFrame = now;
    update();
  }
  if (renderer && scene && camera) {
    orbit.update();
    renderer.render(scene, camera);
  }
}
function interp(xs, ys, x) {
  let i = xs.findIndex((v) => v >= x);
  if (i <= 0) return ys[0];
  const p = (x - xs[i - 1]) / (xs[i] - xs[i - 1]);
  return ys[i - 1] * (1 - p) + ys[i] * p;
}
function update() {
  if (!state.field) return;
  const f = state.field;
  state.index = Math.min(state.index, f.time_s.length - 1);
  const predicted =
    state.mode === "benchmark" && $("scene-source").value === "prediction";
  const temps =
    (predicted ? f.predictions_C?.[state.selected]?.[state.index] : null) ||
    f.truth_C[state.index];
  $("scene-source").disabled = state.mode !== "benchmark";
  $("scene-status").textContent =
    state.mode === "benchmark"
      ? `${f.run_id} · 3D: ${predicted ? state.selected : "synthetic reference"}`
      : "Exploratory forward simulation";
  $("time").max = f.time_s.length - 1;
  $("time").value = state.index;
  $("time-value").textContent = fmt(f.time_s[state.index], 0) + " s";
  segments.forEach((m, i) =>
    m.material.color.copy(heat(interp(f.x_m, temps, ((i + 0.5) / 100) * 0.5))),
  );
  const xs =
    f.sensor_x_m || Array.from({ length: 8 }, (_, i) => 0.02 + (i * 0.46) / 7);
  const fallback = $("thermal-fallback");
  if (fallback) {
    const length = f.x_m.at(-1);
    fallback.innerHTML =
      Array.from(
        { length: 100 },
        (_, i) =>
          `<rect x="${70 + i * 6.6}" y="165" width="6.8" height="35" fill="#${heat(interp(f.x_m, temps, ((i + 0.5) / 100) * length)).getHexString()}"/>`,
      ).join("") +
      xs
        .map(
          (x, i) =>
            `<line x1="${70 + (x / length) * 660}" y1="145" x2="${70 + (x / length) * 660}" y2="178" stroke="#d4dfbf"/><circle cx="${70 + (x / length) * 660}" cy="180" r="3" fill="#e7edd5"/><text x="${70 + (x / length) * 660}" y="135" text-anchor="middle" fill="#d4dfbf" font-size="12">S${i + 1}</text>`,
        )
        .join("") +
      '<text x="400" y="255" text-anchor="middle" fill="#a8bba8" font-size="13">Temperature colours follow the selected field and time.</text>';
  }
  sensorMeshes.forEach((g, i) => {
    g.visible = i < xs.length;
    if (i < xs.length) g.position.x = -3 + xs[i] * 12;
  });
  $("sensors").innerHTML = xs
    .map((x, i) => {
      const v = f.sensor_C?.[state.index]?.[i] ?? interp(f.x_m, temps, x);
      return `<div class="sensor" style="--heat:#${heat(v).getHexString()}"><span>S${i + 1}</span><strong>${fmt(v, 1)}<small> °C</small></strong><small>${fmt(x, 3)} m</small></div>`;
    })
    .join("");
  drawProfile();
}
$("scene-source").onchange = update;
function drawProfile() {
  const f = state.field,
    truth = f.truth_C[state.index],
    pred =
      state.mode === "benchmark"
        ? f.predictions_C?.[state.selected]?.[state.index]
        : null;
  const ymin = Math.min(20, ...truth, ...(pred || [])) - 2,
    ymax = Math.max(90, ...truth, ...(pred || [])) + 2;
  const X = (x) => 48 + (x / 0.5) * 610,
    Y = (y) => 211 - ((y - ymin) / (ymax - ymin)) * 185;
  let svg = "";
  for (let y = 20; y <= ymax; y += 20)
    svg += `<line x1="48" y1="${Y(y)}" x2="658" y2="${Y(y)}" stroke="#e2e5db"/><text x="35" y="${Y(y) + 3}" text-anchor="end" fill="#67756b" font-size="10">${y}</text>`;
  for (let x = 0; x <= 0.501; x += 0.1)
    svg += `<text x="${X(x)}" y="232" text-anchor="middle" fill="#67756b" font-size="10">${x.toFixed(1)}</text>`;
  const path = (arr) =>
    arr.map((v, i) => (i ? "L" : "M") + X(f.x_m[i]) + "," + Y(v)).join(" ");
  svg += `<path d="${path(truth)}" fill="none" stroke="#476f5e" stroke-width="2.5"/>`;
  if (pred)
    svg += `<path d="${path(pred)}" fill="none" stroke="#bf7249" stroke-width="2" stroke-dasharray="5 3"/>`;
  for (let i = 0; i < (f.sensor_x_m || []).length; i++) {
    const x = f.sensor_x_m[i],
      v = f.sensor_C?.[state.index]?.[i] ?? interp(f.x_m, truth, x);
    svg += `<circle cx="${X(x)}" cy="${Y(v)}" r="3.5" fill="#fffef9" stroke="#476f5e" stroke-width="1.5"/>`;
  }
  $("profile").innerHTML = svg;
}
function loadBenchmark(result) {
  state.result = result;
  $("solver-label").textContent = "ARCHIVED BENCHMARK · PYTHON / BDF";
  $("field-view").value = "hybrid";
  state.field = result.field;
  state.mode = "benchmark";
  const group = result.selection.selected;
  const selected = result.results.find(
    (r) => `${r.method}-${r.model}` === group,
  );
  state.selected = selected.id;
  $("scenario").value = result.config.scenario;
  $("scenario-description").textContent = descriptions[result.config.scenario];
  $("alpha").value = result.config.alpha / 1e-4;
  $("beta").value = result.config.beta;
  $("heater").value = result.field.amplitude_C;
  $("alpha").oninput();
  document.querySelectorAll(".download-row a").forEach((a) => {
    const artifact =
      a.dataset.artifact || new URL(a.href).pathname.split("/").pop();
    a.dataset.artifact = artifact;
    if (STATIC_MODE) {
      a.href = `/experiments/${result.artifact_id}/${artifact}`;
      return;
    }
    const url = new URL(
      `/api/download/${artifact}`,
      API_ORIGIN || location.origin,
    );
    if (result.artifact_id) url.searchParams.set("run", result.artifact_id);
    a.href = url.href;
  });
  $("best-model").textContent = group;
  $("best-rmse").textContent = fmt(
    result.results
      .filter((r) => `${r.method}-${r.model}` === group)
      .reduce((s, r) => s + r.test.rmse_C, 0) /
      result.results.filter((r) => `${r.method}-${r.model}` === group).length,
    3,
  );
  $("prediction-label").textContent = selected.id;
  $("mode-label").textContent = "BENCHMARK · HELD-OUT EXPERIMENT";
  $("off-label").textContent = `Switch-off at ${fmt(result.field.off_s, 0)} s`;
  $("scene-status").textContent =
    `${result.field.run_id} · Seed ${result.config.seed} · Synthetic reference`;
  $("sensor-state").textContent = "SYNTHETIC + NOISE";
  $("result-rows").innerHTML = result.results
    .map(
      (r) =>
        `<tr><td>${r.id}</td><td>${fmt(r.validation.rmse_C, 3)} °C</td><td>${fmt(r.test.rmse_C, 3)} °C</td><td>${fmt(r.test.mae_C, 3)} °C</td><td>${fmt(r.elapsed_s, 1)} s</td><td><button data-model="${r.id}" class="${r.id === state.selected ? "selected" : ""}">Profile ↗</button></td></tr>`,
    )
    .join("");
  $("result-rows")
    .querySelectorAll("button")
    .forEach(
      (b) =>
        (b.onclick = () => {
          state.field = state.result.field;
          state.mode = "benchmark";
          state.selected = b.dataset.model;
          $("prediction-label").textContent = state.selected;
          $("mode-label").textContent = "BENCHMARK · HELD-OUT EXPERIMENT";
          $("sensor-state").textContent = "SYNTHETIC + NOISE";
          $("off-label").textContent =
            `Switch-off at ${fmt(state.field.off_s, 0)} s`;
          $("scene-status").textContent =
            `${state.field.run_id} · ${state.selected} · Synthetic reference`;
          $("result-rows")
            .querySelectorAll("button")
            .forEach((x) => x.classList.toggle("selected", x === b));
          update();
        }),
    );
  renderDiagnostics(result, (id, mode) => {
    state.field = state.result.field;
    state.mode = "benchmark";
    state.selected = mode === "direct" ? id + "-direct" : id;
    $("prediction-label").textContent =
      id +
      (mode === "direct"
        ? " · direct neural"
        : " · inferred parameters + solver");
    $("scene-status").textContent =
      `${result.field.run_id} · ${mode === "direct" ? "Direct neural reconstruction selected" : "Learned coefficients + forward solver"}`;
    update();
  });
  update();
}
async function api(url, options) {
  if (STATIC_MODE) return staticApi(url, options);
  const res = await fetch(API_ORIGIN + url, options);
  if (!res.ok) {
    let error;
    try {
      error = await res.json();
    } catch {
      error = { detail: res.statusText };
    }
    throw new Error(
      typeof error.detail === "string"
        ? error.detail
        : JSON.stringify(error.detail),
    );
  }
  return res.json();
}
async function simulate() {
  const button = $("simulate");
  button.disabled = true;
  $("scene-status").textContent = "Computing the temperature field…";
  try {
    const f = await api("/api/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        scenario: $("scenario").value,
        alpha: Number($("alpha").value) * 1e-4,
        beta: Number($("beta").value),
        amplitude: Number($("heater").value),
        off: 230,
      }),
    });
    state.mode = "exploration";
    $("solver-label").textContent = STATIC_MODE
      ? "BROWSER SOLVER · RK4"
      : "CONSERVATIVE SOLVER · BDF";
    state.field = {
      x_m: f.x_m,
      time_s: f.time_s,
      truth_C: f.temperature_C,
      sensor_x_m: Array.from({ length: 8 }, (_, i) => 0.02 + (i * 0.46) / 7),
    };
    $("mode-label").textContent = "EXPLORATION · FORWARD SOLVER";
    $("scene-status").textContent =
      "New forward simulation · The trained benchmark is unchanged";
    $("prediction-label").textContent = "No trained model";
    $("sensor-state").textContent = "SOLVER · NO NOISE";
    $("off-label").textContent = "Switch-off at 230 s";
    update();
  } catch (e) {
    $("scene-status").textContent = "Error: " + e.message;
  } finally {
    button.disabled = false;
  }
}
$("simulate").onclick = simulate;
$("restore").onclick = () => {
  if (state.result) loadBenchmark(state.result);
  else
    $("scene-status").textContent =
      "Run a benchmark in the Results section first.";
};
$("time").oninput = (e) => {
  state.index = Number(e.target.value);
  update();
};
$("play").onclick = () => {
  if (!state.field) return;
  state.playing = !state.playing;
  $("play").textContent = state.playing ? "Ⅱ" : "▶";
  $("play").setAttribute(
    "aria-label",
    state.playing ? "Pause thermal evolution" : "Play thermal evolution",
  );
};
for (const id of ["alpha", "beta", "heater"])
  $(id).oninput = () => {
    $("alpha-value").textContent =
      Number($("alpha").value).toFixed(2) + " × 10⁻⁴";
    $("beta-value").textContent = Number($("beta").value).toFixed(3) + " s⁻¹";
    $("heater-value").textContent = $("heater").value + " °C";
  };
const descriptions = {
  uniform: "Constant diffusivity and heat loss along the bar.",
  local_loss: "Localized heat loss around x = 0.20 m.",
  variable_alpha:
    "Spatial diffusivity with a positive quadratic parameterization.",
  temperature_alpha:
    "Positive diffusivity that changes with local temperature.",
};
$("scenario").onchange = () => {
  $("scenario-description").textContent = descriptions[$("scenario").value];
};
$("run").onclick = async () => {
  if (STATIC_MODE) {
    const config =
      $("training-preset").value === "advanced" ? "advanced-demo" : "demo";
    $("training-command").textContent =
      `.venv/bin/python main-2.py run --config configs/${config}.json --output results/my-${config}`;
    $("local-training").showModal();
    return;
  }
  const b = $("run");
  b.disabled = true;
  $("job-status").textContent = "Starting reproducible training…";
  try {
    const job = await api("/api/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ preset: $("training-preset").value }),
    });
    const poll = async () => {
      try {
        const j = await api("/api/jobs/" + job.id);
        $("job-status").textContent = j.message;
        if (j.status === "completed") {
          loadBenchmark(j.result);
          refreshExperiments();
          b.disabled = false;
        } else if (j.status === "failed") {
          b.disabled = false;
        } else setTimeout(poll, 1800);
      } catch (e) {
        $("job-status").textContent = "Connection interrupted: " + e.message;
        b.disabled = false;
      }
    };
    poll();
  } catch (e) {
    $("job-status").textContent = e.message;
    b.disabled = false;
  }
};
$("experiment-picker").onchange = async () => {
  try {
    loadBenchmark(
      await api(
        "/api/results?run=" + encodeURIComponent($("experiment-picker").value),
      ),
    );
  } catch (e) {
    $("job-status").textContent = e.message;
  }
};
async function refreshExperiments() {
  const list = await api("/api/experiments");
  $("experiment-picker").innerHTML = list
    .map(
      (r) =>
        `<option value="${r.id}">${r.id} · ${r.scenario} · ${r.seeds} seed</option>`,
    )
    .join("");
  if (state.result?.artifact_id)
    $("experiment-picker").value = state.result.artifact_id;
}
$("api-link").href = STATIC_MODE ? "/reproduce.html" : API_ORIGIN + "/docs";
if (STATIC_MODE) {
  $("api-link").textContent = "Reproduce locally ↗";
  $("run").textContent = "Train on your laptop ↗";
  $("training-hint").textContent =
    "Archived results are ready to explore. New PINN training runs locally with the downloadable Python kit.";
  $("execution-note").hidden = false;
}
$("close-training").onclick = () => $("local-training").close();
makeScene();
try {
  const run = new URLSearchParams(location.search).get("run");
  loadBenchmark(
    await api("/api/results" + (run ? "?run=" + encodeURIComponent(run) : "")),
  );
} catch (e) {
  $("job-status").textContent = STATIC_MODE
    ? "The archive could not be loaded. Forward simulation is still available; reload to retry."
    : "No saved benchmark. Select Reproduce benchmark to begin.";
  await simulate();
}

refreshExperiments().catch((e) => {
  $("job-status").textContent = e.message;
});
