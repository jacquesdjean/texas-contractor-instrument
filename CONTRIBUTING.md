# Contributing to TDLR License Monitor

Thank you for your interest in contributing to the TDLR License Monitor! This
document provides guidelines and information to make the contribution process
smooth and effective.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Code Style](#code-style)
- [Commit Messages](#commit-messages)
- [Pull Request Process](#pull-request-process)
- [Testing](#testing)
- [Reporting Bugs](#reporting-bugs)
- [Requesting Features](#requesting-features)
- [First-Time Contributors](#first-time-contributors)

## Code of Conduct

This project adheres to the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md).
By participating, you are expected to uphold this code. Please report
unacceptable behavior via the channels described in the Code of Conduct.

## Getting Started

### Prerequisites

- **Python 3.11+** (3.12 also supported)
- **git** for version control
- **make** for running development tasks (optional but recommended)

### Development Setup

1. **Fork and clone the repository**

   ```bash
   git clone https://github.com/<your-username>/texas-contractor-instrument.git
   cd texas-contractor-instrument
   ```

2. **Create a virtual environment**

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies (including dev tools)**

   ```bash
   make install
   # Or manually: pip install -e ".[dev]"
   ```

4. **Install pre-commit hooks**

   ```bash
   pre-commit install
   ```

5. **Verify your setup**

   ```bash
   make test    # Run the test suite
   make lint    # Run the linter
   ```

## Project Structure

```
texas-contractor-instrument/
├── src/                        # Application source code
│   ├── __init__.py             # Package init with version
│   ├── main.py                 # Pipeline orchestrator
│   ├── scraper.py              # TDLR Socrata API client
│   ├── tsbpe_scraper.py        # TSBPE plumbing license scraper
│   ├── differ.py               # Snapshot diffing and reinstated detection
│   ├── scorer.py               # Recruitment value scoring
│   ├── sheets_output.py        # Google Sheets integration
│   └── notifications.py        # Slack and email alerts
├── config/                     # YAML configuration files
│   ├── territory.yml           # County definitions
│   ├── license_types.yml       # License type mappings
│   └── scoring.yml             # Scoring weights and bonuses
├── tests/                      # Unit tests
│   ├── test_differ.py
│   ├── test_scorer.py
│   ├── test_notifications.py
│   └── fixtures/               # Test data
├── data/                       # Runtime snapshots (committed weekly by CI)
├── .github/workflows/          # CI/CD automation
├── pyproject.toml              # Project metadata and tool configuration
└── Makefile                    # Developer task runner
```

## Code Style

This project uses [Ruff](https://docs.astral.sh/ruff/) for both linting and
formatting.

### Key conventions

- **Line length**: 100 characters maximum
- **Quotes**: Double quotes for strings
- **Imports**: Sorted by isort rules (stdlib, third-party, first-party)
- **Type hints**: Encouraged but not yet enforced
- **Docstrings**: Required for all public functions and classes

### Running the linter

```bash
make lint          # Check for issues
make format        # Auto-fix formatting
```

### Editor integration

Ruff has plugins for most editors. Configuration is in `pyproject.toml` under
`[tool.ruff]`, so your editor will pick it up automatically.

## Commit Messages

We follow [Conventional Commits](https://www.conventionalcommits.org/) for
clear, structured commit history.

### Format

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

### Types

| Type       | Description                                      |
|------------|--------------------------------------------------|
| `feat`     | A new feature                                    |
| `fix`      | A bug fix                                        |
| `docs`     | Documentation changes only                       |
| `style`    | Formatting, missing semicolons, etc. (no logic)  |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `test`     | Adding or correcting tests                       |
| `chore`    | Maintenance tasks (CI, build, dependencies)      |
| `perf`     | Performance improvement                          |

### Examples

```
feat(scraper): add retry logic for Socrata API timeouts
fix(differ): handle empty snapshot on first run
docs: update README with new configuration options
chore(ci): add Python 3.12 to test matrix
```

## Pull Request Process

1. **Create a feature branch** from `master`:

   ```bash
   git checkout -b feat/your-feature-name
   ```

2. **Make your changes** with clear, focused commits.

3. **Ensure all checks pass**:

   ```bash
   make lint     # Linting passes
   make test     # All tests pass
   ```

4. **Push your branch** and open a pull request.

5. **Fill out the PR template** completely, including:
   - A clear description of the change
   - The type of change (bug fix, feature, etc.)
   - How you tested the change

6. **Address review feedback** promptly. We aim to review PRs within 48 hours.

### Branch naming convention

| Prefix     | Use case                |
|------------|-------------------------|
| `feat/`    | New features            |
| `fix/`     | Bug fixes               |
| `docs/`    | Documentation updates   |
| `chore/`   | Maintenance tasks       |
| `refactor/`| Code refactoring        |

### PR requirements

- All CI checks must pass (tests, linting)
- At least one approving review from a maintainer
- No unresolved review comments
- Commit messages follow the conventional commits format

## Testing

### Running tests

```bash
make test              # Run all tests
make test-cov          # Run tests with coverage report
python -m pytest tests/test_differ.py -v   # Run a specific test file
```

### Writing tests

- Place tests in the `tests/` directory
- Name test files `test_<module>.py`
- Name test functions `test_<behavior_being_tested>`
- Use fixtures in `tests/fixtures/` for sample data
- Aim for clear, focused tests that test one behavior each

### Test coverage

We aim to maintain and improve test coverage. When adding new features, please
include corresponding tests.

## Reporting Bugs

Use the [Bug Report](https://github.com/jacquesdjean/texas-contractor-instrument/issues/new?template=bug_report.yml)
issue template. Include:

- A clear, descriptive title
- Steps to reproduce the behavior
- Expected vs. actual behavior
- Your environment (Python version, OS)
- Relevant log output

## Requesting Features

Use the [Feature Request](https://github.com/jacquesdjean/texas-contractor-instrument/issues/new?template=feature_request.yml)
issue template. Include:

- The problem you're trying to solve
- Your proposed solution
- Any alternatives you've considered

## First-Time Contributors

New to open source? Welcome! Here are some tips:

1. **Start small** — Look for issues labeled `good first issue`
2. **Ask questions** — Open an issue if anything is unclear
3. **Read the code** — Familiarize yourself with the project structure above
4. **Follow the process** — Small, focused PRs are easier to review and merge

We appreciate every contribution, whether it's fixing a typo, improving
documentation, or adding a new feature.

---

Thank you for contributing!
