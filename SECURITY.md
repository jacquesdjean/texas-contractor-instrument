# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 1.0.x   | Yes                |
| < 1.0   | No                 |

## Reporting a Vulnerability

We take the security of TDLR License Monitor seriously. If you believe you have
found a security vulnerability, please report it to us as described below.

**Please do not report security vulnerabilities through public GitHub issues.**

### How to Report

1. Open a **private security advisory** via
   [GitHub Security Advisories](https://github.com/jacquesdjean/texas-contractor-instrument/security/advisories/new).
2. Alternatively, email the maintainers directly with a description of the issue.

### What to Include

- A description of the vulnerability and its potential impact
- Step-by-step instructions to reproduce the issue
- Any relevant logs, screenshots, or proof-of-concept code
- Your suggested fix, if you have one

### Response Timeline

| Action                     | Timeframe       |
|----------------------------|-----------------|
| Acknowledgment of report   | Within 48 hours |
| Initial assessment         | Within 7 days   |
| Fix development and review | Within 30 days  |
| Public disclosure           | After fix is released |

### What to Expect

- You will receive an acknowledgment within 48 hours confirming we received
  your report.
- We will work with you to understand and validate the issue.
- We will keep you informed of our progress toward a fix.
- We will credit you in the release notes (unless you prefer to remain
  anonymous).

### Scope

The following are in scope for security reports:

- Authentication and authorization issues
- Data exposure or leakage (API tokens, credentials)
- Injection vulnerabilities in data processing
- Insecure dependencies with known CVEs

The following are **out of scope**:

- Issues in third-party dependencies that do not affect this project
- Social engineering attacks
- Denial of service attacks against the Socrata API

## Security Best Practices for Users

- **Never commit `.env` files** containing real credentials
- **Use GitHub Secrets** for all sensitive configuration in CI/CD
- **Rotate API tokens** regularly, especially the Socrata app token
- **Restrict Google Sheets service account** permissions to only the
  necessary spreadsheet
- **Review the `.env.example`** file for a list of all configurable secrets
