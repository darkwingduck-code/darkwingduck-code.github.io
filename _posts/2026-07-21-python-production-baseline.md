---
title: "Python 코드를 운영 가능한 소프트웨어로 만드는 최소 기준"
date: 2026-07-21 10:10:00 +0900
categories: [Software Engineering, Python]
tags: [python, packaging, testing, typing, logging, reproducibility]
description: 스크립트를 재현 가능하고 테스트 가능하며 관측 가능한 Python 애플리케이션으로 발전시키는 실전 기준을 정리합니다.
---

Python 파일이 한 번 실행되는 것과, 다른 환경에서도 안전하게 반복 실행되는 소프트웨어가 되는 것은 전혀 다른 문제다. 운영 가능한 코드의 핵심은 화려한 프레임워크가 아니라 **입력·출력·의존성·실패가 명시되어 있는가**에 있다.

## 1. 먼저 경계를 만든다

가장 유지하기 어려운 코드는 계산, 파일 접근, 네트워크 요청, 환경 변수 읽기, 로그 출력이 한 함수에 섞인 코드다. 다음 세 층으로 나누면 테스트와 교체가 쉬워진다.

1. **도메인 로직**: 같은 입력에 같은 출력을 내는 순수 계산
2. **어댑터**: 파일, 데이터베이스, HTTP, 메시지 큐와 통신
3. **진입점**: 설정을 읽고 객체를 조립하며 종료 코드를 결정

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

이 함수는 파일도, 시계도, 네트워크도 보지 않는다. 따라서 경계값을 빠르게 검증할 수 있고 실패 원인도 좁다.

## 2. 프로젝트 구조는 작게 시작하되 역할을 분리한다

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

`src` 레이아웃은 저장소 루트가 우연히 import 경로가 되어 패키징 오류를 숨기는 일을 줄인다. `pyproject.toml`에는 빌드 시스템, 프로젝트 메타데이터, 런타임 의존성과 개발 도구 설정을 모은다.

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

버전 범위는 예시일 뿐이다. 실제 프로젝트에서는 지원 Python 버전과 잠금 파일 전략을 한 가지로 정하고 CI와 배포에서 동일하게 써야 한다.

## 3. 설정과 비밀을 분리한다

설정에는 세 종류가 있다.

| 종류 | 예시 | 저장 위치 |
|---|---|---|
| 코드 기본값 | 배치 크기, 타임아웃 기본값 | 코드 또는 공개 설정 파일 |
| 환경별 설정 | API 주소, 로그 수준 | 환경 변수 또는 배포 설정 |
| 비밀 | 토큰, 비밀번호, 개인키 | 비밀 관리자 |

`DEBUG=true` 같은 값도 문자열이다. 암묵적 형변환 대신 시작 시 한 번 검증한다.

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

비밀값을 예외 메시지, CLI 인자, Git, 테스트 fixture, 노트북 출력에 남기지 않는다. `***`로 가리는 것만으로는 부족하며, 애초에 로그 필드에 넣지 않는 편이 안전하다.

## 4. 타입은 실행을 대신하지 않고 계약을 설명한다

타입 힌트는 입력과 출력의 의도를 빠르게 전달하고 리팩터링 오류를 줄인다. 그러나 외부에서 들어온 JSON, CSV, 환경 변수는 타입 힌트만으로 검증되지 않는다. **신뢰 경계에서 런타임 검증**, 내부에서는 타입 검사라는 두 층이 필요하다.

- `Any`는 점진적 이전 구간에만 제한한다.
- `dict[str, object]`보다 의미 있는 `dataclass`, `TypedDict`, 모델 타입을 쓴다.
- `None`이 정상 상태인지 오류 상태인지 명확히 한다.
- 단위가 다른 숫자는 이름이나 별도 타입으로 구분한다.

## 5. 로그는 문장이 아니라 사건의 구조다

운영 로그는 나중에 필터링하고 집계할 수 있어야 한다.

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

최소 공통 필드는 `event`, `timestamp`, `severity`, `service`, `request_id` 또는 `job_id`, `duration`, `outcome`이다. 원시 요청 본문이나 인증 헤더를 통째로 남기지 않는다.

## 6. 테스트는 위험의 층을 따라 배치한다

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

- 단위 테스트: 순수 로직, 경계값, 불변조건
- 통합 테스트: 데이터베이스·파일·HTTP 어댑터
- 계약 테스트: 요청/응답 스키마와 오류 형식
- 스모크 테스트: 배포 후 핵심 경로가 살아 있는지

모든 구현 세부를 mock하면 실제 연결 오류를 놓친다. 반대로 모든 테스트를 E2E로 만들면 느리고 원인 파악이 어렵다. 실패 비용과 변경 빈도에 맞춰 층을 나눈다.

## 7. 종료와 재시도도 API다

CLI나 배치 작업은 성공과 실패를 종료 코드로 구분해야 한다. 네트워크 재시도에는 최대 횟수, 지수 backoff, jitter, 전체 deadline이 필요하다. 부작용이 있는 작업은 idempotency 보장 없이 자동 재시도하지 않는다.

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

## 운영 전 체크리스트

- [ ] 새 환경에서 문서의 명령만으로 설치·실행할 수 있다.
- [ ] Python 버전과 의존성이 선언되고 잠금 전략이 있다.
- [ ] 입력 스키마, 단위, 범위, 누락값 정책이 검증된다.
- [ ] 비밀값이 코드·Git 이력·로그·테스트 데이터에 없다.
- [ ] 핵심 도메인 로직은 외부 I/O 없이 테스트된다.
- [ ] 타임아웃, retry budget, 종료 코드가 명시되어 있다.
- [ ] 구조화 로그로 한 요청 또는 작업을 추적할 수 있다.
- [ ] 릴리스 산출물을 깨끗한 환경에서 다시 만들 수 있다.

## 흔한 실패

- 노트북에서만 성공하고 패키지 import와 CLI가 깨진다.
- 전역 상태와 import 시 부작용 때문에 테스트 순서에 따라 결과가 바뀐다.
- `except Exception: pass`로 실패를 성공처럼 만든다.
- 최신 버전을 무조건 설치해 어제의 환경을 재현하지 못한다.
- 로그를 많이 남겼지만 식별자와 사건명이 없어 검색할 수 없다.

운영 가능성은 코드 줄 수가 아니라 **다시 설치하고, 실패를 재현하고, 안전하게 복구할 수 있는 정도**로 판단해야 한다.

## 참고 자료

- [Python Packaging User Guide — Writing `pyproject.toml`](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/)
- [Python Packaging User Guide — Packaging Python Projects](https://packaging.python.org/tutorials/packaging-projects/)
