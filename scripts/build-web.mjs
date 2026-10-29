/** Static by default: no Python, credentials or external service at build/runtime. */
import { cp, mkdir, writeFile, rm, readFile, readdir } from "node:fs/promises";
import { createHash } from "node:crypto";
import { zipSync, strToU8 } from "fflate";
const raw = process.env.CANON_API_URL;
let origin = "";
if (raw) {
  const url = new URL(raw);
  if (
    url.protocol !== "https:" ||
    url.username ||
    url.password ||
    url.pathname !== "/" ||
    url.search ||
    url.hash
  ) {
    throw new Error(
      "CANON_API_URL must be an HTTPS origin without credentials, path, query or fragment.",
    );
  }
  origin = url.origin;
}
await rm("dist", { recursive: true, force: true });
await cp("web", "dist", { recursive: true });
await writeFile(
  "dist/runtime-config.js",
  `window.CANON_API_URL = ${JSON.stringify(origin)};\nwindow.CANON_STATIC = ${!origin};\n`,
);
if (origin) {
  console.log("Optional Python backend mode:", origin);
} else {
  const ids = JSON.parse(await readFile("configs/site-archives.json", "utf8"));
  if (!ids.length || new Set(ids).size !== ids.length)
    throw new Error("Publish a nonempty, unique archive list");
  const index = [];
  const files = [
    "results.json",
    "metrics.csv",
    "benchmark.svg",
    "benchmark.png",
    "config.json",
    "fields.npz",
    "summary.json",
    "protocol.json",
    "artifacts.json",
    "comparison-summary.svg",
    "parameter-stability.svg",
    "training-diagnostics.png",
    "losses.png",
  ];
  for (const id of ids) {
    if (!/^[A-Za-z0-9_-]+$/.test(id)) throw new Error("Invalid archive ID");
    const folder = `results/${id}`;
    const result = JSON.parse(await readFile(`${folder}/results.json`, "utf8"));
    if (result.provenance !== "synthetic")
      throw new Error(
        "Only explicitly approved synthetic experiments may be published",
      );
    if (result.schema_version >= 2) {
      const marker = JSON.parse(
        await readFile(`${folder}/COMPLETE.json`, "utf8"),
      );
      if (marker.status !== "complete")
        throw new Error(`Incomplete experiment: ${id}`);
      const hashes = JSON.parse(
        await readFile(`${folder}/artifacts.json`, "utf8"),
      );
      for (const [file, hash] of Object.entries(hashes)) {
        if (file.includes("/") || file.includes("\\"))
          throw new Error("Invalid artifact name");
        const actual = createHash("sha256")
          .update(await readFile(`${folder}/${file}`))
          .digest("hex");
        if (actual !== hash)
          throw new Error(`Artifact mismatch: ${id}/${file}`);
      }
    }
    const available = await readdir(folder);
    await mkdir(`dist/experiments/${id}`, { recursive: true });
    for (const file of files.filter((f) => available.includes(f)))
      await cp(`${folder}/${file}`, `dist/experiments/${id}/${file}`);
    index.push({
      id,
      scenario: result.config.scenario,
      seeds: result.config.seeds.length,
      edition: result.config.boundary_mode === "hard" ? "advanced" : "original",
    });
  }
  await writeFile("dist/experiments/index.json", JSON.stringify(index));
  const kit = {};
  for (const dir of ["canon", "configs"]) {
    // Deliberate whitelist: no credentials, local measurements, caches or arbitrary repository files.
    for (const entry of await readdir(dir, { withFileTypes: true })) {
      if (entry.isFile() && /\.(py|json)$/.test(entry.name))
        kit[`${dir}/${entry.name}`] = new Uint8Array(
          await readFile(`${dir}/${entry.name}`),
        );
    }
  }
  for (const file of ["main-2.py", "requirements-lock.txt", "LICENSE"])
    kit[file] = new Uint8Array(await readFile(file));
  kit["START-HERE.md"] = strToU8(
    "# Local PINN training\n\nPython 3.12 is required. Create a virtual environment and install requirements-lock.txt.\n\n```sh\npython3.12 -m venv .venv\n.venv/bin/python -m pip install -r requirements-lock.txt\n.venv/bin/python main-2.py run --config configs/demo.json --output results/my-demo\n```\n\nOn Windows use `.venv\\Scripts\\python.exe` instead. For enhanced training, use configs/advanced-demo.json. For five seeds, use configs/advanced.json. Use a new output folder each time. This is the numerical training kit, not a standalone copy of the website. The public site displays archived results; local runs are not uploaded automatically.\n",
  );
  await mkdir("dist/downloads", { recursive: true });
  await writeFile("dist/downloads/python-training-kit.zip", zipSync(kit));
  console.log(
    `Static edition ready: ${index.length} real experiment archives, browser solver and local training kit. No backend required.`,
  );
}
