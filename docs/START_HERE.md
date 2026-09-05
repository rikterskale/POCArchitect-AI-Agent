# Start Here: POCArchitect

This guide is for people who have never used POCArchitect, Python virtual
environments, or AI-provider APIs. Follow it in order. Every important step has
a **Success check** and a direct recovery path.

POCArchitect reviews an authorized proof-of-concept (PoC) source, creates a
security report and candidate implementation, and can prove that the reviewed
implementation works inside a controlled Docker sandbox.

> [!IMPORTANT]
> Use POCArchitect only on source and systems you own or have explicit written
> permission to assess. A generated report or scaffold is a candidate. It is a
> working PoC only after `verify run` reports **VERIFIED** and writes evidence.

## The shortest successful path

If Python, Git, and Docker are already installed:

1. Clone this repository.
2. Create and activate `.venv`.
3. Install POCArchitect.
4. Run `python -m pocarchitect quickstart`.
5. Run `pocarchitect gui` and create the credential-free demo.
6. Configure one model provider with `pocarchitect setup`.
7. Analyze one authorized source and create its scaffold.
8. Review the generated code, tests, authorization, and Docker image.
9. Run `pocarchitect verify run PATH_TO_SCAFFOLD`.
10. Call the result a working PoC only when the final status is **VERIFIED**.

The rest of this guide supplies the exact commands and fixes.

## Contents

1. [Know the finish line](#1-know-the-finish-line)
2. [Install prerequisites](#2-install-prerequisites)
3. [Install POCArchitect](#3-install-pocarchitect)
4. [Prove the installation works](#4-prove-the-installation-works)
5. [Create your first VERIFIED PoC](#5-create-your-first-verified-poc)
6. [Use POCArchitect day to day](#6-use-pocarchitect-day-to-day)
7. [Remediate a finding safely](#7-remediate-a-finding-safely)
8. [Troubleshoot and repair](#8-troubleshoot-and-repair)
9. [Update, back up, or uninstall](#9-update-back-up-or-uninstall)
10. [Use the cheat sheet and glossary](#10-use-the-cheat-sheet-and-glossary)

## 1. Know the finish line

POCArchitect separates analysis from execution:

```text
Authorized source
      ↓
Report + candidate implementation
      ↓
Human review + explicit test contract
      ↓
Locked-down Docker build and test
      ↓
VERIFIED status + retained JSON evidence
```

These labels have precise meanings:

| Label | Meaning |
|---|---|
| Report | AI-assisted analysis. Review it; it can be incomplete or wrong. |
| Candidate | Generated implementation files that have not passed the verification gate. |
| VERIFIED PoC | A reviewed candidate whose declared build, tests, artifacts, and sandbox cleanup all passed. |

Analysis may send selected, redacted source text to the model provider you
approve. Analysis does not execute retrieved repository code. Execution occurs
only when you separately approve `pocarchitect verify run`.

The verifier has no network, uses a read-only source snapshot and root
filesystem, runs as a non-root user, drops Linux capabilities, applies resource
and timeout limits, and removes its container afterward. Docker containers still
share the host kernel. Use a disposable VM or an equivalently isolated runner
for code outside your organization's container-risk tolerance.

**Success check:** You understand that “generated” is not “working”; only a
successful verification record supports the working-PoC claim.

## 2. Install prerequisites

For the smoothest path, use Python 3.12. The project supports Python 3.10
through 3.14.

| Requirement | Why it is needed | Official setup |
|---|---|---|
| Python 3.10–3.14 | Runs POCArchitect | [Python downloads](https://www.python.org/downloads/) |
| Git | Downloads POCArchitect and grounds public GitHub repositories | [Git downloads](https://git-scm.com/downloads) |
| Docker | Runs the controlled working-PoC verifier | [Docker Desktop](https://docs.docker.com/desktop/) or [Docker Engine](https://docs.docker.com/engine/install/) |
| Modern browser | Opens the optional local GUI | Use a supported current browser from your organization |

You can create reports without Docker. Docker is required before a candidate
can receive VERIFIED status.

### Windows

Install Python, Git, and Docker Desktop. Start Docker Desktop, then open
**Windows Terminal** and choose **PowerShell**:

```powershell
py --version
git --version
docker version
docker info
```

If a command is not recognized, finish that application's installer, close the
terminal, open a new one, and retry.

### macOS

Install Python, Git, and Docker Desktop. Start Docker Desktop, then open
**Terminal**:

```bash
python3 --version
git --version
docker version
docker info
```

### Linux

Install Python, its virtual-environment package, Git, and Docker Engine using
the instructions for your distribution. On Debian or Ubuntu, the Python and Git
prerequisites are commonly installed with:

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip git
```

Install Docker from the official Docker Engine guide, start it, and run:

```bash
python3 --version
git --version
docker version
docker info
```

Do not use `sudo pip`. If Docker reports a permission error, follow Docker's
documented Linux post-installation guidance or ask your administrator. Access
to the Docker daemon is security-sensitive and should follow your organization's
policy.

**Success check:** Python reports 3.10–3.14, Git reports a version, and
`docker info` ends without a daemon or permission error.

## 3. Install POCArchitect

### 3.1 Get the files

Open a terminal in a folder where you keep projects.

Windows PowerShell:

```powershell
git clone https://github.com/rikterskale/POCArchitect-AI-Agent.git
Set-Location .\POCArchitect-AI-Agent
Get-ChildItem README.md, pyproject.toml
```

macOS or Linux:

```bash
git clone https://github.com/rikterskale/POCArchitect-AI-Agent.git
cd POCArchitect-AI-Agent
ls README.md pyproject.toml
```

If Git is unavailable, download the repository ZIP from GitHub, extract it to a
folder you own, and open a terminal in that folder. A ZIP install works, but it
cannot be updated with `git pull`.

**Success check:** both `README.md` and `pyproject.toml` are listed.

### 3.2 Create an isolated Python environment

The `.venv` folder keeps POCArchitect's packages separate from system Python.

Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[gui]"
```

If PowerShell blocks activation, allow it for this terminal only:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

macOS or Linux:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[gui]'
```

Confirm the installed command:

```text
python -m pocarchitect --version
python -m pocarchitect preflight --offline --format json --no-color
```

**Success check:** the version starts with `POCArchitect v`, and every offline
preflight row passes.

> [!TIP]
> Install once, but activate `.venv` in each new terminal. Use
> `.\.venv\Scripts\Activate.ps1` on Windows or `. .venv/bin/activate` on
> macOS/Linux.

## 4. Prove the installation works

Run the complete credential-free check:

```text
python -m pocarchitect quickstart
```

Quickstart diagnoses the installation and creates a deterministic demonstration
report under `reports/demo/`. It does not need a provider key, contact a model
provider, start a server, or incur provider cost.

The same checks can be run separately:

```text
python -m pocarchitect doctor --offline
python -m pocarchitect demo
```

**Success check:** quickstart reports success and prints the path to a Markdown
file under `reports/demo/`.

### Try the local GUI

```text
pocarchitect gui --help
pocarchitect gui
```

Your browser should open a protected workspace on `127.0.0.1`. Select **Create
credential-free demo**. If the browser does not open, stop the command with
`Ctrl+C`, run `pocarchitect gui --no-open`, and paste the complete one-time URL
into your browser.

Never expose or reverse-proxy the GUI. It is a loopback-only workspace for one
local operator. Do not share its launch URL or token.

**Success check:** the GUI shows **Ready**, the demo completes, and its report
appears in **Reports**.

### Try a safe terminal preview

```text
python -m pocarchitect --url https://github.com/example/poc --no-ingest --dry-run --format json --no-color
```

The placeholder URL is intentional. This command does not clone a repository,
call a provider, or create a real analysis report.

## 5. Create your first VERIFIED PoC

This journey has four gates. Do not skip the review gate.

### 5.1 Configure one provider

Run the interactive setup wizard:

```text
pocarchitect setup
```

Choose xAI, OpenAI, Groq, or a local OpenAI-compatible endpoint. Cloud keys are
stored in the repository's ignored `.env` file and are never intentionally
printed. Only these exact cloud variable names are recognized:

- `XAI_API_KEY`
- `OPENAI_API_KEY`
- `GROQ_API_KEY`

Check the result without exposing the key:

```text
pocarchitect config
pocarchitect preflight --provider openai
git check-ignore .env
```

Replace `openai` with the provider you selected. For a local provider, use:

```text
pocarchitect preflight --provider local --base-url http://localhost:11434/v1
```

**Success check:** preflight reports that the selected provider is ready, and
`git check-ignore .env` prints `.env` for a cloud-provider setup.

> [!CAUTION]
> Never commit `.env`, paste a key into a command, include a key in a screenshot,
> or attach `.env` to an issue. Provider API usage can cost money. Review the
> transfer estimate and the provider's current pricing and data policy.

### 5.2 Analyze an authorized source and create a scaffold

The GUI is easiest:

1. Start `pocarchitect gui`.
2. Enter an authorized public GitHub repository or local directory.
3. Select the configured provider.
4. Keep **Ground source files** enabled.
5. Enable **Create safe scaffold** under **Advanced controls**.
6. Select **Prepare transfer review**.
7. Review every filename, redaction count, and estimated cost.
8. Remove anything that should not leave the computer.
9. Confirm authorization and select **Approve and run analysis**.

The equivalent terminal command for a public repository is:

```text
pocarchitect --url https://github.com/OWNER/REPOSITORY --provider openai --curate --scaffold --scaffold-output poc-blueprint
```

Replace `OWNER/REPOSITORY` and `openai`. For a private local checkout:

```text
pocarchitect --path ./authorized-source --provider openai --curate --scaffold --scaffold-output poc-blueprint
```

The terminal shows a transfer preview and asks before contacting the provider.
Do not use `--yes` until an automated workflow has an equivalent approval gate.

**Success check:** POCArchitect prints both the report and scaffold paths. The
terminal example creates `poc-blueprint/.pocarchitect/poc-verification.json`;
the GUI uses the source name in its scaffold path.

### 5.3 Review the candidate

Open the printed scaffold path in your editor. The terminal examples call this
folder `poc-blueprint`. Before execution:

1. Read every generated file.
2. Confirm dependencies are declared and intentionally pinned where practical.
3. Remove unrelated or unsafe behavior.
4. Replace placeholder tests with meaningful acceptance tests.
5. Make the test assert observable PoC behavior in an isolated local fixture.
6. Keep secrets, live credentials, and public targets out of the candidate.
7. Review `.pocarchitect/poc-verification.json`.

The contract starts as `draft`. Set a concise `authorization`, verify the
`image`, `build_commands`, `test_commands`, and `required_artifacts`, then set
`implementation_status` to `ready`. A ready contract must have at least one
explicit test command.

If you are creating a contract for an existing implementation instead, run:

```text
pocarchitect verify init ./authorized-poc --authorization "Ticket SEC-123; isolated lab"
```

This also creates a draft. See the focused [Working PoC Verification
Guide](verification-guide.md) for non-Python toolchains and the complete schema.

### 5.4 Prepare the reviewed Docker image

POCArchitect never pulls a verification image automatically. Pull and review
the exact image declared in the contract. For a Python 3.12 candidate, the
default example is:

```text
docker pull python:3.12-slim
docker image inspect python:3.12-slim
```

Use the contract's actual image for another toolchain. For durable evidence,
prefer a reviewed digest instead of a mutable tag. The verifier resolves the
local image to an immutable ID and starts Docker with that ID.

**Success check:** `docker image inspect` returns image metadata without an
error.

### 5.5 Run the verification gate

From the POCArchitect repository folder, replace `./poc-blueprint` if the GUI
printed a different scaffold path:

```text
pocarchitect verify run ./poc-blueprint
```

Read the confirmation and approve only the reviewed, authorized candidate. In
non-interactive CI, `--yes` is required because no prompt can be displayed:

```text
pocarchitect verify run ./poc-blueprint --yes
```

Interpret the result literally:

| Result | Meaning | Next action |
|---|---|---|
| `VERIFIED` / exit 0 | Every declared step and cleanup passed | Retain the JSON evidence with the assessment record |
| `NOT VERIFIED` / exit 1 | A build, test, artifact, or cleanup step failed | Open the evidence, fix the named step, and run again |
| Verification error / exit 2 | Contract, authorization, Docker, confirmation, or input was not ready | Correct the configuration; no working claim was made |

Evidence is private, collision-safe JSON under `reports/` unless you selected
another `--evidence` path. A changed source, contract, or image requires a new
verification.

**Success check:** the final event says **VERIFIED**, all step counts match, and
the evidence file exists. That is the working PoC.

## 6. Use POCArchitect day to day

### Start the GUI

```text
pocarchitect gui
```

Stop it with `Ctrl+C`. It does not install a background service.

### Analyze a local directory

```text
pocarchitect --path ./authorized-source --provider openai --curate
```

### Preview without a provider call

```text
pocarchitect --url https://github.com/OWNER/REPOSITORY --provider openai --no-ingest --dry-run
```

Add `--full` only when you are prepared to handle the full provider-facing
prompt as potentially sensitive output.

### Work with reports

Replace the sample filenames before commands that read an existing report:

```text
pocarchitect history --output-dir reports
pocarchitect diff reports/older-report.md reports/newer-report.md
pocarchitect export reports/your-report.md --format html
pocarchitect scaffold --report reports/your-report.md --output blueprint
pocarchitect compare ./candidate-a ./candidate-b --output reports/comparison.md
```

Reports can contain sensitive assessment data. Store and share them under your
organization's data-handling policy.

### Process several authorized sources

Create `sources.txt` with one URL per line. Blank lines and full-line comments
beginning with `#` are ignored:

```text
# Approved assessment scope
https://github.com/OWNER/FIRST-REPOSITORY
https://github.com/OWNER/SECOND-REPOSITORY
```

Run:

```text
pocarchitect --batch sources.txt --provider openai
```

Inspect or recover batch state without a provider call:

```text
python -m pocarchitect --format json --no-color batch-status --batch-state reports/batch_progress.json
python -m pocarchitect --format json --no-color batch-reset --batch-state reports/batch_progress.json --yes
```

Reset moves the existing ledger to a timestamped backup instead of deleting it.

### Remember non-secret project defaults

```text
pocarchitect init
pocarchitect config
pocarchitect models
```

`pocarchitect init` creates `.pocarchitect.toml`. Never store provider keys in
that file.

## 7. Remediate a finding safely

POCArchitect explains findings and mitigations; it does not silently modify the
reviewed repository. Use this controlled remediation loop:

1. Confirm the finding against source evidence and the authorized scope.
2. Reproduce it only in the isolated lab. Retain the baseline report and, when
   appropriate, baseline verification evidence.
3. Create a normal source-control branch in the affected project.
4. Make the smallest defensible fix and add a regression test.
5. Run that project's normal test and security checks.
6. Analyze the remediated source again.
7. Compare the before and after reports.
8. Confirm the vulnerable behavior is blocked and intended behavior still
   works.
9. Record the fix, test output, reviewer, and residual risk in the issue.

For a second analysis, use the same options and add `--diff`, or compare two
saved reports directly:

```text
pocarchitect diff reports/older-report.md reports/newer-report.md
```

Do not close an issue merely because a model suggested a patch or severity. A
human reviewer must validate the code change and evidence. For teams that need
durable finding states and approval gates, continue with the
[finding-driven workflow guide](finding-workflow.md).

**Success check:** the fix has a passing regression test, an independently
reviewed code change, and retained before/after evidence.

## 8. Troubleshoot and repair

Start with the built-in diagnosis:

```text
pocarchitect doctor --offline
pocarchitect doctor --offline --fix
```

Use `--fix` only after reading the proposed repair. For a configured provider:

```text
pocarchitect doctor --provider openai
```

### Troubleshooting matrix

| Symptom | Cause | Repair |
|---|---|---|
| `python`, `python3`, or `py` is not recognized | Python is missing or the terminal is stale | Install Python, open a new terminal, and repeat Section 2 |
| Python is older than 3.10 | Unsupported interpreter is first on PATH | Install Python 3.10–3.14 and recreate `.venv` |
| `git` is not recognized | Git is missing or not on PATH | Install Git and open a new terminal |
| `pyproject.toml` is missing | Terminal is in the wrong folder | Enter `POCArchitect-AI-Agent` and rerun the folder check |
| PowerShell blocks `Activate.ps1` | Script policy blocks activation | Use the process-scoped command in Section 3; do not change machine policy |
| `externally-managed-environment` | System Python is active | Activate `.venv`; never use `sudo pip` |
| `No module named pocarchitect` | `.venv` is inactive or installation failed | Activate it and repeat the install command |
| Dependency or certificate download fails | Network, proxy, CA, or package index is unavailable | Use your organization's approved proxy/CA settings and retry |
| GUI dependencies are missing | Installed without the GUI extra | Run `python -m pip install -e ".[gui]"` in the active environment |
| Browser does not open | Automatic browser launch failed | Use `pocarchitect gui --no-open` and open the full printed URL |
| `Address already in use` | Port 8765 is occupied | Run `pocarchitect gui --port 8876` |
| Provider needs configuration | Key is missing, placeholder, or stale in the GUI process | Run `pocarchitect setup`, then **Recheck** or restart after replacing a loaded key |
| Provider returns 401/403 | Key is invalid or lacks access | Correct the selected provider key; never paste it into an issue |
| Provider returns 429 | Rate or quota limit | Wait, reduce request frequency, or resolve quota with the provider |
| Model not found | Model is unavailable to the account or endpoint | Run `pocarchitect models` and choose an available model |
| GitHub ingestion fails | URL, Git, network, access, or repository visibility issue | Confirm the authorized public URL and run `git --version` |
| Report cannot be written | Output directory is missing or read-only | Choose a folder you own and preflight it with `--output-dir` |
| `Docker was not found` | Docker is not installed or not on PATH | Install Docker, open a new terminal, and run `docker info` |
| Docker is unavailable | Daemon is stopped or permission is denied | Start Docker Desktop/Engine and resolve daemon access under local policy |
| Verification image is unavailable | Contract image is not present locally | Review and explicitly `docker pull` that exact image |
| Implementation is still draft | Review gate has not been completed | Review code and contract, then set `implementation_status` to `ready` |
| Authorization is required | Contract scope is blank | Add the approved ticket/lab scope; do not invent authorization |
| Test command is required | Ready contract has no meaningful acceptance test | Add and review at least one explicit test command |
| `NOT VERIFIED` names a build or test | Candidate does not satisfy its contract | Read bounded stdout/stderr in the evidence and fix the named step |
| Required artifact failed | Declared output is missing or traverses a symlink | Correct the build or artifact path; do not weaken the assertion to hide failure |
| Verification timed out | Command exceeded its limit or hung | Fix the command; raise `--timeout` only with a documented reason |
| Evidence path already exists | Evidence is intentionally never overwritten | Choose a new evidence path; retain or deliberately archive the old record |
| Network-dependent test fails in verification | Sandbox networking is intentionally disabled | Use a self-contained local mock or a separately governed lab pipeline |

### Rebuild a damaged virtual environment

Close POCArchitect, run `deactivate` if available, and rename the old
environment instead of deleting it immediately.

Windows PowerShell:

```powershell
Rename-Item .venv .venv-old
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[gui]"
python -m pocarchitect quickstart
```

macOS or Linux:

```bash
mv .venv .venv-old
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[gui]'
python -m pocarchitect quickstart
```

After the new environment passes, remove `.venv-old` using your file manager or
your organization's normal cleanup process.

**Success check:** quickstart passes again before you retry a real source or
provider.

## 9. Update, back up, or uninstall

### Update a Git clone

Activate `.venv`, then run from the repository folder:

```text
git status --short
git pull --ff-only
python -m pip install -e ".[gui]"
python -m pocarchitect quickstart
```

If `git status` lists changes, preserve or commit your work before pulling. Do
not discard local work just to update. ZIP users should extract a fresh download
to a new folder and copy only approved configuration and reports.

### Back up

Back up these items according to your data policy:

- reports and verification evidence you must retain;
- batch ledgers and workflow state;
- reviewed project configuration; and
- provider credentials only to an approved secret manager.

Never put `.env` in an ordinary backup, ticket, chat, or source repository.

### Uninstall

1. Stop the GUI or command with `Ctrl+C`.
2. Run `deactivate`.
3. Back up required reports and evidence.
4. Delete the POCArchitect folder with your file manager.

POCArchitect does not install a system service. The local `.venv` and `.env`
are removed with the project folder.

### Ask for help safely

Collect these diagnostics:

```text
python -m pocarchitect --version
python -m pocarchitect preflight --offline --format json --no-color
git status --short
```

Include the operating system, Python version, sanitized command, exit code, and
smallest relevant error. Never attach `.env`, a GUI launch URL, private source,
provider output containing secrets, or an unredacted assessment report.

Use the [issue tracker](https://github.com/rikterskale/POCArchitect-AI-Agent/issues)
for non-sensitive defects. Report vulnerabilities privately through the
[Security Policy](../SECURITY.md).

## 10. Use the cheat sheet and glossary

### Command cheat sheet

| Goal | Command |
|---|---|
| Show help | `pocarchitect --help` |
| Show version | `python -m pocarchitect --version` |
| Prove the local installation | `python -m pocarchitect quickstart` |
| Diagnose without credentials | `pocarchitect doctor --offline` |
| Launch the local GUI | `pocarchitect gui` |
| Configure a provider | `pocarchitect setup` |
| Show masked configuration | `pocarchitect config` |
| Analyze an authorized repository | `pocarchitect --url https://github.com/OWNER/REPOSITORY --provider openai --curate` |
| Materialize a report manually | `pocarchitect scaffold --report reports/your-report.md --output blueprint` |
| Create a draft verification contract | `pocarchitect verify init ./authorized-poc --authorization "Ticket SEC-123; isolated lab"` |
| Verify a reviewed candidate | `pocarchitect verify run ./poc-blueprint` |
| List reports | `pocarchitect history --output-dir reports` |
| Inspect batch recovery | `python -m pocarchitect --format json --no-color batch-status --batch-state reports/batch_progress.json` |

Root options such as `--format` and `--no-color` appear before subcommands such
as `batch-status`. Use the generated [CLI Reference](cli-reference.md) for every
command and option.

### Glossary

- **Authorization:** Explicit permission defining what may be assessed and in
  which lab or environment.
- **Candidate implementation:** Generated or copied code that has not passed
  its verification contract.
- **Contract:** The reviewed image, build commands, test commands, artifacts,
  authorization, and readiness state used by the verifier.
- **Dry run:** A preview that stops before a model-provider request.
- **Evidence:** Private JSON recording digests, sandbox controls, image identity,
  step results, output, timing, and cleanup.
- **Grounding:** Selected source text supplied to the model as evidence.
- **Provider:** The cloud or local model service used for analysis.
- **Redaction:** Replacement of recognized secret patterns before transfer.
- **Scaffold:** Candidate implementation files materialized from a report's
  strict Implementation Bundle.
- **Transfer review:** The file, size, cost, and redaction summary shown before
  an approved provider request.
- **VERIFIED PoC:** A reviewed implementation whose declared build, tests,
  artifacts, and cleanup passed inside the constrained sandbox.
- **Virtual environment:** The repository-local `.venv` containing isolated
  Python packages.

## Continue learning

- [Working PoC Verification Guide](verification-guide.md) — contract schema,
  sandbox controls, evidence, and non-Python toolchains.
- [CLI Reference](cli-reference.md) — every command and option.
- [Command Guide](command-guide.md) — batch, Docker, automation, and advanced
  workflows.
- [Local Provider Guide](ollama-setup-guide.md) — Ollama-oriented setup.
- [Finding-driven Workflow](finding-workflow.md) — durable finding lifecycle and
  approval gates.
- [Security Policy](../SECURITY.md) — safe-use and vulnerability-reporting
  expectations.
