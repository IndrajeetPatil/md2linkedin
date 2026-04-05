// Configure dependencies for Pyodide code runner
// Note: pytest is already available in Pyodide, only install md2linkedin
window.pyodide_run_deps = ["md2linkedin"];

// Log debug info about code blocks after DOM is ready
document.addEventListener("DOMContentLoaded", function () {
  console.log(
    "DOM loaded, code blocks found:",
    document.querySelectorAll(".language-py, .language-python").length
  );
});
