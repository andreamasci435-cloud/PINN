let archive;
async function read(path) {
  const response = await fetch(path);
  if (!response.ok)
    throw new Error(`Could not load ${path} (${response.status})`);
  return response.json();
}
function simulate(parameters) {
  return new Promise((resolve, reject) => {
    const worker = new Worker(new URL("./solver-worker.js", import.meta.url), {
      type: "module",
    });
    const timer = setTimeout(() => {
      worker.terminate();
      reject(
        new Error("Simulation timed out. Please retry on a faster device."),
      );
    }, 60000);
    const done = () => {
      clearTimeout(timer);
      worker.terminate();
    };
    worker.onmessage = ({ data }) => {
      done();
      data.error ? reject(new Error(data.error)) : resolve(data.result);
    };
    worker.onerror = () => {
      done();
      reject(
        new Error(
          "Browser simulation could not start. Reload the page and try again.",
        ),
      );
    };
    worker.postMessage(parameters);
  });
}
export async function staticApi(path, options) {
  const url = new URL(path, location.origin);
  if (url.pathname === "/api/simulate")
    return simulate(JSON.parse(options.body));
  archive ||= read("/experiments/index.json");
  const list = await archive;
  if (url.pathname === "/api/experiments") return list;
  if (url.pathname === "/api/results") {
    const id = url.searchParams.get("run") || list[0]?.id;
    if (!list.some((r) => r.id === id))
      throw new Error("Archived experiment unavailable");
    const data = await read(`/experiments/${id}/results.json`);
    return { ...data, artifact_id: id };
  }
  throw new Error(
    "New PINN training is available in the downloadable local Python project.",
  );
}
