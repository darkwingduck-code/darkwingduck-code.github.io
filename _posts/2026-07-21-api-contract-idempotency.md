---
title: "계약 우선 API 설계: 오류, 버전, 멱등성과 비동기 작업"
date: 2026-07-21 10:30:00 +0900
categories: [Software Engineering, API Design]
tags: [api, openapi, idempotency, schema, pagination, versioning]
description: API를 함수 모음이 아닌 장기적으로 진화하는 계약으로 보고 요청·응답·오류·재시도·버전을 설계하는 방법을 다룹니다.
lang: ko-KR
translation_key: api-contract-idempotency
---

{% include language-switcher.html %}

API의 품질은 endpoint 개수보다 **호출자가 성공, 실패, 재시도를 예측할 수 있는가**로 판단해야 한다. 서버 구현은 바뀌어도 계약은 여러 클라이언트와 자동화에 오래 남는다.

## 계약은 성공 응답보다 넓다

한 operation의 계약에는 최소한 다음이 포함된다.

- method와 path
- 인증·권한 요구사항
- path/query/header/body 스키마
- 단위, 시간대, 범위, nullable 규칙
- 성공 상태 코드와 응답 스키마
- 오류 코드와 재시도 가능성
- idempotency와 동시성 규칙
- rate limit과 pagination
- timeout 또는 비동기 처리 방식

OpenAPI 같은 기계 판독 가능한 명세는 문서 생성만을 위한 파일이 아니다. schema 검증, client 생성, contract test, breaking-change 검사를 연결하는 기준점이다.

## 리소스와 작업을 구분한다

명사형 리소스는 상태를 표현하고 HTTP method는 의도를 표현한다.

```text
GET    /v1/jobs/{job_id}
POST   /v1/jobs
PATCH  /v1/jobs/{job_id}
DELETE /v1/jobs/{job_id}
```

몇 분 걸리는 작업을 동기 HTTP 연결로 끝까지 기다리게 하지 않는다.

1. `POST /v1/jobs`가 입력을 검증하고 작업을 등록한다.
2. 서버는 `202 Accepted`와 `job_id`, 상태 URL을 반환한다.
3. 클라이언트는 상태를 polling하거나 webhook/event를 받는다.
4. 상태는 `queued → running → succeeded | failed | cancelled`처럼 명시한다.

상태 전이는 단방향이어야 하며, 실패 사유와 다시 시도 가능한지 구분한다.

## 입력은 경계에서 엄격히 검증한다

```yaml
components:
  schemas:
    CreateJobRequest:
      type: object
      additionalProperties: false
      required: [source_uri, mode]
      properties:
        source_uri:
          type: string
          format: uri
        mode:
          type: string
          enum: [quick, full]
```

중요한 것은 YAML 문법이 아니라 정책이다.

- 알 수 없는 필드를 거부할지 무시할지 결정한다.
- 누락과 명시적 `null`을 구분한다.
- 숫자의 단위와 허용 범위를 이름·설명·검증에 반영한다.
- 시간은 offset이 포함된 표준 형식으로 교환하고 내부 기준을 정한다.
- enum에 새 값을 추가할 때 오래된 client가 어떻게 반응할지 고려한다.

## 오류도 안정적인 스키마다

사람용 문장만 반환하면 client가 문자열을 파싱하게 된다.

```json
{
  "error": {
    "code": "INVALID_INPUT",
    "message": "The request failed validation.",
    "details": [
      {"field": "mode", "reason": "unsupported_value"}
    ],
    "request_id": "req-example",
    "retryable": false
  }
}
```

- `code`는 기계가 분기하는 안정적 식별자다.
- `message`는 사용자 또는 운영자가 읽는다.
- `details`는 필드별 문제를 구조화한다.
- `request_id`는 지원과 trace 연결에 사용한다.
- 내부 stack trace, SQL, 경로, 비밀값은 외부에 반환하지 않는다.

## POST 재시도에는 idempotency key가 필요하다

클라이언트가 요청을 전송한 뒤 응답을 받기 전에 연결이 끊기면, 작업이 생성됐는지 알 수 없다. 무조건 다시 POST하면 중복 생성될 수 있다.

```text
Idempotency-Key: client-generated-unique-key
```

서버 기본 흐름은 다음과 같다.

1. 인증 주체와 key 조합으로 기존 기록을 찾는다.
2. 처음이면 요청 body의 정규화된 hash와 함께 처리 결과를 저장한다.
3. 같은 key와 같은 body면 저장된 결과를 반환한다.
4. 같은 key에 다른 body면 충돌로 거부한다.
5. 보관 기간과 동시 요청 처리 규칙을 문서화한다.

데이터베이스 unique constraint 없이 애플리케이션의 “먼저 조회”만 사용하면 경쟁 상태가 생긴다.

## 동시 수정에는 조건부 요청이 필요하다

두 사용자가 같은 리소스를 읽고 수정하면 나중 write가 앞선 변경을 덮을 수 있다. version number 또는 `ETag`를 사용한 optimistic concurrency가 일반적인 해법이다.

```text
GET /v1/items/42
ETag: "version-7"

PATCH /v1/items/42
If-Match: "version-7"
```

버전이 달라졌으면 서버는 충돌을 알려 클라이언트가 최신 상태를 다시 읽게 한다.

## pagination은 데이터 변경을 견뎌야 한다

큰 목록을 한 번에 반환하지 않는다. offset pagination은 단순하지만 앞쪽 데이터가 삽입·삭제될 때 중복이나 누락이 생길 수 있다. 변경이 잦은 대규모 목록에는 안정적인 정렬 키를 이용한 cursor pagination이 적합하다.

```json
{
  "items": [],
  "next_cursor": "opaque-cursor",
  "has_more": false
}
```

cursor는 opaque하게 취급하고 정렬 순서, page size 상한, 필터와 cursor 조합 규칙을 계약에 넣는다.

## 버전은 마지막 수단이 아니라 변화 정책이다

변경을 세 종류로 분류한다.

- 호환: optional 필드 추가, 새 endpoint 추가
- 조건부 호환: enum 값 추가, 제한 완화
- 비호환: 필드 삭제·타입 변경·의미 변경

비호환 변경은 명시적인 새 버전 또는 병행 operation으로 이동한다. deprecation 공지, 관측 기간, client 사용량, 종료 일정을 함께 관리한다. URL에 버전 숫자를 붙이는 것만으로는 변화 관리가 끝나지 않는다.

## 계약 테스트와 배포 게이트

- 명세가 유효한지 검사한다.
- 서버 응답이 명세와 일치하는지 테스트한다.
- 대표 client가 새 명세로 생성·컴파일되는지 확인한다.
- 이전 버전 대비 breaking change를 검사한다.
- 인증 누락, 권한 부족, rate limit, validation 오류를 테스트한다.
- 동일 idempotency key의 동시 요청을 테스트한다.
- 배포 후 핵심 endpoint를 smoke test한다.

## 검증 체크리스트

- [ ] 요청과 응답뿐 아니라 오류 스키마도 명시되어 있다.
- [ ] 단위, 시간대, nullable, enum 확장 정책이 명확하다.
- [ ] 부작용 POST의 중복 방지 전략이 있다.
- [ ] 오래 걸리는 작업은 상태 리소스로 분리된다.
- [ ] 동시 수정의 lost update를 방지한다.
- [ ] pagination 정렬이 결정적이고 cursor가 opaque하다.
- [ ] 비호환 변경 탐지가 CI에 포함되어 있다.
- [ ] stack trace와 내부 구현 정보가 외부 오류에 노출되지 않는다.

## 흔한 실패

- 모든 결과를 `200 OK`와 자유 형식 JSON으로 반환한다.
- 재시도 가능한 오류와 영구 오류를 구분하지 않는다.
- 서버가 client timeout 이후에도 작업을 생성했는데 중복 방지가 없다.
- 같은 필드가 endpoint마다 다른 단위나 시간대를 가진다.
- 응답 필드를 삭제하고 “문서만 수정”한다.
- offset pagination 중간에 데이터가 바뀌어 누락을 만든다.

좋은 API는 구현 세부를 숨기는 동시에, **호출자가 안전하게 실패하고 다시 시도할 수 있을 만큼 동작을 명시한다.**

## 참고 자료

- [OpenAPI Specification](https://spec.openapis.org/oas/latest.html)
- [RFC 9110 — HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html)
