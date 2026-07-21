---
title: "Airflow 3 오케스트레이션 기본기: 시간, 상태, 재실행 가능성의 설계"
date: 2026-07-21 10:10:00 +0900
categories: [Data Engineering, Orchestration]
tags: [airflow, orchestration, data-pipelines, idempotency, observability]
description: Airflow 3의 Dag·task·data interval을 기준으로 XCom, Connection, Variable, retry, backfill, deferrable sensor, asset scheduling과 운영 검증을 설계합니다.
---

## 문제: task를 순서대로 연결하는 것만으로 운영 가능한 pipeline이 되지 않는다

Airflow는 batch workflow를 개발·스케줄·관찰하는 오케스트레이터다. 실제 계산 engine이나 대용량 데이터 전달 통로를 대신하지 않는다. 이 경계를 놓치면 다음 문제가 생긴다.

- 실행 시각과 처리 대상 기간을 혼동해 잘못된 partition을 읽는다.
- task 재시도 때 append가 반복돼 데이터가 중복된다.
- dataframe을 XCom으로 넘겨 metadata database가 비대해진다.
- sensor가 worker slot을 장시간 점유한다.
- `catchup=False`를 과거 데이터 재처리 금지로 오해한다.
- secret과 runtime 설정을 Dag source에 직접 적는다.
- Dag는 성공했지만 산출물 freshness와 품질은 실패한다.

운영 가능한 Airflow workflow는 세 가지 질문에 명확히 답해야 한다.

1. 이 Dag run은 **어느 데이터 구간**을 처리하는가?
2. 같은 task가 다시 실행돼도 **같은 최종 상태**를 만드는가?
3. 실패했을 때 Airflow 상태뿐 아니라 **사용자 산출물의 정상 여부**를 어떻게 확인하는가?

이 글의 Airflow 3 관련 API와 동작은 작성 시점의 [Apache Airflow stable 3.x 공식 문서](https://airflow.apache.org/docs/apache-airflow/stable/)를 기준으로 한다. minor version과 provider version에 따라 public API와 operator argument가 달라질 수 있으므로 실제 배포 version의 문서를 함께 고정한다.

## Mental model: Dag run은 시간 또는 event에 대응하는 orchestration instance다

### Dag, task, task instance, Dag run을 구분한다

- **Dag**: schedule, task, dependency, callback을 포함한 workflow 정의
- **task**: 작업의 template. Operator, Sensor, TaskFlow `@task` 등으로 선언
- **Dag run**: 특정 논리 구간이나 event에 대한 Dag 실행 instance
- **task instance**: 특정 Dag run 안에서 task가 실제로 실행되는 instance

같은 task 정의가 매일 하나씩 실행되면 task는 하나지만 task instance는 날짜별 Dag run마다 생긴다. retry는 같은 task instance의 새로운 시도이고, backfill은 과거 구간에 새로운 Dag run들을 생성하는 작업이다.

Airflow 3의 작성용 public interface는 `airflow.sdk`를 중심으로 제공된다. Dag 파일에서 내부 metadata model을 직접 조작하지 않고 public API와 provider operator를 사용한다. 기본 개념은 공식 [Dags와 Tasks 문서](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/)에서 확인할 수 있다.

### logical date는 실제 실행 시각이 아니다

시간 기반 schedule에는 **data interval**이 있다. 일간 Dag run의 처리 구간이 `[2026-01-01 00:00, 2026-01-02 00:00)`이라면 scheduler는 일반적으로 구간이 끝난 뒤 run을 만든다. 이 run의 logical date는 data interval의 시작을 나타내며 wall-clock 실행 시작 시각이 아니다.

공식 [Dag Runs 문서](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/dag-run.html)는 scheduled run이 해당 data interval이 끝난 뒤 만들어지고, logical date가 data interval 시작을 나타낸다고 설명한다. 따라서 task에서 `now()`로 처리 partition을 고르면 queue 지연, retry, backfill 때 다른 데이터를 읽을 수 있다.

시간 기반 task는 다음 값을 기준으로 해야 한다.

- `data_interval_start`: 포함할 구간의 시작
- `data_interval_end`: 포함하지 않을 구간의 끝
- `run_id`: 동일 interval의 수동 재실행·backfill instance 구분

구간은 반개방 interval `[start, end)`로 통일하면 경계 event의 중복과 누락을 줄일 수 있다.

### dependency는 실행 순서이지 데이터 전달 통로가 아니다

`extract >> transform`은 transform이 extract 성공 뒤 실행될 수 있다는 control dependency를 표현한다. 대용량 데이터가 worker memory 사이로 전달된다는 뜻이 아니다.

권장 data plane:

```text
task A -> object/table/stream에 데이터 기록
       -> XCom에는 URI, partition, row count, checksum만 기록
task B -> 해당 URI와 metadata를 받아 외부 저장소에서 읽기
```

Airflow metadata database는 orchestration state를 위한 곳이다. 실제 dataset, model binary, dataframe은 목적에 맞는 object storage, database, compute engine에 둔다.

## 실전 패턴: interval 기반의 idempotent task를 먼저 만든다

### 안전한 local 예제로 data interval과 atomic publish 이해하기

다음 Dag는 `/tmp` 아래에 interval별 파일을 만들고 같은 interval을 재실행하면 동일 target을 atomic replace한다. 학습·local test용이며 실제 운영에서는 object storage의 conditional write, table transaction, atomic rename 특성에 맞게 바꾼다.

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

공식 [Dag debugging 문서](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/debug.html)는 `dag.test()`로 task를 한 process에서 fail-fast 실행하는 방법을 제공한다. local 성공만으로 executor, network, permission, secret backend까지 검증되지는 않으므로 integration 환경이 별도로 필요하다.

### idempotency는 retry와 backfill의 전제다

idempotent task는 동일한 논리 입력으로 여러 번 실행해도 동일한 최종 상태를 만든다. 단순히 “두 번째 실행이 성공한다”보다 강한 조건이다.

실전 패턴:

- output key를 wall clock이 아니라 `data_interval_start/end`로 결정
- append 대신 partition overwrite, merge/upsert, replace를 목적에 맞게 사용
- staging에 완성한 뒤 atomic publish
- 외부 API에는 deterministic idempotency key 전달
- side effect와 완료 marker를 transaction 또는 compare-and-set으로 결합
- task가 부분 완료됐을 때 재시작 위치와 정리 책임을 명시

예를 들어 email 발송, 결제, 외부 ticket 생성은 단순 retry 시 중복 side effect가 생긴다. Airflow retry 설정만 믿지 말고 외부 시스템의 idempotency key와 결과 조회 API를 사용한다.

재현성을 위해 task가 다음 입력을 log에 남기되 secret은 제외한다.

- Dag ID, task ID, run ID, try number
- data interval start/end
- source partition/version과 output URI
- code/image revision
- row count, checksum, data quality 결과

### retry는 일시 오류에만 사용한다

retry가 잘 맞는 오류:

- 일시적인 network timeout
- rate limit과 명시적 retry-after
- 잠시 unavailable한 dependency
- worker 선점이나 process crash

retry가 해결하지 못하는 오류:

- schema와 code 불일치
- 잘못된 credential 또는 권한
- 유효하지 않은 입력
- deterministic bug
- storage quota가 지속적으로 초과된 상태

retry에는 제한 횟수, exponential backoff, 최대 delay, task execution timeout을 둔다. 모든 task에 큰 retry 수를 일괄 적용하면 장애를 늦게 알리고 dependency에 retry storm을 만든다.

Airflow 재시도 전에 task 자체 library도 retry한다면 전체 시도 횟수가 곱해질 수 있다. 어느 층이 빠른 network retry를 담당하고 어느 층이 workflow-level 재실행을 담당하는지 budget을 정한다.

## XCom, Connection, Variable, Params를 역할별로 분리한다

| 도구 | scope와 목적 | 적합한 값 | 피해야 할 값 |
|---|---|---|---|
| XCom | task instance/Dag run 내부 통신 | URI, partition, 작은 JSON metadata | dataframe, 대형 binary, retry checkpoint |
| Connection | 외부 시스템 endpoint와 인증 연결 | host, schema, conn ID, credential reference | task 결과, business parameter |
| Variable | 설치 또는 team 범위 runtime 구성 | 긴급 runtime switch, 배포별 작은 설정 | version 관리할 상수, run별 입력, 대형 JSON |
| Params | Dag run별 검증 가능한 입력 | 처리 mode, 제한된 날짜/옵션 | 장기 secret, task 간 결과 |

공식 [XCom 문서](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/xcoms.html)는 XCom이 작은 serializable 값용이고 dataframe 같은 큰 값에는 적합하지 않다고 명시한다. Airflow 3에서는 다른 task의 XCom을 가져올 때 `task_ids`를 명시해야 하며, 실패한 task retry 전에 XCom이 정리될 수 있으므로 durable checkpoint로 사용하면 안 된다.

TaskFlow return은 편리하지만 반환 object 전체가 XCom으로 직렬화될 수 있다. 외부 작업의 실제 결과 대신 다음 같은 manifest를 반환한다.

```python
{
    "uri": "object://<BUCKET>/<KEY>",
    "partition": "2026-01-01",
    "checksum": "sha256:<DIGEST>",
    "row_count": 1234,
}
```

Connection은 `conn_id`라는 논리 이름으로 외부 연결을 참조하고 Hook/provider가 실제 credential 처리를 담당한다. Dag source에 URI 원문과 password를 쓰지 않는다. 개념과 public API는 [Connections & Hooks 문서](https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/connections.html)를 기준으로 한다.

Variable은 global runtime key/value store다. 공식 [Variables 문서](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/variables.html)는 가능한 설정을 Dag source에 두어 version 관리하고, Variable은 정말 runtime-dependent한 값에 제한할 것을 권장한다. Dag parse top-level에서 `Variable.get()`을 반복하면 metadata/secret backend 조회가 parsing 성능과 가용성에 결합될 수 있으므로 task runtime 또는 template에서 읽는다.

## secret은 Dag가 아니라 실행 identity와 secrets backend에서 관리한다

Airflow Connection이나 Variable 이름을 사용한다고 값이 자동으로 안전한 것은 아니다. metadata database, environment variable, log, serialized Dag, task environment로 노출되는 경로를 검토한다.

권장 원칙:

- Dag에는 `conn_id`와 secret logical name만 기록
- 외부 secrets backend 또는 workload identity 사용
- scheduler, Dag processor, API server, worker가 필요한 secret 범위를 분리
- worker task별 cloud role과 namespace 권한 최소화
- 장기 access key보다 짧은 수명 credential 사용
- secret 원문, Connection URI, environment 전체를 log에 출력하지 않기

Airflow 3은 worker용 secrets backend를 별도로 구성할 수 있다. lookup 순서와 key collision이 있으므로 migration 때 같은 이름이 여러 backend에 존재하지 않게 확인한다. 자세한 동작은 공식 [Secrets Backend 문서](https://airflow.apache.org/docs/apache-airflow/stable/security/secrets/secrets-backend/index.html)를 따른다.

Fernet encryption이나 UI masking은 secret lifecycle 전체를 보호하지 않는다. task code가 값을 읽는 순간 worker process에는 평문이 존재한다. worker isolation, log redaction, egress 제한, rotation, audit가 함께 필요하다.

## 기다림은 worker slot에서 분리한다

### poke, reschedule, deferrable의 차이

| 방식 | 기다리는 동안 worker slot | 적합한 상황 | 주요 trade-off |
|---|---:|---|---|
| sensor `poke` | 계속 점유 | 매우 짧고 자주 확인해야 하는 대기 | 긴 대기에서 worker 낭비 |
| sensor `reschedule` | check 사이 반환 | 분 단위 polling을 허용하는 대기 | scheduler 재스케줄 overhead |
| deferrable operator | triggerer로 넘기고 반환 | 장시간 external event 대기 | triggerer 운영과 provider 지원 필요 |

공식 [Sensors 문서](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/sensors.html)는 `poke`와 `reschedule`의 slot 사용 차이를 설명한다. [Deferrable Operators & Triggers 문서](https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/deferring.html)에 따르면 deferral 중 polling은 triggerer의 async trigger가 담당하고 task는 worker slot을 해제한다.

provider sensor가 `deferrable=True`를 지원하는지 해당 provider version 문서에서 확인한다. 모든 sensor에 argument를 임의로 추가할 수 있는 것은 아니다. custom trigger에는 blocking I/O나 CPU 연산을 넣지 않는다. 하나의 trigger가 event loop를 막으면 많은 deferred task가 함께 지연될 수 있다.

대기 task에는 다음을 반드시 둔다.

- 전체 `timeout`
- polling interval 또는 trigger semantics
- timeout 시 soft fail인지 hard fail인지
- stale event와 새 event를 구분할 기준
- 외부 조건이 이미 충족된 경우의 즉시 성공
- triggerer health와 deferred task age 관측

polling할 수밖에 없다면 “파일이 존재하는가”뿐 아니라 expected partition, checksum/완료 marker, event timestamp를 확인한다. 이전 run의 오래된 파일을 새 성공으로 오인하지 않아야 한다.

## catchup과 backfill은 과거 구간을 다루는 서로 다른 제어다

### catchup

시간 기반 schedule에서 `catchup=True`이면 scheduler는 `start_date` 이후 아직 생성되지 않은 data interval의 Dag run을 만들 수 있다. 새 Dag를 오래된 `start_date`로 배포하면 많은 run이 한꺼번에 생길 수 있다.

`catchup=False`는 일상 scheduler가 과거 누락 interval을 자동 생성하지 않게 하는 선택이지, task가 `now()`를 써도 된다는 뜻이나 과거 재처리가 불가능하다는 뜻이 아니다.

### backfill

backfill은 명시한 과거 날짜 범위에 Dag run을 만드는 운영 작업이다. Airflow 3의 공식 [Backfill 문서](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/backfill.html)는 reprocessing behavior, 독립적인 `max_active_runs`, 실행 순서와 dry-run을 제공한다.

먼저 생성될 interval을 dry-run으로 확인한다.

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

실제 생성 전 확인할 항목:

- source retention이 과거 interval을 아직 보존하는가?
- 현재 code가 과거 schema와 호환되는가?
- output overwrite가 downstream과 동시 충돌하지 않는가?
- API quota, database load, pool capacity는 충분한가?
- reprocess behavior가 기존 성공 run을 덮어쓸 의도와 맞는가?
- 최신 interval 먼저 처리할지 과거부터 처리할지 dependency가 허용하는가?

backfill concurrency는 production traffic과 같은 pool을 무제한 경쟁하지 않게 별도 pool 또는 quota로 제한한다. 성공 판단은 task state뿐 아니라 partition count, checksum, data quality, downstream freshness로 한다.

## asset와 event-driven scheduling을 사용할 때

시간 schedule은 “매일 이 시각 이후 전날 구간을 처리한다”는 계약에 강하다. upstream 완료 시점이 크게 변하거나 여러 producer 사이 data dependency를 표현해야 한다면 asset-aware schedule이 더 직접적일 수 있다.

producer가 output asset을 선언하고 성공하면 consumer Dag를 schedule할 수 있다.

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

공식 [Asset-Aware Scheduling 문서](https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/asset-scheduling.html)에 따르면 producer task가 성공했을 때 asset update가 기록되고 consumer Dag가 schedule된다. 여러 asset의 AND/OR 조건과 시간 schedule 결합도 가능하지만, 복잡한 논리에는 event 순서, 중복, coalescing, replay 의미를 먼저 정의한다.

Airflow 3에서 추가된 [event-driven scheduling](https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/event-scheduling.html)은 외부 event를 asset update와 연결할 수 있다. 모든 `BaseTrigger`가 event schedule에 적합한 것은 아니며 호환 trigger가 필요하다. message queue가 at-least-once 전달이라면 같은 event가 여러 번 와도 결과가 중복되지 않도록 event ID와 idempotency를 설계한다.

asset은 data catalog 전체를 자동으로 만들어 주지 않는다. URI naming, owner, schema, freshness, partition, quality contract를 별도로 관리해야 한다. 민감한 credential이나 개인 식별 정보를 asset URI와 `extra`에 넣지 않는다. 공식 문서는 asset URI/extra가 암호화되지 않을 수 있음을 전제로 공개 가능한 식별자를 사용하도록 안내한다.

## Dag parsing과 business logic을 분리한다

scheduler와 Dag processor는 Dag 파일을 반복해서 import한다. top-level Python code에서 다음을 실행하면 parsing이 느리고 불안정해진다.

- 외부 API와 database 호출
- 대형 dataframe 로딩
- Variable/Connection 반복 조회
- 무거운 machine learning library import
- 현재 시각에 따라 task 구조를 비결정적으로 변경

Dag 파일은 graph 선언과 얇은 adapter에 집중하고, domain logic은 일반 Python package로 분리해 Airflow 없이 unit test한다.

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

provider와 Airflow dependency 충돌이 크거나 계산이 무거우면 task가 별도 container/job을 제출하게 한다. Airflow worker에 모든 workload dependency를 설치하면 image가 커지고 Dag 간 dependency 충돌과 upgrade 위험이 커진다.

## 관측성: Airflow control plane과 data product를 함께 본다

### control plane 신호

- scheduler와 Dag processor heartbeat
- Dag import error와 parse duration
- queued/scheduled task age
- executor와 pool의 open/queued/running slot
- deferred task 수와 triggerer health
- metadata database latency, connection, storage 증가
- remote task log 전달 실패

공식 [Airflow metrics 문서](https://airflow.apache.org/docs/apache-airflow/stable/administration-and-deployment/logging-monitoring/metrics.html)는 `scheduler_heartbeat`, `dag_processor_heartbeat`, `dag_processing.import_errors`, pool·executor·task 상태 metric 등을 제공한다. 설치한 executor와 telemetry backend에 맞는 이름과 tag를 실제 version에서 확인한다.

### workflow 신호

- Dag run success/failure와 duration
- task retry·timeout·zombie/heartbeat failure
- schedule delay: logical interval 종료부터 run 시작까지
- queue delay: task schedulable부터 실제 시작까지
- end-to-end completion: interval 종료부터 output publish까지

### data product 신호

- freshness와 마지막 성공 partition
- expected/actual row count와 volume anomaly
- schema/contract 위반
- null, duplicate, referential integrity
- source-to-output reconciliation과 checksum

Airflow Dag가 성공해도 빈 파일을 정상 publish했다면 data product는 실패다. 반대로 task 하나가 retry한 뒤 정확한 output을 제시간에 만들었다면 사용자 SLO는 지켜질 수 있다. on-call page는 task 실패 수보다 중요 산출물의 freshness와 correctness 영향에 연결한다.

log에는 Dag/task/run/try/data interval/output revision을 구조화해 남긴다. secret, Connection URI, 원본 record 전체는 남기지 않는다. disposable worker를 사용하면 remote logging을 구성하고 log backend 장애도 관측한다. production 구성의 기본 주의사항은 공식 [Production Deployment 문서](https://airflow.apache.org/docs/apache-airflow/stable/administration-and-deployment/production-deployment.html)를 참고한다.

## local test와 CI 검증 체크리스트

### 빠른 검증 계층

1. 일반 Python domain logic unit test
2. 모든 Dag import와 parse error 검사
3. Dag ID, task ID, dependency, schedule, retry 정책 구조 test
4. `dag.test()`로 대표 interval local 실행
5. staging에서 실제 Connection, secret backend, executor, storage integration
6. production 배포 후 synthetic Dag와 freshness 관찰

공식 [Best Practices의 Testing a Dag](https://airflow.apache.org/docs/apache-airflow/stable/best-practices.html#testing-a-dag)는 Dag loader test, unit test, self-check, staging 검증을 구분한다.

CI의 DagBag test 예시:

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

`airflow.dag_processing.dagbag`는 official test 예시에 등장하지만 internal package path이므로 Airflow minor version을 올릴 때 test import도 확인한다. production Dag code에서는 Airflow 3 public interface를 우선한다.

CI 명령 예시:

```bash
python -m compileall -q dags src tests
python -m pytest -q
airflow dags list
airflow dags list-import-errors
```

실제 CI image는 production과 같은 Airflow core, provider, Python dependency lock을 사용한다. Airflow는 application과 library 성격을 함께 가지므로 공식 constraints와 조직 lock 전략을 함께 적용하고, core와 provider compatibility를 staging에서 검증한다.

Dag review:

- [ ] schedule, timezone, `start_date`, catchup 의미가 명확하다.
- [ ] task가 `data_interval_start/end`로 partition을 결정한다.
- [ ] retry와 backfill에도 output이 중복되지 않는다.
- [ ] timeout, retry, pool, concurrency가 dependency 용량과 맞는다.
- [ ] XCom은 작은 metadata만 전달한다.
- [ ] Connection, Variable, Params가 역할에 맞게 분리돼 있다.
- [ ] secret 원문이 source, log, XCom, asset URI에 없다.
- [ ] 장기 대기는 reschedule/deferrable/event 방식으로 worker에서 분리한다.
- [ ] top-level parse에 network/DB/대형 import가 없다.
- [ ] leaf task와 trigger rule이 전체 Dag run 상태를 오해하게 만들지 않는다.

운영 review:

- [ ] backfill dry-run, concurrency, reprocessing behavior를 검토한다.
- [ ] source retention과 과거 schema compatibility를 확인한다.
- [ ] scheduler, Dag processor, triggerer, executor, metadata DB를 관측한다.
- [ ] 사용자 산출물 freshness와 correctness 경보가 있다.
- [ ] log retention과 metadata database 정리 정책이 있다.
- [ ] upgrade 전 metadata backup, migration, provider 호환성, staging을 시험한다.
- [ ] task clear/retry/backfill 권한과 감사 log가 제한돼 있다.

## 실패 사례와 한계

### Airflow를 data processing engine으로 사용하기

worker memory에서 대규모 dataframe을 처리하고 XCom으로 넘기면 확장성과 격리가 무너진다. Airflow는 Spark, warehouse, container job 같은 외부 compute를 orchestration하고 작은 metadata를 추적하는 역할에 집중한다.

### `now()`를 partition key로 사용하기

retry, queue 지연, manual run, backfill 때 다른 partition을 읽거나 쓴다. 논리 입력은 data interval과 명시적 Params에서 만든다.

### task 성공을 output commit보다 먼저 기록하기

비동기 외부 job을 제출하고 완료 확인 없이 task가 성공하면 downstream이 미완성 데이터를 읽는다. deferrable operator나 별도 sensor로 terminal state와 output quality를 확인한 뒤 성공한다.

### XCom을 durable state store로 사용하기

XCom은 task 통신을 위한 작은 값이며 retry 시 정리될 수 있다. 장기 checkpoint와 대형 payload는 외부 저장소에 version을 붙여 보관하고 XCom에는 reference만 둔다.

### retry 횟수를 늘려 불안정성을 숨기기

일시 오류에는 도움이 되지만 deterministic failure 발견을 늦추고 dependency 부하를 키운다. error taxonomy와 retry budget을 두고, 소진 시 사람이 행동할 수 있는 context와 함께 실패시킨다.

### 모든 dependency를 sensor polling으로 표현하기

worker와 scheduler 부하, polling latency가 늘어난다. source가 event를 제공하면 asset/event schedule을 검토하고, polling이 필요하면 deferrable sensor와 timeout을 사용한다.

### asset event를 exactly-once delivery로 오해하기

producer 재실행, 외부 event 중복, consumer 실패 후 재처리가 가능하다. asset은 dependency 표현이지 business transaction이 아니다. output과 consumer 모두 idempotent해야 한다.

### Airflow가 streaming을 대체한다고 생각하기

Airflow는 batch-oriented orchestration에 적합하다. 낮은 latency의 지속적 event 처리, per-event state, backpressure가 핵심이면 stream processor와 message system이 data plane을 담당하고 Airflow는 배치 보정·관리 workflow를 맡는 편이 자연스럽다.

Airflow 운영의 핵심은 화려한 Dag graph가 아니다. 처리 구간을 정확히 정의하고, task를 재실행 가능하게 만들며, 작은 orchestration metadata와 실제 data plane을 분리하고, 과거 재처리와 장애 대응을 처음부터 설계하는 것이다.
