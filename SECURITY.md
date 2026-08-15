# Security Policy

## Reporting a vulnerability

**POCArchitect does not accept vulnerability reports.**

This project is maintained on an as-is, best-effort basis. It has no security
response process, no coordinated-disclosure channel, and no commitment to
triage, acknowledge, or remediate reported security issues. Please do not open
GitHub issues, pull requests, private security advisories, or email describing
security vulnerabilities — they will not be actioned.

## No security support

- No versions are covered by any security-support or maintenance commitment.
- No security patches, advisories, or CVEs are issued by this project.
- The software is provided "AS IS", without warranty of any kind, as stated in
  the [LICENSE](LICENSE).

## Using this tool responsibly

POCArchitect is offensive-security tooling that sends selected source content to
an external LLM provider. Operating it safely is the user's responsibility, not
a security guarantee by the project:

- Only analyze repositories you are authorized to inspect.
- Keep provider credentials in a local, gitignored `.env` file; never place a
  key on a command line or in an issue, log, or report.
- Review the redacted transfer preview before confirming any real provider call.
- Treat generated reports as unverified model output that requires your review.

These practices reduce operational risk but do not constitute a security-support
commitment.
