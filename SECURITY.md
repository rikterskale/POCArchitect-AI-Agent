# Security Policy

## Reporting a vulnerability

POCArchitect handles untrusted source code and can transmit selected content to
external model providers. Security reports are welcome and should be handled
privately through GitHub Security Advisories. If private advisories are
unavailable, contact the repository maintainer through the verified contact on
the repository profile. Do not include credentials, private source, or exploit
payloads in a public issue.

Include the affected version/commit, operating system and Python version,
reproduction steps, impact, and a safe mitigation. The project aims to
acknowledge reports within 7 calendar days and publish a fix or mitigation
decision within 30 days when practical. Coordinated disclosure dates should be
agreed with the reporter.

## Supported versions

Only the latest released version and the current `main` branch receive
security fixes. Users should update before relying on a fix.

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
