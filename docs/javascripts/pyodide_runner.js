/**
 * Pyodide-based code runner for documentation site.
 * Enables interactive Python code execution in the browser.
 */

class PyodideRunner {
  constructor() {
    this.pyodide = null;
    this.loadPromise = null;
    this.installedPackages = new Set();
  }

  /**
   * Load Pyodide and initialize micropip using native ES module import.
   */
  async loadPyodide() {
    if (this.pyodide) return this.pyodide;
    if (this.loadPromise) return this.loadPromise;

    this.loadPromise = (async () => {
      try {
        const { loadPyodide } = await import(
          "https://cdn.jsdelivr.net/pyodide/v314.0.8/full/pyodide.mjs"
        );
        this.pyodide = await loadPyodide({
          packages: ["micropip"],
        });
        return this.pyodide;
      } catch (error) {
        this.loadPromise = null;
        throw new Error(`Failed to load Pyodide: ${error.message}`);
      }
    })();

    return this.loadPromise;
  }

  /**
   * Install Python packages using micropip.
   */
  async installPackages(packages) {
    const toInstall = packages.filter((pkg) => !this.installedPackages.has(pkg));
    if (toInstall.length === 0) return;

    const pyodide = await this.loadPyodide();
    const micropip = pyodide.pyimport("micropip");

    for (const pkg of toInstall) {
      await micropip.install(pkg);
      this.installedPackages.add(pkg);
    }
  }

  /**
   * Execute Python code and capture stdout/stderr.
   */
  async runCode(code, packages = []) {
    const pyodide = await this.loadPyodide();

    if (packages.length > 0) {
      try {
        await this.installPackages(packages);
      } catch (error) {
        return {
          success: false,
          output: "",
          error: `Failed to install packages: ${error.message}`,
        };
      }
    }

    const decoder = new TextDecoder();
    const output = [];
    const writeHandler = (buffer) => {
      output.push(decoder.decode(buffer, { stream: true }));
      return buffer.length;
    };

    pyodide.setStdout({ write: writeHandler });
    pyodide.setStderr({ write: writeHandler });

    const collect = () => output.join("") + decoder.decode();

    try {
      await pyodide.runPythonAsync(code);
      return {
        success: true,
        output: collect(),
        error: null,
      };
    } catch (error) {
      return {
        success: false,
        output: collect(),
        error: error.message,
      };
    }
  }
}

// Global instance
window.pyodideRunner = new PyodideRunner();

/**
 * Interactive code block handler
 */
class InteractiveCodeBlock {
  constructor(element) {
    this.element = element;
    this.code = this.extractCode();
    element.classList.add("pyodide-enabled");
    this.setupUI();
  }

  extractCode() {
    const codeElement = this.element.querySelector("code");
    if (!codeElement) return "";
    const raw = codeElement.textContent || "";
    return raw
      .split(/\r?\n/)
      .filter((line) => !/^\s*#\s*@pyodide\b/.test(line))
      .join("\n");
  }

  setupUI() {
    const container = document.createElement("div");
    container.className = "pyodide-controls";

    const runButton = document.createElement("button");
    runButton.type = "button";
    runButton.className = "pyodide-run-btn";
    runButton.textContent = "▶ Run";
    runButton.onclick = () => this.runCode();

    const clearButton = document.createElement("button");
    clearButton.type = "button";
    clearButton.className = "pyodide-clear-btn";
    clearButton.textContent = "✕ Clear";
    clearButton.onclick = () => this.clearOutput();
    clearButton.style.display = "none";

    container.appendChild(runButton);
    container.appendChild(clearButton);

    const outputDiv = document.createElement("div");
    outputDiv.className = "pyodide-result";
    outputDiv.style.display = "none";

    this.element.parentNode.insertBefore(container, this.element.nextSibling);
    container.after(outputDiv);

    this.runButton = runButton;
    this.clearButton = clearButton;
    this.container = container;
    this.outputDiv = outputDiv;
  }

  async runCode() {
    this.runButton.disabled = true;
    this.runButton.textContent = "⏳ Running...";

    this.outputDiv.innerHTML =
      '<div class="pyodide-loading">Loading Python environment...</div>';
    this.outputDiv.style.display = "block";

    try {
      const packages = window.pyodide_run_deps || ["md2linkedin"];
      const result = await window.pyodideRunner.runCode(this.code, packages);

      if (result.success) {
        if (result.output) {
          this.outputDiv.innerHTML = `<pre class="pyodide-stdout"><code>${this.escapeHtml(
            result.output.trimEnd()
          )}</code></pre>`;
        } else {
          this.outputDiv.innerHTML =
            '<div class="pyodide-success">✓ Code executed successfully (no output)</div>';
        }
      } else {
        this.outputDiv.innerHTML = `<pre class="pyodide-error"><code>Error: ${this.escapeHtml(
          result.error
        )}</code></pre>`;
      }

      this.clearButton.style.display = "inline-block";
    } catch (error) {
      this.outputDiv.innerHTML = `<pre class="pyodide-error"><code>Failed to execute: ${this.escapeHtml(
        error.message
      )}</code></pre>`;
      this.clearButton.style.display = "inline-block";
    } finally {
      this.runButton.disabled = false;
      this.runButton.textContent = "▶ Run";
    }
  }

  clearOutput() {
    if (this.outputDiv) {
      this.outputDiv.innerHTML = "";
      this.outputDiv.style.display = "none";
    }
    this.clearButton.style.display = "none";
  }

  escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }
}

/**
 * Track processed code blocks to avoid duplicate initialization.
 */
const processedBlocks = new WeakSet();

/**
 * Initialize interactive code blocks.
 */
function initPyodideCodeBlocks() {
  const codeBlocks = document.querySelectorAll(
    ".language-python, .language-py"
  );

  codeBlocks.forEach((block) => {
    const codeElement = block.querySelector("code");
    if (codeElement) {
      const code = codeElement.textContent;
      if (code.includes("# @pyodide") || block.classList.contains("pyodide")) {
        const highlightContainer = block.closest(".highlight");
        if (highlightContainer && !processedBlocks.has(highlightContainer)) {
          processedBlocks.add(highlightContainer);
          new InteractiveCodeBlock(highlightContainer);
        }
      }
    }
  });
}

// Subscribe to Material for MkDocs / Zensical document$ observable for instant navigation
if (typeof document$ !== "undefined") {
  document$.subscribe(() => {
    initPyodideCodeBlocks();
  });
} else if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initPyodideCodeBlocks);
} else {
  initPyodideCodeBlocks();
}
