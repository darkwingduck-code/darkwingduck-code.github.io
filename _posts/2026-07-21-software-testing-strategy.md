---
title: "테스트 피라미드보다 중요한 위험 기반 소프트웨어 검증 전략"
date: 2026-07-21 10:40:00 +0900
categories: [Software Engineering, Testing]
tags: [testing, pytest, contract-testing, property-testing, integration-testing, quality]
description: 단위·통합·계약·E2E 테스트를 위험에 맞게 조합하고 좋은 oracle과 불변조건을 설계하는 방법을 정리합니다.
lang: ko-KR
translation_key: software-testing-strategy
---

{% include language-switcher.html %}

테스트의 목적은 코드 줄을 실행하는 것이 아니라 **중요한 실패를 릴리스 전에 발견하고, 변경 후에도 계약이 유지된다는 증거를 만드는 것**이다. coverage가 높아도 assertion이 약하거나 실제 위험을 건드리지 않으면 신뢰도는 낮다.

## 위험에서 테스트를 역설계한다

먼저 실패 모드를 쓴다.

| 실패 모드 | 영향 | 적합한 검증 |
|---|---|---|
| 경계값 분류 오류 | 잘못된 의사결정 | 단위·경계값 테스트 |
| DB schema 불일치 | 요청 전체 실패 | 통합·migration 테스트 |
| client/server 계약 파손 | 배포 후 연동 실패 | 계약 테스트 |
| 인증 우회 | 권한 없는 접근 | 보안·통합 테스트 |
| 배포 설정 누락 | 서비스 기동 실패 | smoke test |
| 긴 사용자 흐름 파손 | 핵심 업무 중단 | 소수의 E2E 테스트 |

발생 가능성, 영향, 탐지 난이도가 높은 항목을 먼저 자동화한다. 사소한 getter보다 금액·권한·상태 전이·데이터 손실 경로가 우선이다.

## 테스트 층은 서로 다른 질문에 답한다

### 단위 테스트

“작은 규칙이 모든 중요한 입력에서 맞는가?”를 빠르게 확인한다. I/O를 격리하고 경계값, 예외, 불변조건에 집중한다.

### 통합 테스트

“실제 구성요소들이 같은 계약으로 통신하는가?”를 확인한다. 실제 데이터베이스 엔진, 파일 형식, serializer, HTTP adapter처럼 mock이 숨길 수 있는 차이를 검증한다.

### 계약 테스트

“provider와 consumer가 합의한 schema와 의미가 유지되는가?”를 확인한다. 필드 타입, required/optional, 오류 코드, backward compatibility를 검사한다.

### E2E 테스트

“배포된 시스템에서 사용자의 핵심 결과가 달성되는가?”를 확인한다. 느리고 취약하므로 매 화면을 자동화하기보다 가치가 큰 3~5개 경로부터 시작한다.

### 배포 후 검증

health endpoint만 200인지 보는 데 그치지 않는다. 핵심 의존성 연결, 최소 read/write, 권한, 버전, background worker 상태를 안전한 synthetic transaction으로 점검한다.

## 좋은 테스트는 Arrange–Act–Assert가 선명하다

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

한 테스트에서 너무 많은 행동을 하면 어디서 실패했는지 불분명하다. 반대로 구현의 private method까지 고정하면 정상적인 리팩터링도 깨진다. 외부 관찰 가능한 결과와 핵심 불변조건을 검증한다.

## 예시 기반 테스트와 속성 기반 테스트를 함께 쓴다

예시 테스트는 읽기 쉽지만 개발자가 생각한 사례만 다룬다. 속성 기반 테스트는 넓은 입력 공간에서 항상 지켜야 할 성질을 검사한다.

예를 들어 정규화 함수라면 다음 속성을 생각할 수 있다.

- 출력은 허용 범위 안에 있다.
- 같은 입력을 두 번 정규화해도 결과가 같다.
- 입력 순서를 바꿔도 순서 비의존 집계 결과는 같다.
- serialize 후 deserialize하면 의미가 보존된다.

수치 계산에서는 오차 허용치의 근거가 필요하다. 무조건 큰 `epsilon`을 쓰면 오류를 숨기고, bitwise equality만 요구하면 플랫폼 차이 때문에 불안정해진다. 절대오차와 상대오차를 값의 규모와 문제 조건에 맞춰 결합한다.

## test double을 정확히 선택한다

- stub: 정해진 값을 반환한다.
- fake: 간단하지만 동작 가능한 대체 구현이다.
- spy: 호출 기록을 관찰한다.
- mock: 기대한 상호작용을 명시한다.

도메인 규칙 테스트에 네트워크 mock은 유용하다. 그러나 SQL dialect, transaction, serialization 같은 실제 경계까지 mock하면 통합 오류를 놓친다. “무엇을 빠르게 격리할 것인가”와 “무엇을 실제로 확인해야 하는가”를 분리한다.

## 비결정성을 통제한다

불안정한 테스트는 신뢰를 무너뜨린다. 시간, 난수, 네트워크, 병렬성, 전역 상태를 제어 가능한 의존성으로 만든다.

```python
from datetime import datetime, timezone
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime: ...


class FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 1, 1, tzinfo=timezone.utc)
```

난수 seed만 기록한다고 완전한 결정성이 보장되지는 않는다. 라이브러리 버전, 병렬 실행, 하드웨어별 연산, 입력 순서도 결과에 영향을 줄 수 있다. 요구하는 재현성 수준을 먼저 정한다.

## 데이터베이스 테스트의 핵심

- 각 테스트는 독립된 데이터와 namespace를 사용한다.
- migration을 빈 DB와 이전 버전 DB 모두에 적용한다.
- unique·foreign key·check constraint가 실제로 실패를 막는지 본다.
- transaction rollback만 믿지 말고 background worker와 별도 connection을 고려한다.
- 운영 데이터를 테스트 fixture로 복사하지 않는다.

## 실패를 조사 가능한 상태로 만든다

CI 실패 시 최소한 다음을 보존한다.

- test name과 seed
- 입력 fixture 또는 최소 재현 입력
- application/logical version
- 환경과 의존성 잠금 정보
- 관련 로그·trace·screenshot
- 첫 실패 원인과 후속 실패 구분

무조건 rerun해서 녹색이 되면 통과시키는 정책은 flaky test를 숨긴다. 격리, 원인 분류, 담당자와 수정 기한이 필요하다.

## 검증 체크리스트

- [ ] 가장 비싼 실패 모드가 어떤 테스트로 탐지되는지 연결되어 있다.
- [ ] 경계값의 바로 아래·값·바로 위를 검사한다.
- [ ] 예외뿐 아니라 실패 후 상태가 보존되는지 확인한다.
- [ ] 실제 DB·serializer·HTTP 경계의 통합 테스트가 있다.
- [ ] schema breaking change를 CI에서 탐지한다.
- [ ] 핵심 사용자 흐름만 안정적인 E2E로 유지한다.
- [ ] 시간·난수·외부 의존성의 비결정성이 통제된다.
- [ ] flaky test를 자동 rerun으로만 덮지 않는다.
- [ ] 배포 후 smoke test와 rollback 판단 기준이 있다.

## 흔한 실패

- coverage 숫자를 품질 목표로 착각한다.
- 같은 정상 사례만 반복하고 경계·오류·동시성을 놓친다.
- 내부 구현 호출 횟수까지 고정해 리팩터링 비용을 키운다.
- 테스트끼리 순서와 전역 상태를 공유한다.
- 모든 외부 경계를 mock해 실제 schema와 transaction 오류를 놓친다.
- E2E에서 임의 sleep과 화면 좌표에 의존한다.

테스트 전략의 최종 질문은 “몇 개를 썼는가?”가 아니라 **“어떤 위험을 어떤 증거로 통제했는가?”**다.
