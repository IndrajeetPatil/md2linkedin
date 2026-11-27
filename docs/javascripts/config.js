// Packages the Pyodide code runner installs before running an example.
// md2linkedin depends on comrak (Rust) and selectolax (C), which have no pure
// Python wheels on PyPI. Load the pre-compiled WebAssembly wheels served by
// linkedin-post-formatter.
window.pyodide_run_deps = [
  "https://www.indrapatil.com/linkedin-post-formatter/wheels/comrak-0.0.16-cp314-abi3-pyemscripten_2026_0_wasm32.whl",
  "https://www.indrapatil.com/linkedin-post-formatter/wheels/selectolax-1.0.2-cp314-cp314-pyemscripten_2026_0_wasm32.whl",
  "https://www.indrapatil.com/linkedin-post-formatter/wheels/md2linkedin-0.6.0-py3-none-any.whl",
];
