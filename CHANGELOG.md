# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-03-31

### Added

- Modern Python packaging with `pyproject.toml` and PEP 621 metadata
- Apache License 2.0
- Contributor Covenant Code of Conduct (v2.1)
- Security vulnerability disclosure policy (`SECURITY.md`)
- Comprehensive contributing guide (`CONTRIBUTING.md`)
- This changelog
- GitHub issue templates (bug report and feature request as YAML forms)
- Pull request template with review checklist
- `CODEOWNERS` file for automated review assignment
- Enhanced CI pipeline with Python version matrix (3.11, 3.12), ruff linting,
  and coverage reporting
- Release workflow triggered on version tags
- CodeQL security analysis workflow
- `Makefile` with standard development targets (install, test, lint, format, clean)
- `.editorconfig` for consistent editor settings
- `.pre-commit-config.yaml` for automated code quality checks
- PEP 561 `py.typed` marker file
- Version identifier in `src/__init__.py`

### Changed

- Complete README overhaul with badges, table of contents, architecture
  diagrams, and comprehensive documentation
- CI workflow upgraded from basic pytest to matrix testing with linting

## [0.2.0] - 2026-03-31

### Added

- TSBPE plumbing license scraper (`src/tsbpe_scraper.py`) with optional
  activation via `ENABLE_TSBPE` environment variable
- Reinstated license detection in snapshot differ
- Slack notification support via incoming webhooks
- Email notification support via SMTP
- Notification threshold filtering (score >= 90)
- GitHub Actions CI pipeline with pytest and syntax validation
- Automated weekly scan workflow (Mondays 7:00 AM CT)
- Auto-merge support for PRs passing CI
- Historical license tracking to prevent duplicate detection
- Snapshot commit automation in weekly workflow

### Changed

- Differ module enhanced with reinstated license logic
- Main orchestrator updated to support dual pipeline (TDLR + TSBPE)

## [0.1.0] - 2026-03-31

### Added

- Initial TDLR contractor license monitor
- Socrata SODA API client for TDLR dataset (`7358-krk7`)
- Weekly snapshot diffing for new license detection
- Recruitment value scoring system (0-130 scale)
- Google Sheets output integration (New Licenses and Weekly Summary tabs)
- YAML-based configuration for territory, license types, and scoring weights
- Central Texas territory definition (12 counties)
- 7 TDLR license types with base scores
- Unit test suite (44 tests)
- `.env.example` with all configurable environment variables
- `.gitignore` for Python projects

[Unreleased]: https://github.com/jacquesdjean/texas-contractor-instrument/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/jacquesdjean/texas-contractor-instrument/compare/v0.2.0...v1.0.0
[0.2.0]: https://github.com/jacquesdjean/texas-contractor-instrument/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/jacquesdjean/texas-contractor-instrument/releases/tag/v0.1.0
