# Security Policy

## Supported Versions

| Version | Supported |
|---|---|
| `initial-release` (default branch) | ✅ |

## Reporting a Vulnerability

If you find a security issue — SQL injection vector, auth bypass, or sensitive data exposure — **do not open a public issue.**

Instead, report it privately:

1. Go to [github.com/ansh44233/FraudDetector/security/advisories](https://github.com/ansh44233/FraudDetector/security/advisories)
2. Click **"Report a vulnerability"**
3. Describe the issue, steps to reproduce, and potential impact

You'll receive a response within 48 hours. If a fix is warranted, a patched release will be cut and you'll be credited in the changelog.

## Security notes on this project

- The `.env` file (DB password) is in `.gitignore` — never committed
- Only `.env.example` with placeholder values is in the repo
- All SQL uses parameterized queries (`%s` via psycopg2) — no string interpolation
- The API has no authentication by default — not intended for public production deployment without adding auth middleware
