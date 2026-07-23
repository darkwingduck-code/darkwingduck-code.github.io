---
title: "A Risk-Based Software Verification Strategy Beyond the Testing Pyramid"
date: 2026-07-21 10:40:00 +0900
categories: [Software Engineering, Testing]
tags: [testing, pytest, contract-testing, property-testing, integration-testing, quality]
description: How to combine unit, integration, contract, and E2E tests according to risk and design strong oracles and invariants.
lang: en
translation_key: software-testing-strategy
hidden: true
---

{% include language-switcher.html %}

The purpose of testing is not to execute lines of code, but to **find important failures before release and produce evidence that contracts remain intact after changes**. Even high coverage provides little confidence if assertions are weak or the tests do not address real risks.

## Work Backward from Risk to Design Tests

Start by writing down the failure modes.

| Failure mode | Impact | Appropriate verification |
|---|---|---|
| Boundary-value classification error | Incorrect decision | Unit and boundary-value tests |
| DB schema mismatch | Complete request failure | Integration and migration tests |
| Broken client/server contract | Integration failure after deployment | Contract tests |
| Authentication bypass | Unauthorized access | Security and integration tests |
| Missing deployment configuration | Service startup failure | Smoke test |
| Broken long user flow | Critical workflow interruption | A small number of E2E tests |

Automate first the items with high likelihood, impact, and difficulty of detection. Money, permissions, state transitions, and data-loss paths take priority over trivial getters.

## Test Layers Answer Different Questions

### Unit Tests

Quickly answer, “Is a small rule correct for every important input?” Isolate I/O and focus on boundary values, exceptions, and invariants.

### Integration Tests

Answer, “Do real components communicate under the same contract?” Verify differences that mocks can conceal by using the real database engine, file format, serializer, and HTTP adapter.

### Contract Tests

Answer, “Are the schema and semantics agreed upon by provider and consumer still intact?” Check field types, required and optional fields, error codes, and backward compatibility.

### E2E Tests

Answer, “Can users achieve their critical outcomes in the deployed system?” Because these tests are slow and fragile, begin with three to five high-value paths instead of automating every screen.

### Post-Deployment Verification

Do not stop after checking that a health endpoint returns 200. Use safe synthetic transactions to check connections to critical dependencies, minimal reads and writes, permissions, versions, and background-worker status.

## Good Tests Have Clear Arrange–Act–Assert Phases

```python
def test_cancelled_job_cannot_restart() -> None:
    # Arrange
    job = Job.cancelled(id="job-example")

    # Act
    result = job.start()

    # Assert
    assert result.is_error
    assert result.code == "INVALID_STATE_TRANSITION"
    assert job.status == "cancelled"
```

Too many actions in one test make it unclear where the failure occurred. At the other extreme, pinning private implementation methods causes even valid refactoring to break tests. Verify externally observable results and critical invariants.

## Combine Example-Based and Property-Based Tests

Example tests are easy to read, but they cover only cases the developer anticipated. Property-based tests check properties that must always hold across a broad input space.

For example, consider these properties for a normalization function.

- The output lies within the permitted range.
- Normalizing the same input twice produces the same result.
- Reordering the input does not change an order-independent aggregate result.
- Serializing and then deserializing preserves meaning.

Numerical computations need a justified error tolerance. An arbitrarily large `epsilon` conceals errors, while requiring bitwise equality makes tests unstable across platforms. Combine absolute and relative error according to the value's scale and the problem conditions.

## Choose Test Doubles Precisely

- stub: Returns a predetermined value.
- fake: A simplified but functional replacement implementation.
- spy: Observes call history.
- mock: Specifies expected interactions.

A network mock is useful when testing domain rules. However, mocking real boundaries such as SQL dialects, transactions, and serialization misses integration errors. Separate “what should be isolated for speed?” from “what must be verified with the real thing?”

## Control Nondeterminism

Flaky tests destroy trust. Make time, randomness, the network, parallelism, and global state controllable dependencies.

```python
from datetime import datetime, timezone
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime: ...


class FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 1, 1, tzinfo=timezone.utc)
```

Recording a random seed alone does not guarantee complete determinism. Library versions, parallel execution, hardware-specific operations, and input order can also affect results. Define the required level of reproducibility first.

## Essentials of Database Testing

- Each test uses independent data and a separate namespace.
- Apply migrations both to an empty DB and to a DB from the previous version.
- Verify that unique, foreign-key, and check constraints actually prevent failures.
- Do not rely solely on transaction rollback; account for background workers and separate connections.
- Do not copy production data into test fixtures.

## Make Failures Investigable

When CI fails, preserve at least the following.

- Test name and seed
- Input fixture or minimal reproducing input
- Application/logical version
- Environment and dependency-lock information
- Relevant logs, traces, and screenshots
- Distinction between the initial cause and subsequent failures

A policy of unconditionally rerunning tests until they turn green conceals flaky tests. They need isolation, cause classification, an owner, and a deadline for correction.

## Verification Checklist

- [ ] The most expensive failure modes are mapped to the tests that detect them.
- [ ] Values immediately below, at, and immediately above boundaries are checked.
- [ ] Tests verify not only exceptions but also whether state is preserved after failure.
- [ ] Integration tests cover real DB, serializer, and HTTP boundaries.
- [ ] Schema-breaking changes are detected in CI.
- [ ] Only critical user flows are maintained as stable E2E tests.
- [ ] Nondeterminism in time, randomness, and external dependencies is controlled.
- [ ] Flaky tests are not concealed solely through automatic reruns.
- [ ] Post-deployment smoke tests and rollback criteria are in place.

## Common Failures

- Treating the coverage number as a quality goal.
- Repeating the same happy-path case while missing boundaries, errors, and concurrency.
- Pinning even internal implementation call counts, which raises refactoring costs.
- Tests sharing order and global state with one another.
- Mocking every external boundary and missing actual schema and transaction errors.
- Depending on arbitrary sleeps and screen coordinates in E2E tests.

The final question for a testing strategy is not “How many tests did we write?” but **“Which risks did we control, and with what evidence?”**
