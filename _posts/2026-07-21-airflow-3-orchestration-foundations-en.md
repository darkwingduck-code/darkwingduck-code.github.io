---
title: "Airflow 3 Orchestration Foundations: Designing Time, State, and Rerunnability"
date: 2026-07-21 10:10:00 +0900
categories: [Data Engineering, Orchestration]
tags: [airflow, orchestration, data-pipelines, idempotency, observability]
description: Design XCom, Connections, Variables, retries, backfills, deferrable sensors, asset scheduling, and operational verification around Airflow 3 DAGs, tasks, and data intervals.
lang: en
hidden: true
translation_key: airflow-3-orchestration-foundations
---

{% include language-switcher.html %}

## The problem: connecting tasks in order does not make an operable pipeline

Airflow is an orchestrator for developing, scheduling, and observing batch workflows. It does not replace the actual compute engine or a high-volume data transport. Missing this boundary causes the following problems.

- Execution time is confused with the period being processed, so the wrong partition is read.
- Appends repeat on task retry, duplicating data.
- Passing a dataframe through XCom bloats the metadata database.
- A sensor occupies a worker slot for a long time.
- `catchup=False` is mistaken for a prohibition on reprocessing historical data.
- Secrets and runtime configuration are written directly into DAG source.
- The DAG succeeds while artifact freshness and quality fail.

An operable Airflow workflow must answer three questions clearly.

1. **Which data interval** does this DAG run process?
2. Does rerunning the same task produce **the same final state**?
3. After failure, how do we check not only Airflow state but also **whether the user-facing artifact is healthy**?

The Airflow 3 APIs and behavior in this article follow the [official Apache Airflow stable 3.x documentation](https://airflow.apache.org/docs/apache-airflow/stable/) available at the time of writing. Public APIs and operator arguments may vary by minor and provider version, so pin the documentation for the deployed version as well.

## Mental model: a DAG run is an orchestration instance corresponding to a time interval or event

### Distinguish DAGs, tasks, task instances, and DAG runs

- **DAG**: a workflow definition containing schedules, tasks, dependencies, and callbacks
- **task**: a work template declared through an Operator, Sensor, TaskFlow `@task`, or similar interface
- **DAG run**: execution of a DAG for a particular logical interval or event
- **task instance**: an actual execution of a task within a particular DAG run

If the same task definition executes daily, there is one task but a task instance in each day's DAG run. A retry is a new attempt by the same task instance; a backfill creates new DAG runs for historical intervals.

Airflow 3's public authoring interface centers on `airflow.sdk`. DAG files should use public APIs and provider operators instead of manipulating internal metadata models. See the official [DAGs and Tasks documentation](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/) for the fundamentals.

### Logical date is not actual execution time

A time-based schedule has a **data interval**. If a daily DAG run processes `[2026-01-01 00:00, 2026-01-02 00:00)`, the scheduler generally creates the run after the interval ends. Its logical date represents the start of the data interval, not its wall-clock start time.

The official [DAG Runs documentation](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/dag-run.html) explains that a scheduled run is created after its data interval ends and that logical date represents the interval start. Choosing a partition with `now()` can therefore read different data after queue delays, retries, or backfills.

Time-based tasks should use:

- `data_interval_start`: inclusive start of the interval
- `data_interval_end`: exclusive end of the interval
- `run_id`: distinguishes manual reruns or backfill instances for the same interval

Standardizing on half-open intervals `[start, end)` reduces duplicate and missing boundary events.

### A dependency is execution order, not a data transport

`extract >> transform` expresses a control dependency: transform may execute after extract succeeds. It does not mean large data moves between worker memories.

Recommended data plane:

```text
task A -> object/table/stream에 데이터 기록
       -> XCom에는 URI, partition, row count, checksum만 기록
task B -> 해당 URI와 metadata를 받아 외부 저장소에서 읽기
```

The Airflow metadata database is for orchestration state. Put actual datasets, model binaries, and dataframes in appropriate object storage, databases, or compute engines.

## Practical pattern: build interval-based idempotent tasks first

### Understand data intervals and atomic publication with a safe local example

The following DAG creates one file per interval under `/tmp` and atomically replaces the same target when the interval is rerun. It is for learning and local tests; in production, adapt it to object-storage conditional writes, table transactions, or atomic-rename semantics.

```python
from __future__ import annotations

import hashlib
import json
from datetime import timedelta
from pathlib import Path

import pendulum
from airflow.sdk import DAG, Asset, get_current_context, task


OUTPUT_ROOT = Path("/tmp/airflow-orchestration-example")
PUBLISHED_ASSET = Asset("local-example://orchestration/partitions")


with DAG(
    dag_id="interval_aware_example",
    schedule="@daily",
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
    max_active_runs=1,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=2),
    },
) as dag:

    @task(outlets=[PUBLISHED_ASSET])
    def publish_partition() -> dict[str, str]:
        context = get_current_context()
        interval_start = context["data_interval_start"]
        interval_end = context["data_interval_end"]
        run_id = context["run_id"]

        partition = interval_start.format("YYYY-MM-DD")
        target = OUTPUT_ROOT / f"date={partition}" / "result.json"
        target.parent.mkdir(parents=True, exist_ok=True)

        # run_id를 그대로 파일명에 쓰지 않고 안정된 제한 길이 ID로 만든다.
        attempt_id = hashlib.sha256(run_id.encode("utf-8")).hexdigest()[:12]
        staging = target.with_name(f".{target.name}.{attempt_id}.tmp")

        payload = {
            "data_interval_start": interval_start.isoformat(),
            "data_interval_end": interval_end.isoformat(),
        }
        staging.write_text(
            json.dumps(payload, sort_keys=True),
            encoding="utf-8",
        )
        staging.replace(target)

        # XCom에는 작은 metadata만 반환한다.
        return {
            "path": str(target),
            "partition": partition,
        }

    @task
    def verify_partition(metadata: dict[str, str]) -> None:
        path = Path(metadata["path"])
        if not path.is_file() or path.stat().st_size == 0:
            raise RuntimeError(f"published partition is invalid: {metadata['partition']}")

    verify_partition(publish_partition())


if __name__ == "__main__":
    dag.test()
```

The official [DAG debugging documentation](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/debug.html) provides `dag.test()` for fail-fast execution of tasks in one process. Local success does not validate the executor, network, permissions, or secret backend, so a separate integration environment is required.

### Idempotency is a prerequisite for retries and backfills

An idempotent task produces the same final state after repeated executions with the same logical input. This is stronger than merely saying “the second run succeeds.”

Practical patterns:

- derive output keys from `data_interval_start/end`, not wall clock
- use partition overwrite, merge/upsert, or replace as appropriate instead of append
- finish in staging before atomic publication
- send deterministic idempotency keys to external APIs
- combine side effects and completion markers through a transaction or compare-and-set
- specify restart position and cleanup ownership after partial completion

Email delivery, payments, and external ticket creation can produce duplicate side effects on a simple retry. Do not rely on Airflow retry settings alone; use the external system's idempotency key and result-query API.

For reproducibility, log the following inputs while excluding secrets.

- DAG ID, task ID, run ID, and try number
- data interval start/end
- source partition/version and output URI
- code/image revision
- row count, checksum, and data-quality results

### Retry only transient errors

Errors suited to retry:

- temporary network timeout
- rate limiting with an explicit retry-after
- temporarily unavailable dependency
- worker preemption or process crash

Errors that retry cannot fix:

- schema/code mismatch
- invalid credentials or permissions
- invalid input
- deterministic bug
- persistently exceeded storage quota

Set a limited attempt count, exponential backoff, maximum delay, and task execution timeout. Applying a high retry count to every task delays incident detection and creates retry storms against dependencies.

If a task's own library retries before Airflow does, the total attempt count may multiply. Budget which layer handles fast network retries and which handles workflow-level reruns.

## Separate XCom, Connections, Variables, and Params by role

| Tool | Scope and purpose | Suitable values | Values to avoid |
|---|---|---|---|
| XCom | communication within a task instance/DAG run | URI, partition, small JSON metadata | dataframe, large binary, retry checkpoint |
| Connection | endpoint and authentication for an external system | host, schema, conn ID, credential reference | task result, business parameter |
| Variable | installation- or team-scoped runtime configuration | emergency runtime switch, small per-deployment setting | versioned constant, per-run input, large JSON |
| Params | validated per-DAG-run input | processing mode, bounded dates/options | long-lived secret, result between tasks |

The official [XCom documentation](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/xcoms.html) states that XCom is for small serializable values, not large objects such as dataframes. Airflow 3 requires `task_ids` when retrieving another task's XCom, and XComs may be cleared before retrying a failed task, so do not use them as durable checkpoints.

A TaskFlow return is convenient, but the entire object may be serialized to XCom. Return a manifest like this instead of the actual external work result.

```python
{
    "uri": "object://<BUCKET>/<KEY>",
    "partition": "2026-01-01",
    "checksum": "sha256:<DIGEST>",
    "row_count": 1234,
}
```

A Connection references an external connection by logical `conn_id`, while Hooks/providers handle actual credentials. Do not place raw URIs and passwords in DAG source. Follow the [Connections & Hooks documentation](https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/connections.html).

A Variable is a global runtime key/value store. The official [Variables documentation](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/variables.html) recommends putting configuration in version-controlled DAG source where possible and limiting Variables to genuinely runtime-dependent values. Repeated top-level `Variable.get()` calls couple parsing performance and availability to metadata/secret-backend lookups; read them at task runtime or in templates.

## Manage secrets in execution identity and a secrets backend, not in DAGs

Using an Airflow Connection or Variable name does not automatically make a value safe. Review exposure paths through the metadata database, environment variables, logs, serialized DAGs, and task environments.

Recommended principles:

- record only `conn_id` and logical secret names in DAGs
- use an external secrets backend or workload identity
- separate the secret scopes required by scheduler, DAG processor, API server, and worker
- minimize cloud roles and namespace permissions per worker task
- prefer short-lived credentials to long-lived access keys
- never log raw secrets, Connection URIs, or the complete environment

Airflow 3 can configure a separate worker secrets backend. Because lookup ordering and key collisions matter, ensure the same name is not present in several backends during migration. Follow the official [Secrets Backend documentation](https://airflow.apache.org/docs/apache-airflow/stable/security/secrets/secrets-backend/index.html).

Fernet encryption and UI masking do not protect the full secret lifecycle. The worker process holds plaintext as soon as task code reads a value. Worker isolation, log redaction, egress restrictions, rotation, and audits are also required.

## Separate waiting from worker slots

### Poke, reschedule, and deferrable modes

| Mode | Worker slot while waiting | Suitable situation | Main tradeoff |
|---|---:|---|---|
| sensor `poke` | continuously occupied | very short waits requiring frequent checks | wastes workers during long waits |
| sensor `reschedule` | released between checks | waits that allow polling every few minutes | scheduler rescheduling overhead |
| deferrable operator | handed to triggerer and released | long external-event waits | triggerer operations and provider support required |

The official [Sensors documentation](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/sensors.html) explains the slot-use difference between `poke` and `reschedule`. According to [Deferrable Operators & Triggers](https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/deferring.html), an asynchronous trigger in the triggerer polls during deferral while the task releases its worker slot.

Check the provider-version documentation to see whether a sensor supports `deferrable=True`; the argument cannot be added arbitrarily to every sensor. Do not place blocking I/O or CPU work in custom triggers. One trigger blocking the event loop can delay many deferred tasks.

Every waiting task must have:

- an overall `timeout`
- a polling interval or trigger semantics
- whether timeout causes soft or hard failure
- a criterion distinguishing stale and new events
- immediate success if the external condition is already satisfied
- monitoring of triggerer health and deferred-task age

If polling is unavoidable, verify not just that a file exists but also its expected partition, checksum/completion marker, and event timestamp. Do not mistake an old file from a previous run for a new success.

## Catchup and backfill are different controls for historical intervals

### Catchup

With `catchup=True` on a time-based schedule, the scheduler may create DAG runs for uncreated data intervals after `start_date`. Deploying a new DAG with an old `start_date` can create many runs at once.

`catchup=False` prevents the everyday scheduler from automatically creating missing historical intervals. It does not mean tasks may use `now()` or that historical reprocessing is impossible.

### Backfill

A backfill creates DAG runs for an explicit historical date range. Airflow 3's official [Backfill documentation](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/backfill.html) provides reprocessing behavior, an independent `max_active_runs`, execution ordering, and dry runs.

First inspect the intervals that would be created.

```bash
export DAG_ID='interval_aware_example'
export FROM_DATE='2026-01-01'
export TO_DATE='2026-01-07'

airflow backfill create \
  --dag-id "$DAG_ID" \
  --from-date "$FROM_DATE" \
  --to-date "$TO_DATE" \
  --reprocess-behavior failed \
  --max-active-runs 2 \
  --dry-run
```

Before creating them, check:

- Does source retention still preserve the historical interval?
- Is current code compatible with the historical schema?
- Can output overwrite conflict with concurrent downstream work?
- Are API quotas, database load, and pool capacity sufficient?
- Does reprocessing behavior match the intent for existing successful runs?
- Do dependencies allow newest-first or oldest-first processing?

Use a separate pool or quota so backfill concurrency does not compete without limit with production traffic. Judge success by partition counts, checksums, data quality, and downstream freshness as well as task state.

## When to use assets and event-driven scheduling

A time schedule strongly expresses “process the previous day's interval after this time each day.” If upstream completion varies greatly or dependencies among several producers must be expressed, an asset-aware schedule may be more direct.

A producer declares an output asset; after success, it can schedule a consumer DAG.

```python
import pendulum
from airflow.sdk import DAG, Asset, task


CURATED_ASSET = Asset("object://<BUCKET>/curated/<DATASET>")


with DAG(
    dag_id="asset_producer_example",
    schedule="@daily",
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
):
    @task(outlets=[CURATED_ASSET])
    def publish() -> None:
        # 실제 구현은 output을 완전히 검증한 뒤 atomic publish해야 한다.
        pass

    publish()


with DAG(
    dag_id="asset_consumer_example",
    schedule=[CURATED_ASSET],
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
):
    @task
    def consume() -> None:
        pass

    consume()
```

According to the official [Asset-Aware Scheduling documentation](https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/asset-scheduling.html), an asset update is recorded when the producer task succeeds, and the consumer DAG is scheduled. AND/OR conditions among assets and combinations with time schedules are possible, but first define event order, duplication, coalescing, and replay semantics for complex logic.

Airflow 3's [event-driven scheduling](https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/event-scheduling.html) can connect external events to asset updates. Not every `BaseTrigger` is suitable; a compatible trigger is required. If a message queue provides at-least-once delivery, design event IDs and idempotency so duplicate delivery does not duplicate results.

Assets do not automatically create a full data catalog. Manage URI naming, owner, schema, freshness, partition, and quality contracts separately. Do not put credentials or personal identifiers in asset URIs or `extra`; official documentation assumes these may be unencrypted and recommends publicly safe identifiers.

## Separate DAG parsing from business logic

The scheduler and DAG processor repeatedly import DAG files. These top-level actions make parsing slow and unreliable.

- external API and database calls
- loading large dataframes
- repeated Variable/Connection lookups
- importing heavy machine-learning libraries
- nondeterministically changing task structure based on current time

Keep DAG files focused on graph declarations and thin adapters. Put domain logic in an ordinary Python package and unit-test it without Airflow.

```text
repository/
├── dags/
│   └── curated_pipeline.py
├── src/
│   └── pipeline_core/
│       ├── extract.py
│       ├── transform.py
│       └── contracts.py
└── tests/
    ├── test_dag_structure.py
    └── test_transform.py
```

If provider/Airflow dependency conflicts are large or computation is heavy, have the task submit a separate container or job. Installing every workload dependency on Airflow workers enlarges images and increases cross-DAG conflicts and upgrade risk.

## Observability: watch the Airflow control plane and data product together

### Control-plane signals

- scheduler and DAG processor heartbeats
- DAG import errors and parse duration
- queued/scheduled task age
- open/queued/running executor and pool slots
- deferred-task count and triggerer health
- metadata database latency, connections, and storage growth
- remote task-log delivery failures

The official [Airflow metrics documentation](https://airflow.apache.org/docs/apache-airflow/stable/administration-and-deployment/logging-monitoring/metrics.html) provides `scheduler_heartbeat`, `dag_processor_heartbeat`, `dag_processing.import_errors`, and pool, executor, and task-state metrics. Verify names and tags for the installed executor and telemetry backend.

### Workflow signals

- DAG run success/failure and duration
- task retry, timeout, zombie, and heartbeat failure
- schedule delay: interval end to run start
- queue delay: task schedulable to actual start
- end-to-end completion: interval end to output publication

### Data-product signals

- freshness and latest successful partition
- expected/actual row counts and volume anomalies
- schema/contract violations
- nulls, duplicates, and referential integrity
- source-to-output reconciliation and checksums

A DAG can succeed after publishing an empty file, while the data product fails. Conversely, the user SLO may hold if a task retries and still produces correct output on time. Connect on-call pages to freshness and correctness impact on important artifacts rather than the number of failed tasks.

Structure logs with DAG/task/run/try/data interval/output revision. Do not log secrets, Connection URIs, or full source records. Configure remote logging for disposable workers and observe log-backend failures. See the official [Production Deployment documentation](https://airflow.apache.org/docs/apache-airflow/stable/administration-and-deployment/production-deployment.html).

## Local test and CI verification checklist

### Fast verification layers

1. Unit-test ordinary Python domain logic.
2. Check every DAG import and parse error.
3. Structurally test DAG IDs, task IDs, dependencies, schedules, and retry policies.
4. Run a representative interval locally with `dag.test()`.
5. Test actual Connections, secret backend, executor, and storage integration in staging.
6. Observe a synthetic DAG and freshness after production deployment.

Official [Best Practices: Testing a DAG](https://airflow.apache.org/docs/apache-airflow/stable/best-practices.html#testing-a-dag) distinguishes DAG loader tests, unit tests, self-checks, and staging verification.

Example CI DagBag test:

```python
from airflow.dag_processing.dagbag import DagBag


def test_all_dags_import_without_errors() -> None:
    dagbag = DagBag(dag_folder="dags", include_examples=False)
    assert dagbag.import_errors == {}


def test_critical_dag_contract() -> None:
    dagbag = DagBag(dag_folder="dags", include_examples=False)
    dag = dagbag.get_dag("interval_aware_example")

    assert dag is not None
    assert dag.catchup is False
    assert set(dag.task_ids) == {"publish_partition", "verify_partition"}
    assert dag.get_task("publish_partition").downstream_task_ids == {
        "verify_partition"
    }
```

`airflow.dag_processing.dagbag` appears in official test examples but is an internal package path, so check test imports during Airflow minor upgrades. Prefer the Airflow 3 public interface in production DAG code.

Example CI commands:

```bash
python -m compileall -q dags src tests
python -m pytest -q
airflow dags list
airflow dags list-import-errors
```

Use the same Airflow core, provider, and Python dependency lock in CI as production. Airflow behaves as both application and library, so combine official constraints with the organization's locking strategy and verify core/provider compatibility in staging.

DAG review:

- [ ] Schedule, timezone, `start_date`, and catchup semantics are clear.
- [ ] Tasks derive partitions from `data_interval_start/end`.
- [ ] Retries and backfills do not duplicate output.
- [ ] Timeouts, retries, pools, and concurrency match dependency capacity.
- [ ] XCom carries only small metadata.
- [ ] Connections, Variables, and Params are separated by role.
- [ ] No raw secret appears in source, logs, XCom, or asset URIs.
- [ ] Long waits are moved off workers through reschedule, deferral, or events.
- [ ] Top-level parsing performs no network/DB/heavy imports.
- [ ] Leaf tasks and trigger rules do not misrepresent overall DAG-run state.

Operations review:

- [ ] Backfill dry run, concurrency, and reprocessing behavior were reviewed.
- [ ] Source retention and historical schema compatibility were checked.
- [ ] Scheduler, DAG processor, triggerer, executor, and metadata DB are observed.
- [ ] User-artifact freshness and correctness alerts exist.
- [ ] Log retention and metadata database cleanup policies exist.
- [ ] Metadata backup, migration, provider compatibility, and staging are tested before upgrades.
- [ ] Task clear/retry/backfill permissions and audit logs are restricted.

## Failure cases and limitations

### Using Airflow as a data-processing engine

Processing large dataframes in worker memory and passing them through XCom breaks scalability and isolation. Let Airflow orchestrate external compute such as Spark, warehouses, and container jobs while tracking small metadata.

### Using `now()` as a partition key

Retries, queue delays, manual runs, and backfills may read or write different partitions. Derive logical inputs from data intervals and explicit Params.

### Marking task success before output commit

If a task submits an asynchronous external job and succeeds before checking completion, downstream work reads incomplete data. Use a deferrable operator or separate sensor to verify terminal state and output quality before success.

### Using XCom as a durable state store

XCom is for small task-communication values and may be cleared on retry. Store long-lived checkpoints and large payloads with versions in external storage, placing only references in XCom.

### Hiding instability by increasing retries

Retries help transient errors but delay detection of deterministic failures and increase dependency load. Define an error taxonomy and retry budget, then fail with actionable context when exhausted.

### Expressing every dependency through sensor polling

This increases worker and scheduler load and polling latency. If the source emits events, consider asset/event schedules; if polling is necessary, use a deferrable sensor and timeout.

### Mistaking asset events for exactly-once delivery

Producer reruns, duplicate external events, and consumer reprocessing after failure are all possible. An asset expresses a dependency, not a business transaction. Outputs and consumers must both be idempotent.

### Believing Airflow replaces streaming

Airflow suits batch-oriented orchestration. When low-latency continuous event processing, per-event state, and backpressure are central, let a stream processor and messaging system own the data plane while Airflow handles batch reconciliation and management workflows.

The core of Airflow operations is not an elaborate DAG graph. It is defining processing intervals precisely, making tasks rerunnable, separating small orchestration metadata from the real data plane, and designing historical reprocessing and incident response from the beginning.
