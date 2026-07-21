---
title: "GitHub Actions CI/CD 설계: 빠른 자동화보다 신뢰 경계부터"
date: 2026-07-21 09:20:00 +0900
categories: [Platform Engineering, CI-CD]
tags: [github-actions, ci-cd, supply-chain, automation, security]
description: GitHub Actions의 workflow·job·runner 신뢰 경계를 이해하고 permissions, secrets, environments, matrix, cache, concurrency를 안전하게 설계합니다.
---

## 문제: 통과하는 workflow와 신뢰할 수 있는 pipeline은 다르다

CI/CD는 반복 작업을 줄이지만, 잘못 설계하면 저장소의 가장 강한 권한을 외부 입력에 연결한다. workflow는 소스 코드를 체크아웃하고, dependency를 내려받으며, 테스트를 실행하고, 때로는 운영 환경까지 변경한다. 즉 작은 YAML 파일이 빌드 시스템이자 credential broker이고 배포 제어면이다.

“테스트가 자동으로 돈다”에서 멈추면 다음 문제가 남는다.

- 모든 job이 쓰기 가능한 기본 토큰을 공유한다.
- fork PR의 신뢰하지 못한 코드가 secret에 접근한다.
- 같은 branch의 오래된 배포가 최신 배포를 덮어쓴다.
- cache와 artifact가 출처 확인 없이 실행 단계로 전달된다.
- 여러 matrix 조합 중 하나만 실제로 의미 있는 검증을 한다.
- build와 deploy가 결합돼 동일 artifact를 승격하지 못한다.

좋은 pipeline의 목표는 단순한 초록색 체크가 아니라 **동일 입력에 대한 재현 가능한 결과, 최소 권한, 검증된 artifact의 일관된 승격, 실패 시 명확한 중단점**이다.

## Mental model: workflow는 권한과 데이터를 전달하는 DAG다

GitHub Actions의 주요 단위를 구분한다.

- **event**: `pull_request`, `push`, `workflow_dispatch`처럼 실행을 시작하는 외부 입력
- **workflow**: event와 job 그래프를 정의한 파일
- **job**: 한 runner에서 실행되는 step 집합. job 사이 파일시스템은 기본적으로 공유되지 않는다.
- **step**: action 또는 shell command 한 번
- **runner**: 코드를 실행하는 일회성 또는 self-hosted compute
- **artifact**: job과 workflow 사이에 명시적으로 전달·보존하는 결과물
- **cache**: 재생성 가능한 dependency를 빠르게 복원하는 최적화 수단
- **environment**: 배포 대상과 승인, 보호 규칙, 환경 secret을 묶는 제어 경계

각 경계에서 네 가지를 묻는다.

1. 입력을 누가 통제하는가?
2. 어떤 코드가 실행되는가?
3. 어떤 token과 secret이 노출되는가?
4. 결과물의 출처와 무결성을 어떻게 확인하는가?

### CI와 CD를 분리한다

CI는 커밋의 품질을 검증하고 immutable artifact를 만든다. CD는 이미 검증된 artifact를 특정 환경에 승격한다. 환경마다 다시 build하면 “테스트한 바이너리”와 “운영에 배포한 바이너리”가 달라질 수 있다.

```text
commit -> test -> build -> scan -> signed artifact
                                      |
                                      +-> staging deploy
                                      +-> production approval -> production deploy
```

배포의 식별자는 branch 이름보다 commit SHA, image digest, artifact digest처럼 바뀌지 않는 값이어야 한다.

## 실전 패턴: PR은 낮은 권한으로 검증하고 배포는 별도 경계에서 수행한다

### 최소 권한 CI workflow

다음 예시는 Python 프로젝트의 기본 골격이다. 저장소의 lock file과 테스트 명령에 맞게 조정한다.

{% raw %}
```yaml
name: ci

on:
  pull_request:
  push:
    branches: [main]

# workflow 전체의 기본값은 읽기 전용이다.
permissions:
  contents: read

concurrency:
  group: ci-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  test:
    name: python-${{ matrix.python }} / ${{ matrix.os }}
    runs-on: ${{ matrix.os }}
    timeout-minutes: 20
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, windows-latest]
        python: ["3.11", "3.12"]

    steps:
      - name: Check out source
        uses: actions/checkout@v4
        with:
          persist-credentials: false

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python }}
          cache: pip
          cache-dependency-path: requirements.lock

      - name: Install locked dependencies
        run: python -m pip install --require-hashes -r requirements.lock

      - name: Static checks
        run: python -m ruff check .

      - name: Unit tests
        run: python -m pytest -q --maxfail=1
```
{% endraw %}

읽기 쉬운 예시를 위해 공식 action의 major tag를 사용했다. 높은 assurance가 필요한 저장소에서는 검토한 **full commit SHA**로 action을 고정하고 dependency update 도구로 갱신한다. third-party action은 marketplace 별점보다 source, 유지보수 주체, release provenance, 요청 권한을 검토한다.

matrix는 “많을수록 좋다”가 아니다. 지원 계약에서 실제로 보장해야 하는 축만 둔다.

- 라이브러리: 지원하는 최소·최신 runtime 조합
- 애플리케이션: 운영과 같은 주력 환경 + 호환성 위험이 큰 환경
- GPU·대형 integration: 매 PR smoke test와 예약된 전체 test를 분리

`fail-fast: false`는 한 조합이 실패해도 나머지 호환성 정보를 얻는다. 반대로 비용이 큰 job은 빠른 lint/unit job을 선행하고 `needs`로 차단하는 편이 낫다.

### cache와 artifact를 구분한다

| 항목 | cache | artifact |
|---|---|---|
| 목적 | 재생성 가능한 입력의 속도 개선 | 빌드 결과·리포트의 전달과 보존 |
| miss 시 | 느려져도 정상 실행 가능해야 함 | 다음 단계가 필요로 하면 실패해야 함 |
| 키 | OS, runtime, lock file hash 등 | commit SHA, build ID, digest 등 |
| 신뢰 | 오염 가능성을 가정하고 검증 | provenance와 digest를 함께 관리 |

cache에서 복원한 dependency도 lock file과 package hash로 검증한다. cache에 실행 권한 있는 임의 스크립트나 장기 자격 증명을 넣지 않는다. PR에서 write 가능한 cache가 보호 branch의 고권한 job으로 흘러가지 않도록 event와 scope를 검토한다.

artifact는 한 번 build한 것을 환경 간 승격한다. 보존 기간을 업무 목적에 맞게 제한하고, 배포 전에 digest를 검증한다. test report와 coverage는 관찰 자료이지 배포 binary를 대체하지 않는다.

### 배포 job은 environment와 짧은 수명의 자격 증명을 사용한다

운영 배포는 PR workflow가 아니라 보호 branch/tag에서 실행되는 별도 workflow 또는 엄격히 분리된 job으로 둔다. 다음은 구조를 보여 주는 skeleton이다. `<...>` 값과 action SHA는 해당 cloud 및 저장소 설정으로 교체해야 한다.

{% raw %}
```yaml
name: deploy

on:
  workflow_dispatch:
    inputs:
      artifact_digest:
        description: "검증된 artifact digest"
        required: true
        type: string

permissions:
  contents: read
  id-token: write

concurrency:
  group: production
  cancel-in-progress: false

jobs:
  deploy:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    environment: production

    steps:
      - uses: actions/checkout@<REVIEWED_FULL_COMMIT_SHA>
        with:
          persist-credentials: false

      - name: Exchange OIDC token for short-lived cloud credentials
        uses: <CLOUD_PROVIDER_LOGIN_ACTION>@<REVIEWED_FULL_COMMIT_SHA>
        with:
          role: <DEPLOYMENT_ROLE_IDENTIFIER>

      - name: Verify and deploy the immutable artifact
        env:
          ARTIFACT_DIGEST: ${{ inputs.artifact_digest }}
        run: ./scripts/deploy.sh --digest "$ARTIFACT_DIGEST"
```
{% endraw %}

핵심은 다음과 같다.

- `id-token: write`는 OIDC 교환에 필요한 job에만 부여한다.
- cloud trust policy는 저장소, branch/tag, environment claim을 제한한다.
- 장기 access key를 repository secret으로 저장하는 대신 짧은 수명 credential을 발급한다.
- `production` environment에 승인자, 허용 branch/tag, 환경별 secret을 설정한다.
- 운영 배포는 `cancel-in-progress: false`로 두고, deploy 도구 자체도 중복 실행에 안전하게 만든다.

OIDC를 쓴다고 자동으로 안전해지지는 않는다. cloud 쪽 trust condition이 너무 넓으면 어떤 branch의 workflow도 운영 role을 얻을 수 있다.

### secret은 “값”보다 노출 경로를 관리한다

secret은 GitHub UI에 저장했다고 끝이 아니다.

- shell argument는 process listing이나 debug log에 드러날 수 있다.
- secret을 변형·인코딩하면 masking이 인식하지 못할 수 있다.
- 에러 객체, test fixture, artifact에 값이 복제될 수 있다.
- self-hosted runner의 디스크나 process가 다음 job에 흔적을 남길 수 있다.

필요한 step의 environment variable로만 전달하고, 값 전체를 출력하지 않는다.

{% raw %}
```yaml
- name: Call protected service
  env:
    SERVICE_TOKEN: ${{ secrets.SERVICE_TOKEN }}
  run: python scripts/publish.py
```
{% endraw %}

fork PR에는 보호 secret을 제공하지 않는 것이 기본이다. 특히 `pull_request_target`은 base branch 문맥에서 권한을 얻을 수 있으므로, 신뢰하지 못한 PR 코드를 checkout해 실행하는 패턴과 결합하면 안 된다. label·comment 같은 metadata 처리와 코드 실행을 서로 다른 workflow로 나눈다.

### 표현식 삽입과 shell 인용을 분리한다

PR 제목 같은 사용자 입력을 `run` 블록에 직접 보간하면 shell code가 될 수 있다. 값을 environment를 통해 전달하고 shell에서 인용한다.

위험한 형태:

{% raw %}
```yaml
- run: echo "${{ github.event.pull_request.title }}"
```
{% endraw %}

더 안전한 형태:

{% raw %}
```yaml
- name: Print PR title as data
  env:
    PR_TITLE: ${{ github.event.pull_request.title }}
  shell: bash
  run: printf '%s\n' "$PR_TITLE"
```
{% endraw %}

가능하면 사용자 입력을 출력하는 것조차 줄이고, 입력 형식 검증과 allowlist를 둔다.

### concurrency 정책은 CI와 CD가 다르다

PR CI에서는 새 commit이 오면 이전 실행 결과의 가치가 낮아지므로 취소가 효율적이다.

{% raw %}
```yaml
concurrency:
  group: ci-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```
{% endraw %}

배포에서는 실행 중인 변경을 갑자기 취소하면 환경이 중간 상태에 남을 수 있다. 동일 환경 deploy를 직렬화하고, 취소 대신 queueing을 기본으로 한다. 애플리케이션의 배포 도구는 idempotency, timeout, rollback 또는 roll-forward를 지원해야 한다.

## 검증 체크리스트

workflow 변경 PR에서 확인할 항목:

- [ ] trigger가 필요한 event와 branch에만 반응한다.
- [ ] 최상위 `permissions`가 읽기 전용이며 쓰기 권한은 필요한 job에만 있다.
- [ ] fork PR과 신뢰하지 못한 코드는 secret·배포 credential에 접근하지 않는다.
- [ ] action을 신뢰 가능한 source의 검토된 SHA로 고정하는 정책이 있다.
- [ ] dependency는 lock file과 hash로 검증된다.
- [ ] cache miss여도 빌드가 정확하게 성공한다.
- [ ] artifact는 commit/digest와 연결되고 환경마다 재build하지 않는다.
- [ ] environment 승인과 cloud trust policy가 branch/tag 범위를 제한한다.
- [ ] CI는 오래된 실행을 취소하고, CD는 동일 환경 변경을 직렬화한다.
- [ ] 모든 job에 합리적인 `timeout-minutes`가 있다.
- [ ] 실패 log와 artifact에 secret·개인정보가 포함되지 않는다.
- [ ] branch protection의 required check 이름이 workflow 변경 후에도 유효하다.

정적 검사는 workflow schema lint, dependency review, secret scan, action 정책 검사를 조합한다. 다만 lint 통과는 권한 설계가 안전하다는 증명이 아니므로 event별 위협 모델을 함께 검토한다.

## 실패 사례와 한계

### `permissions: write-all`로 문제를 해결하기

권한 오류는 사라지지만 침해 범위가 커진다. 필요한 API 동작을 확인해 특정 scope만 job 수준에서 추가한다.

### tag만 pin하면 공급망이 완전히 고정된다고 생각하기

major/version tag는 이동할 수 있다. full commit SHA가 더 강한 고정점이지만, 그 commit의 source와 release 과정 자체를 검토해야 한다. pinning은 update 자동화와 취약점 대응을 동반해야 한다.

### cache를 신뢰할 수 있는 build output으로 사용하기

cache는 최적화이며 삭제돼도 정확성이 유지돼야 한다. 배포 대상은 명시적 artifact와 provenance로 전달한다.

### self-hosted runner를 비용 절감 장치로만 보기

self-hosted runner는 네트워크 접근, 장기 디스크, cloud metadata 등 더 큰 공격면을 가질 수 있다. public/fork PR을 영구 runner에서 실행하지 말고 ephemeral 격리, image 초기화, egress 제한, patching을 운영한다.

### 모든 테스트를 모든 PR에서 실행하기

검증이 느려지면 개발자가 우회하거나 큰 batch를 만든다. 빠른 필수 gate, 변경 경로 기반 integration, 예약된 전체 회귀, 배포 후 검증으로 test portfolio를 계층화한다. 단, path filter가 실제 dependency를 빠뜨리지 않도록 보수적으로 설계한다.

GitHub Actions는 YAML 문법 문제가 아니라 신뢰 경계 설계 문제다. event, code, credential, artifact, environment를 분리해 보면 어떤 자동화가 위험한지 훨씬 일찍 발견할 수 있다.
