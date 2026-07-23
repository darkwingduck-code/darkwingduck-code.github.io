---
title: "契約優先のAPI設計：エラー、バージョン、冪等性と非同期ジョブ"
date: 2026-07-21 10:30:00 +0900
categories: [Software Engineering, API Design]
tags: [api, openapi, idempotency, schema, pagination, versioning]
description: APIを関数の集合ではなく長期的に進化する契約として捉え、リクエスト・レスポンス・エラー・再試行・バージョンを設計する方法を扱います。
lang: ja-JP
translation_key: api-contract-idempotency
hidden: true
---

{% include language-switcher.html %}

APIの品質はendpointの数ではなく、**呼び出し側が成功、失敗、再試行を予測できるか**で判断すべきである。サーバー実装は変わっても、契約は複数のクライアントと自動化に長く残る。

## 契約は成功レスポンスより広い

1つのoperationの契約には、最低限次を含める。

- methodとpath
- 認証・権限要件
- path/query/header/bodyのスキーマ
- 単位、タイムゾーン、範囲、nullable規則
- 成功ステータスコードとレスポンススキーマ
- エラーコードと再試行可能性
- idempotencyと同時実行規則
- rate limitとpagination
- timeoutまたは非同期処理方式

OpenAPIのような機械可読仕様は、文書生成だけのためのファイルではない。schema検証、client生成、contract test、breaking-change検査を結び付ける基準点である。

## リソースとジョブを区別する

名詞形のリソースは状態を表し、HTTP methodは意図を表す。

```text
GET    /v1/jobs/{job_id}
POST   /v1/jobs
PATCH  /v1/jobs/{job_id}
DELETE /v1/jobs/{job_id}
```

数分かかる処理を、同期HTTP接続のまま最後まで待たせない。

1. `POST /v1/jobs`が入力を検証してジョブを登録する。
2. サーバーは`202 Accepted`と`job_id`、状態URLを返す。
3. クライアントは状態をpollingするか、webhook/eventを受け取る。
4. 状態は`queued → running → succeeded | failed | cancelled`のように明示する。

状態遷移は一方向であるべきで、失敗理由と再試行可能かどうかを区別する。

## 入力は境界で厳格に検証する

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

重要なのはYAML構文ではなく方針である。

- 未知のフィールドを拒否するか無視するかを決める。
- 欠落と明示的な`null`を区別する。
- 数値の単位と許容範囲を、名前・説明・検証に反映する。
- 時刻はoffsetを含む標準形式で交換し、内部基準を定める。
- enumに新しい値を追加したとき、古いclientがどう反応するかを考慮する。

## エラーも安定したスキーマである

人間向け文章だけを返すと、clientは文字列を解析することになる。

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

- `code`は機械が分岐に使う安定した識別子である。
- `message`は利用者または運用者が読む。
- `details`はフィールドごとの問題を構造化する。
- `request_id`はサポートとtraceの連携に使う。
- 内部stack trace、SQL、パス、秘密値を外部へ返さない。

## POSTの再試行にはidempotency keyが必要である

クライアントがリクエストを送信した後、レスポンスを受け取る前に接続が切れると、ジョブが作成されたか分からない。無条件にPOSTし直すと重複作成される可能性がある。

```text
Idempotency-Key: client-generated-unique-key
```

サーバーの基本フローは次のとおりである。

1. 認証主体とkeyの組み合わせで既存記録を探す。
2. 初回ならリクエストbodyの正規化済みhashとともに処理結果を保存する。
3. 同じkeyと同じbodyなら保存済み結果を返す。
4. 同じkeyで異なるbodyなら競合として拒否する。
5. 保持期間と同時リクエストの処理規則を文書化する。

データベースのunique constraintなしにアプリケーションの「先に検索」だけを使うと競合状態が生じる。

## 同時更新には条件付きリクエストが必要である

2人の利用者が同じリソースを読み、変更すると、後のwriteが先の変更を上書きし得る。version numberまたは`ETag`を使ったoptimistic concurrencyが一般的な解決策である。

```text
GET /v1/items/42
ETag: "version-7"

PATCH /v1/items/42
If-Match: "version-7"
```

バージョンが変わっていれば、サーバーは競合を通知し、クライアントに最新状態を再取得させる。

## paginationはデータ変更に耐えなければならない

大きな一覧を一度に返さない。offset paginationは単純だが、前方のデータが挿入・削除されると重複や欠落が生じ得る。変更の多い大規模一覧には、安定したソートキーを用いるcursor paginationが適している。

```json
{
  "items": [],
  "next_cursor": "opaque-cursor",
  "has_more": false
}
```

cursorはopaqueとして扱い、ソート順、page size上限、filterとcursorの組み合わせ規則を契約に含める。

## バージョンは最後の手段ではなく変更方針である

変更を3種類に分ける。

- 互換：optionalフィールド追加、新規endpoint追加
- 条件付き互換：enum値追加、制限緩和
- 非互換：フィールド削除・型変更・意味変更

非互換変更は明示的な新バージョンまたは並行operationへ移す。deprecation通知、観測期間、client利用量、終了日程を合わせて管理する。URLにバージョン番号を付けるだけでは変更管理は完了しない。

## Contract testとデプロイゲート

- 仕様が有効か検査する。
- サーバーのレスポンスが仕様と一致するかテストする。
- 代表clientが新仕様から生成・コンパイルできるか確認する。
- 以前のバージョンとの差分からbreaking changeを検査する。
- 認証欠落、権限不足、rate limit、validation errorをテストする。
- 同一idempotency keyによる同時リクエストをテストする。
- デプロイ後に主要endpointをsmoke testする。

## 検証チェックリスト

- [ ] リクエストとレスポンスだけでなく、エラースキーマも明示されている。
- [ ] 単位、タイムゾーン、nullable、enum拡張方針が明確である。
- [ ] 副作用を持つPOSTの重複防止戦略がある。
- [ ] 長時間処理は状態リソースとして分離される。
- [ ] 同時更新によるlost updateを防止する。
- [ ] paginationのソートが決定的で、cursorがopaqueである。
- [ ] 非互換変更の検出がCIに含まれている。
- [ ] stack traceと内部実装情報が外部エラーへ露出しない。

## よくある失敗

- すべての結果を`200 OK`と自由形式JSONで返す。
- 再試行可能なエラーと永続的エラーを区別しない。
- client timeout後もサーバーがジョブを作成したのに重複防止がない。
- 同じフィールドがendpointごとに異なる単位やタイムゾーンを持つ。
- レスポンスフィールドを削除して「文書だけ修正」する。
- offset pagination中にデータが変わり、欠落を生む。

優れたAPIは実装詳細を隠す一方、**呼び出し側が安全に失敗し再試行できるだけの動作を明示する。**

## 参考資料

- [OpenAPI Specification](https://spec.openapis.org/oas/latest.html)
- [RFC 9110 — HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html)
