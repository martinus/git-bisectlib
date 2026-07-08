# Dependency Audit

_Audit date: 2026-07-08 · package `git_bisectlib` v0.16.2_

## Summary

`git_bisectlib` has **zero third-party runtime dependencies**. Every module it
imports — at import time or lazily inside functions — is part of the Python
standard library. The only external tooling is the build backend (`setuptools`)
and the GitHub Actions used for CI and publishing.

This is a deliberate strength for a bisect helper: it drops into any project
that already has Python 3.10+ without pulling a dependency tree along with it.

## Runtime dependencies

**None.** The `bisectlib` package (`__init__.py`, `_report.py`) uses only the
standard library:

| Module | Where |
| --- | --- |
| `atexit`, `signal`, `sys`, `os`, `time`, `threading` | process/lifecycle handling |
| `subprocess`, `shlex`, `shutil` | running git and build/test commands |
| `hashlib`, `json`, `re` | state hashing, `.bisect/status.md`, parsing |
| `concurrent.futures` | parallel `hammer` runs (lazy import) |
| `traceback` | error reporting (lazy import) |
| `contextlib`, `dataclasses`, `datetime`, `pathlib`, `typing`, `__future__` | structure & typing |

All of the above ship with every supported CPython (3.10–3.13). No wheels are
downloaded when a user installs `git_bisectlib`.

## Test dependencies

**None beyond the standard library.** `tests/test_bisectlib.py` and
`tests/test_report.py` use `unittest` and `tempfile`; the CI job runs them with
`python -m unittest discover`. There is no `pytest`, `tox`, `requirements`, or
`Pipfile` — nothing extra to install to run the suite.

## Example dependencies

**None.** The scripts under `examples/` import only from `bisectlib` itself.

## Build dependencies

Declared in `pyproject.toml`:

| Dependency | Constraint | Notes |
| --- | --- | --- |
| `setuptools` | `>=61` | build backend (PEP 621 metadata support) |

The publish workflow additionally installs `build` (`pip install build`) to
produce the sdist/wheel. Neither is a runtime dependency.

## CI / release tooling (GitHub Actions)

| Action | Version | Used in |
| --- | --- | --- |
| `actions/checkout` | `v4` | `test.yml`, `publish.yml` |
| `actions/setup-python` | `v5` | `test.yml`, `publish.yml` |
| `pypa/gh-action-pypi-publish` | `release/v1` | `publish.yml` (trusted publishing, no stored token) |

## Supported Python

`requires-python = ">=3.10"`, tested in CI against **3.10, 3.11, 3.12, and
3.13**. No language or stdlib feature used here goes beyond 3.10 (e.g. PEP 604
`X | Y` unions are guarded by `from __future__ import annotations`).

## Findings & recommendations

- **No action required** on runtime dependencies — the package is dependency-free
  and should stay that way.
- The GitHub Actions are pinned to major version tags (`@v4`, `@v5`,
  `@release/v1`) rather than commit SHAs. This is the common convention and fine
  for a project of this size; pinning to full SHAs would harden the supply chain
  further if that ever becomes a concern.
- No dependency manifests (`requirements.txt`, `Pipfile`, `poetry.lock`,
  `constraints.txt`) exist, which is correct — there is nothing to pin.
