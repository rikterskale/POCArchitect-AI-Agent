# POCArchitect user journey

This document describes how a person actually uses POCArchitect, from first
install to a finished report. Every command, screen, flag, and message below
exists in the current code and was exercised in the project’s test suite.

## 1. Product overview

POCArchitect is a local command-line tool, with an optional loopback web
interface, that turns an authorized proof-of-concept source into a structured
Markdown architecture report. The operator supplies a GitHub repository, a
local directory, a generic source identifier, or a batch file of sources. For
public GitHub repositories and local directories, the tool can shallow-clone or
walk the tree, select a bounded set of text files, redact recognized secret
patterns, and show a transfer preview before any model provider is called.

It does not execute retrieved proof-of-concept code. A credential-free
`quickstart` / `demo` path writes a clearly labeled local report without an API
key or a billable provider call. A real analysis requires a configured
provider (`xai`, `openai`, `groq`, or a local OpenAI-compatible endpoint),
explicit confirmation (`--yes` or an interactive prompt), and a successful
provider response. Reports are written under `reports/` by default (or
`/reports` in Docker) with provenance metadata.

The product is for security practitioners who need reproducible blueprints from
authorized sources: red-team and assessment operators, people installing the
tool for the first time, and automation that consumes JSON events or the
composite GitHub Action. Finding lifecycle work (scope, validation, closure)
is a separate, auditable CLI beside the report generator.

## 2. Personas

| Persona | Goal | Entry point |
|---|---|---|
| First-run operator | Prove the install works without spending provider credits | `python -m pocarchitect quickstart` |
| CLI analyst | Produce a report from an authorized GitHub URL or local tree | `pocarchitect --url …` or `--path …` |
| GUI operator | Review files, redaction, and cost, then approve a transfer in a browser | `pocarchitect gui` |
| Automation / CI user | Run a dry-run or real analysis from a workflow and keep the report | `action.yml` composite action, or `pocarchitect --format json` |
| Assessment lead | Record scope, findings, and closure decisions independently of an LLM report | `pocarchitect workflow-init` |

## 3. Primary journey

Core value for a new user is a finished, on-disk Markdown report with no
credential and no provider bill. That is `quickstart` (offline doctor + demo).
The same report path is what a later real analysis uses after transfer
approval.

1. **Obtain the source.** Clone or unpack the repository and change into it.
   PyPI is not a supported install path. Observable: `pyproject.toml` and the
   `pocarchitect/` package are present.

2. **Create an environment and install.**
   ```bash
   python -m venv .venv
   . .venv/bin/activate
   python -m pip install -e ".[gui]"
   ```
   The console script is `pocarchitect` (`pocarchitect.cli:app`). The `gui`
   extra installs FastAPI and Uvicorn. Observable: `pocarchitect --help` exits
   0.

3. **Show the version.**
   ```bash
   python -m pocarchitect --version
   ```
   Observable: a line `POCArchitect v0.3.0` (or the installed package version)
   and exit 0.

4. **Prove the install without credentials.**
   ```bash
   python -m pocarchitect quickstart
   ```
   This runs `preflight` with `require_api_key=False`, `offline=True`,
   `require_git=False`, then `demo`. Observable: preflight reports that
   configured checks passed; a Markdown file appears under `reports/demo/`
   named `POCAnalysis_*.md`.

5. **Open the demo report.** The file starts with YAML-like provenance (`project`,
   `source_url`, `provider`, `model`, `ingestion`, `content_sha256`) and a body
   containing `POCArchitect Demo Report` and the sentence that the path is
   credential-free. Observable: the file exists and contains that heading.

6. **Optional — inspect a dry-run without calling a provider.**
   ```bash
   python -m pocarchitect --url https://github.com/example/poc --no-ingest --dry-run --format json --no-color
   ```
   `--dry-run` skips automatic preflight. Observable: a JSON object with
   `"event": "dry_run"` and `"report_preview"`; exit 0; no new provider call.

7. **Optional — launch the local GUI.**
   ```bash
   pocarchitect gui --no-open
   ```
   The process binds `127.0.0.1` (default port `8765`), prints
   `POCArchitect GUI is starting at http://127.0.0.1:8765/`, and a one-time
   launch URL `http://127.0.0.1:8765/?token=…`. Observable: that event; opening
   `/` without the cookie returns HTTP 401 with detail
   `Open the GUI from its launch URL`.

8. **Optional — create the same demo from the GUI.** On the Analyze view, select
   **Create credential-free demo**. The UI queues `POST /api/demo`, streams
   run events, then shows the report titled from the saved file, with
   **Copy Markdown** and **Download**. Observable: `# POCArchitect Demo Report`
   in the report body; the Reports tab lists the file.

9. **Later — first authorized analysis (CLI).** After `pocarchitect setup` (or
   an environment key) and `pocarchitect preflight --provider <name>`:
   ```bash
   pocarchitect --url owner/repo --yes --output-dir reports
   ```
   Shorthand `owner/repo` expands to `https://github.com/owner/repo`. Without
   `--no-ingest`, a public GitHub repository is shallow-cloned. Without `--yes`
   on a non-TTY, the process exits 2 with
   `Confirmation is required in non-interactive mode; review the preview and rerun with --yes.`
   Observable on success: `Report saved: POCAnalysis_….md` and a file in the
   output directory.

10. **Later — first authorized analysis (GUI).** Choose **Repository or source**
    or **Local directory**, enter a source, select provider and model, then
    **Prepare transfer review**. After the file list, redaction summary, and
    cost estimate, check the approval box and **Approve and run analysis**.
    Unconfigured cloud providers keep the run button disabled and show
    `The selected provider is not configured. Run pocarchitect setup in another terminal, then select Recheck.`

## 4. Alternate and error paths

| Step | Failure | What the user sees | Recovery |
|---|---|---|---|
| Install without GUI extra, then `pocarchitect gui` | `ImportError` for FastAPI/Uvicorn | `The GUI dependencies are not installed. Run: python -m pip install -e ".[gui]"` and exit 2 | Install the `gui` extra |
| `quickstart` / `demo` / `preflight --offline` | Python &lt; 3.10, missing import, unwritable output dir | Preflight table with `FAIL` rows and `FAIL: Preflight failed.` Exit 1 | Follow the Fix column; `pocarchitect doctor --offline --fix --yes` can create the output directory |
| Analyze with no source | Missing `--url` / `--source` / `--path` / `--batch` | `Provide --url, --source, --path, or --batch` and exit 2 | Pass exactly one of those options |
| `--url` and `--batch` together | Conflicting inputs | `Provide either --url or --batch, not both` and exit 2 | Use one input form |
| Malformed GitHub URL with ingest | `validate_poc_url` / `normalize_github_repo_url` | `Invalid PoC URL: …` and exit 2 | Use `/owner/repo` or pass `--no-ingest` |
| Clone or local walk fails, real run | Ingestion outcome `url-only-ingestion-failed` | `Source ingestion failed; no provider call was made. Fix ingestion or rerun explicitly with --no-ingest.` Exit 2 | Fix Git/URL/path, or rerun with `--no-ingest` |
| Real run, non-TTY, no `--yes` | Confirmation gate | `Confirmation is required in non-interactive mode; review the preview and rerun with --yes.` Exit 2 | Add `--yes` after reviewing the preview |
| Interactive decline | Operator answers no | `No source content was sent to the provider.` Exit 0 | Rerun and confirm, or `--yes` |
| Estimated cost over `--max-estimated-cost` | Cost gate | Error that the estimated input cost exceeds the limit; exit 2; no provider call | Raise the limit or reduce grounding |
| Unknown model | Provider 404 / model_not_found | Friendly model error and known-good names; `FatalProviderError`; exit 1 | Pass a valid `--model` or omit it |
| `setup` in a pipe | `stdin` is not a TTY | `Setup is interactive; run it in a terminal, or set the provider key environment variable and use \`preflight\` instead.` Exit 2 | Run in a terminal, or set the key and use `preflight` |
| GUI without launch URL | Missing session cookie | HTTP 401 `Open the GUI from its launch URL` | Open the printed `?token=` URL |
| GUI cloud provider with no key | `provider_configuration()` is false | Run button stays disabled; copy-setup control is shown | `pocarchitect setup`, then **Recheck** |
| GUI connection drop | `fetch` TypeError / EventSource error | Banner `Connection interrupted.` and **Retry connection** | Retry; a running job id in `sessionStorage` can be resumed |
| Batch file missing or comment-only | Empty URL list | `Batch file not found` or `Batch file is empty or contains no valid URLs`; exit 2 | Point at a file with non-comment lines |
| `workflow-status` on a missing file | No state file | `Workflow state not found: …` and exit 2 | `workflow-init --state …` first |
| `publish` without `gh` | `shutil.which("gh")` is None | `GitHub CLI is required for publishing. Install and authenticate \`gh\`, then retry.` Exit 2 | Install and authenticate `gh` |
| `init` when `.pocarchitect.toml` exists | File exists | `Config already exists: …. Use --force to replace it.` Exit 2 | `--force` |
| Misspelled subcommand | `SuggestingGroup` | Usage error plus `Did you mean 'models'?` (example) | Use the suggested name |

Non-GitHub identifiers (`pypi:…`, `docker:…`, ordinary `https://` URLs) are
accepted as sources. Grounding ingestion still only clones `github.com` or
reads a local directory; other hosts get URL-only context labeled
`url-only-non-github`.

## 5. Journey map

Every success criterion is binary and observable. Phase 5 consumes this table.

| Step | User action | System response | Success criterion |
|---|---|---|---|
| J1 | `python -m pip install -e ".[gui]"` from the repo root in a venv | Package and `pocarchitect` console script install | `pocarchitect --help` exits 0 |
| J2 | `python -m pocarchitect --version` | Prints `POCArchitect v…` | Exit 0 and stdout contains `POCArchitect v` |
| J3 | `python -m pocarchitect preflight --offline --format json --no-color` | One JSON preflight event | Exit 0 and `"event": "preflight"` with message `Preflight passed.` |
| J4 | `python -m pocarchitect --format json --no-color quickstart` | Offline preflight then demo report write | Exit 0, a `preflight` event, and a `report_saved` event |
| J5 | Inspect `reports/demo/POCAnalysis_*.md` after demo/quickstart | Provenance front matter plus demo body | File exists and body contains `POCArchitect Demo Report` |
| J6 | `python -m pocarchitect --url https://github.com/example/poc --no-ingest --dry-run --format json --no-color` | Dry-run JSON; no provider call | Exit 0, `"event": "dry_run"`, stdout contains `report_preview` |
| J7 | `pocarchitect gui --no-open` (or CLI equivalent in-process) | Loopback server + launch URL | Output contains `http://127.0.0.1:` and `?token=` |
| J8 | `GET /` without the session cookie | Reject unauthenticated index | HTTP 401 and detail `Open the GUI from its launch URL` |
| J9 | `GET /?token=<launch-token>` then `POST /api/demo` | Cookie set; demo job completes | Job `status` is `completed` and result content contains `POCArchitect Demo Report` |
| J10 | Open Reports and select the demo file | Library lists and renders the Markdown | Reports list is non-empty; preview contains `POCArchitect Demo Report` |
| J11 | `pocarchitect --url https://github.com/owner --dry-run` | Early GitHub URL validation | Exit 2 and stdout contains `Invalid PoC URL` |
| J12 | `pocarchitect --dry-run` with no source | Input arity check | Exit 2 and `Provide --url, --source, --path, or --batch` |
| J13 | `pocarchitect --url u --batch f` | Mutual exclusion | Exit 2 and `Provide either --url or --batch, not both` |
| J14 | Real ingest of a missing GitHub repo without `--no-ingest` | Ingestion failure before provider | Exit 2 and `Source ingestion failed; no provider call was made` |
| J15 | Real run, non-TTY, no `--yes`, ingest enabled | Confirmation gate | Exit 2 and `Confirmation is required in non-interactive mode` |
| J16 | `--max-estimated-cost 0` on a priced model with `--no-ingest --yes` | Cost gate | Exit 2 and message contains `exceeds the` |
| J17 | `pocarchitect setup` with stdin not a TTY | Setup refuses | Exit 2 and `Setup is interactive` |
| J18 | `pocarchitect gui` without the `gui` extra | Import guard | Exit 2 and `The GUI dependencies are not installed` |
| J19 | `pocarchitect workflow-status --state missing.json` | Missing state | Exit 2 and `Workflow state not found` |
| J20 | `pocarchitect compare only-one` | Compare arity | Exit 2 and `Compare requires at least two sources` |
| J21 | `pocarchitect publish report.md` when `gh` is missing | Publish guard | Exit 2 and `GitHub CLI is required for publishing` |
| J22 | `pocarchitect init` twice | Config collision | Second call exit 2 and `Use --force to replace it` |
| J23 | GUI prepare with empty source | Client validation | Inline error `Enter a repository, package, image, or source URL.` |
| J24 | GUI with unconfigured cloud provider, approval checked | Run stays blocked | `#run-button` is disabled; setup copy control is visible |
| J25 | GUI bootstrap aborted then Retry | Connection banner | Banner shows `Connection interrupted.`; Retry restores `Ready` |
