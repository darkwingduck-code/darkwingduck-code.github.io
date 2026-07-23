---
title: "Testing Deterministic Simulations: Invariants, Property-Based Testing, and Replay"
date: 2026-07-21 09:40:00 +0900
categories: [Software Engineering, Simulation Testing]
tags: [determinism, simulation-testing, invariants, property-based-testing, replay, regression-testing, reproducibility]
description: "Learn how to validate deterministic simulators with invariants, generative property tests, state hashes, and event replay rather than a handful of examples."
math: true
lang: en
hidden: true
translation_key: deterministic-simulation-testing-invariants-replay
---

{% include language-switcher.html %}

If simulation testing stops at “run a representative input and see whether the graph looks similar,” it is difficult to know which law a small change violated. Conversely, freezing an entire output file as a golden file makes tests fail on harmless floating-point differences and can preserve an incorrect legacy result forever.

A stronger strategy combines three layers.

1. **Invariants and relations** that every correct run must satisfy
2. **Property-based tests** that automatically explore a broad input space
3. **Seed, event, and state replay** that reproduces a failure exactly

## 1. Distinguish Three Terms First

### Determinism

The property of obtaining the same state transitions from the same initial state, input, configuration, and execution environment.

$$
s_{t+1}=F(s_t,u_t;\theta)
$$

must produce the same \(s_{t+1}\) for the same \(s_t,u_t,\theta\).

### Reproducibility

The ability to recreate a result within an allowed range at a different time or in another environment. It is broader than bitwise determinism and requires information about the source, dependencies, configuration, data, compiler, and hardware.

### Robustness

The property that a conclusion remains stable under acceptable changes in input or environment. A program that always gives the same wrong answer for the same input is deterministic, but neither robust nor correct.

## 2. Hidden Inputs That Break Determinism

Function arguments in the code are not the only inputs. The following can also affect state transitions.

- pseudo-random number generator seed and algorithm
- wall-clock time and locale
- hash-map iteration order
- thread scheduling and reduction order
- atomic operations in GPU kernels
- compiler flags and fast-math
- BLAS, runtime, and driver
- file-enumeration order
- environment variables and configuration defaults
- responses from external services
- uninitialized memory

Consequently, “we fixed the seed” does not complete determinism. It is better to separate random streams by subsystem so a change in execution order does not alter another subsystem's random-number consumption.

## 3. A Test Lattice Rather Than a Test Pyramid

A simulator needs several kinds of oracle.

| Test type | Question | Failures it reveals well |
|---|---|---|
| unit test | Does a small operation behave as defined? | signs, units, indexes, boundary handling |
| analytic/benchmark test | Does it converge to a known solution? | equation or scheme implementation |
| invariant test | Does it obey laws that must be preserved? | cumulative drift, missing sources |
| property-based test | Do properties hold over broad valid inputs? | unexpected corner cases |
| metamorphic test | Are output relations correct under input transformations? | logical errors in problems without an oracle |
| differential test | Does it agree with an independent implementation? | implementation-specific divergence |
| regression/golden test | Did approved behavior remain unchanged? | unintended changes |
| replay test | Can a past failure be reproduced exactly? | nondeterminism, omitted state |

No one type replaces another. A conservation test may pass while the spatial distribution is wrong, and a golden output may match even though the reference itself is wrong.

## 4. Turn Invariants into Executable Specifications

An invariant should not be merely a sentence in documentation; it should be an assertion evaluated on every run.

### Conservation Equation

Given a general balance

$$
M_{t+1}
=
M_t+\Delta t\,(I_t-O_t+S_t)+e_t
$$

the defect

$$
d_t=M_{t+1}-M_t-\Delta t\,(I_t-O_t+S_t)
$$

must remain within the numerical tolerance.

### Bounds and Positivity

States with restricted domains, such as probabilities, concentrations, and mass fractions, must satisfy bounds such as

$$
0\le x_i\le 1
$$

At the same time, check whether the scheme permits a small undershoot and whether clipping breaks conservation. Simply replacing negative values with zero can hide a bug.

### Symmetry and Equivariance

If rotating, reflecting, or permuting the input coordinates should induce the same physical transformation in the output, test

$$
f(Tx)=Tf(x)
$$

This relation provides a strong oracle even when the correct output values are unknown.

### Dimensional Consistency and Scale Relations

When a unit change expresses the same physical state, dimensionless outputs should remain the same. First derive whether scale invariance actually holds for the governing equation and boundary conditions.

### State-Machine Invariants

- Do not remove a nonexistent entity twice.
- Do not process a completed event again.
- Resource counts never become negative.
- Timestamps do not decrease against causal order.
- The lifecycle of each entity ID follows only valid state transitions.

## 5. Use Absolute and Relative Tolerances Together

The basic form of a floating-point comparison is

$$
|a-b|
\le
\mathrm{atol}
+\mathrm{rtol}\cdot s
$$

where \(s\) is a reference scale appropriate to the problem.

~~~python
def assert_close(actual, expected, *, atol, rtol, scale=None):
    reference_scale = abs(expected) if scale is None else abs(scale)
    error = abs(actual - expected)
    limit = atol + rtol * reference_scale
    assert error <= limit, {
        "actual": actual,
        "expected": expected,
        "error": error,
        "limit": limit,
    }
~~~

Relative error alone cannot be used when the expected value is near zero, while absolute error alone is difficult to interpret for large values. A tolerance is not a number adjusted after the fact to make a test pass; it should be an error budget based on:

- discretization truncation error
- iterative solver tolerance
- floating-point accumulation bounds
- measurement or input precision
- downstream decision thresholds

## 6. Property-Based Testing: Generate Properties, Not Examples

An example-based test checks only points a person thought of. Property-based testing generates valid inputs and shrinks a failure to a simpler counterexample.

The following is a conceptual example.

~~~python
from hypothesis import given, strategies as st

@given(
    total=st.floats(min_value=0.0, max_value=1.0e3,
                    allow_nan=False, allow_infinity=False),
    fraction=st.floats(min_value=0.0, max_value=1.0,
                       allow_nan=False, allow_infinity=False),
)
def test_partition_conserves_total(total, fraction):
    left, right = partition(total, fraction)

    assert left >= 0.0
    assert right >= 0.0
    assert_close(
        left + right,
        total,
        atol=1.0e-12,
        rtol=1.0e-12,
    )
~~~

These numbers illustrate the code form; they are not criteria for a particular project. Set actual tolerances from computational precision and the error budget.

### Qualities of a Good Generator

- It satisfies physically valid constraints.
- It generates enough boundary values, zeros, very small values, and wide dynamic ranges.
- It does not generate correlated variables independently.
- It separates invalid-input tests from valid-domain property tests.
- It saves not only the failing seed but also the shrunken minimal input.

Unlike fuzzing that merely throws many random inputs at a program, property-based testing states **what must be true**.

## 7. Metamorphic Testing: Know the Relation Even When the Answer Is Unknown

For a complex simulation, the exact output for an arbitrary input is difficult to know. Instead, test the expected relationship between outputs when the input is transformed.

For example:

- Changing entity order leaves permutation-invariant aggregates unchanged.
- Translating the domain and source by the same symmetry translates the output identically.
- A limiting case with a zero source reaches a known simple state.
- The total of two independent combined subsystems equals the sum of their individual totals.
- Running two consecutive time intervals agrees with one uninterrupted run within checkpoint error.

The final relation tests both the semigroup property and checkpoint serialization.

$$
F_{t_2}\left(F_{t_1}(s_0)\right)
\approx
F_{t_1+t_2}(s_0).
$$

Adaptive solvers or event localization may take different execution paths, so explicitly define the required level of equivalence.

## 8. Minimum Records Required for Replay

Reproducing a failure requires **input events and state lineage**, not merely log messages.

### Run Manifest

~~~yaml
schema_version: 1
run_id: "<opaque-run-id>"
source_revision: "<commit>"
configuration_digest: "<hash>"
input_digest: "<hash>"
dependency_lock_digest: "<hash>"
random_streams:
  initialization: "<seed>"
  events: "<seed>"
execution:
  worker_count: "<count>"
  numeric_mode: "<mode>"
~~~

Replace the placeholders with actual values, but do not include secrets, user paths, or internal hostnames.

### Event Log

In an event-sourcing design, give each event:

- a monotonically increasing sequence number;
- simulation time and logical time;
- event type and schema version;
- a canonical payload;
- a pre-state or post-state digest; and
- a causal parent or correlation key.

The replay engine replaces external I/O with recorded responses and applies the event sequence in the same order.

### Checkpoint

Replaying a long run from the beginning is expensive. Store a versioned checkpoint together with the subsequent event log. The checkpoint loader must test migration from older schemas or fail clearly when a version is unsupported.

## 9. Pitfalls of State Hashes

A state hash helps locate the step where divergence begins, but is unreliable without canonicalization.

- Sort map keys.
- Fix the serialization format and schema version.
- Exclude transient caches and timestamps.
- Define policies for NaN representation and signed zero.
- Do not hash floats after arbitrarily rounding them to strings.

Separate a discrete core that requires bitwise equality from numeric fields suited to tolerance comparisons. For example, compare event order and entity count exactly, while comparing continuous fields with norms and invariants.

## 10. Parallel Computation and Reproducible Reduction

Floating-point addition is not exactly associative.

$$
(a+b)+c\neq a+(b+c)
$$

so reduction results can vary with thread scheduling. Options include:

- a fixed partition and reduction tree
- pairwise or compensated summation
- a deterministic library mode
- an exact accumulator for critical totals
- a numerically equivalent rather than bitwise criterion

A nondeterministic reduction may be allowed for performance. In that case, use statistical or tolerance-based tests to verify that results stay within the allowed envelope, and document the contract that exact replay is unavailable.

## 11. Use Regression and Golden Files Safely

Golden tests are useful for detecting changes to APIs, formats, and representative trajectories, but they require these principles.

1. Version-control the golden-generation procedure too.
2. During approval, present a human-readable summary of the diff.
3. Prefer key quantities of interest and invariants to an entire large binary.
4. Specify tolerances and ordering.
5. Separate reference updates from ordinary test execution.
6. Do not rely on golden tests without analytic or invariant tests.

“Automatically overwrite the reference file with the new output” disables regression testing.

## 12. A Workflow That Turns Failures into Assets

1. Detect a failure in production or a generative test.
2. Preserve the source revision, manifest, minimal input, event log, and checkpoint.
3. Confirm that replay reproduces the failure.
4. Find the first state digest at which divergence begins.
5. Add the smallest invariant or property test that explains the cause.
6. After the fix, pass both the new test and the existing suite.
7. Retain the minimal case in the counterexample corpus.
8. If nondeterminism itself caused the failure, add a separate repeated-scheduling test.

## 13. Verification Checklist

- [ ] Were determinism, reproducibility, and correctness distinguished?
- [ ] Were hidden inputs and the execution environment recorded in addition to the seed?
- [ ] Were random streams separated by subsystem?
- [ ] Are critical conservation equations and bounds runtime assertions or tests?
- [ ] Does the property generator handle physical constraints and boundary values?
- [ ] Were metamorphic relations derived from governing rules?
- [ ] Do tolerances have numerical justification and units?
- [ ] Were exact- and approximate-comparison targets separated?
- [ ] Were the shrunken input and seed for each failure saved?
- [ ] Are event and checkpoint schemas versioned?
- [ ] Was external I/O fixed or recorded during replay?
- [ ] Is the determinism contract for parallel reduction explicit?
- [ ] Are golden updates prevented from running automatically without review?

## 14. Pitfalls and Limitations

### An Incorrect Property Makes Correct Code Fail

Monotonicity, symmetry, and positivity may fail depending on the model, boundary conditions, or numerical scheme. Derive properties from the specification and equations, not intuition.

### Exact Replay Is Not Possible on Every Platform

Different compilers, instruction sets, transcendental functions, and GPU scheduling can change bitwise results. Defining supported reproducibility tiers is more realistic.

- Tier A: bitwise equality on identical binary and hardware
- Tier B: numerical tolerance on the same architecture
- Tier C: equivalence of quantities of interest and invariants across platforms

### Logging All State Increases Cost and Information Exposure

Combine event logs, periodic checkpoints, and state digests, with retention and redaction policies. Prevent secrets or personal data from entering payloads at the schema level.

### Deterministic Mode May Differ from the Real Production Path

A test-only single-threaded mode may pass while the production parallel path remains unverified. Compare the deterministic reference mode and actual execution mode with differential tests.

## Conclusion

Strong simulation tests do not memorize particular output values. They encode **what must never break**, **which relations must hold when inputs change**, and **how to restart a failure from the same state**.

Invariants turn physics and domain knowledge into executable specifications, property-based testing discovers inputs people overlooked, and replay transforms a one-off accidental failure into a permanent regression asset.
