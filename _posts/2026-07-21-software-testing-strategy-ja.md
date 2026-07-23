---
title: "テストピラミッドより重要なリスクベースのソフトウェア検証戦略"
date: 2026-07-21 10:40:00 +0900
categories: [Software Engineering, Testing]
tags: [testing, pytest, contract-testing, property-testing, integration-testing, quality]
description: 単体・統合・契約・E2Eテストをリスクに応じて組み合わせ、優れたoracleと不変条件を設計する方法を整理します。
lang: ja-JP
hidden: true
translation_key: software-testing-strategy
---

{% include language-switcher.html %}

テストの目的はコード行を実行することではなく、**重大な失敗をリリース前に発見し、変更後も契約が維持されているというエビデンスを作ること**である。coverageが高くても、assertionが弱い、または実際のリスクに触れていなければ、信頼性は低い。

## リスクからテストを逆設計する

まずfailure modeを書き出す。

| failure mode | 影響 | 適した検証 |
|---|---|---|
| 境界値の分類エラー | 誤った意思決定 | 単体・境界値テスト |
| DB schemaの不一致 | リクエスト全体の失敗 | 統合・migrationテスト |
| client/server契約の破損 | デプロイ後の連携失敗 | 契約テスト |
| 認証の迂回 | 権限のないアクセス | セキュリティ・統合テスト |
| デプロイ設定の欠落 | サービス起動の失敗 | smoke test |
| 長いユーザーフローの破損 | 中核業務の停止 | 少数のE2Eテスト |

発生可能性、影響、検出難度が高い項目から自動化する。単純なgetterよりも、金額・権限・状態遷移・データ損失につながる経路を優先する。

## テスト層はそれぞれ異なる問いに答える

### 単体テスト

「小さなルールは、すべての重要な入力に対して正しいか」を迅速に確認する。I/Oを分離し、境界値、例外、不変条件に集中する。

### 統合テスト

「実際の構成要素は、同じ契約に基づいて通信できるか」を確認する。実際のデータベースエンジン、ファイル形式、serializer、HTTP adapterなど、mockによって隠され得る差異を検証する。

### 契約テスト

「providerとconsumerが合意したschemaと意味は維持されているか」を確認する。フィールド型、required/optional、エラーコード、backward compatibilityを検査する。

### E2Eテスト

「デプロイされたシステムで、ユーザーの中核的な成果を達成できるか」を確認する。遅く壊れやすいため、すべての画面を自動化するのではなく、価値の高い3～5個の経路から始める。

### デプロイ後の検証

health endpointが200を返すかだけを確認して終わらせない。中核dependencyへの接続、最小限のread/write、権限、version、background workerの状態を、安全なsynthetic transactionで点検する。

## 優れたテストではArrange–Act–Assertが明確である

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

一つのテストで多くの動作を扱いすぎると、失敗箇所が不明確になる。反対に、実装のprivate methodまで固定すると、正当なrefactoringでもテストが壊れる。外部から観測できる結果と中核的な不変条件を検証する。

## 例示ベーステストとproperty-based testを併用する

例示テストは読みやすいが、開発者が想定した事例しか扱わない。property-based testは、広い入力空間において常に守るべき性質を検査する。

例えば正規化関数なら、次の性質を考えられる。

- 出力が許容範囲内にある。
- 同じ入力を二度正規化しても結果が同じである。
- 入力順序を変えても、順序に依存しない集計結果は同じである。
- serialize後にdeserializeしても意味が保たれる。

数値計算では、許容誤差の根拠が必要である。無条件に大きな`epsilon`を使うとエラーを隠し、bitwise equalityだけを要求するとプラットフォーム差によって不安定になる。絶対誤差と相対誤差を、値の規模と問題の条件に合わせて組み合わせる。

## test doubleを正しく選ぶ

- stub：定められた値を返す。
- fake：単純だが動作可能な代替実装である。
- spy：呼び出し記録を観測する。
- mock：期待する相互作用を明示する。

ドメインルールのテストにはnetwork mockが有用である。しかし、SQL dialect、transaction、serializationといった実際の境界までmockすると、統合上のエラーを見逃す。「何を迅速に分離するのか」と「何を実物で確認すべきか」を分けて考える。

## 非決定性を制御する

不安定なテストは信頼を損なう。時刻、乱数、network、並列性、global stateを、制御可能なdependencyとして設計する。

```python
from datetime import datetime, timezone
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime: ...


class FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 1, 1, tzinfo=timezone.utc)
```

乱数seedを記録するだけでは、完全な決定性は保証されない。library version、並列実行、hardwareごとの演算、入力順序も結果に影響し得る。まず、必要とする再現性の水準を定める。

## データベーステストの要点

- 各テストは独立したデータとnamespaceを使用する。
- migrationを空のDBと旧versionのDBの双方に適用する。
- unique・foreign key・check constraintが実際に不正状態を防ぐか確認する。
- transaction rollbackだけに依存せず、background workerと別connectionを考慮する。
- 本番データをtest fixtureへコピーしない。

## 失敗を調査可能な状態にする

CIで失敗した場合、少なくとも次の情報を保存する。

- test nameとseed
- 入力fixtureまたは最小再現入力
- application/logical version
- 環境とdependency lockの情報
- 関連するlog・trace・screenshot
- 最初の失敗原因と、その後に派生した失敗の区別

無条件にrerunし、greenになれば通過とする方針はflaky testを隠す。隔離、原因分類、担当者、修正期限が必要である。

## 検証チェックリスト

- [ ] 最も損失の大きいfailure modeと、それを検出するテストが対応付けられている。
- [ ] 境界値の直下・境界値そのもの・直上を検査している。
- [ ] 例外だけでなく、失敗後に状態が保全されるか確認している。
- [ ] 実際のDB・serializer・HTTP境界を使う統合テストがある。
- [ ] schemaのbreaking changeをCIで検出する。
- [ ] 中核ユーザーフローだけを、安定したE2Eとして維持している。
- [ ] 時刻・乱数・外部dependencyの非決定性が制御されている。
- [ ] flaky testを自動rerunだけで覆い隠していない。
- [ ] デプロイ後のsmoke testとrollback判断基準がある。

## よくある失敗

- coverageの数値を品質目標だと誤認する。
- 同じ正常事例だけを繰り返し、境界・エラー・並行性を見落とす。
- 内部実装の呼び出し回数まで固定し、refactoringコストを高める。
- テスト間で実行順序とglobal stateを共有する。
- すべての外部境界をmockし、実際のschemaとtransactionのエラーを見落とす。
- E2Eで任意のsleepや画面座標に依存する。

テスト戦略における最終的な問いは「いくつ書いたか」ではなく、**「どのリスクを、どのエビデンスによって制御したか」**である。
