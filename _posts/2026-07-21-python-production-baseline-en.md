---
title: "Minimum Standards for Turning Python Code into Production-Ready Software"
date: 2026-07-21 10:10:00 +0900
categories: [Software Engineering, Python]
tags: [python, packaging, testing, typing, logging, reproducibility]
description: Practical standards for evolving scripts into reproducible, testable, and observable Python applications.
lang: en
translation_key: python-production-baseline
hidden: true
---

{% include language-switcher.html %}

Getting a Python file to run once and turning it into software that runs safely and repeatedly in other environments are entirely different challenges. The essence of production-ready code is not an elaborate framework, but whether **inputs, outputs, dependencies, and failures are explicit**.

## 1. Establish Boundaries First

The hardest code to maintain mixes computation, file access, network requests, environment-variable reads, and log output in a single function. Dividing it into the following three layers makes testing and replacement easier.

1. **Domain logic**: Pure computation that produces the same output for the same input
2. **Adapters**: Communication with files, databases, HTTP services, and message queues
3. **Entry point**: Reading configuration, assembling objects, and determining exit codes

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class Reading:
    value: float
    lower: float
    upper: float


def classify(reading: Reading) -> str:
    if reading.lower > reading.upper:
        raise ValueError("lower must not exceed upper")
    if reading.value < reading.lower:
        return "low"
    if reading.value > reading.upper:
        return "high"
    return "normal"
```

This function does not access files, clocks, or networks. Boundary values can therefore be checked quickly, and the possible causes of failure are limited.

## 2. Start with a Small Project Structure, but Separate Responsibilities

```text
project/
├── pyproject.toml
├── README.md
├── src/
│   └── app/
│       ├── __init__.py
│       ├── domain.py
│       ├── adapters.py
│       └── cli.py
└── tests/
    ├── unit/
    └── integration/
```

The `src` layout reduces the chance that the repository root accidentally becomes an import path and conceals packaging errors. `pyproject.toml` brings together the build system, project metadata, runtime dependencies, and development-tool configuration.

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "example-app"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["httpx>=0.27,<1"]

[project.optional-dependencies]
dev = ["pytest>=8,<9", "ruff>=0.5,<1", "mypy>=1.10,<2"]
```

The version ranges are only examples. In a real project, choose one supported Python-version policy and one lock-file strategy, then use them consistently in CI and deployment.

## 3. Separate Configuration from Secrets

Configuration falls into three categories.

| Category | Examples | Storage location |
|---|---|---|
| Code defaults | Batch size, default timeout | Code or a public configuration file |
| Environment-specific configuration | API address, log level | Environment variables or deployment configuration |
| Secrets | Tokens, passwords, private keys | Secrets manager |

Even a value such as `DEBUG=true` is a string. Validate it once at startup instead of relying on implicit type conversion.

```python
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    api_base_url: str
    timeout_seconds: float


def load_settings() -> Settings:
    base_url = os.environ["API_BASE_URL"]
    timeout = float(os.getenv("HTTP_TIMEOUT_SECONDS", "10"))
    if timeout <= 0:
        raise ValueError("HTTP_TIMEOUT_SECONDS must be positive")
    return Settings(api_base_url=base_url, timeout_seconds=timeout)
```

Do not leave secret values in exception messages, CLI arguments, Git, test fixtures, or notebook output. Merely masking them with `***` is not enough; it is safer never to place them in log fields in the first place.

## 4. Types Explain Contracts; They Do Not Replace Execution

Type hints quickly communicate the intent of inputs and outputs and reduce refactoring errors. However, JSON, CSV, and environment variables received from outside are not validated by type hints alone. Two layers are necessary: **runtime validation at trust boundaries**, and type checking internally.

- Restrict `Any` to areas undergoing gradual migration.
- Prefer meaningful `dataclass`, `TypedDict`, or model types to `dict[str, object]`.
- Make clear whether `None` is a normal state or an error state.
- Distinguish numbers with different units through names or separate types.

## 5. Logs Are Structured Events, Not Sentences

Production logs must be filterable and aggregatable later.

```python
import logging

logger = logging.getLogger(__name__)


def handle(job_id: str) -> None:
    logger.info("job_started", extra={"job_id": job_id})
    try:
        run_job(job_id)
    except TimeoutError:
        logger.exception("job_timed_out", extra={"job_id": job_id})
        raise
```

The minimum common fields are `event`, `timestamp`, `severity`, `service`, `request_id` or `job_id`, `duration`, and `outcome`. Do not log entire raw request bodies or authentication headers.

## 6. Arrange Tests Along Layers of Risk

```python
import pytest

from app.domain import Reading, classify


@pytest.mark.parametrize(
    ("value", "expected"),
    [(9.0, "low"), (10.0, "normal"), (20.0, "normal"), (21.0, "high")],
)
def test_classify_boundaries(value: float, expected: str) -> None:
    assert classify(Reading(value=value, lower=10.0, upper=20.0)) == expected
```

- Unit tests: Pure logic, boundary values, and invariants
- Integration tests: Database, file, and HTTP adapters
- Contract tests: Request/response schemas and error formats
- Smoke tests: Whether critical paths remain operational after deployment

Mocking every implementation detail can conceal real integration errors. Conversely, making every test E2E makes the suite slow and failures hard to diagnose. Divide the layers according to the cost of failure and frequency of change.

## 7. Exits and Retries Are APIs Too

CLIs and batch jobs must distinguish success from failure through exit codes. Network retries require a maximum attempt count, exponential backoff, jitter, and an overall deadline. Do not automatically retry operations with side effects unless idempotency is guaranteed.

```python
def main() -> int:
    try:
        settings = load_settings()
        execute(settings)
    except ConfigurationError as exc:
        logger.error("invalid_configuration", extra={"reason": str(exc)})
        return 2
    except Exception:
        logger.exception("unhandled_failure")
        return 1
    return 0
```

## Preproduction Checklist

- [ ] The application can be installed and run in a new environment using only the documented commands.
- [ ] The Python version and dependencies are declared, and a locking strategy exists.
- [ ] Input schemas, units, ranges, and missing-value policies are validated.
- [ ] No secrets appear in code, Git history, logs, or test data.
- [ ] Core domain logic is tested without external I/O.
- [ ] Timeouts, the retry budget, and exit codes are explicit.
- [ ] A request or job can be traced through structured logs.
- [ ] Release artifacts can be rebuilt in a clean environment.

## Common Failures

- The code succeeds only in a notebook, while package imports and the CLI are broken.
- Global state and import-time side effects make results depend on test order.
- `except Exception: pass` makes failure look like success.
- Always installing the latest versions makes yesterday's environment impossible to reproduce.
- Many logs are generated, but without identifiers or event names they cannot be searched.

Production readiness should be judged not by lines of code, but by **how reliably the software can be reinstalled, failures reproduced, and recovery performed safely**.

## References

- [Python Packaging User Guide — Writing `pyproject.toml`](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/)
- [Python Packaging User Guide — Packaging Python Projects](https://packaging.python.org/tutorials/packaging-projects/)
