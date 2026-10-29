import { solveBrowser } from "./browser-solver.js";
self.onmessage = ({ data }) => {
  try {
    self.postMessage({ result: solveBrowser(data) });
  } catch (error) {
    self.postMessage({ error: error.message });
  }
};
