// Packages the Pyodide code runner installs before running an example.
// Native dependencies comrak and selectolax are served as WebAssembly wheels
// directly from docs assets to satisfy micropip in the browser environment.
window.pyodide_run_deps = [
  new URL("assets/pyodide-wheels/comrak-0.0.16-cp314-abi3-pyemscripten_2026_0_wasm32.whl", document.baseURI).href,
  new URL("assets/pyodide-wheels/selectolax-1.0.2-cp314-cp314-pyemscripten_2026_0_wasm32.whl", document.baseURI).href,
  "md2linkedin",
];
