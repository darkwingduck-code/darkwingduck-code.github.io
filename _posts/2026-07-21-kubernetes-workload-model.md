---
title: "Kubernetes 워크로드 모델: Pod를 넘어서 Controller와 상태를 설계하기"
date: 2026-07-21 12:01:00 +0900
categories: [Cloud Native, Kubernetes]
tags: [kubernetes, pods, deployments, statefulsets, scheduling]
description: Kubernetes의 선언적 reconciliation 관점에서 Pod, Deployment, StatefulSet, DaemonSet, Job을 선택하고 안전하게 운영하는 기준을 정리합니다.
lang: ko-KR
translation_key: kubernetes-workload-model
mermaid: true
---

{% include language-switcher.html %}

## 문제: YAML을 배포했다고 운영 모델이 생기지는 않는다

Kubernetes는 container 실행 명령을 원격으로 보내는 도구가 아니다.

사용자가 원하는 상태를 API object로 기록하면 controller가 실제 상태를 계속 그쪽으로 수렴시키는 시스템이다.

이 mental model이 없으면 다음 문제가 반복된다.

- 사람이 만든 Pod가 사라진 뒤 복구되지 않는다.
- Deployment에 identity가 필요한 상태 저장 workload를 억지로 넣는다.
- readiness와 liveness를 같은 endpoint로 사용해 장애를 확대한다.
- request 없이 limit만 설정해 scheduling과 throttling을 예측하지 못한다.
- rolling update 중 schema 비호환으로 구버전과 신버전이 충돌한다.
- `kubectl exec` 수정으로 임시 복구한 뒤 선언 상태와 drift가 생긴다.
- probe 실패와 실제 사용자 실패를 구분하지 못한다.

공식 [Kubernetes Workloads 문서](https://kubernetes.io/docs/concepts/workloads/)는 Pod를 직접 관리하기보다 Deployment, StatefulSet, DaemonSet, Job 같은 workload resource가 Pod 집합을 관리하도록 설명한다.

## Mental model: 원하는 상태와 실제 상태 사이의 제어 loop

```mermaid
flowchart LR
    G[Git과 배포 도구] --> A[Kubernetes API]
    A --> E[(etcd의 원하는 상태)]
    E --> C[Controller]
    C --> P[Pod와 하위 object]
    P --> O[관찰된 실제 상태]
    O --> C
```

### API object는 명령이 아니라 상태 계약이다

`replicas: 3`은 Pod 세 개를 한 번 만들라는 명령이 아니다.

controller가 관찰하는 동안 사용 가능한 replica 수를 목표에 맞추라는 선언이다.

node 장애로 Pod가 사라지면 새 Pod가 만들어질 수 있다.

그러나 새 Pod는 이전 process의 memory나 local disk 상태를 자동으로 상속하지 않는다.

### Pod는 가장 작은 scheduling 단위다

Pod 안 container들은 network namespace와 volume을 공유한다.

강하게 결합되어 함께 배치·종료되어야 할 process만 같은 Pod에 둔다.

일반적으로 서로 독립적으로 확장해야 하는 application과 database를 한 Pod에 넣지 않는다.

sidecar는 lifecycle과 resource 경쟁까지 포함한 결합임을 기억한다.

### Controller 선택은 identity와 완료 조건의 선택이다

- **Deployment**: replica가 교체 가능한 장기 실행 무상태 workload
- **StatefulSet**: 안정된 이름, 순서, storage binding 같은 identity가 필요한 workload
- **DaemonSet**: 선택된 각 node에 하나씩 필요한 node-local agent
- **Job**: 성공 완료 횟수가 중요한 유한 작업
- **CronJob**: 일정에 따라 Job을 만드는 schedule controller

StatefulSet이 애플리케이션 복제나 데이터 일관성을 자동 제공하지는 않는다.

그 책임은 database 또는 application protocol에 남는다.

## 핵심 object와 경계

### Deployment와 ReplicaSet

Deployment는 rollout history와 전략을 관리하고 ReplicaSet이 Pod 수를 관리한다.

Pod template가 바뀌면 새 ReplicaSet이 생성된다.

selector는 controller 소유권의 핵심이므로 배포 뒤 임의 변경 대상으로 보지 않는다.

### Service와 EndpointSlice

Service는 변하는 Pod 집합 앞에 안정된 접근점을 제공한다.

label selector가 의도한 Pod만 선택하는지 검증한다.

readiness를 통과하지 못한 Pod는 일반적인 Service endpoint에서 제외될 수 있다.

Service가 애플리케이션 수준의 transaction 성공까지 보증하지는 않는다.

### ConfigMap과 Secret

ConfigMap은 비기밀 설정을 분리한다.

Secret object는 민감 값을 표현하지만 저장 시 암호화, RBAC, 외부 secret 연동을 별도로 설계해야 한다.

환경 변수 주입은 process 시작 뒤 자동 갱신되지 않는다.

volume 반영도 application reload 의미와 일치하는지 확인한다.

### PersistentVolume과 PersistentVolumeClaim

PVC는 storage 요청이고 PV는 제공된 storage 자원이다.

access mode 이름만 보고 실제 backend의 동시 쓰기 안전성을 추정하지 않는다.

reclaim policy, snapshot, backup, zone topology, restore 절차를 함께 검토한다.

## Workflow: workload를 설계하는 순서

### Step 1. 실행 의미를 분류한다

다음을 먼저 답한다.

- 영구 실행인가, 완료되는 작업인가?
- replica가 서로 교체 가능한가?
- 안정된 network identity가 필요한가?
- node마다 실행되어야 하는가?
- 외부에서 이미 상태를 관리하는가?
- 종료 신호 뒤 얼마 동안 정리해야 하는가?

이 답으로 workload controller 후보를 좁힌다.

### Step 2. resource request를 실제 측정으로 정한다

request는 scheduler가 배치 가능성을 판단하는 기준이다.

limit은 runtime 제약이며 CPU와 memory의 실패 방식이 다르다.

- CPU limit 초과는 throttling으로 나타날 수 있다.
- memory limit 초과는 OOM 종료로 이어질 수 있다.
- request가 너무 작으면 node가 과밀해진다.
- request가 너무 크면 실제 여유가 있어도 scheduling이 막힌다.

peak와 percentile, warm-up, GC, sidecar 사용량을 함께 측정한다.

### Step 3. startup, readiness, liveness를 분리한다

`startupProbe`는 느린 초기화를 보호한다.

`readinessProbe`는 새 요청을 받을 준비가 되었는지 나타낸다.

`livenessProbe`는 restart가 복구에 도움이 되는 교착 상태를 탐지한다.

liveness가 외부 database 장애에 의존하면 모든 Pod가 재시작되며 장애가 커질 수 있다.

probe에는 timeout, period, failureThreshold를 의도적으로 정한다.

### Step 4. 종료를 정상 경로로 설계한다

Pod 종료 시 application은 SIGTERM을 받고 grace period 안에 작업을 마쳐야 한다.

새 요청 차단, connection drain, checkpoint, lock 해제 순서를 설계한다.

grace period가 실제 최대 처리 시간보다 짧으면 강제 종료가 정상 동작이 된다.

`preStop` hook을 사용할 때도 전체 grace period 안에 포함됨을 고려한다.

### Step 5. rollout 호환성을 확보한다

rolling update 동안 구버전과 신버전이 동시에 존재한다.

따라서 API와 message schema, database schema는 공존 가능해야 한다.

expand-and-contract migration을 사용한다.

1. 기존 version이 무시할 수 있는 additive schema를 배포한다.
2. 양쪽 schema를 처리하는 application을 배포한다.
3. data backfill을 완료하고 검증한다.
4. 모든 consumer 전환 뒤 오래된 field를 제거한다.

### Step 6. placement와 disruption을 설계한다

topology spread와 anti-affinity로 replica를 실패 도메인에 분산한다.

node selector, affinity, taint, toleration은 placement 계약이다.

PodDisruptionBudget은 voluntary disruption 때 동시 중단 범위를 제한한다.

PDB는 node 장애 같은 involuntary disruption을 막지 못한다.

### Step 7. 권한과 network를 최소화한다

workload마다 ServiceAccount를 분리한다.

Kubernetes API 권한은 RBAC의 최소 verb와 resource로 제한한다.

cloud access는 장기 key보다 workload identity를 사용한다.

NetworkPolicy는 지원하는 CNI와 ingress·egress 양방향 동작을 검증한다.

default deny 도입 전 DNS와 필요한 control path를 식별한다.

### Step 8. 관찰성과 debug evidence를 남긴다

다음 신호를 연결한다.

- deployment revision과 image digest
- Pod phase와 container state
- restart count와 last termination reason
- scheduling event와 pending reason
- request 대비 실제 CPU·memory
- probe 실패와 endpoint 제외 시간
- 사용자 SLI와 trace
- node pressure와 eviction event

## 실전 예제: 무상태 API Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: example-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: example-api
  strategy:
    rollingUpdate:
      maxUnavailable: 0
      maxSurge: 1
  template:
    metadata:
      labels:
        app: example-api
    spec:
      serviceAccountName: example-api
      containers:
        - name: api
          image: registry.example.invalid/api@sha256:REPLACE_WITH_DIGEST
          ports:
            - containerPort: 8080
          resources:
            requests:
              cpu: 200m
              memory: 256Mi
            limits:
              memory: 512Mi
          startupProbe:
            httpGet:
              path: /health/startup
              port: 8080
            failureThreshold: 30
            periodSeconds: 2
          readinessProbe:
            httpGet:
              path: /health/ready
              port: 8080
            periodSeconds: 5
          livenessProbe:
            httpGet:
              path: /health/live
              port: 8080
            periodSeconds: 10
      terminationGracePeriodSeconds: 60
```

이 예시는 출발점일 뿐 완성된 보안 설정이 아니다.

digest 고정, ServiceAccount, NetworkPolicy, securityContext, autoscaling, disruption policy를 환경 요구에 맞춰 추가한다.

readiness endpoint는 필수 초기화 완료와 새 요청 수용 가능성을 검사한다.

liveness endpoint는 외부 dependency보다 process 자체의 회복 불가능 상태에 집중한다.

## 장애 진단 절차

### Pending Pod

1. Pod event에서 scheduler reason을 확인한다.
2. request와 node allocatable을 비교한다.
3. taint, affinity, topology constraint를 확인한다.
4. PVC binding과 zone 제약을 확인한다.
5. quota와 LimitRange를 확인한다.

### CrashLoopBackOff

1. 현재 log와 `--previous` log를 모두 확인한다.
2. last termination reason과 exit code를 확인한다.
3. config·secret key 누락을 확인한다.
4. startup와 liveness timing을 확인한다.
5. OOMKilled 여부와 memory peak를 확인한다.

### rollout 정체

1. 새 ReplicaSet의 desired·ready·available을 비교한다.
2. 새 Pod event와 readiness 실패를 확인한다.
3. `maxSurge`, `maxUnavailable`, quota를 확인한다.
4. PDB와 node 용량의 상호작용을 확인한다.
5. 사용자 SLI가 나빠지면 rollout을 중단한다.

## 검증 Checklist

### workload 의미

- [ ] controller 선택 근거가 ADR에 있다.
- [ ] Pod가 교체되어도 상태를 복원할 수 있다.
- [ ] 종료와 중복 실행의 의미가 정의되어 있다.
- [ ] batch 작업의 완료·실패 조건이 명확하다.

### resource와 scheduling

- [ ] request는 관측값으로 정했다.
- [ ] memory OOM과 CPU throttling 경보가 있다.
- [ ] 실패 도메인 분산을 검증했다.
- [ ] cluster autoscaler 반응 시간을 부하 시험했다.
- [ ] quota와 priority 정책을 확인했다.

### 배포

- [ ] image를 immutable digest로 추적한다.
- [ ] 이전·새 version 동시 실행이 안전하다.
- [ ] probe 세 종류의 목적이 분리되어 있다.
- [ ] graceful shutdown을 부하 상태에서 시험했다.
- [ ] rollback과 schema 호환성을 검증했다.

### 보안과 운영

- [ ] ServiceAccount token 필요성을 검토했다.
- [ ] privileged와 host namespace 사용을 최소화했다.
- [ ] Secret 저장 암호화와 RBAC를 검토했다.
- [ ] NetworkPolicy를 실제 packet 흐름으로 시험했다.
- [ ] audit log와 deployment identity가 연결된다.
- [ ] debug용 임시 변경을 선언 상태에 반영하거나 제거한다.

## 자주 겪는 실패와 한계

### Kubernetes가 application HA를 자동 제공한다고 믿는다

Kubernetes는 process를 다시 배치할 수 있지만 데이터 복제, transaction, leader election의 정확성은 application과 storage 책임이다.

### 모든 문제에 liveness restart를 사용한다

재시작이 외부 장애를 해결하지 못하면 부하와 복구 시간을 늘린다.

### `latest` tag를 배포한다

같은 manifest가 다른 bytes를 가리키면 rollback과 감사를 재현할 수 없다.

### 운영 중 `kubectl edit`를 정상 변경 경로로 쓴다

Git 또는 배포 source와 cluster 상태가 갈라져 다음 reconcile 때 수정이 사라진다.

### StatefulSet을 database 운영 자동화로 오해한다

일관된 backup, quorum, upgrade, failover는 별도 검증이 필요하다.

### abstraction 비용을 무시한다

작은 시스템에서는 managed runtime이나 단순 VM이 더 낮은 운영 위험을 가질 수 있다.

Kubernetes 채택은 조직의 운영 능력과 workload 수명주기를 함께 평가해야 한다.

## 공식 참고자료

- [Kubernetes Workloads](https://kubernetes.io/docs/concepts/workloads/)
- [Kubernetes Deployments](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)
- [Kubernetes StatefulSets](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/)
- [Pod Lifecycle과 Container Probes](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/)
- [Resource Management for Pods and Containers](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)
- [Kubernetes Security Checklist](https://kubernetes.io/docs/concepts/security/security-checklist/)

## 마무리

Kubernetes 운영의 기본 단위는 YAML 파일이 아니라 지속적인 reconciliation 계약이다.

workload identity, resource, probe, 종료, rollout, storage, 권한을 하나의 lifecycle로 설계하자.

Pod가 사라지는 사건을 예외가 아니라 정상적인 상태 전이로 다룰 때 Kubernetes의 장점이 드러난다.
