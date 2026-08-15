# POCArchitect Novice Usability Guide

| Field | Reviewed value |
|---|---|
| Project | POCArchitect AI Agent |
| Guide purpose | Beginner installation, first use, verification, recovery, and common operations |
| Status | **PARTIALLY VERIFIED** |
| Reviewed branch | <code>main</code> |
| Detected project version | <code>0.2.0</code> |
| Last documentation update | 2026-08-15 |
| Verified platforms | Existing Windows PowerShell virtual environment; Ubuntu CI uses Python 3.10–3.13; Docker CI builds the image and runs <code>--help</code> |
| Validation limitations | No clean-room installation, live provider request, live Ollama request, or native Docker Desktop run was performed in this review |

## 1. What This Guide Helps You Do

This guide takes a first-time user from a local checkout to a safe POCArchitect preview. The preview prints the provider-facing prompt but does not clone a repository, call an LLM, require a credential, or create a report.

## 2. Who This Guide Is For

Use this guide if you are installing POCArchitect from this repository and will analyze source you are authorized to inspect. It assumes you can open a terminal but does not assume prior Git, Python, Docker, or environment-variable experience.

## 3. What the Project Does

POCArchitect accepts one URL or a text file of URLs and prepares a Markdown analysis request for an LLM provider. For a public GitHub repository URL, it can shallow-clone the repository into a temporary directory and select matching source files as grounding. A successful provider call is saved as a Markdown report with metadata and a body hash.

## 4. What the Project Does Not Do

POCArchitect does not execute retrieved PoC source. It is not an API server, a vulnerability scanner, or a guarantee that an LLM response is accurate. Non-GitHub URLs are accepted but are not cloned for grounding. Private GitHub repository access is not configured by the project by default.

## 5. Important Safety, Cost, Data, or Authorization Notes

Only analyze repositories you are authorized to inspect. A real grounded run clones selected source from GitHub and sends a redacted preview to the selected provider after confirmation. Cloud-provider calls can incur charges. <code>--yes</code> bypasses confirmation, so use it only for an already-reviewed and authorized noninteractive job. Never paste a provider key into a command line or issue report.

## 6. Before You Begin

You need Python 3.10 or newer, Git, and a terminal: Windows Terminal with PowerShell on Windows or a Bash-compatible terminal on Linux. Check Python with <code>py --version</code> in PowerShell or <code>python3 --version</code> in Bash, and check Git with <code>git --version</code>. A provider credential is required only for a real cloud-provider run.

Ubuntu CI validates Python 3.10–3.13. The safe workflow was reviewed in an existing Windows virtual environment. macOS and clean Windows/Linux installations were not independently tested. The repository requires Python 3.10+ but does not enforce a processor-architecture restriction.

## 7. Basic Terms Explained

- **Repository:** a project folder tracked by Git.
- **Clone:** a local copy of a Git repository made with Git.
- **Virtual environment:** project-local Python packages kept separate from other projects.
- **Provider:** the cloud or local service that generates the report.
- **Environment variable:** a named value such as <code>XAI_API_KEY</code>; POCArchitect can load it from a local <code>.env</code> file.
- **Grounding:** selected files from a public GitHub repository included in the provider request.
- **Dry run:** a preview that stops before a provider call.
- **JSON Lines:** one JSON object per output line.

## 8. Choose the Correct Setup Path

Use the **native Python path** below for the simplest first experience. The Windows PowerShell and Bash commands install the same project. Use Docker only when you already use Docker; see the [Docker Guide](docker-guide.md). Use a local provider only after its local service is running; see the [Local OpenAI-Compatible Provider Guide](ollama-setup-guide.md).

## 9. Obtain or Clone the Repository

Run these commands in a folder where you keep source code.

### Windows PowerShell

~~~powershell
git clone https://github.com/rikterskale/POCArchitect-AI-Agent.git
Set-Location .\POCArchitect-AI-Agent
~~~

### Bash

~~~bash
git clone https://github.com/rikterskale/POCArchitect-AI-Agent.git
cd POCArchitect-AI-Agent
~~~

**Success indicator:** <code>README.md</code>, <code>pyproject.toml</code>, <code>pocarchitect/</code>, and <code>docs/</code> are visible in the current folder. If Git is not found, install Git using the official installer for your operating system, open a new terminal, run <code>git --version</code>, and repeat the clone command.

If you downloaded a ZIP instead, extract it to a folder you own and open a terminal in the extracted folder. ZIP downloads cannot use <code>git pull</code> for updates.

## 10. Enter the Correct Project Folder

All remaining native commands run from the repository root: the folder containing <code>pyproject.toml</code> and <code>README.md</code>.

~~~powershell
Get-ChildItem pyproject.toml, README.md
~~~

~~~bash
ls pyproject.toml README.md
~~~

**Success indicator:** both filenames are printed. If they are not, use <code>Set-Location</code> or <code>cd</code> to return to the folder created by the clone.

## 11. Install Required Software

Python and Git must be installed before project dependencies.

~~~powershell
py --version
git --version
~~~

~~~bash
python3 --version
git --version
~~~

**Success indicator:** Python reports 3.10 or newer and Git reports a version. If Python is older than 3.10, install a supported Python release, reopen the terminal, then recreate the virtual environment. Do not use administrator or root access for the project installation unless your operating system requires it to install Python or Git.

## 12. Install Project Dependencies

From the repository root, create a virtual environment and install the editable project. Editable means changes in this checkout are immediately used by the environment.

### Windows PowerShell

~~~powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[all]"
~~~

If PowerShell blocks activation, run this for the current terminal only, then activate again:

~~~powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
~~~

### Bash

~~~bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[all]'
~~~

**Success indicator:** the install completes without an error. If it reports a missing package or network error, confirm that Python 3.10+ is active, rerun the install command from the repository root, then repeat the verification in Section 16.

## 13. Configure the Minimum Required Settings

No configuration is needed for the safe preview or <code>preflight --offline</code>.

For an interactive guided setup, run:

~~~bash
pocarchitect setup
~~~

The wizard chooses a provider, writes a cloud key only to the current
directory's <code>.env</code> (or asks for a local endpoint), runs readiness
checks, and offers a safe dry run. It does not support redirected or
noninteractive input. Review masked effective settings later with
<code>pocarchitect config</code>.

For a real cloud-provider run, copy <code>.env.example</code> to <code>.env</code> in the repository root and replace **one** <code>your_key_here</code> value with a credential for the selected provider:

| Provider option | Required <code>.env</code> name |
|---|---|
| <code>--provider xai</code> | <code>XAI_API_KEY</code> |
| <code>--provider openai</code> | <code>OPENAI_API_KEY</code> |
| <code>--provider groq</code> | <code>GROQ_API_KEY</code> |

In PowerShell use <code>Copy-Item .env.example .env</code>; in Bash use <code>cp .env.example .env</code>. Existing environment variables take precedence over values in <code>.env</code>.

For a local provider, no cloud key is needed. Its default endpoint is <code>http://localhost:11434/v1</code>. Verify a running endpoint with:

~~~bash
python -m pocarchitect preflight --provider local --base-url http://localhost:11434/v1
~~~

## 14. Protect Passwords, Tokens, and Other Secrets

This repository ignores <code>.env</code>. Verify it before adding a key:

~~~bash
git check-ignore .env
~~~

**Success indicator:** Git prints <code>.env</code>. Keep the key out of shell history, screenshots, logs, report content, and issue descriptions. The project redacts recognized key and private-key patterns before a real transfer, but review the preview and do not rely on redaction as a substitute for protecting secrets.

## 15. Run the Safest First Example

From the repository root with the virtual environment active, run:

~~~bash
python -m pocarchitect --url https://github.com/example/poc --no-ingest --dry-run --format json --no-color
~~~

The URL is a placeholder. Because <code>--no-ingest</code> is present, POCArchitect does not contact it. <code>--dry-run</code> stops before the provider call, <code>--format json</code> produces JSON Lines, and <code>--no-color</code> removes terminal styling. This workflow was executed during this review.

## 16. Verify the First Run Succeeded

The safe example exits with code 0 and prints two JSON objects. The final object has <code>"event": "dry_run"</code> and the message <code>Dry-run complete; no provider call was made.</code>.

Also verify the local installation without credentials:

~~~bash
python -m pocarchitect preflight --offline --format json --no-color
~~~

**Success indicator:** the JSON event message is <code>Preflight passed.</code>
It checks Python 3.10+, imports for <code>typer</code>, <code>rich</code>,
<code>openai</code>, <code>dotenv</code>, and <code>tenacity</code>, a runnable
Git executable, the CLI command, prompt file, and resolved writable output
directory. This command may create the default <code>reports/</code> folder; it
creates and removes only <code>.write_test</code>.

To verify a custom report destination, include it in preflight:

~~~bash
python -m pocarchitect preflight --offline --output-dir ./my-reports
~~~

POCArchitect local-provider preflight requests only
<code>&lt;base-url&gt;/models</code>. It does not test chat completions, model
suitability, the full prompt, or report generation.

## 17. If Verification Fails: Diagnose and Fix It

If <code>python -m pocarchitect</code> is not found, confirm that the virtual environment is active and reinstall from the repository root:

~~~bash
python -m pip install -e '.[all]'
python -m pocarchitect --version
~~~

Expected result: <code>POCArchitect v0.2.0</code>.

If offline preflight reports a missing dependency, rerun the same install
command and then repeat the offline preflight. If it reports an output-directory
permission error, rerun it with
<code>--output-dir &lt;WRITABLE_FOLDER&gt;</code>; automatic preflight checks that
same resolved path on a real command. If the safe example attempts a provider
call, confirm both <code>--no-ingest</code> and <code>--dry-run</code> are
present exactly as shown.

## 18. Common Tasks

### Analyze one authorized public GitHub repository

In an interactive terminal, replace <code>&lt;AUTHORIZED_GITHUB_URL&gt;</code> with a public repository you are allowed to inspect:

~~~bash
python -m pocarchitect --url <AUTHORIZED_GITHUB_URL> --provider xai
~~~

You may also use <code>--url owner/repository</code> shorthand for GitHub.

POCArchitect performs preflight, displays a redacted transfer preview, and asks
for confirmation before sending source to the provider. Inspect the preview for
<code>WARNING: Ingestion failed</code>. A clone failure falls back to URL-only
warning context and can still proceed after approval; cancel unless that reduced
context is acceptable. A successful provider call saves a report with the
actual ingestion outcome.

### Inspect batch recovery state

~~~bash
python -m pocarchitect --format json --no-color batch-status --batch-state reports/batch_progress.json
~~~

The command emits one <code>batch_status</code> object with version, total,
successful, failed, and unknown counts. Root options such as
<code>--format</code> must appear before the subcommand.

### Reset batch recovery state without deleting history

~~~bash
python -m pocarchitect --format json --no-color batch-reset --batch-state reports/batch_progress.json --yes
~~~

This moves an existing state file to a timestamped <code>.bak</code> file. Check the printed backup path before starting a new batch.

## 19. Command and Option Basics

Use either <code>--url</code> or <code>--batch</code>, never both.
<code>--provider</code> accepts <code>xai</code>, <code>openai</code>,
<code>groq</code>, or <code>local</code>; its default is <code>xai</code>.
Default models are <code>grok-3</code>, <code>gpt-4o</code>,
<code>llama-3.1-70b-versatile</code>, and
<code>qwen2.5-coder:32b</code>, respectively. Claude/Gemini prompt wording does
not add CLI providers; another OpenAI-compatible service uses
<code>--provider local --base-url</code>.

<code>--risk-level</code> and <code>--target-os</code> accept free text and are
added to the provider request. <code>--include-mitigations</code> defaults to
enabled; use <code>--no-mitigations</code> to omit them. Root
<code>--format json</code> and <code>--no-color</code> also apply to
<code>batch-status</code> and <code>batch-reset</code> when placed before the
subcommand. Text dry runs show a summary unless <code>--full</code> is present.
Use <code>--open</code> to ask the operating system to open a completed report.
See the generated [CLI Reference](cli-reference.md).

## 20. Where Results, Logs, and Generated Files Are Stored

Successful real runs write
<code>POCAnalysis_&lt;url-slug&gt;_&lt;UTC timestamp&gt;.md</code> to
<code>reports/</code> by default; Docker/<code>IN_DOCKER</code> defaults to
<code>/reports</code>. Front matter records project, source URL, provider,
model, prompt asset, generation time, actual ingestion outcome, selected-file
count, and a SHA-256 of the provider response. Ingestion is one of
<code>disabled</code>, <code>url-only-non-github</code>,
<code>url-only-ingestion-failed</code>, or <code>github-shallow-clone</code>.
Dry runs create no reports.

Real text runs print the report's absolute path and a short preview. Viewer
opening through <code>--open</code> is best-effort. Interactive batches may show
progress and ETA; JSON and redirected output stays event-based.

Batch recovery state defaults to <code>reports/batch_progress.json</code>.
Version 2 requires a top-level <code>version: 2</code> and object-valued
<code>items</code>. Current records use <code>status</code>,
<code>updated_at</code>, and failure <code>error</code>. Unsupported/corrupt
state is preserved until <code>batch-reset</code> moves it to a backup. See the
[Command Guide](command-guide.md#version-2-batch-ledger) for the exact sample.

## 21. How to Stop the Project or Running Services

POCArchitect is a foreground command: press <code>Ctrl+C</code> to interrupt it. No background POCArchitect service is started. If you use a local provider such as Ollama, stop that provider using its own documented process; POCArchitect does not manage it. Docker commands that use <code>--rm</code> remove their container after exit.

## 22. Cleanup and Rollback

Keep reports and batch-state backups you may need before deleting anything. Run <code>deactivate</code> to leave the virtual environment. To remove the environment later, close terminals that use it and delete only the <code>.venv</code> folder inside this repository. To remove reports, delete only the chosen report directory after reviewing its contents. <code>batch-reset</code> is the recoverable way to reset batch state because it creates a backup instead of deleting the old ledger.

## 23. Update or Upgrade the Project

For a Git clone, from the repository root run:

~~~bash
git pull
python -m pip install -e '.[all]'
python -m pocarchitect preflight --offline --format json --no-color
~~~

If <code>git pull</code> reports local changes, inspect them with <code>git status</code> before deciding whether to keep, commit, or discard them. Do not delete local work just to update. ZIP downloads should be replaced by a fresh download because they have no Git update history.

## 24. Uninstall the Project

POCArchitect has no system service or global uninstall step when installed in the project virtual environment. Run <code>deactivate</code>, then remove the repository folder only after retaining any reports and <code>.env</code> values you need. Deleting the checkout also deletes its <code>.venv</code> and local <code>.env</code>; copy needed reports elsewhere first.

## 25. Troubleshooting Matrix

| Symptom or exact error | Most likely cause | Confirm the cause | Exact fix | Verify the fix |
|---|---|---|---|---|
| <code>python</code> or <code>py</code> is not recognized | Python is unavailable in this terminal | Run <code>py --version</code> on Windows or <code>python3 --version</code> on Bash | Install Python 3.10+, reopen the terminal, then recreate <code>.venv</code> | Run the version check again |
| <code>ModuleNotFoundError</code> | The environment is inactive or dependencies are missing | Run <code>python -m pip show pocarchitect</code> | Activate <code>.venv</code> and run <code>python -m pip install -e '.[all]'</code> | <code>python -m pocarchitect --version</code> prints the version |
| <code>FAIL: No API key found</code> | A real cloud-provider run lacks the matching key | Check <code>--provider</code> and the matching name in <code>.env</code> without printing its value | Copy <code>.env.example</code>, replace one placeholder, and rerun provider preflight | Provider preflight reports the selected key source |
| Local endpoint unavailable | The local service is stopped or uses another URL | Run local-provider preflight with its endpoint | Start the local service or use its OpenAI-compatible <code>--base-url</code> | Repeat the same preflight |
| Batch file not found | The <code>--batch</code> path is wrong | List the file from the repository root | Pass the correct relative or absolute path | Batch mode prints the file name |
| Confirmation required in noninteractive mode | A real run cannot show its prompt | Check for CI, redirected input, or Docker without <code>-it</code> | Use an interactive terminal, or add <code>--yes</code> only after review | The preview is followed by the expected confirmation behavior |
| Git ingestion fails or preview contains <code>WARNING: Ingestion failed</code> | URL is not a reachable public GitHub repository, Git is unavailable, or network is unavailable | Run offline preflight and inspect the transfer preview | Cancel the transfer, correct the cause, and retry; approve only if URL-only analysis is acceptable | Metadata says <code>github-shallow-clone</code> only after a completed clone |
| Batch exits 1 | At least one item failed after processing continued | Inspect <code>batch_complete.failed</code> and <code>batch-status</code> | Correct failed items and rerun the same ledger | Exit is 0 and failed count is 0 |

## 26. Known Limitations and Unsupported Scenarios

The project has no documented API or library interface. It does not provide
private-GitHub authentication, cloning for non-GitHub URLs, report caching, or a
public option to disable <code>include_mitigations</code>. Source candidates are
selected by fixed filename keywords/extensions, files over 250,000 bytes are
skipped, content is truncated at 7,500 characters, and only the first 25
matches are included. Cloud responses, live credentials/endpoints, native
Docker Desktop, macOS, and clean-room installation paths remain external or
unverified.

## 27. Collect Diagnostic Information and Report a Problem

Do not include provider keys, unauthorized source, or full report content in a public issue. Collect:

~~~bash
python -m pocarchitect --version
python -m pocarchitect preflight --offline --format json --no-color
git status --short
~~~

Include the operating system, Python version, provider name (not its key), command used with secrets removed, exit code, and the smallest relevant error output. Report it at the repository [issue tracker](https://github.com/rikterskale/POCArchitect-AI-Agent/issues).

## 28. Where to Learn More

- [CLI Reference](cli-reference.md) explains published options.
- [Configuration Reference](configuration-reference.md) lists provider keys, defaults, and precedence.
- [Docker Guide](docker-guide.md) covers the container path.
- [Local OpenAI-Compatible Provider Guide](ollama-setup-guide.md) covers Ollama-specific setup.
- [Windows supplement](guides/WINDOWS_NOVICE_USABILITY_GUIDE.md) and [Linux supplement](guides/LINUX_NOVICE_USABILITY_GUIDE.md) retain platform command ledgers.
- [Architecture](architecture.md) describes implementation components and boundaries.
- [Documentation Gap Analysis](DOCUMENTATION_GAP_ANALYSIS.md) records the current-tree audit and remediation closure evidence.
- [Historical Documentation Review](DOCUMENTATION_REVIEW_REPORT.md) is a point-in-time snapshot for commit <code>60d55...</code>, not current validation evidence.

## 29. Glossary

- **API key:** a secret credential used by a cloud provider.
- **Batch ledger:** the JSON file that records completed and failed batch items.
- **Dry run:** a command that previews the prompt and exits before a provider call.
- **Grounding:** selected repository content included in the provider request.
- **JSON Lines:** one JSON object per output line.
- **Local provider:** a service reachable through an OpenAI-compatible endpoint, such as a locally running Ollama service.
- **Provider:** the cloud or local service that creates the report response.
- **Report:** a Markdown file saved after a successful real provider response.
- **Virtual environment:** project-local Python packages isolated from other Python projects.
