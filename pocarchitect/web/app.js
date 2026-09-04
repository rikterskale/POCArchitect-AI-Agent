"use strict";

const state = {
  bootstrap: null,
  sourceMode: "url",
  preparation: null,
  reports: [],
  stream: null,
  activeJobId: null,
  seenEvents: new Set(),
  estimateTimer: null,
  estimateController: null,
  estimateSequence: 0,
  selectionWithinLimit: true,
  runStartedAt: null,
  elapsedTimer: null,
  recoveryTimer: null,
  reportContent: "",
  libraryContent: "",
  selectedReportId: null,
};

const byId = (id) => document.getElementById(id);
const show = (id) => byId(id)?.classList.remove("is-hidden");
const hide = (id) => byId(id)?.classList.add("is-hidden");

function setConnection(status, title = null) {
  const node = byId("connection-status");
  node.dataset.state = status;
  node.querySelector("strong").textContent = title || (status === "ready" ? "Ready" : status === "error" ? "Disconnected" : "Connecting");
  byId("connection-banner").classList.toggle("is-hidden", status !== "error");
}

function toast(message, tone = "info") {
  const node = byId("toast");
  byId("toast-message").textContent = message;
  node.dataset.tone = tone;
  node.classList.remove("is-hidden");
  window.clearTimeout(toast.timer);
  toast.timer = window.setTimeout(() => node.classList.add("is-hidden"), 5500);
}

function errorDetail(body, fallback) {
  if (typeof body?.detail === "string") return body.detail;
  if (Array.isArray(body?.detail)) return body.detail.map((item) => item.msg || "Invalid value").join("; ");
  return fallback;
}

async function api(path, options = {}) {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), options.timeout || 120000);
  if (options.signal) options.signal.addEventListener("abort", () => controller.abort(), { once: true });
  const headers = { Accept: "application/json", ...(options.headers || {}) };
  if (options.body != null) headers["Content-Type"] = "application/json";
  try {
    const response = await fetch(path, { ...options, headers, credentials: "same-origin", signal: controller.signal });
    const contentType = response.headers.get("content-type") || "";
    const body = contentType.includes("application/json") ? await response.json() : null;
    if (!response.ok) {
      if (response.status === 401) throw new Error("This GUI session has expired. Relaunch POCArchitect from the terminal.");
      throw new Error(errorDetail(body, `Request failed (${response.status})`));
    }
    setConnection("ready");
    return body;
  } catch (error) {
    if (error.name === "AbortError") throw new Error("The request did not complete in time. Check the source and try again.");
    if (error instanceof TypeError) setConnection("error");
    throw error;
  } finally {
    window.clearTimeout(timeout);
  }
}

function setInlineError(id, message = "") {
  const node = byId(id);
  node.textContent = message;
  node.classList.toggle("is-hidden", !message);
}

function setButtonBusy(button, busy, busyLabel = "Working…") {
  if (!button.dataset.idleLabel) button.dataset.idleLabel = button.querySelector(".button-label")?.textContent || button.textContent;
  button.classList.toggle("is-busy", busy);
  button.disabled = busy;
  button.setAttribute("aria-busy", String(busy));
  const label = button.querySelector(".button-label");
  if (label) label.textContent = busy ? busyLabel : button.dataset.idleLabel;
}

function focusPanel(id) {
  const node = byId(id);
  node.setAttribute("tabindex", "-1");
  node.focus({ preventScroll: true });
  node.scrollIntoView({ behavior: "smooth", block: "start" });
}

function setView(name, { updateHash = true, focus = false } = {}) {
  const selected = name === "reports" ? "reports" : "analyze";
  document.querySelectorAll(".nav-item").forEach((button) => {
    const active = button.dataset.view === selected;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-selected", String(active));
    button.tabIndex = active ? 0 : -1;
  });
  document.querySelectorAll(".view").forEach((view) => {
    const active = view.id === `view-${selected}`;
    view.classList.toggle("is-active", active);
    view.hidden = !active;
  });
  if (updateHash && window.location.hash !== `#${selected}`) history.replaceState(null, "", `#${selected}`);
  if (selected === "reports") refreshReports({ silent: true });
  if (focus) byId(`tab-${selected}`).focus();
}

function handleTabKeys(event) {
  const tabs = Array.from(document.querySelectorAll(".nav-item"));
  const index = tabs.indexOf(event.currentTarget);
  let next = null;
  if (["ArrowRight", "ArrowDown"].includes(event.key)) next = (index + 1) % tabs.length;
  if (["ArrowLeft", "ArrowUp"].includes(event.key)) next = (index - 1 + tabs.length) % tabs.length;
  if (event.key === "Home") next = 0;
  if (event.key === "End") next = tabs.length - 1;
  if (next == null) return;
  event.preventDefault();
  setView(tabs[next].dataset.view, { focus: true });
}

function setSourceMode(mode) {
  state.sourceMode = mode;
  document.querySelectorAll("[data-source-mode]").forEach((button) => {
    const active = button.dataset.sourceMode === mode;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-pressed", String(active));
  });
  const local = mode === "local";
  byId("source-label").textContent = local ? "Local directory path" : "Repository, package, image, or URL";
  byId("source").placeholder = local ? "/path/to/authorized/source" : "owner/repository or https://…";
  byId("source-hint").textContent = local ? "The backend reads this directory locally; content remains in memory until approval." : "Examples: owner/repository, pypi:package, docker:image, or an HTTP(S) URL.";
  clearSourceError();
}

function clearSourceError() {
  byId("source").closest(".field").classList.remove("is-invalid");
  setInlineError("source-error");
}

function updateProvider({ preserveModel = false } = {}) {
  if (!state.bootstrap) return;
  const provider = byId("provider").value;
  if (!preserveModel) byId("model").value = state.bootstrap.models[provider] || "";
  byId("base-url-field").classList.toggle("is-hidden", provider !== "local");
  const configured = Boolean(state.bootstrap.providers[provider]);
  const label = byId("provider-state");
  const name = byId("provider").selectedOptions[0]?.textContent || provider;
  label.textContent = provider === "local" ? "No cloud key needed. Endpoint connectivity is checked when the run starts." : configured ? "Credential detected in the backend." : "Credential not detected. Run pocarchitect setup, then recheck.";
  label.classList.toggle("provider-ready", configured || provider === "local");
  label.classList.toggle("provider-warning", !configured && provider !== "local");
  byId("provider-readiness-dot").className = `readiness-dot ${configured || provider === "local" ? "is-ready" : "is-warning"}`;
  byId("provider-readiness-name").textContent = provider === "local" ? `${name} needs no cloud key` : configured ? `${name} is ready` : `${name} needs configuration`;
  byId("provider-readiness-copy").textContent = provider === "local" ? "The endpoint remains local; connectivity and the model are checked only after approval." : configured ? "A credential is present. Its value is never sent to this interface." : "Run pocarchitect setup in another terminal. Return here and select Recheck—no GUI restart needed for a newly added key.";
  byId("copy-setup").classList.toggle("is-hidden", configured || provider === "local");
  updateRunAvailability();
}

function preferredProvider(bootstrap) {
  if (bootstrap.providers[bootstrap.default_provider]) return bootstrap.default_provider;
  return ["openai", "xai", "groq"].find((provider) => bootstrap.providers[provider]) || bootstrap.default_provider;
}

function payloadFromForm() {
  const costValue = byId("cost-limit").value;
  return {
    source_mode: state.sourceMode,
    source: byId("source").value.trim(),
    provider: byId("provider").value,
    model: byId("model").value.trim() || null,
    temperature: 0.2,
    base_url: byId("provider").value === "local" ? byId("base-url").value.trim() : null,
    output_dir: byId("output-dir").value.trim() || null,
    risk_level: byId("risk-level").value,
    target_os: byId("target-os").value.trim(),
    include_mitigations: byId("mitigations").checked,
    no_ingest: !byId("ingest").checked,
    max_estimated_cost: costValue === "" ? null : Number(costValue),
    report_format: byId("report-format").value,
    vulnerability_scan: byId("vulnerability-scan").checked,
    diff_previous: byId("diff-previous").checked,
    scaffold: byId("scaffold").checked,
  };
}

function validateForm() {
  clearSourceError();
  setInlineError("form-error");
  const source = byId("source").value.trim();
  let error = "";
  if (!source) error = state.sourceMode === "local" ? "Enter an authorized local directory path." : "Enter a repository, package, image, or source URL.";
  if (!error && state.sourceMode === "url" && source.includes("://")) {
    try {
      const parsed = new URL(source);
      if (!["http:", "https:"].includes(parsed.protocol)) error = "Use an HTTP or HTTPS source URL.";
    } catch (_) { error = "Enter a valid source URL."; }
  }
  if (error) {
    const field = byId("source").closest(".field");
    field.classList.add("is-invalid");
    setInlineError("source-error", error);
    byId("source").focus();
    return false;
  }
  if (!byId("model").value.trim()) {
    setInlineError("form-error", "Select or enter a model before preparing the transfer.");
    byId("model").focus();
    return false;
  }
  return true;
}

function bytes(value) {
  const amount = Number(value) || 0;
  if (amount < 1024) return `${amount} B`;
  if (amount < 1024 * 1024) return `${(amount / 1024).toFixed(1)} KB`;
  return `${(amount / 1024 / 1024).toFixed(1)} MB`;
}

function cost(value) {
  return value == null ? "Unavailable" : `$${Number(value).toFixed(4)}`;
}

function setConfigurationLocked(locked, status = locked ? "Prepared" : "Draft") {
  const form = byId("analysis-form");
  form.classList.toggle("is-locked", locked);
  form.querySelectorAll("input, select, button").forEach((control) => { control.disabled = locked; });
  const badge = form.querySelector(".panel-status");
  badge.textContent = status;
  badge.className = `panel-status${locked ? " is-ready" : ""}`;
}

function setReviewStatus(label, tone = "") {
  const node = byId("review-status");
  node.textContent = label;
  node.className = `panel-status${tone ? ` is-${tone}` : ""}`;
}

function renderMetrics(estimate) {
  byId("metric-files").textContent = Number(estimate.files ?? 0).toLocaleString();
  byId("metric-bytes").textContent = bytes(estimate.total_bytes);
  byId("metric-tokens").textContent = Number(estimate.estimated_tokens ?? 0).toLocaleString();
  byId("metric-cost").textContent = cost(estimate.estimated_cost_usd);
  byId("metric-redactions").textContent = Number(estimate.redaction_count ?? 0).toLocaleString();
  document.querySelectorAll(".review-summary > div").forEach((node) => node.classList.remove("is-updating"));
  state.selectionWithinLimit = estimate.within_cost_limit !== false;
  const notice = byId("cost-notice");
  notice.classList.toggle("is-warning", !state.selectionWithinLimit);
  notice.querySelector("span").textContent = state.selectionWithinLimit ? "✓" : "!";
  notice.querySelector("p").innerHTML = state.selectionWithinLimit ? "<strong>No provider call has been made.</strong> The estimate updates when you change the file selection." : "<strong>The selected payload exceeds your cost limit.</strong> Remove files or start a new analysis with a higher limit.";
  const categories = estimate.redaction_categories || [];
  byId("redaction-detail").textContent = estimate.redaction_count ? `${estimate.redaction_count} match${estimate.redaction_count === 1 ? "" : "es"} removed across: ${categories.join(", ") || "recognized secret patterns"}.` : "No recognized secret patterns found.";
  updateRunAvailability();
}

function renderPreparation(preparation) {
  state.preparation = preparation;
  state.selectionWithinLimit = true;
  hide("review-loading"); hide("review-empty"); hide("run-content"); hide("report-content");
  show("review-content"); show("new-analysis");
  setReviewStatus("Ready", "ready");
  setConfigurationLocked(true);
  const limitValue = byId("cost-limit").value;
  const initialWithinLimit = limitValue === "" || preparation.estimated_cost_usd == null || preparation.estimated_cost_usd <= Number(limitValue);
  renderMetrics({ ...preparation, files: preparation.files.length, within_cost_limit: initialWithinLimit });
  byId("ingestion-label").textContent = String(preparation.ingestion).replaceAll("-", " ");
  byId("approval-provider").textContent = `${preparation.provider}/${preparation.model}`;
  byId("approval").checked = false;
  const list = byId("file-list");
  list.textContent = "";
  byId("toggle-files").classList.toggle("is-hidden", !preparation.files.length);
  if (!preparation.files.length) {
    const row = document.createElement("div");
    row.className = "file-empty";
    row.textContent = "URL-only context — no source files are included in this transfer.";
    list.append(row);
  }
  preparation.files.forEach((file, index) => {
    const label = document.createElement("label");
    label.className = "file-row";
    const input = document.createElement("input");
    input.type = "checkbox";
    input.checked = true;
    input.value = file.path;
    input.setAttribute("aria-label", `Include ${file.path}`);
    input.addEventListener("change", updateSelection);
    const code = document.createElement("code");
    code.textContent = file.path;
    code.title = file.path;
    const size = document.createElement("small");
    size.textContent = bytes(file.bytes);
    label.dataset.index = String(index);
    label.append(input, code, size);
    list.append(label);
  });
  updateSelectionLabel();
  const minutes = Math.round(Number(preparation.expires_in_seconds || 1800) / 60);
  byId("review-expiry").textContent = `Prepared reviews expire after ${minutes} minutes and can be used once.`;
  setInlineError("review-error", providerReady() ? "" : "The selected provider is not configured. Run pocarchitect setup in another terminal, then select Recheck.");
  updateRunAvailability();
  byId("new-analysis-label").textContent = "Edit configuration";
  focusPanel("review-title");
}

function selectedFiles() {
  return Array.from(byId("file-list").querySelectorAll("input:checked")).map((input) => input.value);
}

function providerReady() {
  if (!state.bootstrap) return false;
  const provider = state.preparation?.provider || byId("provider").value;
  return Boolean(state.bootstrap.providers[provider]);
}

function updateSelectionLabel() {
  const inputs = Array.from(byId("file-list").querySelectorAll("input"));
  const selected = inputs.filter((input) => input.checked).length;
  byId("toggle-files").textContent = inputs.some((input) => input.checked) ? "Clear all" : "Select all";
  byId("selection-status").textContent = inputs.length ? `${selected} of ${inputs.length} files selected` : "No source files selected; URL context only";
}

function updateSelection() {
  if (!state.preparation) return;
  byId("approval").checked = false;
  updateSelectionLabel();
  updateRunAvailability();
  document.querySelectorAll(".review-summary > div").forEach((node) => node.classList.add("is-updating"));
  window.clearTimeout(state.estimateTimer);
  state.estimateTimer = window.setTimeout(requestSelectionEstimate, 220);
}

async function requestSelectionEstimate() {
  if (!state.preparation) return;
  state.estimateController?.abort();
  state.estimateController = new AbortController();
  const sequence = ++state.estimateSequence;
  try {
    const estimate = await api(`/api/preparations/${encodeURIComponent(state.preparation.preparation_id)}/estimate`, { method: "POST", body: JSON.stringify({ selected_files: selectedFiles() }), signal: state.estimateController.signal, timeout: 30000 });
    if (sequence === state.estimateSequence) renderMetrics(estimate);
  } catch (error) {
    if (sequence !== state.estimateSequence) return;
    document.querySelectorAll(".review-summary > div").forEach((node) => node.classList.remove("is-updating"));
    setInlineError("review-error", error.message);
    updateRunAvailability();
  }
}

function updateRunAvailability() {
  const approval = byId("approval");
  const button = byId("run-button");
  const ready = Boolean(state.preparation && approval.checked && state.selectionWithinLimit && providerReady());
  if (!button.classList.contains("is-busy")) button.disabled = !ready;
}

async function prepareAnalysis(event) {
  event.preventDefault();
  if (!validateForm()) return;
  const button = byId("prepare-button");
  setButtonBusy(button, true, "Preparing source…");
  setConfigurationLocked(true, "Preparing");
  hide("review-empty"); hide("review-content"); hide("run-content"); hide("report-content");
  show("review-loading"); hide("new-analysis");
  setReviewStatus("Preparing", "running");
  setInlineError("form-error");
  try {
    const preparation = await api("/api/preparations", { method: "POST", body: JSON.stringify(payloadFromForm()) });
    renderPreparation(preparation);
  } catch (error) {
    hide("review-loading"); show("review-empty");
    setReviewStatus("Needs attention", "error");
    setConfigurationLocked(false);
    setInlineError("form-error", error.message);
    toast(error.message, "error");
  } finally {
    setButtonBusy(button, false);
    if (state.preparation) button.disabled = true;
  }
}

function resetPhases() {
  document.querySelectorAll(".phase").forEach((phase, index) => {
    phase.classList.toggle("is-active", index === 0);
    phase.classList.remove("is-complete");
  });
}

function advancePhase(eventName) {
  let index = 0;
  if (["provider_started", "vulnerability_scan", "vulnerability_scan_failed"].includes(eventName)) index = 1;
  if (["report_writing", "report_saved", "report_exported", "report_diff", "scaffold_created"].includes(eventName)) index = 2;
  if (eventName === "run_complete") index = 3;
  document.querySelectorAll(".phase").forEach((phase, phaseIndex) => {
    phase.classList.toggle("is-active", phaseIndex === index);
    phase.classList.toggle("is-complete", phaseIndex < index || (index === 3 && phaseIndex === 3));
  });
}

function appendEvent(event) {
  const sequence = String(event.sequence ?? `${event.event}-${event.at}`);
  if (state.seenEvents.has(sequence)) return;
  state.seenEvents.add(sequence);
  const log = byId("event-log");
  const row = document.createElement("div");
  row.className = `event-row${event.event === "error" ? " is-error" : ""}`;
  const time = document.createElement("time");
  time.dateTime = event.at || new Date().toISOString();
  time.textContent = new Date(event.at || Date.now()).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  const message = document.createElement("span");
  message.textContent = event.message || event.event;
  row.append(time, message);
  log.append(row);
  log.scrollTop = log.scrollHeight;
  advancePhase(event.event);
}

function startElapsedTimer(startedAt = null) {
  window.clearInterval(state.elapsedTimer);
  state.runStartedAt = startedAt ? new Date(startedAt).getTime() : Date.now();
  const update = () => {
    const seconds = Math.max(0, Math.floor((Date.now() - state.runStartedAt) / 1000));
    byId("run-elapsed").textContent = `Elapsed ${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
  };
  update();
  state.elapsedTimer = window.setInterval(update, 1000);
}

function showRunState() {
  hide("review-content"); hide("review-empty"); hide("review-loading"); hide("report-content");
  show("run-content"); hide("run-error-actions"); show("new-analysis");
  byId("new-analysis-label").textContent = "New analysis";
  setReviewStatus("Running", "running");
}

async function startRun() {
  if (!state.preparation || !byId("approval").checked) return;
  if (!providerReady()) {
    setInlineError("review-error", "The selected provider is not configured. Run pocarchitect setup in another terminal, then select Recheck.");
    return;
  }
  const button = byId("run-button");
  setButtonBusy(button, true, "Starting analysis…");
  setInlineError("review-error");
  showRunState();
  byId("event-log").textContent = "";
  byId("run-state-label").textContent = "Analysis queued";
  byId("run-heading").textContent = "Building your architecture report.";
  state.seenEvents.clear();
  resetPhases();
  startElapsedTimer();
  try {
    const started = await api("/api/runs", { method: "POST", body: JSON.stringify({ preparation_id: state.preparation.preparation_id, selected_files: selectedFiles() }) });
    state.activeJobId = started.job_id;
    sessionStorage.setItem("pocarchitect.activeJob", started.job_id);
    watchRun(started.job_id);
  } catch (error) {
    window.clearInterval(state.elapsedTimer);
    hide("run-content"); show("review-content");
    setReviewStatus("Needs attention", "error");
    setInlineError("review-error", error.message);
    toast(error.message, "error");
  } finally {
    setButtonBusy(button, false);
    updateRunAvailability();
  }
}

async function startDemo() {
  const button = byId("run-demo");
  setButtonBusy(button, true, "Creating demo…");
  setConfigurationLocked(true, "Demo");
  showRunState();
  byId("event-log").textContent = "";
  byId("run-state-label").textContent = "Credential-free demo";
  byId("run-heading").textContent = "Creating a safe example report.";
  state.seenEvents.clear();
  resetPhases();
  startElapsedTimer();
  try {
    const started = await api("/api/demo", { method: "POST" });
    state.activeJobId = started.job_id;
    sessionStorage.setItem("pocarchitect.activeJob", started.job_id);
    watchRun(started.job_id);
  } catch (error) {
    window.clearInterval(state.elapsedTimer);
    hide("run-content"); hide("new-analysis"); show("review-empty");
    setReviewStatus("Needs attention", "error");
    setConfigurationLocked(false);
    toast(error.message, "error");
  } finally {
    setButtonBusy(button, false);
  }
}

function watchRun(jobId) {
  state.stream?.close();
  window.clearTimeout(state.recoveryTimer);
  const stream = new EventSource(`/api/runs/${encodeURIComponent(jobId)}/events`);
  state.stream = stream;
  stream.onopen = () => {
    setConnection("ready");
    window.clearTimeout(state.recoveryTimer);
  };
  stream.onmessage = async (message) => {
    let update;
    try { update = JSON.parse(message.data); } catch (_) { return; }
    if (update.type === "event") appendEvent(update.payload);
    if (update.type === "status") byId("run-state-label").textContent = update.status === "running" ? "Analysis in progress" : update.status === "queued" ? "Analysis queued" : update.status;
    if (update.type === "finished") {
      stream.close();
      if (state.stream === stream) state.stream = null;
      window.clearTimeout(state.recoveryTimer);
      await loadJob(jobId);
    }
  };
  stream.onerror = () => {
    byId("run-state-label").textContent = "Reconnecting to analysis";
    setConnection("loading", "Reconnecting");
    window.clearTimeout(state.recoveryTimer);
    state.recoveryTimer = window.setTimeout(() => recoverRun(jobId), 6000);
  };
}

async function recoverRun(jobId) {
  try {
    const job = await api(`/api/runs/${encodeURIComponent(jobId)}`, { timeout: 15000 });
    renderJobEvents(job);
    if (["completed", "failed"].includes(job.status)) renderTerminalJob(job);
    else watchRun(jobId);
  } catch (error) {
    setConnection("error");
    toast(`Unable to recover live progress: ${error.message}`, "error");
  }
}

function renderJobEvents(job) {
  (job.events || []).forEach(appendEvent);
}

async function loadJob(jobId) {
  try {
    const job = await api(`/api/runs/${encodeURIComponent(jobId)}`, { timeout: 15000 });
    renderJobEvents(job);
    renderTerminalJob(job);
  } catch (error) {
    renderRunFailure(error.message);
  }
}

function renderTerminalJob(job) {
  sessionStorage.removeItem("pocarchitect.activeJob");
  state.activeJobId = null;
  window.clearInterval(state.elapsedTimer);
  if (job.status === "completed" && job.result) renderCompletedRun(job.result);
  else renderRunFailure(job.error || "The analysis could not be completed.");
}

function renderRunFailure(message) {
  showRunState();
  setReviewStatus("Failed", "error");
  byId("run-state-label").textContent = "Analysis failed";
  byId("run-heading").textContent = message;
  show("run-error-actions");
  toast(message, "error");
}

function renderCompletedRun(result) {
  hide("run-content"); hide("review-content"); show("report-content"); show("new-analysis");
  byId("new-analysis-label").textContent = "New analysis";
  setReviewStatus("Complete", "complete");
  state.reportContent = result.content || "";
  byId("report-name").textContent = result.report_name;
  byId("report-body").innerHTML = safeMarkdown(state.reportContent);
  byId("download-report").href = `/api/artifacts/${encodeURIComponent(result.export_artifact_id)}/download`;
  const meta = byId("report-meta");
  meta.textContent = "";
  const values = [
    `${(result.grounding_files || []).length} grounding file${(result.grounding_files || []).length === 1 ? "" : "s"}`,
    result.estimated_cost_usd == null ? "Input cost unavailable" : `${cost(result.estimated_cost_usd)} estimated input`,
    result.completed_at ? `Completed ${new Date(result.completed_at).toLocaleString()}` : "Completed",
  ];
  values.forEach((value) => { const item = document.createElement("span"); item.textContent = value; meta.append(item); });
  refreshReports({ silent: true });
  focusPanel("report-name");
  toast("Analysis complete. Your report is ready.", "success");
}

function escapeHtml(value) {
  return String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
}

function inlineMarkup(text) {
  return escapeHtml(text).replace(/`([^`]+)`/g, "<code>$1</code>").replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>").replace(/~~([^~]+)~~/g, "<del>$1</del>");
}

function tableCells(line) {
  return line.trim().replace(/^\||\|$/g, "").split("|").map((cell) => cell.trim());
}

function safeMarkdown(markdown) {
  const lines = String(markdown || "").replaceAll("\r\n", "\n").split("\n");
  const output = [];
  let code = false;
  let list = null;
  const closeList = () => { if (list) { output.push(`</${list}>`); list = null; } };
  for (let index = 0; index < lines.length; index += 1) {
    const raw = lines[index];
    if (raw.startsWith("```")) {
      closeList();
      output.push(code ? "</code></pre>" : `<pre><code data-language="${escapeHtml(raw.slice(3).trim())}">`);
      code = !code;
      continue;
    }
    if (code) { output.push(`${escapeHtml(raw)}\n`); continue; }
    const next = lines[index + 1] || "";
    if (raw.includes("|") && /^\s*\|?\s*:?-{3,}/.test(next)) {
      closeList();
      const headers = tableCells(raw);
      output.push(`<table><thead><tr>${headers.map((cell) => `<th>${inlineMarkup(cell)}</th>`).join("")}</tr></thead><tbody>`);
      index += 2;
      while (index < lines.length && lines[index].includes("|") && lines[index].trim()) {
        output.push(`<tr>${tableCells(lines[index]).map((cell) => `<td>${inlineMarkup(cell)}</td>`).join("")}</tr>`);
        index += 1;
      }
      output.push("</tbody></table>");
      index -= 1;
      continue;
    }
    const unordered = /^\s*[-*]\s+(.+)/.exec(raw);
    const ordered = /^\s*\d+[.)]\s+(.+)/.exec(raw);
    if (unordered || ordered) {
      const type = unordered ? "ul" : "ol";
      if (list !== type) { closeList(); output.push(`<${type}>`); list = type; }
      output.push(`<li>${inlineMarkup((unordered || ordered)[1])}</li>`);
      continue;
    }
    closeList();
    if (/^\s*([-*_])\1\1+\s*$/.test(raw)) output.push("<hr>");
    else if (raw.startsWith("### ")) output.push(`<h3>${inlineMarkup(raw.slice(4))}</h3>`);
    else if (raw.startsWith("## ")) output.push(`<h2>${inlineMarkup(raw.slice(3))}</h2>`);
    else if (raw.startsWith("# ")) output.push(`<h1>${inlineMarkup(raw.slice(2))}</h1>`);
    else if (raw.startsWith("> ")) output.push(`<blockquote>${inlineMarkup(raw.slice(2))}</blockquote>`);
    else if (raw.trim()) output.push(`<p>${inlineMarkup(raw)}</p>`);
  }
  closeList();
  if (code) output.push("</code></pre>");
  return output.join("");
}

async function copyText(text, label) {
  try {
    if (navigator.clipboard?.writeText) await navigator.clipboard.writeText(text);
    else {
      const area = document.createElement("textarea");
      area.value = text;
      area.setAttribute("readonly", "");
      area.className = "clipboard-helper";
      document.body.append(area);
      area.select();
      if (!document.execCommand("copy")) throw new Error("Copy failed");
      area.remove();
    }
    toast(`${label} copied to the clipboard.`, "success");
  } catch (_) { toast("Clipboard access is unavailable. Use the Download action instead.", "error"); }
}

async function refreshReports({ silent = false } = {}) {
  const button = byId("refresh-reports");
  if (!silent) { button.disabled = true; button.setAttribute("aria-busy", "true"); }
  try {
    const response = await api("/api/reports", { timeout: 20000 });
    state.reports = response.reports || [];
    renderReportList();
  } catch (error) { toast(error.message, "error"); }
  finally { if (!silent) { button.disabled = false; button.removeAttribute("aria-busy"); } }
}

function filteredReports() {
  const query = byId("report-search").value.trim().toLocaleLowerCase();
  if (!query) return state.reports;
  return state.reports.filter((report) => `${report.name} ${report.source} ${report.provider} ${report.model}`.toLocaleLowerCase().includes(query));
}

function renderReportList() {
  const reports = filteredReports();
  byId("report-count").textContent = state.reports.length;
  byId("report-count").setAttribute("aria-label", `${state.reports.length} reports`);
  byId("library-count").textContent = String(state.reports.length);
  const list = byId("report-list");
  list.textContent = "";
  if (!reports.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    const title = document.createElement("h3");
    title.textContent = state.reports.length ? "No matching reports." : "No reports yet.";
    const copy = document.createElement("p");
    copy.textContent = state.reports.length ? "Try a different name, source, or provider." : "Complete an analysis and it will appear here.";
    empty.append(title, copy);
    list.append(empty);
    return;
  }
  reports.forEach((report) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `report-list-item${state.selectedReportId === report.artifact_id ? " is-active" : ""}`;
    button.setAttribute("aria-pressed", String(state.selectedReportId === report.artifact_id));
    const title = document.createElement("strong"); title.textContent = report.name;
    const source = document.createElement("span"); source.textContent = report.source;
    const meta = document.createElement("small"); meta.textContent = `${report.provider}/${report.model}${report.generated_at ? ` · ${new Date(report.generated_at).toLocaleString()}` : ""}`;
    button.append(title, source, meta);
    button.addEventListener("click", () => openLibraryReport(report, button));
    list.append(button);
  });
}

async function openLibraryReport(report, button) {
  try {
    document.querySelectorAll(".report-list-item").forEach((item) => { item.classList.remove("is-active"); item.setAttribute("aria-pressed", "false"); });
    button.classList.add("is-active"); button.setAttribute("aria-pressed", "true");
    state.selectedReportId = report.artifact_id;
    hide("library-report"); show("library-empty");
    byId("library-empty").querySelector("h3").textContent = "Loading report…";
    const response = await api(`/api/artifacts/${encodeURIComponent(report.artifact_id)}`, { timeout: 30000 });
    state.libraryContent = response.content || "";
    hide("library-empty"); show("library-report");
    byId("library-report-name").textContent = response.name;
    byId("library-report-body").innerHTML = safeMarkdown(state.libraryContent);
    byId("library-download").href = `/api/artifacts/${encodeURIComponent(report.artifact_id)}/download`;
    focusPanel("library-report-name");
  } catch (error) {
    toast(error.message, "error");
    show("library-empty");
    byId("library-empty").querySelector("h3").textContent = "This report could not be opened.";
  }
}

function resetAnalysis() {
  if (state.activeJobId && !window.confirm("The current analysis will continue in the background, but this page will stop tracking it. Start a new analysis anyway?")) return;
  state.stream?.close(); state.stream = null;
  window.clearTimeout(state.recoveryTimer); window.clearInterval(state.elapsedTimer); window.clearTimeout(state.estimateTimer);
  state.estimateController?.abort();
  sessionStorage.removeItem("pocarchitect.activeJob");
  state.activeJobId = null; state.preparation = null; state.seenEvents.clear(); state.reportContent = "";
  hide("review-content"); hide("review-loading"); hide("run-content"); hide("report-content"); hide("new-analysis"); show("review-empty");
  setReviewStatus("Waiting"); setConfigurationLocked(false); setInlineError("review-error"); setInlineError("form-error"); clearSourceError();
  byId("new-analysis-label").textContent = "New analysis";
  byId("approval").checked = false; byId("event-log").textContent = "";
  byId("source").focus();
}

async function resumeActiveJob() {
  const jobId = sessionStorage.getItem("pocarchitect.activeJob");
  if (!jobId) return;
  try {
    const job = await api(`/api/runs/${encodeURIComponent(jobId)}`, { timeout: 15000 });
    state.activeJobId = jobId;
    state.seenEvents.clear();
    byId("event-log").textContent = "";
    showRunState(); resetPhases(); renderJobEvents(job); startElapsedTimer(job.created_at);
    if (["completed", "failed"].includes(job.status)) renderTerminalJob(job); else watchRun(jobId);
  } catch (_) { sessionStorage.removeItem("pocarchitect.activeJob"); }
}

async function loadBootstrap({ resume = true } = {}) {
  setConnection("loading");
  try {
    const preserveProvider = state.preparation?.provider || (state.bootstrap ? byId("provider").value : null);
    state.bootstrap = await api("/api/bootstrap", { timeout: 20000 });
    byId("version-label").textContent = `POCArchitect v${state.bootstrap.version}`;
    byId("output-dir").placeholder = state.bootstrap.default_output_dir;
    state.reports = state.bootstrap.reports || [];
    byId("provider").value = preserveProvider || preferredProvider(state.bootstrap);
    updateProvider({ preserveModel: Boolean(state.preparation) }); renderReportList(); setConnection("ready");
    if (resume) await resumeActiveJob();
  } catch (error) {
    setConnection("error");
    setInlineError("form-error", error.message);
    toast(error.message, "error");
  }
}

async function recheckProviders() {
  const button = byId("refresh-providers");
  const label = button.textContent;
  button.disabled = true;
  button.textContent = "Checking…";
  await loadBootstrap({ resume: false });
  button.disabled = false;
  button.textContent = label;
  if (providerReady()) {
    setInlineError("review-error");
    updateRunAvailability();
    toast("Provider readiness updated.", "success");
  }
}

function bindEvents() {
  document.querySelectorAll(".nav-item").forEach((button) => {
    button.addEventListener("click", () => setView(button.dataset.view));
    button.addEventListener("keydown", handleTabKeys);
  });
  document.querySelectorAll("[data-source-mode]").forEach((button) => button.addEventListener("click", () => setSourceMode(button.dataset.sourceMode)));
  byId("provider").addEventListener("change", () => updateProvider());
  byId("source").addEventListener("input", clearSourceError);
  byId("analysis-form").addEventListener("submit", prepareAnalysis);
  byId("run-demo").addEventListener("click", startDemo);
  byId("approval").addEventListener("change", updateRunAvailability);
  byId("run-button").addEventListener("click", startRun);
  byId("toggle-files").addEventListener("click", () => {
    const inputs = Array.from(byId("file-list").querySelectorAll("input"));
    const next = !inputs.some((input) => input.checked);
    inputs.forEach((input) => { input.checked = next; });
    updateSelection();
  });
  byId("new-analysis").addEventListener("click", resetAnalysis);
  byId("restart-after-error").addEventListener("click", resetAnalysis);
  byId("refresh-reports").addEventListener("click", () => refreshReports());
  byId("report-search").addEventListener("input", renderReportList);
  byId("copy-report").addEventListener("click", () => copyText(state.reportContent, "Report"));
  byId("library-copy").addEventListener("click", () => copyText(state.libraryContent, "Report"));
  byId("copy-setup").addEventListener("click", () => copyText("pocarchitect setup", "Setup command"));
  byId("refresh-providers").addEventListener("click", recheckProviders);
  byId("retry-connection").addEventListener("click", loadBootstrap);
  window.addEventListener("hashchange", () => setView(window.location.hash.slice(1), { updateHash: false }));
  window.addEventListener("beforeunload", (event) => {
    if (!state.activeJobId) return;
    event.preventDefault();
    event.returnValue = "";
  });
  window.addEventListener("unhandledrejection", (event) => {
    toast(event.reason?.message || "An unexpected interface error occurred.", "error");
  });
}

async function boot() {
  bindEvents();
  setView(window.location.hash.slice(1), { updateHash: true });
  await loadBootstrap();
}

boot();
