---
title: "GitHub Actions CI/CD設計：高速な自動化より先に信頼境界を"
date: 2026-07-21 09:20:00 +0900
categories: [Platform Engineering, CI-CD]
tags: [github-actions, ci-cd, supply-chain, automation, security]
description: GitHub Actionsのworkflow・job・runnerの信頼境界を理解し、permissions、secrets、environments、matrix、cache、concurrencyを安全に設計します。
lang: ja-JP
translation_key: github-actions-ci-cd-design
hidden: true
---

{% include language-switcher.html %}

## 問題：通過するworkflowと信頼できるpipelineは異なる

CI/CDは反復作業を減らすが、設計を誤るとリポジトリで最も強い権限を外部入力に結び付けてしまう。workflowはソースコードをチェックアウトし、dependencyをダウンロードし、テストを実行し、ときには本番環境まで変更する。つまり、小さなYAMLファイルがビルドシステムであると同時にcredential brokerであり、デプロイのコントロールプレーンでもある。

「テストが自動で走る」という段階で止まると、次の問題が残る。

- すべてのjobが書き込み可能なデフォルトトークンを共有する。
- fork PRの信頼できないコードがsecretへアクセスする。
- 同じbranchの古いデプロイが最新のデプロイを上書きする。
- cacheとartifactが出所確認なしに実行段階へ渡される。
- 複数のmatrix組み合わせのうち、実際に意味のある検証を行うものが一つしかない。
- buildとdeployが結合され、同じartifactを昇格できない。

優れたpipelineの目標は、単なる緑色のチェックではなく、**同じ入力に対する再現可能な結果、最小権限、検証済みartifactの一貫した昇格、失敗時の明確な中断点**である。

## メンタルモデル：workflowは権限とデータを渡すDAGである

GitHub Actionsの主な単位を区別する。

- **event**：`pull_request`、`push`、`workflow_dispatch`のように実行を開始する外部入力
- **workflow**：eventとjobグラフを定義したファイル
- **job**：一つのrunnerで実行されるstepの集合。job間でファイルシステムはデフォルトでは共有されない。
- **step**：actionまたはshell commandを1回実行する単位
- **runner**：コードを実行する使い捨てまたはself-hostedのcompute
- **artifact**：jobやworkflow間で明示的に受け渡し、保存する成果物
- **cache**：再生成可能なdependencyを高速に復元するための最適化手段
- **environment**：デプロイ対象、承認、保護ルール、環境secretを束ねる制御境界

各境界で四つの問いを立てる。

1. 入力を誰が制御するのか？
2. どのコードが実行されるのか？
3. どのtokenとsecretが露出するのか？
4. 成果物の出所と完全性をどのように確認するのか？

### CIとCDを分離する

CIはコミットの品質を検証し、immutable artifactを作る。CDはすでに検証済みのartifactを特定の環境へ昇格する。環境ごとに再度buildすると、「テストしたバイナリ」と「本番へデプロイしたバイナリ」が異なる可能性がある。

```text
commit -> test -> build -> scan -> signed artifact
                                      |
                                      +-> staging deploy
                                      +-> production approval -> production deploy
```

デプロイの識別子には、branch名よりcommit SHA、image digest、artifact digestのような不変の値を使うべきである。

## 実践パターン：PRは低い権限で検証し、デプロイは別の境界で実行する

### 最小権限のCI workflow

次の例はPythonプロジェクトの基本構成である。リポジトリのlock fileとテストコマンドに合わせて調整する。

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

読みやすい例にするため、公式actionのmajor tagを使用した。高いassuranceが必要なリポジトリでは、レビュー済みの**full commit SHA**にactionを固定し、dependency updateツールで更新する。third-party actionはmarketplaceの星評価ではなく、source、保守主体、release provenance、要求権限を確認する。

matrixは「多いほどよい」ものではない。サポート契約で実際に保証すべき軸だけを含める。

- ライブラリ：サポートする最小・最新runtimeの組み合わせ
- アプリケーション：本番と同じ主要環境と、互換性リスクが高い環境
- GPU・大規模integration：PRごとのsmoke testとスケジュール実行する全体testを分離

`fail-fast: false`なら、一つの組み合わせが失敗しても残りの互換性情報を得られる。一方、コストの高いjobでは高速なlint/unit jobを先行させ、`needs`でブロックする方がよい。

### cacheとartifactを区別する

| 項目 | cache | artifact |
|---|---|---|
| 目的 | 再生成可能な入力の高速化 | ビルド結果・レポートの受け渡しと保存 |
| miss時 | 遅くなっても正常に実行できる必要がある | 後続段階で必要なら失敗しなければならない |
| キー | OS、runtime、lock file hashなど | commit SHA、build ID、digestなど |
| 信頼 | 汚染の可能性を想定して検証 | provenanceとdigestを併せて管理 |

cacheから復元したdependencyもlock fileとpackage hashで検証する。cacheに実行可能な任意のスクリプトや長期資格情報を入れてはならない。PRから書き込み可能なcacheが、保護branchの高権限jobへ流れ込まないようeventとscopeを確認する。

artifactは一度buildしたものを環境間で昇格する。保存期間を業務目的に合わせて制限し、デプロイ前にdigestを検証する。test reportとcoverageは観測資料であり、デプロイbinaryの代わりではない。

### デプロイjobはenvironmentと短期資格情報を使用する

本番デプロイはPR workflowではなく、保護branch/tagで実行する別workflow、または厳密に分離したjobとして設ける。次は構造を示すskeletonである。`<...>`の値とaction SHAは、該当するcloudおよびリポジトリ設定に置き換える必要がある。

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

要点は次のとおりである。

- `id-token: write`は、OIDC交換を必要とするjobだけに付与する。
- cloud trust policyでは、リポジトリ、branch/tag、environment claimを制限する。
- 長期access keyをrepository secretへ保存する代わりに、短期credentialを発行する。
- `production` environmentに承認者、許可するbranch/tag、環境別secretを設定する。
- 本番デプロイでは`cancel-in-progress: false`を指定し、deployツール自体も重複実行に対して安全にする。

OIDCを使えば自動的に安全になるわけではない。cloud側のtrust conditionが広すぎると、どのbranchのworkflowでも本番roleを取得できる。

### secretは「値」より露出経路を管理する

secretはGitHub UIへ保存すれば終わりではない。

- shell argumentはprocess listingやdebug logに現れる可能性がある。
- secretを変形・エンコードすると、maskingが認識できない場合がある。
- エラーオブジェクト、test fixture、artifactへ値が複製される場合がある。
- self-hosted runnerのディスクやprocessが、後続jobに痕跡を残す場合がある。

必要なstepのenvironment variableとしてのみ渡し、値全体を出力しない。

{% raw %}
```yaml
- name: Call protected service
  env:
    SERVICE_TOKEN: ${{ secrets.SERVICE_TOKEN }}
  run: python scripts/publish.py
```
{% endraw %}

fork PRには保護対象のsecretを提供しないことが基本である。とりわけ`pull_request_target`はbase branchのコンテキストで権限を得られるため、信頼できないPRコードをcheckoutして実行するパターンと組み合わせてはならない。label・commentなどのmetadata処理とコード実行を別々のworkflowに分ける。

### 式の挿入とshellの引用を分離する

PRタイトルのようなユーザー入力を`run`ブロックへ直接展開すると、shell codeになる可能性がある。値はenvironment経由で渡し、shell側で引用する。

危険な形：

{% raw %}
```yaml
- run: echo "${{ github.event.pull_request.title }}"
```
{% endraw %}

より安全な形：

{% raw %}
```yaml
- name: Print PR title as data
  env:
    PR_TITLE: ${{ github.event.pull_request.title }}
  shell: bash
  run: printf '%s\n' "$PR_TITLE"
```
{% endraw %}

可能ならユーザー入力の出力自体を減らし、入力形式の検証とallowlistを設ける。

### concurrencyポリシーはCIとCDで異なる

PR CIでは、新しいcommitが届くと以前の実行結果の価値が下がるため、キャンセルが効率的である。

{% raw %}
```yaml
concurrency:
  group: ci-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```
{% endraw %}

デプロイでは、実行中の変更を突然キャンセルすると環境が中間状態のまま残る可能性がある。同じ環境へのdeployを直列化し、キャンセルではなくqueueingを基本とする。アプリケーションのデプロイツールはidempotency、timeout、rollbackまたはroll-forwardをサポートしなければならない。

## 検証チェックリスト

workflow変更PRで確認する項目：

- [ ] triggerが必要なeventとbranchにだけ反応する。
- [ ] 最上位の`permissions`が読み取り専用であり、書き込み権限は必要なjobだけにある。
- [ ] fork PRと信頼できないコードは、secret・デプロイcredentialへアクセスしない。
- [ ] actionを信頼できるsourceのレビュー済みSHAに固定するポリシーがある。
- [ ] dependencyはlock fileとhashで検証される。
- [ ] cache missでもビルドが正しく成功する。
- [ ] artifactはcommit/digestと紐付き、環境ごとに再buildしない。
- [ ] environment承認とcloud trust policyがbranch/tagの範囲を制限する。
- [ ] CIは古い実行をキャンセルし、CDは同じ環境への変更を直列化する。
- [ ] すべてのjobに妥当な`timeout-minutes`がある。
- [ ] 失敗logとartifactにsecret・個人情報が含まれない。
- [ ] branch protectionのrequired check名がworkflow変更後も有効である。

静的検査では、workflow schema lint、dependency review、secret scan、actionポリシー検査を組み合わせる。ただし、lint通過は権限設計が安全である証明にはならないため、eventごとの脅威モデルも併せて検討する。

## 失敗例と限界

### `permissions: write-all`で問題を解決する

権限エラーは消えるが、侵害の範囲が拡大する。必要なAPI操作を確認し、特定のscopeだけをjobレベルで追加する。

### tagだけをpinすればサプライチェーンが完全に固定されると考える

major/version tagは移動できる。full commit SHAはより強い固定点だが、そのcommitのsourceとreleaseプロセス自体を検討する必要がある。pinningには、updateの自動化と脆弱性対応を伴わせなければならない。

### cacheを信頼できるbuild outputとして使用する

cacheは最適化であり、削除されても正確性が保たれなければならない。デプロイ対象は明示的なartifactとprovenanceで渡す。

### self-hosted runnerをコスト削減手段としてしか見ない

self-hosted runnerには、ネットワークアクセス、長期保存ディスク、cloud metadataなど、より大きな攻撃対象領域が存在する場合がある。public/fork PRを永続runnerで実行せず、ephemeralな隔離、image初期化、egress制限、patchingを運用する。

### すべてのテストをすべてのPRで実行する

検証が遅くなると、開発者は迂回したり大きなbatchを作ったりする。高速な必須gate、変更経路に基づくintegration、スケジュール実行する全体回帰、デプロイ後検証という形でtest portfolioを階層化する。ただし、path filterが実際のdependencyを見落とさないよう保守的に設計する。

GitHub ActionsはYAML構文の問題ではなく、信頼境界の設計問題である。event、code、credential、artifact、environmentを分離して考えれば、どの自動化が危険かをはるかに早く発見できる。
