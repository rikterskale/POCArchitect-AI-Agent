# Start Here: POCArchitect

This is the recommended first-use guide for POCArchitect. Follow it from top to
bottom and you will install the application, prove that it works without using
a credential, open the graphical interface, and create a safe example report.
Provider setup is needed only when you are ready to create a real authorized
analysis report.

You do not need prior Python, Git, AI-provider, or command-line experience.
When Windows and macOS/Linux use different commands, both are shown. Run only
the commands for your operating system.

> [!IMPORTANT]
> POCArchitect is security tooling. Analyze only systems and source code you
> own or have explicit permission to assess. The application never executes
> retrieved proof-of-concept code, but a real analysis can send selected,
> redacted source content to the model provider you choose.

## The shortest successful path

If Python and Git are already installed, this is the shortest credential-free
path to a finished report:

1. Open a terminal in the POCArchitect folder.
2. Create and activate a virtual environment.
3. Install POCArchitect with the GUI dependencies.
4. Run the credential-free quickstart.
5. Launch the GUI.
6. Select **Create credential-free demo**.

The exact commands and success checks are provided below. Do not skip the
credential-free quickstart; it catches most installation problems before a
real source or provider is involved. When you are ready for a real analysis,
configure one provider, select **Recheck** in the open GUI, enter an authorized
source, and review the transfer before approving it.

## Contents

1. [Understand what will happen](#1-understand-what-will-happen)
2. [Choose the GUI or terminal](#2-choose-the-gui-or-terminal)
3. [Install Python and Git](#3-install-python-and-git)
4. [Get the POCArchitect files](#4-get-the-pocarchitect-files)
5. [Create an isolated environment and install](#5-create-an-isolated-environment-and-install)
6. [Prove the installation works without credentials](#6-prove-the-installation-works-without-credentials)
7. [Configure a provider safely](#7-configure-a-provider-safely)
8. [Launch and use the GUI](#8-launch-and-use-the-gui)
9. [Create a report from the terminal](#9-create-a-report-from-the-terminal)
10. [Understand grounding, redaction, cost, and approval](#10-understand-grounding-redaction-cost-and-approval)
11. [Work with reports](#11-work-with-reports)
12. [Analyze multiple sources](#12-analyze-multiple-sources)
13. [Set reusable project defaults](#13-set-reusable-project-defaults)
14. [Use POCArchitect safely every day](#14-use-pocarchitect-safely-every-day)
15. [Troubleshoot problems](#15-troubleshoot-problems)
16. [Update, stop, clean up, or uninstall](#16-update-stop-clean-up-or-uninstall)
17. [Collect safe diagnostic information](#17-collect-safe-diagnostic-information)
18. [Command cheat sheet](#18-command-cheat-sheet)
19. [Glossary](#19-glossary)

## 1. Understand what will happen

POCArchitect turns an authorized source into a structured architecture and risk
analysis report. A source can be:

- a public GitHub repository;
- a local directory you are authorized to read;
- a package or container-image identifier;
- a download or advisory URL; or
- a text file containing several sources for batch processing.

For a public GitHub repository or local directory, POCArchitect can select a
bounded set of relevant text files as grounding. Before a provider call, it
redacts recognized secret patterns and presents transfer metadata for review.
The GUI lets you include or exclude individual files. A report is written only
after a provider returns a successful response.

POCArchitect does **not**:

- execute the source or proof-of-concept code;
- prove that generated findings are correct;
- provide private GitHub authentication automatically;
- upload reports unless you explicitly run a publishing command;
- expose the GUI to other computers; or
- make a provider call during `quickstart`, `demo`, an offline preflight, or a
  dry run.

### What can cost money?

Installation, offline checks, the local demo, source comparison, and dry runs
do not make a billable model request. A real cloud-provider analysis may incur
charges under your provider account. The transfer review includes an estimated
input cost when pricing is known. You can set a maximum with the GUI or the
`--max-estimated-cost` terminal option.

### What data can leave the computer?

Only a real approved provider run can send data to an external model provider.
The provider request can contain the source identifier, selected and redacted
grounding content, your risk posture and target environment, and the packaged
analysis instructions. Read the transfer review and remove files you do not
want to send. Redaction reduces risk but is not a substitute for your review.

## 2. Choose the GUI or terminal

Most first-time users should use the **GUI**. It provides guided configuration,
provider-readiness feedback, file-by-file transfer controls, cost estimates,
live progress, and a searchable report library.

Use the **terminal** when you need batch processing, automation, machine-readable
JSON output, or every advanced option. Both interfaces use the same underlying
analysis service and safety boundary.

This guide installs both. You can switch between them at any time.

## 3. Install Python and Git

You need:

- Python 3.10 or newer;
- Git for downloading the repository and grounding public GitHub sources;
- a modern web browser for the GUI; and
- internet access during installation and for cloud-provider or public GitHub
  operations.

Python and Git are available from their official download pages:

- [Python downloads](https://www.python.org/downloads/)
- [Git downloads](https://git-scm.com/downloads)

You do not need administrator access after those applications are installed.

### Windows check

Open **Windows Terminal**, choose **PowerShell**, and run:

```powershell
py --version
git --version
```

Successful output resembles:

```text
Python 3.12.x
git version 2.x.x
```

Your exact versions can differ. Python must be at least 3.10.

If `py` is not recognized, install Python from the official installer and
enable its launcher or PATH option. If `git` is not recognized, install Git.
Close and reopen Windows Terminal after either installation, then repeat the
checks.

### macOS or Linux check

Open **Terminal** and run:

```bash
python3 --version
git --version
```

Successful output resembles:

```text
Python 3.12.x
git version 2.x.x
```

If Python is missing or older than 3.10, install a current Python release. If
Git is missing, install it using the official installer or your operating
system's package manager. Open a new terminal and repeat the checks.

On Debian or Ubuntu, the typical prerequisite command is:

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip git
```

On Fedora, the typical command is:

```bash
sudo dnf install python3 python3-pip git
```

These system commands install prerequisites only. Do not use `sudo` for the
POCArchitect installation later in this guide.

## 4. Get the POCArchitect files

### Recommended: clone with Git

In a folder where you keep projects, run the commands for your system.

Windows PowerShell:

```powershell
git clone https://github.com/rikterskale/POCArchitect-AI-Agent.git
Set-Location .\POCArchitect-AI-Agent
```

macOS or Linux:

```bash
git clone https://github.com/rikterskale/POCArchitect-AI-Agent.git
cd POCArchitect-AI-Agent
```

### Alternative: download a ZIP

If you cannot use Git, download the repository ZIP, extract it to a folder you
own, and open a terminal in that extracted folder. ZIP installations work, but
you must download a new ZIP to update later; `git pull` will not work.

### Confirm that you are in the correct folder

Windows PowerShell:

```powershell
Get-ChildItem README.md, pyproject.toml
```

macOS or Linux:

```bash
ls README.md pyproject.toml
```

**Success check:** both filenames are printed. All commands in the rest of this
guide must be run from this folder unless a section explicitly says otherwise.

If the files are not found, locate the extracted or cloned
`POCArchitect-AI-Agent` folder and enter it with `Set-Location` on PowerShell or
`cd` on macOS/Linux.

## 5. Create an isolated environment and install

A virtual environment keeps POCArchitect's Python packages separate from the
rest of your computer. The environment used here is a folder named `.venv`
inside the repository.

### Windows PowerShell

Run:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[gui]"
```

If PowerShell says script execution is disabled, allow activation for this
terminal only, then retry it:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

The policy change ends when you close that terminal.

### macOS or Linux

Run:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[gui]'
```

### Confirm that the environment is active

Many terminals show `(.venv)` at the start of the prompt. You can also check
the Python path.

Windows PowerShell:

```powershell
Get-Command python
```

macOS or Linux:

```bash
which python
```

**Success check:** the printed path is inside this repository's `.venv` folder.
Then verify POCArchitect:

```text
python -m pocarchitect --version
```

Expected output starts with `POCArchitect v`.

> [!TIP]
> Every time you open a new terminal, return to the repository folder and
> activate `.venv` again. You install only once, but you activate once per
> terminal session.

To activate again later:

```powershell
.\.venv\Scripts\Activate.ps1
```

```bash
. .venv/bin/activate
```

## 6. Prove the installation works without credentials

Run the complete credential-free first-day check:

```text
python -m pocarchitect quickstart
```

This command:

1. checks the local installation and report directory;
2. uses no cloud credential;
3. uses a deterministic offline response without starting a server;
4. creates a real demonstration report under `reports/demo/`; and
5. makes no network request and incurs no provider cost.

**Success check:** the diagnosis passes and a report path under `reports/demo/`
is printed. Open that Markdown file in a text editor to confirm that a report
was created.

This verifies the command-line installation. After you launch the GUI, its
**Create credential-free demo** action gives you a second, one-click check of
the complete browser-to-report experience. Neither path needs provider setup.

If you want to run the two parts separately:

```text
python -m pocarchitect doctor --offline
python -m pocarchitect demo
```

For a safe prompt preview that creates no report and contacts no source or
provider, run:

```text
python -m pocarchitect --url https://github.com/example/poc --no-ingest --dry-run --no-color
```

The `example/poc` URL is intentionally a placeholder. `--no-ingest` prevents a
clone attempt, and `--dry-run` stops before any provider call.

For the same safe check as machine-readable JSON Lines, run:

```text
python -m pocarchitect --url https://github.com/example/poc --no-ingest --dry-run --format json --no-color
```

If any command fails, do not configure a real provider yet. Go to
[Troubleshoot problems](#15-troubleshoot-problems), fix the installation, and
repeat `quickstart` until it succeeds.

## 7. Configure a provider safely

An analysis of a real source needs either a cloud provider or a running local
OpenAI-compatible endpoint. You need only one.

> [!TIP]
> Provider setup is optional for the credential-free GUI demo. To see the
> finished experience first, skip to [Launch and use the GUI](#8-launch-and-use-the-gui),
> create the demo, and return here only when you want to analyze a real source.

| Choice | What you need | Credential name |
|---|---|---|
| xAI | An xAI account and API key | `XAI_API_KEY` |
| OpenAI | An OpenAI API account and key | `OPENAI_API_KEY` |
| Groq | A Groq API account and key | `GROQ_API_KEY` |
| Local endpoint | A running OpenAI-compatible service and model | No cloud key |

Provider subscriptions and chat-product subscriptions do not necessarily
include API usage. Obtain the credential from the provider's API console and
review that provider's pricing and data-handling terms before a real run.

### Recommended: use the guided setup

If the GUI is already running, leave it open. Open a second terminal in the
repository folder, activate `.venv`, and run:

```text
pocarchitect setup
```

The wizard asks you to:

1. choose `xai`, `openai`, `groq`, or `local`;
2. paste the matching cloud key using hidden input, or enter a local endpoint;
3. run readiness checks; and
4. optionally run another safe dry run.

For a cloud provider, the key is written to `.env` in the current repository
folder and is not printed. For a local provider, the wizard checks the endpoint
but does not manage or start the local service.

Return to the GUI and select **Recheck** in the **Provider readiness** card. A
newly added key becomes available immediately. If setup replaces a key that the
GUI process had already loaded, restart the GUI before using the replacement.

After setup, view the effective configuration with masked credentials:

```text
pocarchitect config
```

### Manual cloud-provider setup

Use this path if you prefer to edit the configuration yourself.

Windows PowerShell:

```powershell
Copy-Item .env.example .env
notepad .env
```

macOS:

```bash
cp .env.example .env
open -e .env
```

Linux:

```bash
cp .env.example .env
nano .env
```

Replace only the placeholder for the provider you will use. For example:

```text
OPENAI_API_KEY=replace_this_with_your_real_key
```

Do not add quotes unless the provider's key itself requires them. Save the
file, close the editor, and verify that Git ignores it:

```text
git check-ignore .env
```

**Success check:** Git prints `.env`. Never run `git add -f .env`, paste a key
into a terminal command, place it in a screenshot, or include it in an issue.

Verify the selected cloud provider without printing the key:

```text
pocarchitect preflight --provider openai
```

Replace `openai` with `xai` or `groq` when appropriate.

### Local provider setup

POCArchitect's default local endpoint is:

```text
http://localhost:11434/v1
```

Your local service must already be running and expose an OpenAI-compatible API.
It must also have the model you select. Check the endpoint with:

```text
pocarchitect preflight --provider local --base-url http://localhost:11434/v1
```

This confirms the endpoint's model-list response. It does not prove that a
specific model can complete the full report prompt. See the
[local-provider guide](ollama-setup-guide.md) for the Ollama-oriented setup and
troubleshooting path.

## 8. Launch and use the GUI

### Start the GUI

With `.venv` active and from the repository folder, run:

```text
pocarchitect gui
```

The terminal remains occupied while the GUI runs. Your default browser should
open automatically.

**Success check:** the browser shows POCArchitect with a **Ready** and **Secure
local session** indicator. The terminal shows the local address but no request
log noise.

Do not close the terminal while using the GUI. Press `Ctrl+C` in that terminal
when you are finished.

### If the browser does not open

Stop the command with `Ctrl+C`, then run:

```text
pocarchitect gui --no-open
```

Copy the complete one-time launch URL printed in the terminal, including the
`?token=...` part, and paste it into your browser. Do not share that URL.

If port 8765 is already in use, choose another port:

```text
pocarchitect gui --port 8876
```

### See the finish line without setup

Before entering any configuration, select **Create credential-free demo** in
the initial **Transfer review** panel. POCArchitect creates and opens a
deterministic local example report without reading a source, contacting a
provider, using a credential, running plugins, or incurring cost.

This proves the browser-to-report path and places the example under
`reports/demo/`, where it is also available from **Reports**. Select **New
analysis** from the completed demo when you are ready to enter an authorized
source. A real analysis still requires the normal transfer review and explicit
approval.

### Configure the analysis

The left panel is **Analysis configuration**.

1. Choose **Repository or source** for a GitHub repository, package, image, or
   advisory URL. Choose **Local directory** for a folder already on this
   computer.
2. Enter the source. Accepted examples include `owner/repository`,
   `pypi:package`, `docker:image`, and an HTTP(S) URL.
3. Choose the configured provider.
4. Review the model. For a local provider, the model name must exist on the
   local service.
5. Choose the risk posture and target environment.
6. Keep **Ground source files** enabled when you want bounded evidence from a
   public GitHub repository or local directory.
7. Keep **Include mitigations** enabled when the report should include defensive
   guidance.

The provider-readiness card on the right reports whether a cloud credential is
present. It never displays the credential value. The GUI preselects the default
provider when it is ready; otherwise it preselects the first configured cloud
provider. If no cloud provider is configured, it keeps the default visible and
offers the exact setup command.

If you add a previously missing key to `.env` while the GUI is open, select
**Recheck** in the provider-readiness card. The new key becomes available without
a restart. If you replace the value of a key that was already loaded, restart
the GUI so the original process environment cannot silently change underneath
an active session.

### Optional advanced controls

Open **Advanced controls** only when needed:

- **Output format** also exports Markdown, HTML, PDF, or JSON.
- **Maximum input cost** blocks the run if its estimated input cost is higher.
- **Output directory** changes where the report is written.
- **OSV enrichment** queries public vulnerability records for exact dependency
  versions discovered in the selected text.
- **Compare with previous** saves a diff against the latest matching report.
- **Create safe scaffold** materializes a candidate implementation and draft
  verification contract from the report.

Network enrichment can take additional time. Start with the defaults for your
first report.

### Prepare the transfer review

Select **Prepare transfer review**.

At this point POCArchitect may read or clone the source, but it has **not** made
a model-provider call. The configuration locks so the review always matches
the prepared request.

If you need to change an entry, select **Edit configuration**. Your form values
remain in place, and the prepared review is discarded so you can prepare a new
one that matches the revised settings.

The transfer review shows:

- the selected file count;
- total selected file size;
- estimated input tokens and cost;
- recognized secret-pattern redactions; and
- the exact bounded files proposed for transfer.

Uncheck any file that should not leave the computer. Size, token, cost, and
redaction metadata are recalculated locally after each change. A prepared
review expires after 30 minutes and can be approved only once.

If preparation reports that ingestion failed, fix the URL, Git, permissions,
or network problem. No provider call is made after a grounding failure. If you
intentionally want URL-only context, start a new analysis and disable **Ground
source files**.

### Approve and run

Only after the transfer looks correct:

1. Read the authorization statement.
2. Select its checkbox.
3. Select **Approve and run analysis**.

The progress view shows the queue, provider, report-writing, and completion
phases. If the page refreshes, the GUI recovers the active run while the same
terminal process remains open. Do not submit the same source repeatedly while
a run is active.

### Review and save the result

After completion you can:

- read the safely rendered report;
- copy the Markdown;
- download the selected export format; or
- open **Reports** to search recent Markdown reports.

The report library includes Markdown reports in the default output directory,
credential-free reports under `reports/demo/`, and reports written to a custom
output directory during the current GUI session.

Generated model output can be wrong or incomplete. Review claims, commands,
and mitigations before acting on them.

## 9. Create a report from the terminal

The GUI is recommended for the first run, but the equivalent terminal workflow
is useful for repeatable commands.

### Public GitHub repository

Replace `OWNER/REPOSITORY` with an authorized public repository:

```text
pocarchitect --url https://github.com/OWNER/REPOSITORY --provider openai --curate
```

`--curate` lets you exclude selected file numbers before the transfer preview.
Replace `openai` with the provider you configured.

### Local directory

Windows example:

```powershell
pocarchitect --path "C:\Users\YourName\source-project" --provider openai --curate
```

macOS or Linux example:

```bash
pocarchitect --path "/home/yourname/source-project" --provider openai --curate
```

Use a real path that you are authorized to read.

### URL-only analysis

For a non-GitHub URL, package identifier, container image, or an intentional
URL-only GitHub analysis:

```text
pocarchitect --source pypi:example-package --provider openai --no-ingest
```

### Preview before a real run

Add `--dry-run` to preview the request without contacting the provider:

```text
pocarchitect --url https://github.com/OWNER/REPOSITORY --provider openai --no-ingest --dry-run
```

Use `--full` with `--dry-run` to print the entire provider-facing prompt. Treat
that output as potentially sensitive when real local context is included.

### Limit estimated input cost

This example blocks the provider call if the known estimated input cost exceeds
ten US cents:

```text
pocarchitect --url https://github.com/OWNER/REPOSITORY --provider openai --max-estimated-cost 0.10
```

### What to expect in the terminal

A real grounded command performs preflight, selects files, shows a redacted
preview, and asks for confirmation. Enter `y` only when the source, provider,
and transfer are authorized. The `--yes` option bypasses confirmation; do not
use it until you have already reviewed and approved an automated workflow.

On success, the command prints the absolute report path. On failure, it exits
without creating a successful report and prints a corrective message.

## 10. Understand grounding, redaction, cost, and approval

### Grounding limits

Grounding is intentionally bounded. POCArchitect:

- scans at most 20,000 files;
- stops if the scanned source exceeds 5,000,000 bytes;
- skips individual files larger than 250,000 bytes;
- selects at most 25 matching files;
- truncates selected file content after 7,500 characters per file; and
- stops if selected grounding exceeds 180,000 characters.

It ignores common dependency and environment folders such as `.git`, `.venv`,
`node_modules`, and `__pycache__`, and it does not follow directory symlinks.

### Redaction

POCArchitect recognizes common API-key, token, password, bearer-token,
private-key, and cloud-credential patterns and replaces their values before the
provider request. The review reports categories and match counts, not secret
values.

Pattern matching cannot recognize every sensitive value. Do not store secrets
in source when avoidable, and always review selected filenames and metadata.

### Approval boundary

Preparation and approval are separate operations. In the GUI, the prepared
content remains in backend memory, expires, and is consumed after one approval.
In the terminal, an interactive confirmation is required unless `--yes` was
explicitly provided.

### Cost estimate

The estimate covers input tokens when the selected model has known pricing. It
is approximate and may not include provider-specific billing details, output
tokens, taxes, minimum charges, or later pricing changes. An unavailable
estimate is not the same as a free request.

## 11. Work with reports

Reports are written to `reports/` by default. A report filename begins with
`POCAnalysis_` and includes a source slug and UTC timestamp. The Markdown front
matter records the source, provider, model, time, ingestion result, selected
file count, and response hash.

### List report history

```text
pocarchitect history --output-dir reports
```

### Compare two reports

```text
pocarchitect diff reports/older-report.md reports/newer-report.md
```

Replace both filenames with real reports. Add `--output reports/change.diff`
to save the comparison.

### Export a Markdown report

```text
pocarchitect export reports/your-report.md --format html
```

Available formats are `markdown`, `html`, `pdf`, and `json`. Replace the sample
filename before running the command.

### Create a safe scaffold

```text
pocarchitect scaffold --report reports/your-report.md --output blueprint
```

The scaffold materializes strictly named files from the report's
`Implementation Bundle` when present and creates a draft verification contract.
Generated code is still only a candidate. Inspect every file, add meaningful
acceptance tests, document the approved lab scope, and use the separate
`pocarchitect verify run` gate before calling it working. Follow the
[Working PoC Verification Guide](verification-guide.md) for the complete
contract and sandbox workflow.

### Keep or back up reports

Reports may contain sensitive source-derived information even after redaction.
Store them according to your organization's data-handling policy. Back up any
reports you need before deleting the repository or report directory.

## 12. Analyze multiple sources

### Provider-free comparison

Compare two local candidates without a model-provider request:

```text
pocarchitect compare ./candidate-a ./candidate-b --output reports/comparison.md
```

### Batch provider analysis

Create a plain-text file such as `sources.txt`. Put one authorized source on
each line. Blank lines and lines beginning with `#` are ignored:

```text
# Authorized assessment sources
https://github.com/OWNER/FIRST-REPOSITORY
https://github.com/OWNER/SECOND-REPOSITORY
```

Then run:

```text
pocarchitect --batch sources.txt --provider openai
```

Batch progress is recorded in `reports/batch_progress.json` by default. A
rerun skips completed items and retries unfinished ones.

Inspect recovery state without making a provider call:

```text
python -m pocarchitect --format json --no-color batch-status --batch-state reports/batch_progress.json
```

Reset the ledger recoverably:

```text
python -m pocarchitect --format json --no-color batch-reset --batch-state reports/batch_progress.json --yes
```

Reset moves the old ledger to a timestamped backup instead of deleting it.
Inspect failures and keep the backup until the replacement batch succeeds.

## 13. Set reusable project defaults

Run this inside a source repository when you want that project to remember
non-secret defaults:

```text
pocarchitect init
```

It creates `.pocarchitect.toml`. You can store provider name, risk level,
target operating system, mitigation preference, output directory, and report
format there. Provider keys never belong in that file; keep them in `.env` or a
protected environment variable.

Explicit terminal options override project defaults. Existing environment
variables override matching `.env` keys. View the effective result with:

```text
pocarchitect config
```

View provider defaults and known model alternatives with:

```text
pocarchitect models
```

## 14. Use POCArchitect safely every day

Before each real analysis:

- Confirm written authorization and scope.
- Activate the correct `.venv`.
- Confirm the selected provider and model.
- Check that the source is the intended public repository or local directory.
- Review every selected grounding filename.
- Review redaction counts and remove questionable files.
- Review the estimated cost or set a cost limit.
- Approve the transfer only once you understand it.

After each analysis:

- Read the entire report before using its conclusions.
- Independently verify high-impact findings and commands.
- Protect the report as assessment data.
- Stop the GUI with `Ctrl+C` when finished.
- Keep `.env` private and never attach it to an issue.

Never expose or reverse-proxy the GUI. It is intentionally bound to this
computer and designed for one local operator, not as a hosted or multi-user
service.

## 15. Troubleshoot problems

Start with the built-in diagnosis:

```text
pocarchitect doctor --offline
```

For a configured cloud provider:

```text
pocarchitect doctor --provider openai
```

For a local provider:

```text
pocarchitect doctor --provider local --base-url http://localhost:11434/v1
```

Replace `openai` or the endpoint as needed.

### Troubleshooting matrix

| Symptom | Likely cause | Fix | Confirm the fix |
|---|---|---|---|
| `py`, `python3`, or `python` is not recognized | Python is missing or the terminal has not refreshed | Install Python 3.10+, close the terminal, and open a new one | Run the matching version command from Section 3 |
| Python is older than 3.10 | An unsupported interpreter is first on PATH | Install a newer Python and recreate `.venv` with it | `python --version` inside `.venv` reports 3.10+ |
| `git` is not recognized | Git is missing or not on PATH | Install Git and reopen the terminal | `git --version` prints a version |
| `pyproject.toml` is not found | The terminal is in the wrong folder | Enter the cloned or extracted repository folder | The folder check in Section 4 prints both files |
| PowerShell blocks `Activate.ps1` | Script execution is restricted | Use the process-scoped policy command in Section 5 | The Python path points inside `.venv` |
| `externally-managed-environment` appears | Installation is using system Python instead of `.venv` | Activate `.venv`; do not use `sudo pip` | `python -m pip show pocarchitect` prints package details |
| `No module named pocarchitect` | `.venv` is inactive or installation failed | Activate `.venv`, then rerun `python -m pip install -e ".[gui]"` | `python -m pocarchitect --version` succeeds |
| Dependency download or certificate error | Network, proxy, certificate, or package-index access failed | Confirm browser access, then configure the organization's approved proxy/certificate settings and retry | The installation finishes without an error |
| GUI says dependencies are not installed | The project was installed without the GUI extra | Run `python -m pip install -e ".[gui]"` inside `.venv` | `pocarchitect gui --help` succeeds |
| Browser does not open | Automatic browser launching is unavailable | Run `pocarchitect gui --no-open` and copy the complete launch URL | The workspace shows **Ready** |
| `Address already in use` | Another application is using port 8765 | Run `pocarchitect gui --port 8876` | The browser opens the new address |
| `Open the GUI from its launch URL` or `GUI session required` | The browser lacks the launch cookie or the process was restarted | Stop and relaunch with `--no-open`, then use the new complete URL | `/` opens the workspace rather than an error |
| GUI shows **Disconnected** | The terminal process stopped or the local connection was interrupted | Confirm the GUI terminal is still running; otherwise relaunch it | The status returns to **Ready** |
| Provider needs configuration | The selected cloud key is missing, a placeholder, or the GUI has not rechecked it | Run `pocarchitect setup` or fix `.env`, then select **Recheck**; restart only when replacing a key already loaded by the GUI | Provider readiness reports available |
| `No API key found` | The key name does not match the selected provider | Use `XAI_API_KEY`, `OPENAI_API_KEY`, or `GROQ_API_KEY` exactly | Provider preflight passes |
| Local endpoint unavailable | The local service is stopped, its URL differs, or it lacks `/v1` compatibility | Start the service and pass its correct base URL | Local preflight passes |
| Model not found | The model name is unavailable to the account or local service | Run `pocarchitect models` and check the provider's available models | Retry with an available model |
| GitHub ingestion fails | The repository is private/unreachable, Git is unavailable, or network access failed | Confirm authorization, public access, Git, URL, and network; then retry | Preparation lists grounded files |
| Source exceeds a limit | The directory is too large for bounded grounding | Analyze a smaller authorized subtree or disable ingestion for URL-only context | Preparation completes within the documented limits |
| Estimated cost exceeds limit | The selected files exceed your configured threshold | Remove files or deliberately raise the limit in a new analysis | Review shows the payload is within the limit |
| No grounding files appear | No eligible text files matched, or grounding was disabled | Confirm the source and toggle; use URL-only context only when intentional | Review shows expected files or clearly states URL-only |
| Report cannot be written | The output path is unavailable or read-only | Choose a folder you own and run offline preflight with `--output-dir` | Preflight reports the directory is writable |
| Batch exits with status 1 | At least one item failed while others continued | Inspect `batch-status`, correct the failed sources, and rerun the same batch | Failed count becomes zero |
| A command displays too much terminal styling | The terminal does not support the output | Add `--no-color`; use `--format json` for automation | Output is plain text or JSON Lines |

### Still stuck? Rebuild the virtual environment

Do this only after closing programs that use `.venv`. Preserve `.env` and
reports; they are separate from `.venv`.

1. Run `deactivate` if the environment is active.
2. Delete only the `.venv` folder inside the repository.
3. Repeat Section 5.
4. Repeat `python -m pocarchitect quickstart`.

Do not delete the entire repository as a first troubleshooting step.

## 16. Update, stop, clean up, or uninstall

### Stop a running command or GUI

Press `Ctrl+C` in the terminal running POCArchitect. The GUI does not install a
background service. POCArchitect also does not start or stop your local model
provider.

### Leave the virtual environment

```text
deactivate
```

This does not uninstall anything. Activate `.venv` again the next time you use
the tool.

### Update a Git clone

From the repository folder:

```text
git status --short
git pull
python -m pip install -e ".[gui]"
python -m pocarchitect quickstart
```

If `git status` shows changes you made, preserve or commit them before pulling.
Do not discard local work just to update. For a ZIP installation, download and
extract a fresh ZIP instead.

### Remove demonstration output

The credential-free demo writes under `reports/demo/`. Inspect that directory
before deleting it. Keep real reports and batch-ledger backups you still need.

### Uninstall completely

1. Stop POCArchitect and run `deactivate`.
2. Back up reports you need.
3. Back up the provider key only if you have an approved secure destination.
4. Delete the repository folder.

Because the virtual environment and `.env` are inside the repository, deleting
the folder removes them too. POCArchitect does not install a system service.

## 17. Collect safe diagnostic information

Before opening an issue, run:

```text
python -m pocarchitect --version
python -m pocarchitect preflight --offline --format json --no-color
git status --short
```

Record:

- operating system;
- Python version;
- provider name, but never the key;
- the exact command with secrets and private paths removed;
- the exit code; and
- the smallest relevant error message.

Never attach `.env`, the launch URL, private source, or a full sensitive report.
Use the repository's [issue tracker](https://github.com/rikterskale/POCArchitect-AI-Agent/issues)
for non-sensitive problems and follow the [Security Policy](../SECURITY.md) for
vulnerabilities.

## 18. Command cheat sheet

| Goal | Command |
|---|---|
| Show the version | `python -m pocarchitect --version` |
| Prove first-day operation without credentials | `python -m pocarchitect quickstart` |
| Diagnose installation only | `pocarchitect doctor --offline` |
| Launch the GUI | `pocarchitect gui` |
| Print a protected GUI URL | `pocarchitect gui --no-open` |
| Configure a provider interactively | `pocarchitect setup` |
| Show masked configuration | `pocarchitect config` |
| Show provider/model choices | `pocarchitect models` |
| Safe, non-provider prompt preview | `python -m pocarchitect --url https://github.com/example/poc --no-ingest --dry-run --no-color` |
| Inspect batch state | `python -m pocarchitect --format json --no-color batch-status --batch-state reports/batch_progress.json` |
| List reports | `pocarchitect history --output-dir reports` |
| Show help | `pocarchitect --help` |

Root options such as `--format` and `--no-color` must appear before a subcommand
such as `batch-status`. Use the generated [CLI Reference](cli-reference.md) for
every command and option.

## 19. Glossary

- **API key:** A secret credential used to authorize requests to a cloud model
  provider.
- **Authorization:** Permission from the system or source owner to perform the
  assessment.
- **Batch:** Several sources processed from a text file.
- **Batch ledger:** The JSON file that records completed and failed batch items
  so work can resume.
- **CLI:** Command-line interface; the terminal version of POCArchitect.
- **Dry run:** A preview that stops before a model-provider request.
- **Candidate implementation:** Generated or copied code that has not yet passed
  its explicit verification contract.
- **Environment variable:** A named configuration value. Provider keys can be
  loaded from the local `.env` file.
- **Grounding:** Selected source content supplied to the model as evidence.
- **GUI:** Graphical user interface; POCArchitect's local browser workspace.
- **JSON Lines:** Machine-readable output containing one JSON object per line.
- **Local provider:** A model service running on this computer or a trusted
  local network endpoint through an OpenAI-compatible API.
- **Model:** The provider's AI system that generates the analysis response.
- **Preflight:** Checks performed before a real operation.
- **Provider:** The cloud or local service that hosts the selected model.
- **Redaction:** Replacement of recognized secret values before transfer.
- **Report:** The generated Markdown analysis and any requested export.
- **Repository:** A project folder managed by Git.
- **Source:** The repository, directory, package, image, or URL being analyzed.
- **Transfer review:** Metadata showing what is proposed for a provider request
  before approval.
- **VERIFIED PoC:** A reviewed implementation whose authorization-bearing build,
  tests, and artifact assertions all passed in the constrained sandbox, with
  retained JSON evidence.
- **Virtual environment:** The project-local `.venv` folder containing isolated
  Python packages.

## Continue learning

- [CLI Reference](cli-reference.md) — every command and option.
- [Configuration Reference](configuration-reference.md) — defaults and
  precedence.
- [Command Guide](command-guide.md) — automation, batch, Docker, and advanced
  workflows.
- [Local Provider Guide](ollama-setup-guide.md) — OpenAI-compatible local model
  setup.
- [Docker Guide](docker-guide.md) — container installation and report volumes.
- [Working PoC Verification Guide](verification-guide.md) — implementation
  bundles, contracts, sandbox controls, and evidence.
- [Security Policy](../SECURITY.md) — safe-use and vulnerability-reporting
  expectations.
