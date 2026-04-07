# ══════════════════════════════════════════════════════════════════════════════
# md2linkedin – Shiny Web App
# Beautiful UI for converting Markdown to LinkedIn-ready text.
# ══════════════════════════════════════════════════════════════════════════════

library(shiny)

source(file.path(dirname(sys.frame(1L)$ofile %||% "."), "main.R"), local = TRUE)

# Null-coalescing (in case main.R didn't define it)
if (!exists("%||%")) `%||%` <- function(x, y) if (is.null(x)) y else x

# Register docs/assets as a static resource path for logo.png and favicon.ico
local({
  app_dir <- tryCatch(dirname(sys.frame(1L)$ofile), error = function(e) getwd())
  assets_dir <- normalizePath(file.path(app_dir, "..", "docs", "assets"), mustWork = FALSE)
  if (dir.exists(assets_dir)) {
    shiny::addResourcePath("assets", assets_dir)
  }
})

# ── CSS ───────────────────────────────────────────────────────────────────────
app_css <- "
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  /* ── OKLCH Color System (Dark) ────────────────────── */
  --bg-base:          oklch(0.10 0.02 270);
  --bg-panel:         oklch(0.14 0.02 270);
  --bg-surface:       oklch(0.18 0.02 270);
  --bg-surface-hover: oklch(0.22 0.02 270);
  --border:           oklch(0.30 0.01 270);
  --border-focus:     oklch(0.55 0.18 270);
  --text-1:           oklch(0.93 0.01 270);
  --text-2:           oklch(0.70 0.02 270);
  --text-3:           oklch(0.50 0.02 270);
  --accent:           oklch(0.55 0.22 270);
  --accent-2:         oklch(0.58 0.22 295);
  --success:          oklch(0.65 0.18 160);
  --success-2:        oklch(0.55 0.16 160);
  --danger:           oklch(0.60 0.22 25);
  --warn:             oklch(0.70 0.16 80);
  --radius: 12px;
  --transition: 180ms cubic-bezier(.4,0,.2,1);
}

/* ── Light Theme ─────────────────────────────────────── */
[data-theme='light'] {
  --bg-base:          oklch(0.96 0.005 270);
  --bg-panel:         oklch(0.99 0.002 270);
  --bg-surface:       oklch(0.94 0.005 270);
  --bg-surface-hover: oklch(0.91 0.008 270);
  --border:           oklch(0.85 0.01 270);
  --border-focus:     oklch(0.55 0.18 270);
  --text-1:           oklch(0.20 0.02 270);
  --text-2:           oklch(0.40 0.02 270);
  --text-3:           oklch(0.60 0.02 270);
  --accent:           oklch(0.50 0.24 270);
  --accent-2:         oklch(0.52 0.22 295);
}
[data-theme='light'] body {
  background-image:
    radial-gradient(ellipse 80% 60% at 50% -10%, oklch(0.70 0.12 270 / 0.12) 0%, transparent 60%),
    radial-gradient(ellipse 50% 40% at 80% 100%, oklch(0.70 0.12 295 / 0.08) 0%, transparent 50%);
}
[data-theme='light'] .app-header { background: oklch(0.97 0.005 270 / 0.85); }
[data-theme='light'] .logo-icon { filter: drop-shadow(0 0 6px oklch(0.50 0.24 270 / 0.3)); }
[data-theme='light'] .modal-box { background: oklch(0.97 0.005 270); }
[data-theme='light'] .modal-field input { background: oklch(0.93 0.005 270); }
[data-theme='light'] .toggle-track { background: oklch(0.82 0.01 270); }
[data-theme='light'] .toggle-track::after { background: oklch(0.98 0 0); }
[data-theme='light'] ::-webkit-scrollbar-thumb { background: oklch(0.78 0.01 270); }
[data-theme='light'] ::-webkit-scrollbar-thumb:hover { background: oklch(0.68 0.01 270); }
[data-theme='light'] .credit-sep { color: oklch(0.78 0.01 270); }

html, body { height: 100%; }
body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  background: var(--bg-base);
  background-image:
    radial-gradient(ellipse 80% 60% at 50% -10%, oklch(0.40 0.18 270 / 0.18) 0%, transparent 60%),
    radial-gradient(ellipse 50% 40% at 80% 100%, oklch(0.40 0.18 295 / 0.12) 0%, transparent 50%);
  color: var(--text-1);
  overflow: hidden;
}

.container-fluid { padding: 0 !important; background: var(--bg-base) !important; }

/* ── Header ─────────────────────────────────────────── */
.app-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 28px;
  border-bottom: 1px solid var(--border);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  background: oklch(0.12 0.02 270 / 0.85);
}
.logo { display: flex; align-items: center; gap: 10px; }
.logo-icon {
  width: 28px; height: 28px; object-fit: contain;
  filter: drop-shadow(0 0 6px oklch(0.55 0.22 270 / 0.4));
}
.logo-text {
  font-size: 20px; font-weight: 700; letter-spacing: -0.5px;
  background: linear-gradient(135deg, var(--text-1), var(--text-2));
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.header-options { display: flex; align-items: center; gap: 20px; }
.opt-label {
  display: flex; align-items: center; gap: 8px;
  font-size: 13px; color: var(--text-2); cursor: pointer;
  transition: color var(--transition);
}
.opt-label:hover { color: var(--text-1); }
.toggle-input { display: none; }
.toggle-track {
  width: 36px; height: 20px; border-radius: 10px;
  background: oklch(0.30 0.02 270); position: relative;
  transition: background var(--transition); cursor: pointer;
}
.toggle-track::after {
  content: ''; position: absolute; top: 2px; left: 2px;
  width: 16px; height: 16px; border-radius: 50%;
  background: var(--text-2); transition: all var(--transition);
}
.toggle-input:checked + .toggle-track { background: var(--accent); }
.toggle-input:checked + .toggle-track::after { left: 18px; background: oklch(0.98 0 0); }

/* ── Editor Layout ──────────────────────────────────── */
.editor-wrap {
  display: grid; grid-template-columns: 1fr 1fr; gap: 0;
  height: calc(100vh - 105px);
}
@media (max-width: 768px) {
  .editor-wrap { grid-template-columns: 1fr; grid-template-rows: 1fr 1fr; }
}

.panel {
  display: flex; flex-direction: column;
  border-right: 1px solid var(--border);
  background: var(--bg-panel);
  overflow: hidden;
}
.panel:last-child { border-right: none; }
.panel-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 20px; border-bottom: 1px solid var(--border);
  background: var(--bg-surface);
  min-height: 50px;
}
.panel-title {
  font-size: 13px; font-weight: 600; color: var(--text-2);
  text-transform: uppercase; letter-spacing: 0.6px;
}

/* ── Toolbar ────────────────────────────────────────── */
.toolbar { display: flex; align-items: center; gap: 2px; }
.tool-sep { width: 1px; height: 20px; background: var(--border); margin: 0 6px; }
.tool-btn {
  display: inline-flex; align-items: center; justify-content: center;
  min-width: 32px; height: 32px; padding: 0 8px;
  border: 1px solid transparent; border-radius: 6px;
  background: transparent; color: var(--text-2);
  font-family: 'Inter', sans-serif; font-size: 13px; font-weight: 600;
  cursor: pointer; transition: all var(--transition);
  position: relative; overflow: hidden;
}
.tool-btn::before {
  content: ''; position: absolute; inset: 0;
  background: linear-gradient(135deg, var(--accent), var(--accent-2));
  opacity: 0; transition: opacity var(--transition);
}
.tool-btn:hover {
  color: oklch(0.98 0 0); border-color: oklch(0.55 0.22 270 / 0.3);
  box-shadow: 0 0 12px oklch(0.55 0.22 270 / 0.15);
}
.tool-btn:hover::before { opacity: 0.15; }
.tool-btn:active { transform: scale(0.95); }
.tool-btn i { position: relative; z-index: 1; font-size: 15px; }
.tool-btn span { position: relative; z-index: 1; }
.tool-btn.accent {
  background: linear-gradient(135deg, var(--accent), var(--accent-2));
  color: oklch(0.98 0 0); border: none; padding: 0 14px; gap: 6px;
  box-shadow: 0 2px 12px oklch(0.55 0.22 270 / 0.25);
}
.tool-btn.accent:hover { box-shadow: 0 4px 20px oklch(0.55 0.22 270 / 0.4); }
.tool-btn.accent::before { display: none; }
.tool-btn.success {
  background: linear-gradient(135deg, var(--success), var(--success-2)) !important;
  box-shadow: 0 2px 12px oklch(0.65 0.18 160 / 0.3) !important;
}

/* ── Textarea ───────────────────────────────────────── */
.editor-body { flex: 1; position: relative; overflow: hidden; }
#md_input {
  width: 100%; height: 100%; padding: 20px;
  background: transparent; border: none; outline: none; resize: none;
  font-family: 'JetBrains Mono', monospace; font-size: 14px; line-height: 1.7;
  color: var(--text-1); caret-color: var(--accent);
}
#md_input::placeholder { color: var(--text-3); }
#md_input:focus { background: oklch(0.55 0.22 270 / 0.03); }

/* ── Preview ────────────────────────────────────────── */
.preview-body {
  flex: 1; padding: 20px; overflow-y: auto;
  font-family: 'Inter', sans-serif; font-size: 14.5px; line-height: 1.8;
  color: var(--text-1); white-space: pre-wrap; word-wrap: break-word;
}
.preview-body .placeholder {
  color: var(--text-3); font-style: italic; user-select: none;
}

/* ── Panel Footer ───────────────────────────────────── */
.panel-foot {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 20px; border-top: 1px solid var(--border);
  background: var(--bg-surface);
}
.char-count { font-size: 12px; color: var(--text-3); font-variant-numeric: tabular-nums; }
.char-count.warn { color: var(--warn); }
.char-count.over { color: var(--danger); font-weight: 600; }
.foot-actions { display: flex; gap: 6px; align-items: center; }
.foot-btn {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 5px 12px; border-radius: 6px;
  background: var(--bg-surface-hover); border: 1px solid var(--border);
  color: var(--text-2); font-size: 12px; font-weight: 500;
  cursor: pointer; transition: all var(--transition);
  font-family: 'Inter', sans-serif;
}
.foot-btn:hover { color: var(--text-1); border-color: oklch(0.55 0.22 270 / 0.3); }
.foot-btn i { font-size: 13px; }

/* ── Upload button fix ──────────────────────────────── */
.upload-wrapper {
  position: relative; display: inline-flex; align-items: center;
}
.upload-wrapper input[type='file'],
.upload-wrapper .form-group,
.upload-wrapper .input-group,
.upload-wrapper .btn-file {
  position: absolute !important; width: 1px !important; height: 1px !important;
  padding: 0 !important; margin: -1px !important; overflow: hidden !important;
  clip: rect(0,0,0,0) !important; border: 0 !important; opacity: 0 !important;
}

/* ── Credit Footer ──────────────────────────────────── */
.credit-footer {
  display: flex; align-items: center; justify-content: center;
  padding: 10px 28px;
  background: var(--bg-base);
  border-top: 1px solid var(--border);
  font-size: 12px; color: var(--text-3);
  gap: 4px;
}
.credit-footer a {
  color: var(--text-2); text-decoration: none;
  transition: color var(--transition);
}
.credit-footer a:hover { color: var(--accent); text-decoration: underline; }
.credit-sep { margin: 0 4px; color: oklch(0.35 0.01 270); }

/* ── Link Modal ─────────────────────────────────────── */
.modal-overlay {
  display: none; position: fixed; inset: 0; z-index: 1000;
  background: oklch(0.05 0.02 270 / 0.7); backdrop-filter: blur(4px);
  align-items: center; justify-content: center;
}
.modal-overlay.active { display: flex; }
.modal-box {
  background: oklch(0.16 0.03 270); border: 1px solid var(--border);
  border-radius: 16px; padding: 28px; width: 420px; max-width: 90vw;
  box-shadow: 0 24px 48px oklch(0.05 0.02 270 / 0.5);
  animation: modalIn 200ms ease-out;
}
@keyframes modalIn { from { opacity:0; transform:scale(0.95) translateY(10px); } }
.modal-title { font-size: 16px; font-weight: 600; margin-bottom: 18px; color: var(--text-1); }
.modal-field { margin-bottom: 14px; }
.modal-field label {
  display: block; font-size: 12px; font-weight: 500;
  color: var(--text-2); margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.5px;
}
.modal-field input {
  width: 100%; padding: 10px 14px; border-radius: 8px;
  background: oklch(0.20 0.02 270); border: 1px solid var(--border);
  color: var(--text-1); font-size: 14px; font-family: 'Inter', sans-serif;
  outline: none; transition: border-color var(--transition);
}
.modal-field input:focus { border-color: var(--accent); }
.modal-actions { display: flex; gap: 10px; justify-content: flex-end; margin-top: 20px; }
.modal-btn {
  padding: 8px 20px; border-radius: 8px; font-size: 13px; font-weight: 600;
  cursor: pointer; border: 1px solid var(--border); font-family: 'Inter', sans-serif;
  transition: all var(--transition);
}
.modal-btn.cancel { background: transparent; color: var(--text-2); }
.modal-btn.cancel:hover { color: var(--text-1); }
.modal-btn.confirm {
  background: linear-gradient(135deg, var(--accent), var(--accent-2));
  color: oklch(0.98 0 0); border: none;
}
.modal-btn.confirm:hover { box-shadow: 0 4px 16px oklch(0.55 0.22 270 / 0.35); }

/* ── Scrollbar ──────────────────────────────────────── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: oklch(0.35 0.01 270); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: oklch(0.45 0.01 270); }

/* ── Emoji Picker ──────────────────────────────────── */
#emoji_picker_wrap {
  position: absolute; top: 0; right: 0; z-index: 500;
  padding: 8px;
  animation: modalIn 150ms ease-out;
}
emoji-picker {
  --border-color: var(--border);
  --background: var(--bg-panel);
  --input-border-color: var(--border);
  --input-font-color: var(--text-1);
  --input-placeholder-color: var(--text-3);
  --category-font-color: var(--text-2);
  --indicator-color: var(--accent);
  --outline-color: var(--accent);
  --button-hover-background: var(--bg-surface-hover);
  --num-columns: 8;
  height: 350px;
  border-radius: 12px;
  border: 1px solid var(--border);
  box-shadow: 0 12px 40px oklch(0.05 0.02 270 / 0.5);
}

/* ── Shiny overrides ────────────────────────────────── */
.shiny-file-input-progress { display: none !important; }
.form-group { margin-bottom: 0 !important; }
"

# ── JavaScript ────────────────────────────────────────────────────────────────
app_js <- "
function getTA() { return document.getElementById('md_input'); }

function notifyShiny() {
  var ta = getTA();
  Shiny.setInputValue('md_input', ta.value, {priority:'event'});
}

// Wrap selected text with prefix/suffix
function wrapSelection(prefix, suffix) {
  var ta = getTA(), s = ta.selectionStart, e = ta.selectionEnd;
  var txt = ta.value, sel = txt.substring(s, e);
  var repl = prefix + (sel || 'text') + suffix;
  ta.value = txt.substring(0, s) + repl + txt.substring(e);
  ta.selectionStart = s + prefix.length;
  ta.selectionEnd = s + repl.length - suffix.length;
  ta.focus(); notifyShiny();
}

// Apply combining character to selection
function applyCombining(cp) {
  var ta = getTA(), s = ta.selectionStart, e = ta.selectionEnd;
  if (s === e) return;
  var txt = ta.value, sel = txt.substring(s, e);
  var out = '';
  for (var i = 0; i < sel.length; i++) {
    out += sel[i] + String.fromCodePoint(cp);
  }
  ta.value = txt.substring(0, s) + out + txt.substring(e);
  ta.focus(); notifyShiny();
}

function insertAtLine(prefix) {
  var ta = getTA(), s = ta.selectionStart;
  var txt = ta.value;
  var lineStart = txt.lastIndexOf('\\n', s - 1) + 1;
  ta.value = txt.substring(0, lineStart) + prefix + txt.substring(lineStart);
  ta.selectionStart = ta.selectionEnd = s + prefix.length;
  ta.focus(); notifyShiny();
}

// Link modal
function openLinkModal() {
  var ta = getTA();
  var sel = ta.value.substring(ta.selectionStart, ta.selectionEnd);
  document.getElementById('link_text').value = sel || '';
  document.getElementById('link_url').value = 'https://';
  document.getElementById('link_modal').classList.add('active');
  setTimeout(function(){ document.getElementById('link_url').focus(); }, 100);
}
function closeLinkModal() {
  document.getElementById('link_modal').classList.remove('active');
}
function confirmLink() {
  var text = document.getElementById('link_text').value || 'link';
  var url  = document.getElementById('link_url').value || '';
  closeLinkModal();
  var ta = getTA(), s = ta.selectionStart, e = ta.selectionEnd;
  var md = '[' + text + '](' + url + ')';
  ta.value = ta.value.substring(0, s) + md + ta.value.substring(e);
  ta.focus(); notifyShiny();
}

// Copy to clipboard
function copyOutput() {
  var el = document.getElementById('preview_out');
  if (!el) return;
  navigator.clipboard.writeText(el.textContent).then(function(){
    var btn = document.getElementById('copy_btn');
    btn.classList.add('success');
    btn.innerHTML = '<i class=\"bi bi-check-lg\"></i><span>Copied!</span>';
    setTimeout(function(){
      btn.classList.remove('success');
      btn.innerHTML = '<i class=\"bi bi-clipboard\"></i><span>Copy</span>';
    }, 1800);
  });
}

// Character counts
function updateCounts() {
  var ta = getTA();
  var len = ta.value.length;
  document.getElementById('input_count').textContent = len + ' characters';
}

$(document).on('shiny:connected', function(){
  var ta = getTA();
  if(ta) { ta.addEventListener('input', updateCounts); }
});

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
  if (!e.ctrlKey && !e.metaKey) return;
  if (e.key === 'b') { e.preventDefault(); wrapSelection('**','**'); }
  if (e.key === 'i') { e.preventDefault(); wrapSelection('*','*'); }
  if (e.key === 'u') { e.preventDefault(); applyCombining(0x0332); }
  if (e.key === 'k') { e.preventDefault(); openLinkModal(); }
});

// Enter key in link modal
document.addEventListener('keydown', function(e) {
  if (e.key === 'Enter' && document.getElementById('link_modal').classList.contains('active')) {
    e.preventDefault(); confirmLink();
  }
  if (e.key === 'Escape') closeLinkModal();
});
// Theme toggle
function toggleTheme() {
  var html = document.documentElement;
  var current = html.getAttribute('data-theme');
  var next = current === 'light' ? 'dark' : 'light';
  html.setAttribute('data-theme', next);
  localStorage.setItem('md2li-theme', next);
  updateThemeIcon(next);
}
function updateThemeIcon(theme) {
  var icon = document.getElementById('theme_icon');
  if (!icon) return;
  icon.className = theme === 'light' ? 'bi bi-moon-stars-fill' : 'bi bi-sun-fill';
}
// Load saved theme on start
(function() {
  var saved = localStorage.getItem('md2li-theme');
  if (saved) {
    document.documentElement.setAttribute('data-theme', saved);
    // defer icon update until DOM ready
    document.addEventListener('DOMContentLoaded', function() { updateThemeIcon(saved); });
  }
})();
// Emoji picker
function toggleEmojiPicker() {
  var wrap = document.getElementById('emoji_picker_wrap');
  if (!wrap) return;
  var visible = wrap.style.display !== 'none';
  wrap.style.display = visible ? 'none' : 'block';
}

// Wire up emoji selection once DOM ready
$(document).on('shiny:connected', function() {
  var picker = document.getElementById('emoji_picker');
  if (picker) {
    picker.addEventListener('emoji-click', function(e) {
      var ta = getTA();
      var s = ta.selectionStart, end = ta.selectionEnd;
      var emoji = e.detail.unicode;
      ta.value = ta.value.substring(0, s) + emoji + ta.value.substring(end);
      ta.selectionStart = ta.selectionEnd = s + emoji.length;
      ta.focus();
      notifyShiny();
      updateCounts();
      document.getElementById('emoji_picker_wrap').style.display = 'none';
    });
  }
});

// Close emoji picker on outside click
document.addEventListener('click', function(e) {
  var wrap = document.getElementById('emoji_picker_wrap');
  var btn = document.getElementById('emoji_btn');
  if (!wrap || wrap.style.display === 'none') return;
  if (!wrap.contains(e.target) && !btn.contains(e.target)) {
    wrap.style.display = 'none';
  }
});
"

# ── UI ────────────────────────────────────────────────────────────────────────
ui <- fluidPage(
  tags$head(
    tags$meta(charset = "UTF-8"),
    tags$meta(name = "viewport", content = "width=device-width, initial-scale=1"),
    tags$title("md2linkedin — Markdown to LinkedIn Converter"),
    tags$link(rel = "icon", type = "image/x-icon", href = "assets/favicon.ico"),
    tags$link(rel = "stylesheet", href = "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css"),
    tags$script(type = "module", src = "https://cdn.jsdelivr.net/npm/emoji-picker-element@1/index.js"),
    tags$style(HTML(app_css)),
    tags$script(HTML(app_js))
  ),

  # Header
  div(class = "app-header",
    div(class = "logo",
      tags$img(src = "assets/logo.png", class = "logo-icon", alt = "md2linkedin logo"),
      span(class = "logo-text", "md2linkedin")
    ),
    div(class = "header-options",
      tags$label(class = "opt-label",
        tags$input(type = "checkbox", id = "preserve_links", class = "toggle-input",
                   onclick = "Shiny.setInputValue('preserve_links', this.checked, {priority:'event'})"),
        span(class = "toggle-track"), span("Preserve Links")
      ),
      tags$label(class = "opt-label",
        tags$input(type = "checkbox", id = "monospace_code", class = "toggle-input", checked = "checked",
                   onclick = "Shiny.setInputValue('monospace_code', this.checked, {priority:'event'})"),
        span(class = "toggle-track"), span("Monospace Code")
      ),
      tags$button(class = "tool-btn", id = "theme_toggle",
                  title = "Toggle light/dark theme", onclick = "toggleTheme()",
        tags$i(class = "bi bi-sun-fill", id = "theme_icon")
      )
    )
  ),

  # Editor layout
  div(class = "editor-wrap",

    # ── Left panel: Editor ──
    div(class = "panel",
      div(class = "panel-head",
        span(class = "panel-title", HTML("&#9998; Markdown Editor")),
        div(class = "toolbar",
          tags$button(class = "tool-btn", title = "Bold (Ctrl+B)", onclick = "wrapSelection('**','**')",
            tags$i(class = "bi bi-type-bold")),
          tags$button(class = "tool-btn", title = "Italic (Ctrl+I)", onclick = "wrapSelection('*','*')",
            tags$i(class = "bi bi-type-italic")),
          tags$button(class = "tool-btn", title = "Underline (Ctrl+U)", onclick = "applyCombining(0x0332)",
            tags$i(class = "bi bi-type-underline")),
          tags$button(class = "tool-btn", title = "Strikethrough", onclick = "applyCombining(0x0336)",
            tags$i(class = "bi bi-type-strikethrough")),
          span(class = "tool-sep"),
          tags$button(class = "tool-btn", title = "Hyperlink (Ctrl+K)", onclick = "openLinkModal()",
            tags$i(class = "bi bi-link-45deg")),
          span(class = "tool-sep"),
          tags$button(class = "tool-btn", title = "Heading 1", onclick = "insertAtLine('# ')",
            tags$span("H1")),
          tags$button(class = "tool-btn", title = "Heading 2", onclick = "insertAtLine('## ')",
            tags$span("H2")),
          tags$button(class = "tool-btn", title = "Inline Code", onclick = "wrapSelection('`','`')",
            tags$i(class = "bi bi-code-slash")),
          tags$button(class = "tool-btn", title = "Bullet List", onclick = "insertAtLine('- ')",
            tags$i(class = "bi bi-list-ul")),
          span(class = "tool-sep"),
          tags$button(class = "tool-btn", id = "emoji_btn", title = "Emoji", onclick = "toggleEmojiPicker()",
            tags$i(class = "bi bi-emoji-smile"))
        )
      ),
      div(class = "editor-body",
        div(id = "emoji_picker_wrap", style = "display:none;",
          HTML('<emoji-picker id="emoji_picker"></emoji-picker>')
        ),
        tags$textarea(id = "md_input", placeholder = "Type or paste your Markdown here...\n\nTip: Use the toolbar above or keyboard shortcuts:\n  Ctrl+B  Bold\n  Ctrl+I  Italic\n  Ctrl+U  Underline\n  Ctrl+K  Hyperlink",
                      oninput = "Shiny.setInputValue('md_input', this.value, {priority:'event'})")
      ),
      div(class = "panel-foot",
        span(class = "char-count", id = "input_count", "0 characters"),
        div(class = "foot-actions",
          tags$label(class = "foot-btn", style = "margin:0; cursor:pointer;",
            tags$i(class = "bi bi-upload"), "Upload .md",
            div(class = "upload-wrapper",
              fileInput("file_upload", NULL, accept = c(".md", ".txt", ".markdown"))
            )
          )
        )
      )
    ),

    # ── Right panel: Preview ──
    div(class = "panel",
      div(class = "panel-head",
        span(class = "panel-title", HTML("&#128065; LinkedIn Preview")),
        div(class = "toolbar",
          tags$button(class = "tool-btn accent", id = "copy_btn", title = "Copy to clipboard",
                      onclick = "copyOutput()",
            tags$i(class = "bi bi-clipboard"), tags$span("Copy")),
          downloadButton("download_txt", label = NULL, class = "tool-btn",
                         icon = icon("download", lib = "glyphicon"))
        )
      ),
      div(class = "preview-body",
        uiOutput("preview_ui")
      ),
      div(class = "panel-foot",
        span(class = "char-count", id = "linkedin_count", "0 / 3,000"),
        div()
      )
    )
  ),

  # Credits footer
  div(class = "credit-footer",
    span("Original source code by"),
    tags$a(href = "https://github.com/IndrajeetPatil/md2linkedin", target = "_blank", "Indrajeet Patil"),
    span(class = "credit-sep", "\u00b7"),
    span("R implementation by"),
    tags$a(href = "https://iamyannc.github.io/Yann-dev/", target = "_blank", "Yann Cohen")
  ),

  # ── Link Modal ──
  div(id = "link_modal", class = "modal-overlay",
    div(class = "modal-box",
      div(class = "modal-title", HTML("&#128279; Insert Hyperlink")),
      div(class = "modal-field",
        tags$label(`for` = "link_text", "Display Text"),
        tags$input(type = "text", id = "link_text", placeholder = "Link text")
      ),
      div(class = "modal-field",
        tags$label(`for` = "link_url", "URL"),
        tags$input(type = "url", id = "link_url", placeholder = "https://example.com")
      ),
      div(class = "modal-actions",
        tags$button(class = "modal-btn cancel", onclick = "closeLinkModal()", "Cancel"),
        tags$button(class = "modal-btn confirm", onclick = "confirmLink()", "Insert Link")
      )
    )
  )
)

# ── Server ────────────────────────────────────────────────────────────────────
server <- function(input, output, session) {

  # Debounced markdown input
  md_reactive <- reactive({ input$md_input %||% "" })
  md_debounced <- debounce(md_reactive, 300)

  # Convert
  converted <- reactive({
    txt <- md_debounced()
    if (!nzchar(trimws(txt))) return("")
    convert(
      txt,
      preserve_links  = isTRUE(input$preserve_links),
      monospace_code   = isTRUE(input$monospace_code %||% TRUE)
    )
  })

  # Preview output
  output$preview_ui <- renderUI({
    txt <- converted()
    if (!nzchar(txt)) {
      return(span(class = "placeholder", "Your LinkedIn-ready text will appear here..."))
    }
    tags$div(id = "preview_out", style = "white-space:pre-wrap;", txt)
  })

  # Update LinkedIn character count
  observe({
    txt <- converted()
    n <- nchar(txt)
    cls <- if (n > 3000) "char-count over" else if (n > 2700) "char-count warn" else "char-count"
    session$sendCustomMessage("updateCount", list(
      id = "linkedin_count",
      text = sprintf("%s / 3,000", format(n, big.mark = ",")),
      cls = cls
    ))
  })

  # File upload
  observeEvent(input$file_upload, {
    req(input$file_upload)
    content <- paste(readLines(input$file_upload$datapath, encoding = "UTF-8", warn = FALSE),
                     collapse = "\n")
    session$sendCustomMessage("setTextarea", content)
  })

  # Download handler
  output$download_txt <- downloadHandler(
    filename = function() { "linkedin-post.txt" },
    content = function(file) {
      writeLines(converted(), file, useBytes = TRUE)
    }
  )
}

# ── Custom message handlers (injected at startup) ────────────────────────────
onStart <- function() {
  # Serve docs/assets so logo.png and favicon.ico are accessible
  # Try ofile (when sourced), fall back to working dir (shiny::runApp)
  app_dir <- tryCatch(dirname(sys.frame(1L)$ofile), error = function(e) getwd())
  assets_dir <- normalizePath(file.path(app_dir, "..", "docs", "assets"), mustWork = FALSE)
  if (dir.exists(assets_dir)) {
    shiny::addResourcePath("assets", assets_dir)
  }
}

# Add message handlers via onFlushed
ui2 <- tagList(
  ui,
  tags$script(HTML("
    Shiny.addCustomMessageHandler('updateCount', function(msg) {
      var el = document.getElementById(msg.id);
      if (el) { el.textContent = msg.text; el.className = msg.cls; }
    });
    Shiny.addCustomMessageHandler('setTextarea', function(content) {
      var ta = document.getElementById('md_input');
      if (ta) { ta.value = content; Shiny.setInputValue('md_input', content, {priority:'event'}); }
      updateCounts();
    });
  "))
)

shinyApp(ui = ui2, server = server, onStart = onStart)
