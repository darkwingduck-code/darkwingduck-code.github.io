---
title: "再現可能で安全なDockerイメージ：build contextからnon-rootまで"
date: 2026-07-21 09:40:00 +0900
categories: [Platform Engineering, Containers]
tags: [docker, containers, reproducibility, supply-chain, security]
description: Dockerのlayerとbuild contextを基準に、multi-stage build、dependencyの固定、healthcheck、non-root実行、イメージ検証手順を設計します。
lang: ja-JP
hidden: true
translation_key: docker-reproducible-secure-images
---

{% include language-switcher.html %}

## 問題：「自分のコンピュータでは動く」をイメージ内へ持ち込むこともある

コンテナは実行環境をパッケージ化するが、自動的に再現性とセキュリティを保証するわけではない。`latest` base image、lockされていないdependency、大きすぎるbuild context、rootユーザー、イメージへコピーされたsecretをそのままにすれば、環境差と攻撃対象領域まで一緒にパッケージ化することになる。

次の要因により、同じDockerfileから作られた二つのイメージでも同一にならないことがある。

- build時点でbase tagが異なるdigestを指していた。
- package indexが新しいdependencyを選択した。
- ローカルの一時ファイルがbuild contextに含まれた。
- CPU architectureに応じて異なるnative wheelを取得した。
- build metadataとtimestampが異なった。

したがって、目標を区別する必要がある。

1. **機能的再現性**：同じsourceとlockから同じ動作が得られる。
2. **dependency再現性**：同じbaseとpackage artifactが選択される。
3. **bit-for-bit再現性**：生成されたimage digestまで一致する。

一般的なサービスでは最初の二つから達成し、サプライチェーン上の要件が高ければdeterministic buildとprovenanceまで拡張する。

## Mental model：imageは不変のlayer、containerは実行状態である

Docker buildの主要な構成要素は次のとおりである。

- **build context**：builderへ渡されるファイルの集合
- **Dockerfile instruction**：layerとimage metadataを作る段階
- **image**：content-addressed layerとconfigからなる不変の集合
- **container**：imageにwritable layer、process、namespace、resource limitを組み合わせた実行インスタンス
- **registry**：image manifestとblobを保管・配布するリポジトリ

Dockerfileの各段階は、それ以前の状態、instruction、使用ファイルを入力としてcache keyを作る。頻繁に変わるsourceをdependencyのインストールより先に`COPY`すると、小さなコード変更でもdependency layerが無効になる。

tagとdigestも異なる。

```text
registry.example.invalid/service:1.4    # 이동 가능한 이름
registry.example.invalid/service@sha256:<DIGEST>  # 불변 content 주소
```

人はversion tagでreleaseを見つけ、デプロイシステムは検証済みのdigestを使用する組み合わせが望ましい。

### コンテナ分離はセキュリティ境界の一層である

一般に、コンテナはVMのような独立したkernelを持たない。rootless runtime、seccomp/AppArmor/SELinux、capabilityの削除、read-only filesystem、network policy、host patchingを組み合わせて使う必要がある。イメージで`USER`をnon-rootに指定することは重要なデフォルトだが、完全なsandboxではない。

## 実践パターン：小さなcontext、lockされた入力、multi-stage、最小限の実行権限

### build contextから制限する

`.dockerignore`の例：

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

`.dockerignore`はimageサイズを小さくするだけのツールではない。builderへ転送する範囲を狭め、secretや不要なファイルが`COPY . .`に混入するのを防ぐ。実際のruntimeでtestやdocsが必要なプロジェクトなら、やみくもに除外せず、buildの目的ごとにcontextを設計する。

`.env`を除外していても、すでにGitへcommitした場合やbuild argumentとして渡した場合は露出しうる。secret scannerとcredential rotationが別途必要である。

### Pythonサービスのmulti-stage Dockerfile

次の例は、compilerを必要とせず、hashがlockされたbinary wheelを使うサービスのひな型である。

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

このパターンの意図は次のとおりである。

- dependency lockをsourceより先にコピーし、cacheの境界を安定させる。
- `--require-hashes`により、lockに存在しないpackage artifactを拒否する。
- build用のdownload段階とruntimeを分離する。
- 数値のUID/GIDによりruntimeユーザー解釈の違いを減らす。
- shell formではなくexec formの`CMD`を使い、signal伝達を単純化する。
- healthcheckがサービスのprocessの存在ではなくHTTP応答を確認する。

CIではbaseをdigestに固定する。

```bash
docker build \
  --pull \
  --build-arg 'PYTHON_IMAGE=python:3.12-slim@sha256:<REVIEWED_BASE_IMAGE_DIGEST>' \
  --tag 'service:<SOURCE_REVISION>' \
  .
```

`<...>` placeholderは、実際にレビューした値へ置き換える必要がある。digestの固定はupdateを止めることではなく、変更をPRとして可視化することである。base imageの脆弱性修正が公開されたら、自動化されたdigest update PRをレビューして再buildする。

native extensionをsourceからcompileする必要がある場合は、builder stageにcompilerとheaderをインストールし、生成したwheelだけをruntimeへコピーする。compiler toolchainとOS package versionも入力であるため、lockとprovenanceの範囲に含める。

### lock fileは範囲ではなく正確なartifactを表す

次のように範囲だけを指定したファイルは、時間が経つと異なる結果を選択しうる。

```text
framework>=1.0
client-library
```

production lockはtransitive dependencyまでversionとhashを固定し、自動updateツールで新しいlockを作成してからテストする。人がdependency treeの一部だけを直接変更すると、解決結果が不整合になることがある。

OS packageにも同じ原則が当てはまる。buildのたびに`apt-get upgrade`を実行する方法は最新になりうるが、再現可能な入力ではない。次のうち、システム要件に合うポリシーを選択する。

- 信頼するbase image digestにOS packageの集合を含め、baseを頻繁に更新
- package snapshot repositoryとexact versionを使用
- 組織のhardened base image pipelineを使用

脆弱性対応は「常に最新」と「永久に固定」の二者択一ではない。**固定した入力を定期的に更新し、検証するプロセス**である。

### build secretをlayerとhistoryに残さない

避けるべき形：

```dockerfile
ARG PACKAGE_TOKEN
ENV PACKAGE_TOKEN=${PACKAGE_TOKEN}
RUN python -m pip install --index-url "https://${PACKAGE_TOKEN}@<PRIVATE_INDEX>/simple" <PACKAGE>
```

build argとenvironmentは、image history、metadata、log、cache経路に露出することがある。BuildKit secret mountを使用し、instruction内でも値を出力しない。

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

例のscriptでもURL、exception、debug logへtokenを残してはならない。可能なら長期tokenよりも、build serviceが短期間だけ発行するcredentialを使う。

### runtimeをread-onlyかつ最小capabilityで実行する

イメージのnon-rootというデフォルトにruntime policyを加える。

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

サービスがファイルを書き込む必要がある場合、root filesystem全体を書き込み可能にせず、`/tmp`、upload、cacheなど必要なmountだけを明示する。`--privileged`、host socket mount、host networkは分離モデルを大きく弱めるため、便宜的なオプションとして使わない。

credentialをimageや通常のenvironment fileへbakeしない。デプロイプラットフォームのsecret storeとworkload identityを使い、secretは必要なprocessだけにメモリまたは制限付きmountで渡す。

### healthcheckではlivenessとreadinessを区別する

Dockerfileの`HEALTHCHECK`は一つの状態しか表現しない。オーケストレーターでは通常、次のように分ける。

- **startup**：初期化が完了したか？
- **liveness**：processを再起動すべきほど停止しているか？
- **readiness**：今、新しいtrafficを受け入れてよいか？

readinessをすべての外部dependencyへ強く結び付けると、一時的な下流サービス障害によって全replicaがtrafficから外れ、連鎖障害を拡大することがある。endpointは実際のtraffic処理能力を反映すべきだが、再起動では解決しない外部障害をliveness失敗にしてはならない。

### imageをbuildした後に証拠を残す

検証pipelineの出力には、imageだけでなく次も含める。

- source revisionとbuild invocation
- base imageと最終image digest
- SBOM
- vulnerability scanの結果と例外の有効期限
- test結果
- build provenanceと署名/attestation

デプロイ時にtagを再resolveせず、承認済みのdigestを使う。registry retentionによってdigestが参照するblobがデプロイ期間より前に削除されないよう、ポリシーを合わせる。

## 検証チェックリスト

build前：

- [ ] `.dockerignore`がGit、secret、local cache、不要なartifactを除外している。
- [ ] base imageとlanguage dependencyが、レビュー済みのversion/digestとhashでlockされている。
- [ ] lock updateが自動テストと脆弱性レビューを通過している。
- [ ] build secretが`ARG`、`ENV`、URL、logに含まれていない。
- [ ] sourceより先にdependency manifestをコピーし、cacheの境界を作った。

image review：

- [ ] runtime imageにcompiler、package manager cache、test credentialがない。
- [ ] `USER`がnon-rootで、固定UID/GIDを使用している。
- [ ] entrypointがsignalを受け取り、正常終了できる。
- [ ] healthcheckが高速でtimeoutを持ち、副作用がない。
- [ ] イメージサイズだけでなく、layerの内容、SBOM、脆弱性を検査した。
- [ ] multi-architecture imageを実際の対象architectureでテストした。

runtime review：

- [ ] immutable digestでデプロイする。
- [ ] root filesystemはread-onlyで、writable mountを最小化した。
- [ ] capabilityの削除、no-new-privileges、seccompの各層が適用されている。
- [ ] CPU・memory・PID制限とgraceful shutdown時間がある。
- [ ] secretはruntime identityまたはsecret storeから渡される。
- [ ] readiness、liveness、startup probeの意味が区別されている。

## 失敗例と限界

### imageサイズだけを見てAlpineを選ぶ

サイズが小さいからといって、リスクが小さい、あるいは運用が速いとは限らない。libcの違い、native wheelの欠如、DNS・timezoneの動作、debuggingの難しさを併せて比較する。運用互換性を検証した最小限のbaseを選ぶ。

### multi-stageなら自動的に安全だと考える

最後のstageで`COPY --from=builder / /`のようにfilesystem全体をコピーすると、build secretとtoolchainが再び入り込む。必要なartifactのパスだけをコピーする。

### healthcheckで認証・書き込み・重いqueryを実行する

probeは頻繁に実行される。遅いprobeや状態を変えるprobeは、それ自体が障害の原因になる。限られた時間内に中核となる準備状態だけを確認する。

### scannerの結果を絶対的な判定として使う

scannerはpackage inventoryとadvisoryの品質に依存する。false positiveも未発見の脆弱性も起こりうる。reachable code、exploitability、compensating controlをレビューしつつ、例外には所有者と有効期限を設定する。

### containerだけで再現性を完成させようとする

外部database schema、feature flag、secret version、hardware driver、kernel、network dependencyはimageの外側にある。デプロイmanifest、migration、IaC、configuration version、data contractまで一緒に追跡する必要がある。

よいDockerfileは、単に短いファイルではない。どの入力から何を作り、runtimeに何が不要であり、その結果をどの権限で実行するのかを説明できるbuild契約である。
