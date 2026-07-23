---
title: "Terraform IaCの安全設計：モジュール、環境、state、secretの境界"
date: 2026-07-21 09:30:00 +0900
categories: [Platform Engineering, Infrastructure]
tags: [terraform, infrastructure-as-code, state-management, security, devops]
description: Terraformを宣言型変更システムとして理解し、モジュール契約、環境分離、リモートstate、secret管理、plan/applyの検証手順を設計します。
lang: ja-JP
translation_key: terraform-iac-safe-foundations
hidden: true
---

{% include language-switcher.html %}

## 問題：コードで作ったからといって、インフラが自動的に安全になるわけではない

Terraformは手動クリックを再現可能なコードに置き換えるが、同時にインフラ変更権限と実際のリソース状態を一つのworkflowへ集約する。構造を決めずに始めると、小さなroot module一つがすべての環境、権限、secret、provider設定を背負うことになる。

代表的な失敗は次のとおりである。

- 開発環境と本番環境が同じstateとcredentialを共有する。
- moduleが過剰に多くの選択肢を公開し、事実上もう一つのプラットフォームになる。
- local stateが失われたり、複数の実行者が同時に変更したりする。
- `sensitive = true`を暗号化と誤解し、secretがstateに残る。
- レビューしたplanと実際のapplyとの間で、コード・provider・stateが変わる。
- `-target`と手動console変更が通常の運用方法になる。

IaCの目標はファイル数を増やすことではなく、**変更意図、実際の状態、権限境界、検証結果を一つの監査可能な流れにすること**である。

## メンタルモデル：configuration、state、provider、real infrastructureの調整

Terraformの実行には四つの要素がある。

- **configuration**：望ましい状態を表現したHCL
- **state**：Terraformアドレスと実際のリモートオブジェクトIDおよび属性との対応情報
- **provider**：APIを読み取り、変更するplugin
- **real infrastructure**：cloud、SaaS、on-premiseの実際のリソース

`terraform plan`は単純なファイルdiffではない。configuration、以前のstate、providerが読み取った実際の状態を比較し、実行計画を作る。`apply`はdependency graphに従ってAPIを呼び出し、成功した結果をstateに記録する。

したがって、stateはcacheではない。次のような重要な運用データである。

- 実際のresource identifier
- dependencyとattribute snapshot
- outputと一部のprovider戻り値
- secretである可能性のある入力と計算結果

stateを失っても実際のインフラは消えないが、Terraformは所有関係を失う。反対に、stateファイルを持つだけの人でも、機密情報とインフラ構造を把握できる。

### 宣言型は「順序がない」という意味ではない

resource referenceはdependency edgeを作る。Terraformは可能な作業を並列化しながら、graphの順序を守る。意味のない`depends_on`を大量に追加すると、隠れたcouplingと遅いplanを生む。データの流れはreferenceで表現し、APIに暗黙の制約があるときだけ`depends_on`を使用する。

### moduleはコード再利用よりもポリシー契約である

優れたmoduleは、組織が許可する選択肢を絞る。

- input：呼び出し側が決定してよいもの
- local：moduleが標準化する名前・tag・ポリシー
- resource：実装の詳細
- output：他のcomponentが依存してよい安定した契約

すべてのprovider argumentをvariableとしてそのまま公開する「thin wrapper」は、抽象化の利点が小さい。反対に、一つのmoduleがnetwork、database、application、monitoringをすべて所有すると、変更のblast radiusが大きくなる。

## 実践パターン：小さなrootと安定したmodule、環境ごとに独立したstate

### 推奨構成の出発点

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

環境directoryを複製することだけが唯一の正解ではない。別repository、orchestration layer、account別pipelineも可能である。重要な不変条件は次のとおりである。

- 環境ごとにstate keyとapply権限が独立している。
- productionは別account/projectと承認境界を使用する。
- 共有moduleのversionまたはcommitが明示的に固定されている。
- environmentの違いは明示的なinputであり、条件分岐の森ではない。

Terraform workspaceは同じconfigurationで複数のstateを運用するための便利な機能だが、強固なセキュリティ分離や、構造が大きく異なる複数環境を自動的に提供するものではない。credentialとaccountの境界が必要なら、directory/stateだけでなく実行identityも分離する。

### moduleに狭く検証可能な契約を作る

`variables.tf`の例：

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

`main.tf`では標準値をmodule内部に置く。

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

`merge`では後ろのmapが前のmapを上書きするため、必須labelを最後に置けば呼び出し側は変更できない。これは小さな例だが、moduleがポリシーをカプセル化する方法である。

outputは必要最小限の契約だけを公開する。

```hcl
output "service_id" {
  description = "다른 module이 참조할 안정된 서비스 ID"
  value       = <RESOURCE_ADDRESS>.id
}
```

resourceオブジェクト全体をoutputすると、呼び出し側が実装の詳細な属性に結合される。ID、endpoint、role identifierのように、利用側が実際に必要とする値だけを出力する。

### versionとprovider lockを一緒に管理する

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

例のplaceholderは実際のproviderに置き換える必要がある。root moduleでversion constraintを定め、`terraform init`が生成する`.terraform.lock.hcl`をcommitする。moduleは必要な最小provider versionを宣言するが、最終選択とlockはrootが担うのが一般的である。

lock fileはprovider binaryの選択とchecksumを固定する。複数のOS/architectureで実行するなら、CIと開発環境に必要なplatform checksumを意図的に管理する。

### backend設定とstateへのアクセスをコードへのアクセスから分離する

backend blockにsecretを直接書いてはならない。

```hcl
terraform {
  backend "<REMOTE_BACKEND_TYPE>" {}
}
```

環境ごとの非機密設定は、別ファイルで渡すことができる。

```hcl
# live/production/backend.hcl
bucket         = "<REMOTE_STATE_BUCKET>"
key            = "<SERVICE>/production/terraform.tfstate"
region         = "<REGION>"
encrypt        = true
use_lockfile   = true
```

上記のargumentはbackendの種類とTerraform versionによって異なるため、公式文書と実際のbackend機能を確認する。中核となる要件は次のとおりである。

- 転送時・保存時の暗号化
- 同時applyを防ぐlocking
- versioningと復旧ポリシー
- 最小権限identity
- 環境ごとに分離したkeyとaccess policy
- audit logと異常アクセスのアラート

初期化は環境directoryで明示的に実行する。

```bash
terraform init -backend-config=backend.hcl
terraform providers
```

backend credentialはファイルに入れず、CIのOIDCまたは標準credential chainを通じて短期間だけ発行する。`backend.hcl`にaccess keyを書くと、`.terraform` metadataやshell historyなど複数の経路に残る可能性がある。

### planとapplyを一つのレビュー可能な変更として結び付ける

基本的な検証フロー：

```bash
terraform fmt -check -recursive
terraform init -input=false -backend=false
terraform validate
```

実際のremote stateとprovider APIを使用するplanは、承認済みのidentityとenvironmentで実行する。

```bash
terraform init -input=false -backend-config=backend.hcl
terraform plan -input=false -out=tfplan
terraform show -no-color tfplan
```

保存したplanファイルはbinaryであり、機密値が含まれる可能性がある。公開CI artifactとして無期限に保存せず、encryption、アクセス制御、短いretentionを適用する。applyには、同じcommit、同じlock file、同じstate lineageから作成したplanだけを使用する。

```bash
terraform apply -input=false tfplan
```

人がテキストplanを承認した後、別のcommitで新しいplanを自動applyすれば、承認の意味が失われる。pipelineはsource SHAとplan artifact digestを結び付けなければならない。

### secretの値そのものではなくsecret referenceを渡す

次の宣言はUIと一部の出力で値を隠すが、stateの暗号化ではない。

```hcl
variable "bootstrap_secret" {
  type        = string
  sensitive   = true
  description = "초기 구성에만 필요한 비밀값"
}
```

provider APIがresource属性として値を受け取ると、その値がstateに保存される場合がある。可能な設計は次のとおりである。

1. secret managerでsecretを別のlifecycleとして生成する。
2. TerraformはsecretのIDまたはパスと読み取り権限だけを紐付ける。
3. workloadはruntime identityを使い、secret managerから値を読み取る。
4. plan、output、logへsecretの平文を渡さない。

Terraformがsecretの生成まで担う必要があるなら、stateがsecret storeになるという事実を認識し、stateへのアクセス・暗号化・rotationをその水準で運用する。`nonsensitive()`で表示上の区分を取り除くことは、セキュリティ上の解決策ではない。

### driftは夜間plan一つで終わらない

定期的なread-only planでconsole変更と外部自動化によるdriftを検知する。発見したら、三つの選択肢を明示する。

- 実際の変更が誤り：Terraformで元の宣言状態を復元
- 実際の変更が正当：configurationへ反映し、通常のPRとして適用
- 所有権が誤り：`import`、`moved`、state operationを検討し、責任境界を修正

resourceアドレスを変更するときは、削除・再作成と誤認されないよう`moved` blockを使用する。

```hcl
moved {
  from = <OLD_RESOURCE_ADDRESS>
  to   = <NEW_RESOURCE_ADDRESS>
}
```

importとstate commandは、実際のリソースを変更しなくてもTerraformの所有権認識を変更する。作業前にstate versioningを確認し、変更後は必ずplanが想定どおり空になっているか、意図したdiffだけを持つかを検証する。

## 検証チェックリスト

module review：

- [ ] moduleが一つの凝集したlifecycleと所有者を持つ。
- [ ] input type、description、validation、defaultが明確である。
- [ ] 必須のセキュリティ・所有labelを呼び出し側が回避できない。
- [ ] outputが実装全体ではなく、安定した最小契約である。
- [ ] providerとTerraform versionの範囲が明示されている。
- [ ] upgradeとアドレス変更に`moved` block・migration文書がある。

environmentとstateのreview：

- [ ] 開発・staging・本番のstateと実行identityが分離されている。
- [ ] remote backendにencryption、locking、versioning、auditがある。
- [ ] stateとplan artifactへのアクセス権限が、コードの読み取り権限より狭い。
- [ ] `.terraform/`、`*.tfstate*`、実際の`*.tfvars`、planファイルがcommitされていない。
- [ ] `.terraform.lock.hcl`はレビュー後にcommitする。
- [ ] 本番applyは、保護環境と承認済みpipelineでのみ実行する。

変更review：

- [ ] `fmt`、`validate`、lint、ポリシー検査を通過した。
- [ ] planのadd/change/destroy/replaceをリソースごとに確認した。
- [ ] 強制置換、データ損失、ネットワーク遮断の可能性を確認した。
- [ ] レビューしたplanとapplyするbinary planが、同じsource/stateから作られた。
- [ ] 適用後に中核機能と観測指標を検証する方法がある。
- [ ] ロールバック不可能な変更では、roll-forward手順とバックアップ復元をテストした。

## 失敗例と限界

### 一つの巨大なstate

参照は容易だが、小さな変更でもgraph全体のrefreshと広い権限を必要とする。一緒に変更され、一緒に所有され、同じblast radiusを持つべきリソースごとにstateを分ける。反対に、細分化しすぎるとcross-state output、順序、orchestrationの負担が増える。

### 環境差をすべて条件分岐で吸収する

`count`、`for_each`、三項演算子ですべての環境を一つのrootに入れると、planを読みづらくなる。共通ポリシーはmoduleに、環境ごとの組み合わせは薄いrootに分離する。

### `-target`を日常的なデプロイツールとして使用する

`-target`は復旧と特殊な状況のための限定的な手段である。graphの一部だけを適用し、configuration全体と実際の状態との一貫性を見落とす可能性がある。使用後は必ず全体planを実行する。

### `prevent_destroy`をバックアップだと考える

lifecycle guardは一部のミスを防ぐが、権限を持つユーザーは削除でき、provider外での削除を防ぐこともできない。データリソースには、別途バックアップ、復旧訓練、retention、deletion protectionが必要である。

### applyの成功をサービス正常と見なす

APIがリソースを作成したことと、アプリケーションが正常であることは異なる。デプロイ後にDNS、権限、接続、health、SLO指標を確認する。IaCは運用検証とincident対応に代わるものではない。

### Terraformですべてを管理する

Terraformは長期lifecycleを持つ宣言型リソースに強い。高頻度のアプリケーションdeploy、imperativeなdata migration、一度きりのbootstrapまで無理に含めると、stateとgraphが不安定になり得る。各変更のlifecycleとrollback特性に合うツールを選ぶ。

安全なTerraformはHCLの技巧より境界設計から生まれる。moduleはポリシー境界、stateはセキュリティ資産、planは変更契約、pipeline identityは実行権限として扱わなければならない。
