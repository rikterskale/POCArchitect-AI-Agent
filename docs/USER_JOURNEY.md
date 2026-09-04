# POCArchitect User Journey

## 1. Product overview

POCArchitect is a local-first command-line and browser application for turning a
proof-of-concept source into a structured architecture and risk report. It can
inspect a repository or local directory, build a bounded grounding set, redact
recognized secret patterns, estimate provider input, and require explicit
approval before a configured provider receives the selected content. Reports
are saved locally and can include architecture diagrams, findings, mitigations,
dependency vulnerability records, comparisons, exports, and safe scaffold
artifacts.

The product also includes a credential-free path that proves installation,
local report generation, persistence, and browser navigation without reading a
real source or calling an external provider. That path is the primary journey
below because it was exercised end to end with a real Chromium browser. Cloud
provider availability, credentials, billing, and model responses remain
external integration conditions; the application validates their configuration
and reports actionable failures, but this journey does not claim that an
external provider is available.

POCArchitect does not require an account or hosted service of its own. The GUI
binds only to the local computer, uses a launch-specific session token, and
stores its session in an HTTP-only cookie. The operator remains responsible for
authorization to inspect source material and for reviewing the transfer before
any provider-backed analysis.

## 2. Personas

| Persona | Goal | Entry point |
|---|---|---|
| First-time evaluator | Prove that the installation works and see a finished report without credentials, source access, or provider cost. | `python -m pocarchitect quickstart`, then `pocarchitect gui --no-open` |
| Security or architecture analyst | Review bounded source evidence and create a decision-ready report with an explicitly selected provider. | `pocarchitect setup`, the GUI **Analyze** tab, or `pocarchitect --path ...` |
| Batch operator | Process several authorized sources, inspect durable progress, and recover failed or corrupt batch state. | `pocarchitect --batch sources.txt ...`, `batch-status`, and `batch-reset` |
| Automation consumer | Receive stable JSON events or drive the finding lifecycle from Python without parsing terminal presentation. | Root `--format json --no-color` options or `WorkflowEngine` |
| Report consumer | Reopen, search, copy, download, compare, export, or scaffold from completed local reports. | GUI **Reports** tab or the `history`, `diff`, `compare`, `export`, and `scaffold` commands |

## 3. Primary journey: credential-free first value

This journey starts from a repository checkout and ends with a persisted report
opened from the local report library. It makes no external provider request.

1. **Create and activate an isolated Python environment.**

   Linux or macOS:

   ```text
   python -m venv .venv
   . .venv/bin/activate
   ```

   Windows PowerShell:

   ```text
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   The active environment supplies the `python` and `pocarchitect` executables
   used by every following step.

2. **Install the application and GUI dependencies.**

   ```text
   python -m pip install -e ".[gui]"
   ```

   A successful command exits with status 0 and installs both the module entry
   point and the `pocarchitect` console command.

3. **Confirm the installed version.**

   ```text
   python -m pocarchitect --version
   ```

   The command exits with status 0 and prints a `pocarchitect` version line.

4. **Run the complete credential-free first-use check.**

   ```text
   python -m pocarchitect quickstart
   ```

   `quickstart` runs offline preflight checks, starts a temporary local demo
   provider, generates a report, and saves it below the local `reports/demo`
   directory. The output includes successful preflight and run-completion
   messages. No cloud credential is required.

5. **Launch the protected local GUI without automatically opening a browser.**

   ```text
   pocarchitect gui --no-open
   ```

   The command prints a launch URL in the form
   `http://127.0.0.1:8765/?token=<launch-token>`. The server listens only on a
   loopback address. Keep this terminal running.

6. **Open the exact launch URL in a browser.**

   The token is exchanged for an HTTP-only session cookie and the browser is
   redirected to `/`. The **Analysis workspace** loads and the secure local
   session indicator changes from **Connecting** to **Ready**.

7. **Review the credential-free demo boundary.**

   On the **Analyze** tab, locate **First time here?** in the **Transfer review**
   panel. The action is labeled **Create credential-free demo**, with the
   boundary statement **No source read · No provider call · No credential · No
   cost**.

8. **Create the browser demo report.**

   Select **Create credential-free demo**. The interface moves through queued,
   report, and complete states. The event log states that the demo is generated
   locally and that no provider request is made.

9. **Confirm core value was delivered.**

   The report panel displays **Analysis complete**, a report name, rendered
   Markdown content beginning with **POCArchitect Demo Report**, and **Copy
   Markdown** and **Download** actions. This is the first complete architecture
   report experience without external prerequisites.

10. **Download the persisted report.**

    Select **Download**. The browser receives the artifact as an attachment, and
    the Markdown body contains the demo-report heading.

11. **Open the report library.**

    Select the **Reports** tab. Under **Report library**, the recent report
    appears in **Recent analyses**. Selecting it displays the saved Markdown and
    exposes **Copy Markdown** and **Download** again.

12. **Recover the completed session after a reload.**

    Reload the page. Completed-run recovery clears the active job identifier,
    while the persisted report remains available from **Reports**. Select **New
    analysis** to return to a clean configuration state.

## 4. Provider-backed analysis journey

Use this path only for an authorized source and a provider account or local
OpenAI-compatible endpoint that the operator controls.

1. Run `pocarchitect setup` in an interactive terminal, or configure the
   provider credential through its environment variable. A local provider needs
   an HTTP(S) base URL rather than a cloud key.
2. Run `pocarchitect preflight --provider openai` for a cloud provider, or
   `pocarchitect preflight --provider local --base-url
   http://localhost:11434/v1` for a local endpoint. Continue only when the
   required checks pass.
3. Launch the GUI and enter a repository, package, image, HTTP(S) URL, or an
   authorized local directory on the **Analyze** tab.
4. Select the provider, model, risk posture, target environment, evidence
   policy, and optional output controls. Select **Prepare transfer review**.
5. In **Transfer review**, inspect the selected file count, transfer size,
   estimated tokens and cost, redactions, and each grounding-file checkbox. No
   provider call has occurred at this point.
6. Confirm that the selected payload is within any configured cost limit, select
   **I reviewed this transfer and authorize sending...**, and then select
   **Approve and run analysis**.
7. Wait for **Analysis complete**, then download the report or reopen it from
   **Reports**.

The equivalent non-sending preview is:

```text
python -m pocarchitect --url https://github.com/example/poc --no-ingest --dry-run --format json --no-color
```

It emits a `dry_run` JSON event and does not call a provider or write a report.

## 5. Alternate and error paths

| Situation | Observable response | Recovery |
|---|---|---|
| Empty GUI source | The source field receives focus and displays **Enter a repository, package, image, or source URL.** | Enter a supported source or switch to **Local directory** and enter an authorized directory path. |
| Provider credential absent | Provider readiness says the provider needs configuration; transfer approval cannot start the run. | Run `pocarchitect setup` in another terminal, return to the GUI, and select **Recheck**. |
| Local endpoint unavailable | Preflight reports `LOCAL_ENDPOINT_UNAVAILABLE`; the run does not proceed. | Start the OpenAI-compatible local server or correct `--base-url`, then rerun preflight. |
| Invalid or unsupported source | CLI validation exits nonzero, or GUI preparation returns HTTP 422 with an explanatory detail. | Correct the source syntax or use `--no-ingest` for an intentionally URL-only analysis. |
| Real source ingestion fails | The service reports **Source ingestion failed** and the CLI states that no provider call was made. | Check source access and Git availability, or deliberately disable ingestion after reviewing the reduced evidence. |
| Estimated cost exceeds the configured maximum | The GUI states that the selected payload exceeds the cost limit; the run button remains disabled. CLI execution aborts before the provider call. | Remove grounding files or begin a new analysis with an approved higher limit. |
| Transfer review expires or was already used | The API returns HTTP 409; prepared reviews expire after 30 minutes and are single-use. | Select **New analysis**, prepare a new transfer review, and approve it once. |
| Browser session is missing or host is not local | GUI API requests return HTTP 401; an unexpected host returns HTTP 400. | Reopen the exact launch URL printed by `pocarchitect gui --no-open`; do not proxy or expose the GUI. |
| Cross-origin mutation is attempted | The GUI returns HTTP 403 and performs no mutation. | Use the locally served GUI origin rather than another page or origin. |
| API request is too large | The GUI returns HTTP 413 with **Request is too large**. | Reduce the request to the supported bounded payload. |
| Report preview is unsupported | Non-Markdown or invalid UTF-8 content returns HTTP 415; an oversized preview returns HTTP 413; a missing report returns HTTP 404. | Use **Download** for non-previewable or large artifacts, or select an available Markdown report. |
| Browser connection is interrupted | A banner displays **Connection interrupted** with **Retry connection**. | Select **Retry connection**; if the server stopped, rerun `pocarchitect gui --no-open` and open its new token URL. |
| Vulnerability lookup is offline or malformed | Analysis continues and emits `vulnerability_scan_failed` instead of treating unverified data as a vulnerability result. | Retry OSV enrichment when connectivity is available; use the completed base report meanwhile. |
| Batch state is corrupt or unsupported | The state loader refuses to overwrite it and instructs the operator to run `batch-reset`. | Run `python -m pocarchitect --format json --no-color batch-reset --batch-state reports/batch_progress.json --yes`; the old state is moved to a timestamped backup. |
| Batch contains a failed item | Processing continues to later items, records success and failure counts, and exits nonzero when failures remain. | Inspect `batch-status`, correct the source or configuration, and rerun the batch to resume safely. |
| Publishing cannot use GitHub CLI | `publish` exits nonzero with a redacted GitHub CLI error and does not claim the report was ingested. | Install and authenticate `gh`, then retry `pocarchitect publish <report>`. |
| Interactive setup is run without a terminal | `setup` exits with status 2 and explains that it is interactive. | Run it in a terminal, or set the provider environment variable and use `preflight`. |

## 6. Journey map

Every success criterion below is binary and observable. Phase 5 UAT must capture
the actual result rather than inferring success from implementation.

| Step | User action | System response | Success criterion |
|---|---|---|---|
| J-01 | Create a virtual environment and install with `python -m pip install -e ".[gui]"`. | The package, module entry point, console script, and GUI dependencies install. | Install command exits 0 and `python -m pip check` exits 0. |
| J-02 | Run `python -m pocarchitect --version`. | The CLI prints its installed version. | Exit code is 0 and stdout contains `pocarchitect`. |
| J-03 | Run `python -m pocarchitect quickstart`. | Offline preflight and the credential-free local demo complete and save a report. | Exit code is 0 and at least one Markdown report exists under `reports/demo`. |
| J-04 | Run `pocarchitect gui --no-open`. | A loopback server starts and prints a protected launch URL. | Stdout contains `http://127.0.0.1:<port>/?token=` and no non-loopback bind occurs. |
| J-05 | Open the printed URL. | The token becomes an HTTP-only session and the workspace loads. | Browser reaches `/`, the page title contains `POCArchitect`, and connection status is **Ready**. |
| J-06 | Submit the empty **Analysis configuration** form. | Inline validation rejects the empty source. | Source error equals **Enter a repository, package, image, or source URL.** and focus is on the source input. |
| J-07 | Select **Create credential-free demo**. | A local demo job is accepted and advances through run states. | The job reaches `completed` and the UI displays **Analysis complete**. |
| J-08 | Inspect the completed browser report. | Rendered Markdown and report actions appear. | Report body contains **POCArchitect Demo Report** and both **Copy Markdown** and **Download** are visible. |
| J-09 | Select **Download**. | The server returns the persisted Markdown artifact. | HTTP response is 200 and the downloaded body contains `# POCArchitect Demo Report`. |
| J-10 | Open **Reports** and select the demo report. | The report library lists and renders the saved report. | At least one report row exists and the selected library body contains **POCArchitect Demo Report**. |
| J-11 | Reload after completion. | The UI recovers without replaying the completed preparation. | No active job remains in session storage and the report remains available from **Reports**. |
| J-12 | Run the documented JSON dry run. | The CLI validates and previews the request without provider access or report creation. | Exit code is 0, exactly one parsed event has `event: "dry_run"`, and no new report is written. |
| J-13 | Prepare a GUI transfer with an authorized source and no ingestion. | The service returns bounded metadata before provider access. | HTTP response is 200, includes file/size/token/redaction metadata, and excludes prompt/source content. |
| J-14 | Estimate a selected transfer. | The service recalculates file count, bytes, tokens, cost, and redactions. | HTTP response is 200 and `within_cost_limit` is a Boolean. |
| J-15 | Approve and submit a prepared transfer once. | The run is queued and the preparation is consumed. | First request returns HTTP 202; replaying the same preparation returns HTTP 409. |
| J-16 | Request missing run and artifact identifiers. | The GUI rejects unknown resources. | Both requests return HTTP 404. |
| J-17 | Send a cross-origin mutation and an oversized body. | Local-session middleware rejects both before mutation. | Cross-origin response is 403 and oversized response is 413. |
| J-18 | Preview non-Markdown, oversized, invalid UTF-8, and missing artifacts. | The preview endpoint returns bounded, typed errors. | Responses are respectively 415, 413, 415, and 404. |
| J-19 | Run batch status and recoverably reset state. | Status is emitted as JSON and reset moves existing state to a backup. | Both commands exit 0, reset emits `batch_reset`, and a `.bak` file preserves prior state. |
| J-20 | Run the expanded documentation-command validator. | Every credential-free documented command is exercised; provider-backed commands remain classified as external. | Validator exits 0 and prints **Credential-free documentation commands passed behavioral probes.** |

## 7. Verified boundaries

- The credential-free CLI and browser journey is automated and does not require
  an external provider, credential, or source repository.
- GUI security behavior is verified for loopback binding, launch-session
  authentication, host validation, origin validation, body limits, artifact
  errors, preparation expiry, and single-use preparation.
- Provider-backed request construction and response handling are tested against
  controlled local doubles. Availability, billing, rate limits, and model
  quality for third-party providers require separate integration acceptance.
- The browser test uses Chromium. CI additionally contains a Windows-specific
  job for redirected CLI help; a hosted run is required for current remote
  Windows evidence.
