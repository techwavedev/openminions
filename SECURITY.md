# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | ✅ Current |

## Reporting a Vulnerability

**Do NOT open a public issue for security vulnerabilities.**

Instead, please report security issues via one of these channels:

1. **GitHub Security Advisories** — Use the ["Report a vulnerability"](https://github.com/techwavedev/openminions/security/advisories/new) button on the Security tab
2. **Email** — Send details to **security@techwave.dev**

### What to Include

- Description of the vulnerability
- Steps to reproduce (if applicable)
- Potential impact assessment
- Suggested fix (if you have one)

### What NOT to Include

- ⛔ Never include actual secrets, API keys, or credentials
- ⛔ Never include production data or PII
- ⛔ Never share vulnerability details publicly before a fix is available

## Response Timeline

| Action | Timeline |
|--------|----------|
| Acknowledgment | Within 48 hours |
| Initial assessment | Within 1 week |
| Fix for critical issues | Within 2 weeks |
| Fix for non-critical issues | Next release cycle |

## Security Measures in Place

- **Pre-push hook** — `bin/security_gate.py` scans for secrets before every push
- **GitHub Secret Scanning** — Enabled with push protection
- **CodeQL Analysis** — Runs on every PR
- **TruffleHog** — Deep secret scanning in CI
- **Dependency Review** — Blocks PRs introducing vulnerabilities
- **Dependabot** — Automatic security updates enabled
- **Branch Protection** — All changes require PR with passing checks
- **Squash Merge Only** — Clean commit history, no accidental leaks in merge commits

## Scope

This policy covers the `techwavedev/openminions` repository. For issues related to the underlying `@techwavedev/agi-agent-kit` framework, please report to that repository's security policy.
