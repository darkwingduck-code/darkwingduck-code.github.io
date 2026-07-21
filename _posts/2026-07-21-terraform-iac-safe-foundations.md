---
title: "Terraform IaC 안전 설계: 모듈, 환경, state, secret의 경계"
date: 2026-07-21 09:30:00 +0900
categories: [Platform Engineering, Infrastructure]
tags: [terraform, infrastructure-as-code, state-management, security, devops]
description: Terraform을 선언형 변경 시스템으로 이해하고 모듈 계약, 환경 격리, 원격 state, 비밀 관리와 plan/apply 검증 절차를 설계합니다.
---

## 문제: 코드로 만들었다고 인프라가 자동으로 안전해지지는 않는다

Terraform은 수동 클릭을 재현 가능한 코드로 바꾸지만, 동시에 인프라 변경 권한과 실제 자원 상태를 하나의 workflow에 모은다. 구조 없이 시작하면 작은 root module 하나가 모든 환경, 권한, 비밀, provider 설정을 떠안게 된다.

대표적인 실패는 다음과 같다.

- 개발과 운영이 같은 state와 credential을 공유한다.
- module이 지나치게 많은 선택지를 노출해 사실상 또 다른 플랫폼이 된다.
- local state가 유실되거나 여러 실행자가 동시에 수정한다.
- `sensitive = true`를 암호화로 오해해 secret이 state에 남는다.
- 검토한 plan과 실제 apply 사이에 코드·provider·state가 바뀐다.
- `-target`과 수동 console 변경이 정상 운영 방식이 된다.

IaC의 목표는 파일 수를 늘리는 것이 아니라 **변경 의도, 실제 상태, 권한 경계, 검증 결과를 하나의 감사 가능한 흐름으로 만드는 것**이다.

## Mental model: configuration, state, provider, real infrastructure의 조정

Terraform 실행에는 네 요소가 있다.

- **configuration**: 원하는 상태를 표현한 HCL
- **state**: Terraform 주소와 실제 원격 객체 ID 및 속성의 대응 정보
- **provider**: API를 읽고 변경하는 plugin
- **real infrastructure**: cloud, SaaS, on-premise의 실제 자원

`terraform plan`은 단순한 파일 diff가 아니다. configuration, 이전 state, provider가 읽은 실제 상태를 비교해 실행 계획을 만든다. `apply`는 dependency graph에 따라 API를 호출하고 성공한 결과를 state에 기록한다.

따라서 state는 cache가 아니다. 다음과 같은 중요한 운영 데이터다.

- 실제 resource identifier
- dependency와 attribute snapshot
- output과 일부 provider 반환 값
- 비밀일 수 있는 입력과 계산 결과

state를 잃으면 실제 인프라가 사라지는 것은 아니지만 Terraform이 소유 관계를 잃는다. 반대로 state 파일만 가진 사람도 민감 정보와 인프라 구조를 파악할 수 있다.

### 선언형은 “순서가 없다”는 뜻이 아니다

resource reference는 dependency edge를 만든다. Terraform은 가능한 작업을 병렬화하되 graph 순서를 지킨다. 의미 없는 `depends_on`을 많이 추가하면 숨은 coupling과 느린 plan을 만든다. 데이터 흐름을 reference로 표현하고, API의 비명시적 제약이 있을 때만 `depends_on`을 사용한다.

### module은 코드 재사용보다 정책 계약이다

좋은 module은 조직이 허용하는 선택을 좁힌다.

- input: 호출자가 결정해도 되는 것
- local: module이 표준화하는 이름·tag·정책
- resource: 구현 세부사항
- output: 다른 component가 의존해도 되는 안정된 계약

모든 provider argument를 variable로 그대로 노출하는 “thin wrapper”는 추상화 이점이 작다. 반대로 하나의 module이 network, database, application, monitoring을 모두 소유하면 변경 blast radius가 커진다.

## 실전 패턴: 작은 root와 안정된 module, 환경별 독립 state

### 권장 구조의 출발점

```text
infrastructure/
├── modules/
│   └── service/
│       ├── main.tf
│       ├── variables.tf
│       ├── outputs.tf
│       └── versions.tf
└── live/
    ├── development/
    │   ├── backend.hcl
    │   ├── main.tf
    │   └── terraform.tfvars.example
    └── production/
        ├── backend.hcl
        ├── main.tf
        └── terraform.tfvars.example
```

환경 directory를 복제하는 것이 유일한 정답은 아니다. 별도 repository, orchestration layer, account별 pipeline도 가능하다. 중요한 불변식은 다음과 같다.

- 환경마다 state key와 apply 권한이 독립적이다.
- production은 별도 account/project와 승인 경계를 사용한다.
- 공유 module의 version 또는 commit이 명시적으로 고정된다.
- environment 차이는 명시적 input이고 조건문 숲이 아니다.

Terraform workspace는 같은 configuration으로 여러 state를 운용하는 편의 기능이지만, 강한 보안 격리나 서로 크게 다른 환경 구조를 자동으로 제공하지 않는다. credential과 account 경계가 필요하면 directory/state만이 아니라 실행 identity도 분리한다.

### module에 좁고 검증 가능한 계약을 만든다

`variables.tf` 예시:

```hcl
variable "name" {
  description = "서비스를 식별하는 짧은 이름"
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,30}$", var.name))
    error_message = "name은 소문자로 시작하고 소문자, 숫자, 하이픈만 사용해야 합니다."
  }
}

variable "environment" {
  description = "배포 환경"
  type        = string

  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "허용된 environment 값을 사용해야 합니다."
  }
}

variable "labels" {
  description = "추가 공통 label"
  type        = map(string)
  default     = {}
}
```

`main.tf`에서 표준값을 module 내부에 둔다.

```hcl
locals {
  required_labels = {
    managed-by  = "terraform"
    environment = var.environment
    service     = var.name
  }

  labels = merge(var.labels, local.required_labels)
}

# provider에 독립적인 예시를 위해 실제 resource는 생략했다.
# 각 resource는 local.labels를 사용해 소유권과 환경을 표시한다.
```

`merge`의 뒤쪽 map이 앞쪽을 덮으므로 필수 label을 마지막에 두면 호출자가 이를 바꾸지 못한다. 이것은 작은 예지만 module이 정책을 캡슐화하는 방식이다.

output은 필요한 최소 계약만 공개한다.

```hcl
output "service_id" {
  description = "다른 module이 참조할 안정된 서비스 ID"
  value       = <RESOURCE_ADDRESS>.id
}
```

전체 resource 객체를 output하면 호출자가 구현 세부 속성에 결합된다. ID, endpoint, role identifier처럼 소비자가 실제로 필요한 값만 낸다.

### version과 provider lock을 함께 관리한다

```hcl
terraform {
  required_version = ">= 1.8, < 2.0"

  required_providers {
    <PROVIDER_NAME> = {
      source  = "<PROVIDER_NAMESPACE>/<PROVIDER_NAME>"
      version = "~> <REVIEWED_MAJOR.MINOR>"
    }
  }
}
```

예시의 placeholder는 실제 provider로 교체해야 한다. root module에서 version constraint를 정하고 `terraform init`이 생성하는 `.terraform.lock.hcl`을 commit한다. module은 필요한 최소 provider version을 선언하되, 최종 선택과 lock은 root가 책임지는 것이 일반적이다.

lock file은 provider binary 선택과 checksum을 고정한다. 여러 OS/architecture에서 실행한다면 CI와 개발 환경에 필요한 platform checksum을 의도적으로 관리한다.

### backend 설정과 state 접근을 코드 접근에서 분리한다

backend block에는 비밀을 직접 쓰지 않는다.

```hcl
terraform {
  backend "<REMOTE_BACKEND_TYPE>" {}
}
```

환경별 비민감 설정은 별도 파일로 전달할 수 있다.

```hcl
# live/production/backend.hcl
bucket         = "<REMOTE_STATE_BUCKET>"
key            = "<SERVICE>/production/terraform.tfstate"
region         = "<REGION>"
encrypt        = true
use_lockfile   = true
```

위 argument는 backend 종류와 Terraform version에 따라 다르므로 공식 문서와 실제 backend 기능을 확인한다. 핵심 요구사항은 다음과 같다.

- 전송·저장 암호화
- 동시 apply를 막는 locking
- versioning과 복구 정책
- 최소 권한 identity
- 환경별 별도 key와 access policy
- audit log와 비정상 접근 경보

초기화는 환경 directory에서 명시적으로 수행한다.

```bash
terraform init -backend-config=backend.hcl
terraform providers
```

backend credential은 파일에 넣지 않고 CI의 OIDC 또는 표준 credential chain으로 짧게 발급한다. `backend.hcl`에 access key를 쓰면 `.terraform` metadata나 shell history 등 여러 경로에 남을 수 있다.

### plan과 apply를 하나의 검토 가능한 변경으로 묶는다

기본 검증 흐름:

```bash
terraform fmt -check -recursive
terraform init -input=false -backend=false
terraform validate
```

실제 remote state와 provider API를 사용하는 plan은 승인된 identity와 environment에서 수행한다.

```bash
terraform init -input=false -backend-config=backend.hcl
terraform plan -input=false -out=tfplan
terraform show -no-color tfplan
```

저장된 plan 파일은 binary이며 민감 값이 포함될 수 있다. 공개 CI artifact로 무기한 보존하지 말고 encryption, 접근 제어, 짧은 retention을 적용한다. apply는 동일 commit, 동일 lock file, 동일 state 계보에서 만든 plan만 사용한다.

```bash
terraform apply -input=false tfplan
```

사람이 텍스트 plan을 승인한 뒤 다른 commit에서 새 plan을 자동 apply하면 승인의 의미가 사라진다. pipeline이 source SHA와 plan artifact digest를 연결해야 한다.

### secret 값 자체보다 secret reference를 전달한다

다음 선언은 UI와 일부 출력에서 값을 숨기지만 state 암호화가 아니다.

```hcl
variable "bootstrap_secret" {
  type        = string
  sensitive   = true
  description = "초기 구성에만 필요한 비밀값"
}
```

provider API가 resource 속성으로 값을 받으면 그 값이 state에 저장될 수 있다. 가능한 설계는 다음과 같다.

1. secret manager에서 비밀을 별도 lifecycle로 생성한다.
2. Terraform은 secret의 ID 또는 경로와 읽기 권한만 연결한다.
3. workload는 runtime identity로 secret manager에서 값을 읽는다.
4. plan, output, log에는 비밀 원문을 전달하지 않는다.

Terraform이 비밀 생성까지 책임져야 한다면 state가 secret store가 된다는 사실을 인정하고 state 접근·암호화·rotation을 그 수준으로 운영한다. `nonsensitive()`로 표시를 제거하는 것은 보안 해결책이 아니다.

### drift는 야간 plan 하나로 끝나지 않는다

정기적인 read-only plan으로 console 변경과 외부 자동화의 drift를 탐지한다. 발견 시 세 선택을 명시한다.

- 실제 변경이 잘못됨: Terraform으로 원래 선언 상태 복원
- 실제 변경이 정당함: configuration에 반영하고 정상 PR로 적용
- 소유권이 잘못됨: `import`, `moved`, state operation을 검토해 책임 경계 수정

resource 주소를 바꿀 때는 삭제·재생성으로 오해되지 않도록 `moved` block을 사용한다.

```hcl
moved {
  from = <OLD_RESOURCE_ADDRESS>
  to   = <NEW_RESOURCE_ADDRESS>
}
```

import와 state command는 실제 자원을 바꾸지 않더라도 Terraform의 소유권 인식을 바꾼다. 작업 전 state versioning을 확인하고, 변경 후 반드시 plan이 예상대로 비어 있거나 의도한 diff만 갖는지 검증한다.

## 검증 체크리스트

module review:

- [ ] module이 하나의 응집된 lifecycle과 소유자를 가진다.
- [ ] input type, description, validation, default가 명확하다.
- [ ] 필수 보안·소유 label을 호출자가 우회할 수 없다.
- [ ] output이 구현 전체가 아니라 안정된 최소 계약이다.
- [ ] provider와 Terraform version 범위가 명시돼 있다.
- [ ] upgrade와 주소 변경에 `moved` block·migration 문서가 있다.

environment와 state review:

- [ ] 개발·staging·운영 state와 실행 identity가 분리돼 있다.
- [ ] remote backend에 encryption, locking, versioning, audit가 있다.
- [ ] state와 plan artifact 접근 권한이 코드 읽기 권한보다 좁다.
- [ ] `.terraform/`, `*.tfstate*`, 실제 `*.tfvars`, plan 파일이 commit되지 않는다.
- [ ] `.terraform.lock.hcl`은 검토 후 commit한다.
- [ ] 운영 apply는 보호 환경과 승인된 pipeline에서만 수행한다.

변경 review:

- [ ] `fmt`, `validate`, lint와 정책 검사를 통과했다.
- [ ] plan의 add/change/destroy/replace를 자원별로 읽었다.
- [ ] 강제 교체, 데이터 손실, 네트워크 차단 가능성을 확인했다.
- [ ] 검토한 plan과 apply할 binary plan이 같은 source/state에서 왔다.
- [ ] 적용 뒤 핵심 기능과 관측 지표를 검증할 방법이 있다.
- [ ] 롤백이 불가능한 변경은 roll-forward 절차와 백업 복원을 시험했다.

## 실패 사례와 한계

### 하나의 거대한 state

참조는 편하지만 작은 변경도 전체 graph refresh와 넓은 권한을 요구한다. 함께 변경되고 함께 소유되며 같은 blast radius를 가져야 하는 자원끼리 state를 나눈다. 반대로 너무 잘게 나누면 cross-state output, 순서, orchestration 부담이 커진다.

### 환경 차이를 조건문으로 모두 흡수하기

`count`, `for_each`, 삼항 연산자로 모든 환경을 한 root에 넣으면 plan을 읽기 어려워진다. 공통 정책은 module로, 환경 조합은 얇은 root로 분리한다.

### `-target`을 일상 배포 도구로 사용하기

`-target`은 복구와 특수 상황을 위한 제한적 수단이다. graph 일부만 적용해 configuration 전체와 실제 상태의 일관성을 놓칠 수 있다. 사용 후 반드시 전체 plan을 수행한다.

### `prevent_destroy`가 백업이라고 생각하기

lifecycle guard는 일부 실수를 막지만 권한 있는 사용자가 제거할 수 있고 provider 밖의 삭제를 막지 못한다. 데이터 자원에는 별도의 백업, 복구 연습, retention, deletion protection이 필요하다.

### apply 성공을 서비스 정상으로 간주하기

API가 자원을 만들었다는 사실과 애플리케이션이 정상이라는 사실은 다르다. 배포 후 DNS, 권한, 연결, health, SLO 지표를 확인한다. IaC는 운영 검증과 incident 대응을 대체하지 않는다.

### Terraform으로 모든 것을 관리하기

Terraform은 장기 lifecycle의 선언형 자원에 강하다. 고빈도 애플리케이션 deploy, imperative data migration, 일회성 bootstrap까지 억지로 넣으면 state와 graph가 불안정해질 수 있다. 각 변경의 lifecycle과 rollback 특성에 맞는 도구를 선택한다.

안전한 Terraform은 HCL 기교보다 경계 설계에서 나온다. module은 정책 경계, state는 보안 자산, plan은 변경 계약, pipeline identity는 실행 권한으로 다뤄야 한다.
