# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
While the version is `0.x`, the API may change without a major version bump.

## [Unreleased]

### Added

- Companies: create, view and list them. Names are required and unique ignoring case
  and surrounding spaces; the website is optional and must be an `http(s)` URL.
  The list is alphabetical (ignoring case) and paginated.
- Application stage transitions: move an application to any later stage, close it
  with an outcome allowed in its stage (`rejected`, `ghosted`, `withdrawn`,
  `offer_declined`), reactivate a `ghosted` application, and view its transition
  history. Transition dates default to today and cannot be in the future or before
  the previous transition.
- `GET /api/v1/applications/{id}` with the application's current stage and outcome.
- Paginated list responses share one envelope: `{items, total, limit, offset}`.
- Error contract: every error response is RFC 9457 problem details
  (`application/problem+json`) with a stable `type`; validation errors list each
  invalid field; unexpected errors return a generic 500 without internal details.
- Bearer token authentication for every `/api/v1` endpoint.
- `GET /health`, which also checks the database connection.
- Development setup: Justfile, Docker Compose Postgres, pre-commit, GitHub Actions CI,
  and a parallel test suite (unit, integration, BDD, migrations and API contract).

### Changed

- The backend runs on Python 3.14.
- CI only runs for backend-related changes and cancels superseded runs.
