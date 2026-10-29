const $ = (id) => document.getElementById(id);
const esc = (value) =>
  String(value).replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const num = (v, d = 3) => (Number.isFinite(v) ? v.toFixed(d) : "Not recorded");
function linePlot(
  id,
  series,
  { log = false, xLabel = "", yLabel = "", scientific = false } = {},
) {
  const valid = series.filter((s) => s.y?.length && s.x?.length);
  if (!valid.length) {
    $(id).innerHTML =
      '<text x="35" y="110" fill="#62726b" font-size="13">Not recorded in this archived experiment.</text>';
    return;
  }
  const transform = (v) => (log ? Math.log10(Math.max(v, 1e-14)) : v);
  const xs = valid.flatMap((s) => s.x),
    ys = valid.flatMap((s) => s.y.map(transform));
  let xmin = Math.min(...xs),
    xmax = Math.max(...xs),
    ymin = Math.min(...ys),
    ymax = Math.max(...ys);
  if (ymax - ymin < 1e-12) {
    ymin -= Math.max(Math.abs(ymin) * 0.1, 1e-6);
    ymax += Math.max(Math.abs(ymax) * 0.1, 1e-6);
  }
  if (xmax === xmin) xmax = xmin + 1;
  const X = (x) => 65 + ((x - xmin) / (xmax - xmin)) * 535,
    Y = (y) => 191 - ((y - ymin) / (ymax - ymin)) * 155;
  let svg = `<text x="65" y="17" fill="#62726b" font-size="9">${esc(yLabel)}</text>`;
  for (let i = 0; i < 5; i++) {
    const v = ymin + ((ymax - ymin) * i) / 4;
    svg += `<line x1="65" y1="${Y(v)}" x2="600" y2="${Y(v)}" stroke="#e0e4d8"/><text x="57" y="${Y(v) + 3}" text-anchor="end" fill="#62726b" font-size="9">${log ? "10^" + v.toFixed(1) : scientific ? v.toExponential(1) : v.toFixed(2)}</text>`;
    const x = xmin + ((xmax - xmin) * i) / 4;
    svg += `<text x="${X(x)}" y="208" text-anchor="middle" fill="#62726b" font-size="9">${xmax > 10 ? x.toFixed(0) : x.toFixed(2)}</text>`;
  }
  for (const s of valid) {
    svg += `<path d="${s.y.map((v, i) => (i ? "L" : "M") + X(s.x[i]) + "," + Y(transform(v))).join(" ")}" fill="none" stroke="${s.color}" stroke-width="2" ${s.dash ? 'stroke-dasharray="5 4"' : ""}/>`;
  }
  svg += `<text x="320" y="226" text-anchor="middle" fill="#62726b" font-size="9">${esc(xLabel)}</text>`;
  $(id).innerHTML = svg;
}
function heatmap(map) {
  if (!map) {
    $("residual-chart").innerHTML =
      '<text x="35" y="110" fill="#62726b" font-size="13">Residual map not recorded in this legacy run.</text>';
    $("residual-caption").textContent =
      "Select a research-edition experiment to inspect the independent residual grid.";
    return;
  }
  const values = map.values,
    max = Math.max(...values.flat().map(Math.abs), 1e-12);
  let svg = "";
  const w = 520 / values[0].length,
    h = 160 / values.length;
  values.forEach((row, j) =>
    row.forEach((v, i) => {
      const p = Math.log1p((Math.abs(v) / max) * 99) / Math.log(100);
      const color = `rgb(${Math.round(237 - p * 72)},${Math.round(240 - p * 141)},${Math.round(230 - p * 172)})`;
      svg += `<rect x="${60 + i * w}" y="${25 + j * h}" width="${w + 0.2}" height="${h + 0.2}" fill="${color}"><title>x ${num(map.x_m[i])} m, t ${num(map.time_s[j], 0)} s: residual ${num(v, 5)}</title></rect>`;
    }),
  );
  svg +=
    '<text x="60" y="208" font-size="10" fill="#62726b">0 m</text>' +
    `<text x="580" y="208" text-anchor="end" font-size="10" fill="#62726b">${num(map.x_m.at(-1), 2)} m</text><text x="52" y="30" text-anchor="end" font-size="9" fill="#62726b">0 s</text><text x="52" y="185" text-anchor="end" font-size="9" fill="#62726b">${num(map.time_s.at(-1), 0)} s</text>`;
  $("residual-chart").innerHTML = svg;
  $("residual-caption").textContent =
    `Independent 41 × 41 grid on the displayed test protocol. Darker means larger |r|; logarithmic colour scale, maximum ${max.toExponential(2)}. The field is not reused for training.`;
}
export function renderDiagnostics(result, onSelect) {
  const rows = result.results.filter((r) => r.method === "PINN");
  const directRows = rows.filter((r) => r.direct_sensor_test);
  if (directRows.length) {
    const values = directRows.map((r) => r.direct_sensor_test.rmse_C);
    const mean = values.reduce((a, b) => a + b, 0) / values.length;
    const sd =
      values.length > 1
        ? Math.sqrt(
            values.reduce((a, b) => a + (b - mean) ** 2, 0) /
              (values.length - 1),
          )
        : null;
    $("neural-aggregate").textContent =
      `All ${values.length} PINN runs · direct test RMSE ${num(mean)} °C mean${sd === null ? "" : ` · ${num(sd)} °C seed SD`}. Individual runs are shown below. Seed spread is not calibrated measurement uncertainty.`;
  } else
    $("neural-aggregate").textContent =
      "Legacy experiment: direct sensor aggregates were not recorded.";
  const picker = $("diagnostic-model");
  picker.replaceChildren(
    ...rows.map((r) => {
      const o = document.createElement("option");
      o.value = r.id;
      o.textContent = r.id;
      return o;
    }),
  );
  const first =
    rows.find((r) => `${r.method}-${r.model}` === result.selection.selected) ||
    rows[0];
  if (!first) {
    $("diagnostic-summary").textContent = "No neural model recorded.";
    return;
  }
  picker.value = first.id;
  function render() {
    const row = rows.find((r) => r.id === picker.value);
    const history = result.histories[row.id] || [];
    const direct = row.direct_sensor_test || row.direct_network_field;
    const audit = row.constraint_audit;
    $("diagnostic-summary").innerHTML = [
      [
        "DIRECT NEURAL RMSE",
        num(direct?.rmse_C),
        row.direct_sensor_test
          ? "°C · held-out sensors"
          : "°C · first test field",
      ],
      ["PARAMETERS → SOLVER", num(row.test.rmse_C), "°C · held-out sensors"],
      [
        "INDEPENDENT PDE RMS",
        row.pde_rms_dimensionless?.toExponential(2) || "Not recorded",
        "dimensionless residual",
      ],
      [
        "BOUNDARY CONSTRAINTS",
        audit && result.config.boundary_mode === "hard"
          ? "Exact"
          : "Soft penalty",
        audit
          ? `max left error ${audit.left_max_error_C.toExponential(1)} °C`
          : "Legacy training formulation",
      ],
    ]
      .map(
        ([label, value, note]) =>
          `<div><span>${label}</span><strong>${esc(value)}</strong><small>${esc(note)}</small></div>`,
      )
      .join("");
    linePlot(
      "loss-chart",
      ["data", "pde", "ic", "bc"].map((term, i) => ({
        x: history.map((h) => h.epoch),
        y: history.map((h) => h[term]),
        color: ["#3b6755", "#b16b43", "#557baf", "#966b99"][i],
      })),
      {
        log: true,
        xLabel: "Adam epochs / final L-BFGS budget",
        yLabel: "Unweighted loss",
      },
    );
    heatmap(row.residual_map);
    const param = $("parameter-view").value;
    linePlot(
      "parameter-chart",
      [
        { x: result.field.x_m, y: row[param + "_profile"], color: "#b16b43" },
        {
          x: result.field.x_m,
          y: result.field["truth_" + param],
          color: "#476f5e",
          dash: true,
        },
      ],
      {
        xLabel: "Position / m",
        yLabel: param === "alpha" ? "Diffusivity / m² s⁻¹" : "Heat loss / s⁻¹",
        scientific: true,
      },
    );
  }
  picker.onchange = () => {
    render();
    onSelect(picker.value, $("field-view").value);
  };
  $("field-view").onchange = () =>
    onSelect(picker.value, $("field-view").value);
  $("parameter-view").onchange = render;
  render();
  const gates = result.evidence?.gates || [
    {
      label: "Archived numerical benchmark",
      status: "limited",
      detail:
        "Legacy run: advanced constraint audits and residual grids were not recorded.",
    },
    {
      label: "Physical validation",
      status: "pending",
      detail: "All data in this experiment are synthetic.",
    },
  ];
  $("evidence-list").innerHTML = gates
    .map(
      (g) =>
        `<article class="evidence-row"><div><b>${esc(g.label)}</b><span class="evidence-status ${esc(g.status)}">${esc(g.status)}</span></div><p>${esc(g.detail)}</p></article>`,
    )
    .join("");
  const splits = result.manifest.runs;
  const count = (key) => splits.filter((r) => r.split === key).length;
  $("split-summary").textContent =
    `${splits.length} protocols · ${count("train")} train / ${count("validation")} validation / ${count("test")} test`;
  const cfg = result.config;
  const records = {
    Experiment: result.artifact_id || "Local run",
    Selection: result.selection.criterion,
    "Training data hash": result.manifest.sha256,
    Architecture: `${cfg.depth} tanh layers × ${cfg.width} units · ${cfg.boundary_mode || "soft"} boundaries`,
    Sampling: cfg.adaptive_sampling
      ? "Residual-guided + fresh global samples"
      : "Random with thermal-front enrichment",
    "Training budget": `${cfg.epochs} Adam + ${cfg.lbfgs} maximum L-BFGS iterations`,
    Seeds: cfg.seeds.join(", "),
    Environment: `${result.environment.python} · PyTorch ${result.environment.torch} · CPU float64`,
    "Displayed field": `${result.field.run_id}; pooled test metrics may include additional protocols`,
  };
  $("run-record").innerHTML =
    "<dl>" +
    Object.entries(records)
      .map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`)
      .join("") +
    "</dl>";
}
