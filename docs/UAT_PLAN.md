# POCArchitect User Acceptance Test Plan and Record

## 1. Scope and execution record

This plan consumes every success criterion in the journey map in
`docs/USER_JOURNEY.md`, every documented alternate or error path, and the
input boundaries that materially affect first use, transfer approval, report
access, and recovery. Results below were recorded on 2026-09-04 on Linux with
Python 3.14, the repository at commit `7f4db4d`, and the Phase 5 tests in the
working tree. Third-party provider availability, billing, rate limits, and
model quality remain external integration acceptance conditions and are not
represented as passing local UAT results.

Automated evidence came from the repository's existing pytest framework,
FastAPI test client, Typer CLI runner, and Playwright 1.62 with Chromium. The
credential-free install, dependency check, version command, quickstart, and
documentation-command validator were also run directly from the terminal.

## 2. Journey-map cases

| Test ID | Precondition | Steps | Expected result | Actual result | Pass/Fail |
|---|---|---|---|---|---|
| UAT-J01 | Checkout and `/tmp/pocarchitect-completeness-venv` available. | Run `python -m pip install -e ".[gui]"`; run `python -m pip check`. | Install exits 0; dependency check exits 0. | Editable wheel built and installed as `pocarchitect-0.2.0`; pip printed `No broken requirements found.` | Pass |
| UAT-J02 | UAT-J01 passed. | Run `python -m pocarchitect --version`. | Exit 0; stdout contains `pocarchitect`. | Exit 0; stdout was `POCArchitect v0.2.0`. | Pass |
| UAT-J03 | UAT-J01 passed; loopback binding available. | Run `python -m pocarchitect quickstart`. | Offline preflight and demo complete; a Markdown report is saved under `reports/demo`. | Both preflight stages reported all checks passed; run completed and saved `reports/demo/POCAnalysis_poc_20260904_134658_955525_93cd00a1.md`. | Pass |
| UAT-J04 | GUI dependencies installed. | Run the GUI CLI with port 9123 and `--no-open`. | Loopback-only launch URL is printed; browser is not opened. | `test_gui_cli_uses_selected_loopback_port_without_opening_browser` passed and observed `http://127.0.0.1:9123/?token=` with host `127.0.0.1`. | Pass |
| UAT-J05 | Live loopback GUI and Chromium available. | Open the protected launch URL. | Token exchange redirects to `/`; title identifies POCArchitect; status becomes **Ready**. | `test_browser_form_validation_demo_recovery_and_report_library` passed in Chromium; secure session and **Ready** state loaded. | Pass |
| UAT-J06 | Analysis workspace loaded. | Submit the empty configuration form. | Exact inline source error appears and source receives focus. | Chromium observed **Enter a repository, package, image, or source URL.** and verified the source was the active element. | Pass |
| UAT-J07 | Analysis workspace loaded. | Select **Create credential-free demo**. | Job reaches `completed`; UI displays **Analysis complete**. | Browser test reached the visible report panel; `test_gui_demo_reaches_a_report_without_source_provider_or_credential` also observed API job status `completed`. | Pass |
| UAT-J08 | Demo completed. | Inspect report content and actions. | Body contains **POCArchitect Demo Report**; Copy and Download actions are visible. | Chromium found the heading, visible **Copy Markdown**, and a download URL ending in `/download`. | Pass |
| UAT-J09 | Demo report visible. | Select **Download**. | HTTP 200 attachment contains the demo heading. | Playwright captured a real browser download and read `# POCArchitect Demo Report` from the persisted artifact. | Pass |
| UAT-J10 | Demo report persisted. | Open **Reports** and select the recent report. | A report row exists and the selected body contains the demo heading. | Chromium selected the first library row and rendered **POCArchitect Demo Report**. | Pass |
| UAT-J11 | Demo completed and library populated. | Reload, wait for readiness, reopen **Reports**, and select the report. | No active job remains; report remains available. | Chromium reloaded the page, observed a null `pocarchitect.activeJob`, and reopened the persisted demo report. | Pass |
| UAT-J12 | Credential-free CLI available. | Run the documented JSON `--no-ingest --dry-run` command. | Exit 0; one `dry_run` event; no report written. | `test_json_dry_run_is_machine_readable_and_no_color` passed with events `processing`, `dry_run`, no ANSI output, and no report creation. | Pass |
| UAT-J13 | Authorized URL-only source and authenticated local GUI session. | POST `/api/preparations` with `no_ingest: true`. | HTTP 200 metadata; raw prompt and grounding content excluded. | `test_service_prepares_metadata_without_exposing_source_content` and `test_gui_prepare_approve_run_and_download` passed; response omitted `system_prompt` and `grounding`. | Pass |
| UAT-J14 | Valid preparation exists. | POST its selected-file estimate. | HTTP 200 with recalculated counts and Boolean `within_cost_limit`. | `test_service_recalculates_metadata_for_selected_files` and GUI API test passed; estimate returned `within_cost_limit: true`. | Pass |
| UAT-J15 | Prepared transfer and controlled local provider double. | POST `/api/runs`, wait for completion, then replay the preparation. | First response 202; replay 409. | GUI API test observed 202, completed report generation, and 409 on reuse. | Pass |
| UAT-J16 | Authenticated GUI session. | GET missing run and artifact identifiers. | Both return 404. | GUI API test observed 404 for `/api/runs/missing` and `/api/artifacts/missing`. | Pass |
| UAT-J17 | Authenticated GUI session. | Send a cross-origin mutation and a 70,000-byte API body. | Responses are 403 and 413. | `test_gui_rejects_cross_origin_mutations` and `test_gui_rejects_oversized_api_payload` observed 403 and 413. | Pass |
| UAT-J18 | Registered non-Markdown, oversized, invalid UTF-8, and removed artifacts. | Request each artifact preview. | Responses are 415, 413, 415, and 404. | `test_gui_preview_reports_type_size_encoding_and_missing_file_errors` observed the exact sequence. | Pass |
| UAT-J19 | Versioned batch state exists. | Run JSON `batch-status`; run recoverable `batch-reset --yes`. | Both exit 0; reset emits `batch_reset`; backup remains. | `test_batch_status_reports_atomic_ledger_summary`, `test_batch_reset_supports_global_json_output`, and `test_state_summary_and_recoverable_reset` passed with a timestamped `.bak`. | Pass |
| UAT-J20 | Repository documentation and CLI installed. | Run `python scripts/validate_documentation_commands.py`. | Exit 0 with the documented success message. | Exit 0; printed `Credential-free documentation commands passed behavioral probes. Provider-backed commands remain external integration checks.` | Pass |

## 3. Alternate and error-path cases

| Test ID | Precondition | Steps | Expected result | Actual result | Pass/Fail |
|---|---|---|---|---|---|
| UAT-A01 | GUI loaded. | Submit an empty URL source; switch to local mode and submit an empty path. | Mode-specific inline validation rejects both and focuses source. | Browser verified URL-mode error and focus; `validateForm` contract and full suite verified the local-mode message. | Pass |
| UAT-A02 | No cloud provider keys in process environment. | Load GUI, prepare URL-only source, approve transfer. | Readiness says provider needs configuration; Run remains disabled; setup recovery is offered. | `test_browser_blocks_unconfigured_provider` observed **needs configuration**, disabled Run, and visible **Copy setup command**. | Pass |
| UAT-A03 | Local provider endpoint unavailable or malformed. | Run local preflight against the endpoint. | Preflight reports bounded endpoint failure and does not continue. | `test_local_endpoint_validation_and_failure_responses` passed for malformed URL, unavailable endpoint, HTTP failure, and malformed response. | Pass |
| UAT-A04 | Authenticated GUI session. | Submit an invalid or empty source to `/api/preparations`. | HTTP 422 with actionable detail. | `test_gui_rejects_invalid_source_with_actionable_detail` observed HTTP 422 and `A source URL or local directory is required`. | Pass |
| UAT-A05 | GitHub ingestion returns the failure sentinel. | Start CLI processing and GUI/service preparation without `--no-ingest`. | Both abort before provider access and explain recovery. | `test_ingestion_failure_exits_before_provider_call` observed exit 2 and **no provider call was made**; `test_service_reports_ingestion_failure_before_preparation` observed `Source ingestion failed`. | Pass |
| UAT-A06 | Estimated input exceeds configured maximum. | Execute a prepared CLI request with zero approved cost. | Abort before provider call. | `test_cost_limit_aborts_before_provider_call` passed with exit 2 and an empty provider-call ledger. | Pass |
| UAT-A07 | Preparation is expired or already consumed. | Estimate expired preparation; replay consumed preparation. | Expired operation fails; replay returns 409. | `test_gui_expires_preparations_and_bounds_artifact_registry` rejected the expired preparation; GUI API test observed 409 on replay. | Pass |
| UAT-A08 | Missing session or attacker Host header. | Request bootstrap without token; request launch URL with unexpected Host. | Responses are 401 and 400. | `test_gui_requires_launch_session_and_sets_security_headers` and `test_gui_rejects_unexpected_host_header` observed 401 and 400. | Pass |
| UAT-A09 | Authenticated session, foreign Origin header. | POST a preparation. | HTTP 403 and no mutation. | Cross-origin test observed HTTP 403. | Pass |
| UAT-A10 | Authenticated session, oversized body. | POST a 70,000-byte preparation body. | HTTP 413 with **Request is too large**. | Oversized-body test observed HTTP 413 and exact detail. | Pass |
| UAT-A11 | Unsupported or unavailable artifacts registered. | Preview non-Markdown, large, invalid UTF-8, and missing artifacts. | Typed responses 415/413/415/404; download remains the recovery path for available files. | Artifact preview test observed all four expected responses. | Pass |
| UAT-A12 | GUI page can load; bootstrap request is temporarily interrupted. | Abort `/api/bootstrap`, inspect banner, restore route, select **Retry connection**. | **Connection interrupted** and retry appear; retry returns status to **Ready** and hides banner. | `test_browser_connection_interruption_and_retry` passed in Chromium. | Pass |
| UAT-A13 | Dependency manifest exists; OSV lookup raises an offline error. | Execute analysis with vulnerability scan enabled. | Base report and optional output complete; `vulnerability_scan_failed` is emitted. | `test_service_optional_outputs_and_vulnerability_failure` passed and observed the failure event plus completed export/scaffold. | Pass |
| UAT-A14 | Batch ledger is corrupt or unsupported. | Run status, then explicit reset. | Status refuses overwrite and points to reset; reset preserves backup. | `test_corrupt_batch_state_is_preserved_until_explicit_reset` and unsupported-version state tests passed; timestamped backup remained. | Pass |
| UAT-A15 | Batch contains one successful and one failing item. | Process batch and inspect final summary. | Later items continue; counts identify failure; exit is nonzero. | `test_process_batch_file_reports_success_failure_and_failed_urls` observed `total=2 processed=2 success=1 failed=1 skipped=0` and exit 1. | Pass |
| UAT-A16 | Report exists; GitHub CLI publish returns an error containing a token-like value. | Run `publish`. | Exit nonzero; diagnostic is useful but secret is redacted; no ingestion claim. | `test_compare_plugins_vulnerabilities_and_publish_commands` observed exit 1, retained `authentication failed`, replaced the token with `[REDACTED]`, and emitted no `ingesting`. | Pass |
| UAT-A17 | stdin is not a terminal. | Run `setup` in JSON/no-color mode. | Exit 2 with an error explaining the interactive requirement. | Documentation command validator and `test_selected_safe_documentation_commands_execute_without_network` passed this probe. | Pass |

## 4. Boundary-input cases

| Test ID | Precondition | Steps | Expected result | Actual result | Pass/Fail |
|---|---|---|---|---|---|
| UAT-B01 | Representative repository, package, image, URL, and local-path inputs. | Classify each source. | Each supported form receives the expected stable classification. | `test_source_classification_covers_broader_inputs` passed. | Pass |
| UAT-B02 | Grounding contains assignment, provider, GitHub, AWS, and bearer token forms. | Detect and redact the content. | No secret value survives; category/count metadata remains. | Three sensitive-input tests passed; all sample secrets were absent from redacted output. | Pass |
| UAT-B03 | Known and unknown model names; zero cost ceiling. | Estimate cost and enforce maximum. | Known model returns estimate, unknown is unavailable, and excess stops before provider. | `test_estimate_cost_usd_known_and_unknown_models` and cost-limit test passed. | Pass |
| UAT-B04 | Prompt limit reduced below prepared request size. | Prepare request. | Preparation fails with a bounded safe-limit error. | `test_service_rejects_prepared_prompt_above_safe_limit` passed. | Pass |
| UAT-B05 | Preparation has a known grounding-file set. | Estimate with an unknown selected path. | Unknown selection is rejected, not silently ignored. | `test_service_rejects_unknown_file_selection` passed. | Pass |
| UAT-B06 | Unsupported provider/report format, missing model/source, temperatures outside 0–2, negative cost, malformed base URL, missing local path. | Normalize each request. | Every invalid field is rejected with its corresponding diagnostic. | All parameterized `test_service_rejects_invalid_requests` cases and `test_service_rejects_missing_local_directory` passed. | Pass |
| UAT-B07 | Unsupported state version, malformed item, unknown status, serialization/replace failure, and held lock. | Load or write each state. | Corruption is rejected; lock/temp cleanup occurs; lock timeout is bounded. | All seven `tests/test_state.py` cases passed. | Pass |
| UAT-B08 | Two reports use the same source and timestamp window. | Save both reports. | Distinct collision-safe names are created and both files remain. | `test_save_report_uses_unique_collision_safe_names` passed. | Pass |

## 5. Automated and terminal evidence

Focused Chromium UAT after adding literal reload, download, interruption, retry,
and provider-readiness coverage:

```text
tests/test_gui_browser.py::test_browser_form_validation_demo_recovery_and_report_library PASSED
tests/test_gui_browser.py::test_browser_connection_interruption_and_retry PASSED
tests/test_gui_browser.py::test_browser_blocks_unconfigured_provider PASSED
3 passed in 9.87s
```

Focused alternate-path UAT:

```text
tests/test_cli.py::test_ingestion_failure_exits_before_provider_call PASSED
tests/test_cli.py::test_compare_plugins_vulnerabilities_and_publish_commands PASSED
tests/test_gui.py::test_gui_rejects_invalid_source_with_actionable_detail PASSED
tests/test_service.py::test_service_reports_ingestion_failure_before_preparation PASSED
4 passed in 1.19s
```

Final complete automated run after all Phase 5 additions:

```text
198 passed in 72.76s (0:01:12)
```

## 6. Acceptance summary

- Total UAT cases: 45
- Passed: 45
- Failed: 0
- External integration conditions excluded from local pass claims: live cloud
  provider credentials, provider billing/rate limits/model quality, and hosted
  Windows execution.

UAT: passed.
