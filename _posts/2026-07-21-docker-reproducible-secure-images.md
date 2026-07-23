---
title: "재현 가능하고 안전한 Docker 이미지: build context부터 non-root까지"
date: 2026-07-21 09:40:00 +0900
categories: [Platform Engineering, Containers]
tags: [docker, containers, reproducibility, supply-chain, security]
description: Docker의 layer와 build context를 기준으로 multi-stage build, dependency 고정, healthcheck, non-root 실행과 이미지 검증 절차를 설계합니다.
lang: ko-KR
translation_key: docker-reproducible-secure-images
---

{% include language-switcher.html %}

## 문제: “내 컴퓨터에서는 된다”를 이미지 안으로 옮길 수도 있다

컨테이너는 실행 환경을 포장하지만, 자동으로 재현성과 보안을 보장하지 않는다. `latest` base image, 잠기지 않은 dependency, 너무 큰 build context, root 사용자, 이미지에 복사된 secret을 그대로 두면 환경 차이와 공격면도 함께 포장한다.

다음 두 이미지는 같은 Dockerfile에서 만들어져도 같지 않을 수 있다.

- build 시점에 base tag가 다른 digest를 가리켰다.
- package index가 새 dependency를 선택했다.
- 로컬의 임시 파일이 build context에 포함됐다.
- CPU architecture에 따라 다른 native wheel을 받았다.
- build metadata와 timestamp가 달라졌다.

따라서 목표를 구분해야 한다.

1. **기능적 재현성**: 같은 source와 lock에서 같은 동작을 한다.
2. **dependency 재현성**: 같은 base와 package artifact를 선택한다.
3. **bit-for-bit 재현성**: 생성된 image digest까지 같다.

일반 서비스는 앞의 두 가지부터 달성하고, 공급망 요구가 높다면 deterministic build와 provenance까지 확장한다.

## Mental model: image는 불변 layer, container는 실행 상태다

Docker build의 핵심 구성요소는 다음과 같다.

- **build context**: builder에 전달되는 파일 집합
- **Dockerfile instruction**: layer와 image metadata를 만드는 단계
- **image**: content-addressed layer와 config의 불변 집합
- **container**: image에 writable layer, process, namespace, resource limit을 결합한 실행 인스턴스
- **registry**: image manifest와 blob을 보관·배포하는 저장소

Dockerfile의 각 단계는 이전 상태와 instruction, 사용 파일을 입력으로 cache key를 만든다. 자주 변하는 source를 dependency 설치보다 먼저 `COPY`하면 작은 코드 변경에도 dependency layer가 무효화된다.

tag와 digest도 다르다.

```text
registry.example.invalid/service:1.4    # 이동 가능한 이름
registry.example.invalid/service@sha256:<DIGEST>  # 불변 content 주소
```

사람은 version tag로 release를 찾고, 배포 시스템은 검증된 digest를 사용하는 조합이 좋다.

### 컨테이너 격리는 보안 경계의 한 층이다

컨테이너는 VM과 같은 별도 kernel을 갖지 않는 경우가 일반적이다. rootless runtime, seccomp/AppArmor/SELinux, capability 제거, read-only filesystem, network policy, host patching을 함께 사용해야 한다. 이미지에서 `USER`를 non-root로 지정하는 것은 중요한 기본값이지만 완전한 sandbox는 아니다.

## 실전 패턴: 작은 context, 잠긴 입력, multi-stage, 최소 실행 권한

### build context부터 제한한다

`.dockerignore` 예시:

```dockerignore
.git
.github
.env
.env.*
!.env.example
.venv
__pycache__/
*.pyc
*.log
.pytest_cache/
.mypy_cache/
tests/
docs/
dist/
build/
```

`.dockerignore`는 image 크기만 줄이는 도구가 아니다. builder로 전송되는 범위를 줄여 secret과 불필요한 파일이 `COPY . .`에 섞이는 것을 막는다. 실제 runtime에 test나 docs가 필요한 프로젝트라면 무작정 제외하지 말고 build 목적별 context를 설계한다.

`.env`를 제외했더라도 이미 Git에 commit했거나 build argument로 전달하면 노출될 수 있다. secret scanner와 credential rotation이 별도로 필요하다.

### Python 서비스의 multi-stage Dockerfile

다음 예시는 compiler가 필요 없는, hash가 잠긴 binary wheel을 사용하는 서비스 골격이다.

```dockerfile
# syntax=docker/dockerfile:1.7

# 로컬에서는 tag로 실행할 수 있지만, CI에서는 검토한 digest로 덮어쓴다.
ARG PYTHON_IMAGE=python:3.12-slim

FROM ${PYTHON_IMAGE} AS dependencies

WORKDIR /build
COPY requirements.lock ./requirements.lock

RUN python -m pip download \
      --require-hashes \
      --only-binary=:all: \
      --destination /wheelhouse \
      --requirement requirements.lock

FROM ${PYTHON_IMAGE} AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --home-dir /nonexistent app

WORKDIR /app

COPY --from=dependencies /wheelhouse /wheelhouse
COPY requirements.lock ./requirements.lock
RUN python -m pip install \
      --no-index \
      --find-links=/wheelhouse \
      --require-hashes \
      --requirement requirements.lock \
    && rm -rf /wheelhouse requirements.lock

COPY --chown=10001:10001 app/ ./app/

USER 10001:10001
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=2)"]

CMD ["python", "-m", "app"]
```

이 패턴의 의도는 다음과 같다.

- dependency lock을 source보다 먼저 복사해 cache 경계를 안정화한다.
- `--require-hashes`로 lock에 없는 package artifact를 거부한다.
- build용 download 단계와 runtime을 분리한다.
- 숫자 UID/GID로 runtime 사용자 해석 차이를 줄인다.
- shell form 대신 exec form `CMD`를 사용해 signal 전달을 단순화한다.
- healthcheck가 서비스의 process 존재가 아니라 HTTP 응답을 확인한다.

CI에서는 base를 digest로 고정한다.

```bash
docker build \
  --pull \
  --build-arg 'PYTHON_IMAGE=python:3.12-slim@sha256:<REVIEWED_BASE_IMAGE_DIGEST>' \
  --tag 'service:<SOURCE_REVISION>' \
  .
```

`<...>` placeholder는 실제 검토한 값으로 교체해야 한다. digest 고정은 update를 막는 것이 아니라 변경을 PR로 보이게 만든다. base image 취약점 수정이 나오면 자동화된 digest update PR을 검토하고 재build한다.

native extension을 source에서 compile해야 한다면 builder stage에 compiler와 header를 설치하고 결과 wheel만 runtime으로 복사한다. compiler toolchain과 OS package version도 입력이므로 lock과 provenance 범위에 포함한다.

### lock file은 범위가 아니라 정확한 artifact를 표현한다

다음과 같은 범위만 있는 파일은 시간이 지나면 다른 결과를 선택할 수 있다.

```text
framework>=1.0
client-library
```

production lock은 transitive dependency까지 version과 hash를 고정하고, 자동 update 도구로 새 lock을 만든 뒤 테스트한다. 사람이 직접 dependency tree 일부만 수정하면 해상 결과가 불일치할 수 있다.

OS package도 같은 원리다. `apt-get upgrade`를 build마다 실행하는 방식은 최신일 수 있지만 재현 가능한 입력은 아니다. 다음 중 시스템 요구에 맞는 정책을 선택한다.

- 신뢰한 base image digest에 OS package 집합을 포함하고 base를 자주 갱신
- package snapshot repository와 exact version 사용
- 조직의 hardened base image pipeline 사용

취약점 대응은 “항상 최신”과 “영원히 고정” 사이의 선택이 아니다. **고정된 입력을 정기적으로 갱신하고 검증하는 과정**이다.

### build secret은 layer와 history에 남기지 않는다

피해야 할 형태:

```dockerfile
ARG PACKAGE_TOKEN
ENV PACKAGE_TOKEN=${PACKAGE_TOKEN}
RUN python -m pip install --index-url "https://${PACKAGE_TOKEN}@<PRIVATE_INDEX>/simple" <PACKAGE>
```

build arg와 environment는 image history, metadata, log, cache 경로에 노출될 수 있다. BuildKit secret mount를 사용하고 instruction 안에서도 값을 출력하지 않는다.

```dockerfile
RUN --mount=type=secret,id=package_token \
    PACKAGE_TOKEN="$(cat /run/secrets/package_token)" \
    python scripts/fetch_private_dependency.py
```

```bash
docker build \
  --secret id=package_token,src='<LOCAL_SECRET_FILE>' \
  --tag 'service:<SOURCE_REVISION>' \
  .
```

예시 script도 URL, exception, debug log에 token을 남기지 않아야 한다. 가능하면 장기 token보다 build service가 짧게 발급한 credential을 쓴다.

### runtime을 read-only와 최소 capability로 실행한다

이미지의 non-root 기본값에 runtime 정책을 더한다.

```bash
docker run --rm \
  --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=64m \
  --cap-drop ALL \
  --security-opt no-new-privileges=true \
  --memory 512m \
  --cpus 1.0 \
  --publish 127.0.0.1:8080:8080 \
  'service:<SOURCE_REVISION>'
```

서비스가 파일을 써야 한다면 root filesystem 전체를 열지 말고 `/tmp`, upload, cache 등 필요한 mount만 명시한다. `--privileged`, host socket mount, host network는 격리 모델을 크게 약화시키므로 편의 옵션으로 사용하지 않는다.

credential은 image나 일반 environment file에 bake하지 않는다. 배포 플랫폼의 secret store와 workload identity를 사용하고, secret은 필요한 process에만 메모리 또는 제한된 mount로 전달한다.

### healthcheck는 liveness와 readiness를 구분한다

Dockerfile의 `HEALTHCHECK`는 단일 상태만 표현한다. 오케스트레이터에서는 보통 다음을 분리한다.

- **startup**: 초기화가 끝났는가?
- **liveness**: process를 재시작해야 할 정도로 막혔는가?
- **readiness**: 지금 새 traffic을 받아도 되는가?

readiness에 모든 외부 dependency를 강하게 묶으면 일시적인 하위 서비스 장애가 전체 replica를 traffic에서 제거해 연쇄 장애를 키울 수 있다. endpoint는 실제 traffic 처리 능력을 반영하되, 재시작으로 해결되지 않는 외부 장애를 liveness 실패로 만들지 않는다.

### image를 build한 뒤 증거를 남긴다

검증 pipeline의 출력은 image뿐 아니라 다음을 포함한다.

- source revision과 build invocation
- base image와 최종 image digest
- SBOM
- vulnerability scan 결과와 예외 만료일
- test 결과
- build provenance와 서명/attestation

배포 시 tag를 다시 resolve하지 말고 승인된 digest를 사용한다. registry retention이 digest가 참조하는 blob을 배포 기간보다 먼저 지우지 않도록 정책을 맞춘다.

## 검증 체크리스트

build 전:

- [ ] `.dockerignore`가 Git, secret, local cache, 불필요한 artifact를 제외한다.
- [ ] base image와 language dependency가 검토된 version/digest와 hash로 잠겨 있다.
- [ ] lock update가 자동 테스트와 취약점 검토를 거친다.
- [ ] build secret이 `ARG`, `ENV`, URL, log에 들어가지 않는다.
- [ ] source보다 dependency manifest를 먼저 복사해 cache 경계를 만들었다.

image review:

- [ ] runtime image에 compiler, package manager cache, test credential이 없다.
- [ ] `USER`가 non-root이고 고정 UID/GID를 사용한다.
- [ ] entrypoint가 signal을 받고 정상 종료할 수 있다.
- [ ] healthcheck가 빠르고 timeout이 있으며 부작용이 없다.
- [ ] 이미지 크기뿐 아니라 layer 내용, SBOM, 취약점을 검사했다.
- [ ] multi-architecture image를 실제 대상 architecture에서 테스트했다.

runtime review:

- [ ] immutable digest로 배포한다.
- [ ] root filesystem은 read-only이고 writable mount를 최소화했다.
- [ ] capability 제거, no-new-privileges, seccomp 계층이 적용된다.
- [ ] CPU·memory·PID 제한과 graceful shutdown 시간이 있다.
- [ ] secret은 runtime identity 또는 secret store에서 전달된다.
- [ ] readiness, liveness, startup probe의 의미가 구분된다.

## 실패 사례와 한계

### image 크기만 보며 Alpine을 선택하기

작은 크기가 항상 작은 위험이나 빠른 운영을 뜻하지 않는다. libc 차이, native wheel 부재, DNS·timezone 동작, debugging 난이도를 함께 비교한다. 운영 호환성이 검증된 최소 base를 선택한다.

### multi-stage면 자동으로 안전하다고 생각하기

마지막 stage에 `COPY --from=builder / /`처럼 전체 filesystem을 복사하면 build secret과 toolchain이 다시 들어온다. 필요한 artifact 경로만 복사한다.

### healthcheck에서 인증·쓰기·무거운 query 수행하기

probe는 자주 실행된다. 느리거나 상태를 바꾸는 probe는 자체 장애 원인이 된다. 제한된 시간 안에 핵심 준비 상태만 확인한다.

### scanner 결과를 절대 판정으로 사용하기

scanner는 package inventory와 advisory 품질에 의존한다. false positive와 발견되지 않은 취약점이 모두 가능하다. reachable code, exploitability, compensating control을 검토하되 예외에는 소유자와 만료일을 둔다.

### container만으로 재현성을 완성하려 하기

외부 database schema, feature flag, secret version, hardware driver, kernel, network dependency는 image 밖에 있다. 배포 manifest, migration, IaC, configuration version, data contract까지 함께 추적해야 한다.

좋은 Dockerfile은 단순히 짧은 파일이 아니다. 어떤 입력으로 무엇을 만들었고, runtime에 무엇이 필요하지 않은지, 그 결과를 어떤 권한으로 실행하는지 설명할 수 있는 build 계약이다.
