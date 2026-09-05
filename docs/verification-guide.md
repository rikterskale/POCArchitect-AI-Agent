# Working PoC Verification

POCArchitect treats “working” as an evidence-backed result, not a writing style.
A report or generated file is a **candidate implementation**. It becomes a
**VERIFIED PoC** only when every reviewed build command, acceptance test, and
required-artifact assertion in its contract succeeds inside the constrained
Docker verification boundary.

Use this workflow only for source and target behavior you are authorized to
test. Verification does not grant authorization or make an unsafe test safe.

## End-to-end workflow

1. Analyze authorized source and request a scaffold:

   ```text
   pocarchitect --url https://github.com/OWNER/REPOSITORY --scaffold
   ```

2. Inspect the generated report and candidate implementation. POCArchitect only
   materializes code blocks from the report's `Implementation Bundle` section
   when each block has a strict `File: relative/path` header. Absolute paths,
   traversal, credential files, repository-control paths, and POCArchitect's
   own control files are rejected.
3. Review every generated file and replace or add acceptance tests that assert
   observable behavior against a local mock or an explicitly authorized lab
   fixture. A generated scaffold without an implementation contains an
   intentionally failing test.
4. Review `.pocarchitect/poc-verification.json`. Add a concise authorization
   scope and keep `implementation_status` set to `draft` until the
   implementation and tests are ready.
5. Review and fetch the declared image yourself. Verification never pulls an
   image implicitly:

   ```text
   docker pull python:3.12-slim
   ```

   For repeatable long-lived contracts, replace the tag with the reviewed image
   digest after pulling it.
6. Change `implementation_status` to `ready`, then run:

   ```text
   pocarchitect verify run ./poc-blueprint --yes
   ```

   Omit `--yes` in an interactive terminal to receive a final confirmation.
   Non-interactive automation must provide `--yes` explicitly.
7. Retain the reported JSON evidence file with the assessment record. Exit code
   `0` and a final `poc_verified` event mean all contracted checks passed. Exit
   code `1` means a build, test, or artifact assertion failed. Exit code `2`
   means the contract, authorization, confirmation, or Docker boundary was not
   ready, so no working-PoC claim was made.

## Create a contract for an existing implementation

POCArchitect can infer conservative defaults for Python, Node.js, Rust, Go, and
Make-based projects:

```text
pocarchitect verify init ./authorized-poc \
  --authorization "customer-owned isolated lab"
```

The new contract starts as `draft`. To declare an already-reviewed project
ready while creating the contract:

```text
pocarchitect verify init ./authorized-poc \
  --authorization "customer-owned isolated lab" \
  --test-command "python -m unittest discover -s tests -v" \
  --ready
```

`--ready` requires at least one explicit `--test-command`; inferred commands
are review aids for draft contracts, not evidence that a test is meaningful.

For another toolchain, state the locally available image and commands
explicitly. Repeat command and artifact options to create multiple steps:

```text
pocarchitect verify init ./authorized-poc \
  --image vendor/reviewed-toolchain@sha256:DIGEST \
  --build-command "make" \
  --test-command "make acceptance" \
  --required-artifact "build/poc" \
  --authorization "ticket SEC-123 isolated lab"
```

Generated contracts are owner-readable/writable only on POSIX systems. Use
`--force` only after reviewing the existing contract; replacement is atomic and
does not follow a destination symlink.

## Contract schema

```json
{
  "authorization": "customer-owned isolated lab",
  "build_commands": ["python -m compileall -q ."],
  "image": "python:3.12-slim@sha256:REVIEWED_DIGEST",
  "implementation_status": "ready",
  "project_name": "authorized-poc",
  "required_artifacts": ["src/poc.py"],
  "schema_version": 1,
  "test_commands": ["python -m unittest discover -s tests -v"]
}
```

A draft for an unrecognized toolchain may leave build and test commands empty
so scaffolding can complete for manual configuration. A ready contract always
requires at least one explicit test command. Commands are executed by `/bin/sh`
inside the container because build systems require shell syntax; POCArchitect
never sends them through a host shell. Artifact paths must remain inside the
copied workspace. Each command has an independently enforced timeout.

## Sandbox controls

Before starting Docker, POCArchitect creates a bounded snapshot of the project.
It excludes version-control metadata, virtual environments, dependency caches,
`.env` variants, and non-regular files. The snapshot is limited to 25,000 files
and 512 MiB. Within its private temporary parent, copied modes are normalized
for the non-root container user while executable bits are preserved; the
original project is unchanged. The snapshot is then mounted read-only. The
build receives no host environment variables or provider credentials.

The verifier then applies all of these controls:

- no network (`--network=none`), including no access to external targets;
- read-only container root filesystem and read-only source snapshot;
- writable size-limited temporary filesystems only for `/workspace` and `/tmp`;
- non-root UID/GID `65534:65534`;
- all Linux capabilities dropped and `no-new-privileges` enabled;
- limits of 128 processes, 512 MiB memory, and one CPU;
- no Docker socket, host devices, host PID namespace, ports, or extra mounts;
- no implicit image pull; the locally reviewed image ID is recorded;
- forced cleanup of the uniquely named verification container; cleanup failure
  prevents VERIFIED status.

Docker containers share the host kernel and are not virtual machines. Use a
dedicated disposable VM or equivalently isolated runner when the source exceeds
your organization's container-risk tolerance. Network-dependent PoCs should use
a self-contained local mock in the same container or a separately governed lab
pipeline; this verifier intentionally does not provide public-target access.

## Evidence and claims

The private JSON evidence document records:

- a unique verification ID and UTC start/finish times;
- the authorization statement;
- a length-framed SHA-256 digest for the sanitized source snapshot and a
  SHA-256 digest for the contract;
- the requested image and locally resolved immutable image ID that was actually
  passed to Docker;
- every applied sandbox control;
- excluded paths;
- each preparation, build, test, artifact, and cleanup step with exit status,
  duration, timeout state, and bounded stdout/stderr. Artifact assertions reject
  symlinks in the artifact or any of its parent components.

Output is capped per stream so a noisy process cannot create unbounded evidence.
Do not put secrets in commands or tests; command text and captured output are
part of the evidence. A changed source tree, contract, or image requires a new
verification record. “Generated,” “scaffolded,” and “build instructions
provided” never mean VERIFIED.
