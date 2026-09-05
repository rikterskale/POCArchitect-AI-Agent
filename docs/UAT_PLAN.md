# POCArchitect UAT plan

Manual and automated acceptance script for every row of
[USER_JOURNEY.md](USER_JOURNEY.md) §5. Actual results are captured command or
test output. A case is Pass only with that evidence.

Automated cases: `tests/test_uat.py` (J1–J22, B1–B3) and
`tests/test_gui_browser.py` (J23–J25). No new E2E tools were added.

| Test ID | Precondition | Steps | Expected result | Actual result | Pass/Fail |
|---|---|---|---|---|---|
| UAT-J1 | Repo checkout; Python ≥ 3.10 venv | `python -m pip install -e ".[gui]"` then `python -m pocarchitect --help` | Help exits 0 and mentions `quickstart` | Live: `Usage: python -m pocarchitect` … exit 0. `tests/test_uat.py::test_uat_j1_help_exits_zero_after_install` PASSED | Pass |
| UAT-J2 | Package installed | `python -m pocarchitect --version` | Exit 0; stdout contains `POCArchitect v` | Live: `POCArchitect v0.3.0` EXIT:0. `test_uat_j2_version_prints_product_banner` PASSED | Pass |
| UAT-J3 | Package installed; writable cwd | `python -m pocarchitect preflight --offline --format json --no-color` | Exit 0; JSON `"event": "preflight"` and `Preflight passed.` | Live JSON starts `{"checks": [{"check": "Python >=3.10"…`; EXIT:0. `test_uat_j3_offline_preflight_passes_json` PASSED | Pass |
| UAT-J4 | Package installed; writable cwd | `python -m pocarchitect --format json --no-color quickstart` | Exit 0; events include `preflight` and `report_saved` | `test_uat_j4_j5_quickstart_writes_demo_report` PASSED (exit 0, both events present) | Pass |
| UAT-J5 | UAT-J4 succeeded | Read `reports/demo/POCAnalysis_*.md` | File exists; body contains `POCArchitect Demo Report` | Same test: glob found `POCAnalysis_*.md` containing `POCArchitect Demo Report` | Pass |
| UAT-J6 | Package installed | `python -m pocarchitect --url https://github.com/example/poc --no-ingest --dry-run --format json --no-color` | Exit 0; `"event": "dry_run"`; `report_preview` present | Live EXIT:0; JSON ends with dry-run preview markdown. `test_uat_j6_json_dry_run_has_preview` PASSED | Pass |
| UAT-J7 | `gui` extra installed | Invoke `gui --port 9123 --no-open` (uvicorn mocked) | Output contains `http://127.0.0.1:` and `?token=` | `test_uat_j7_gui_no_open_prints_launch_url` PASSED; stdout includes `http://127.0.0.1:9123/` and `?token=` | Pass |
| UAT-J8 | GUI app created with a session token | `GET /` with no cookie | HTTP 401; detail `Open the GUI from its launch URL` | Log: `GET http://127.0.0.1:8765/ "HTTP/1.1 401 Unauthorized"`. `test_uat_j8_gui_index_requires_launch_session` PASSED | Pass |
| UAT-J9 | Authenticated GUI session | `POST /api/demo`; wait until job completes | `status` is `completed`; content contains `POCArchitect Demo Report` | `POST /api/demo 202`; job `completed`. `test_uat_j9_j10_gui_demo_and_report_library` PASSED | Pass |
| UAT-J10 | UAT-J9 completed | `GET /api/reports` and open the artifact | Reports list length ≥ 1; preview contains `POCArchitect Demo Report` | `GET /api/reports 200`; `GET /api/artifacts/… 200`. Same test PASSED | Pass |
| UAT-J11 | Package installed | `python -m pocarchitect --url https://github.com/owner --dry-run` | Exit 2; `Invalid PoC URL` | `test_uat_j11_invalid_github_url` PASSED | Pass |
| UAT-J12 | Package installed | `python -m pocarchitect --dry-run` | Exit 2; `Provide --url, --source, --path, or --batch` | Live: `Provide --url, --source, --path, or --batch` EXIT:2. `test_uat_j12_missing_source` PASSED | Pass |
| UAT-J13 | Package installed | `pocarchitect --url u --batch f --dry-run` | Exit 2; `Provide either --url or --batch, not both` | `test_uat_j13_url_and_batch_together` PASSED | Pass |
| UAT-J14 | Package installed | Ingest failure without `--no-ingest` | Exit 2; `Source ingestion failed; no provider call was made` | `test_uat_j14_ingestion_failure_before_provider` PASSED | Pass |
| UAT-J15 | Package installed | Ingest enabled, non-TTY, no `--yes` | Exit 2; `Confirmation is required in non-interactive mode` | `test_uat_j15_confirmation_required_without_yes` PASSED | Pass |
| UAT-J16 | Package installed | `--model gpt-4o --no-ingest --yes --max-estimated-cost 0` | Exit 2; message contains `exceeds the` | `test_uat_j16_cost_limit_exceeded` PASSED | Pass |
| UAT-J17 | Package installed | `pocarchitect setup` with stdin not a TTY | Exit 2; `Setup is interactive` | `test_uat_j17_setup_requires_tty` PASSED | Pass |
| UAT-J18 | `uvicorn` import forced to fail | `pocarchitect gui --no-open` | Exit 2; `The GUI dependencies are not installed` | `test_uat_j18_gui_requires_extra` PASSED | Pass |
| UAT-J19 | No workflow file at the given path | `pocarchitect workflow-status --state missing.json` | Exit 2; `Workflow state not found` | `test_uat_j19_workflow_status_missing_state` PASSED | Pass |
| UAT-J20 | Package installed | `pocarchitect compare only-one` | Exit 2; `Compare requires at least two sources` | `test_uat_j20_compare_requires_two_sources` PASSED | Pass |
| UAT-J21 | `gh` not on PATH | `pocarchitect publish <report.md>` | Exit 2; `GitHub CLI is required for publishing` | `test_uat_j21_publish_requires_gh` PASSED | Pass |
| UAT-J22 | Empty writable directory | `pocarchitect init` twice | First exit 0; second exit 2 and `Use --force to replace it` | `test_uat_j22_init_refuses_existing_config` PASSED | Pass |
| UAT-J23 | Live GUI in Chromium | Open launch URL; click Prepare with empty source | `#source-error` is `Enter a repository, package, image, or source URL.` | `tests/test_gui_browser.py::test_browser_form_validation_demo_recovery_and_report_library` PASSED | Pass |
| UAT-J24 | Live GUI; cloud keys unset | Select unconfigured provider; prepare a URL; check approval | `#run-button` disabled; Copy setup command visible | `test_browser_blocks_unconfigured_provider` PASSED | Pass |
| UAT-J25 | Live GUI | Abort `/api/bootstrap`; then Retry | Banner `Connection interrupted.`; Retry restores Ready | `test_browser_connection_interruption_and_retry` PASSED | Pass |
| UAT-B1 | Empty/comment-only batch file | `--batch` that file | Exit 2; `Batch file is empty or contains no valid URLs` | `test_uat_b1_empty_batch_file` PASSED | Pass |
| UAT-B2 | Fresh workflow state | `workflow-apply --command confirm_scope --payload '{}'` | Exit 2; `Unsupported workflow command` | `test_uat_b2_confirm_scope_is_not_a_workflow_command` PASSED | Pass |
| UAT-B3 | Package installed | `--no-ingest --dry-run --no-mitigations --format json` | Exit 0; prompt contains `Include Mitigations: No` | `test_uat_b3_no_mitigations_in_dry_run_prompt` PASSED | Pass |
