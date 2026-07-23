---
title: "Pythonコードを運用可能なソフトウェアにするための最低基準"
date: 2026-07-21 10:10:00 +0900
categories: [Software Engineering, Python]
tags: [python, packaging, testing, typing, logging, reproducibility]
description: スクリプトを再現可能でテスト可能、かつ観測可能なPythonアプリケーションへ発展させるための実践的な基準を整理します。
lang: ja-JP
hidden: true
translation_key: python-production-baseline
---

{% include language-switcher.html %}

Pythonファイルが一度実行できることと、別の環境でも安全に繰り返し実行できるソフトウェアになることは、まったく別の問題だ。運用可能なコードの核心は、華やかなフレームワークではなく、**入力・出力・依存関係・失敗が明示されているか**にある。

## 1. まず境界を作る

最も保守しにくいのは、計算、ファイルアクセス、ネットワーク要求、環境変数の読み込み、ログ出力が一つの関数に混在したコードだ。次の三層に分ければ、テストや置き換えが容易になる。

1. **ドメインロジック**：同じ入力に対して同じ出力を返す純粋な計算
2. **アダプター**：ファイル、データベース、HTTP、メッセージキューとの通信
3. **エントリーポイント**：設定を読み、オブジェクトを組み立て、終了コードを決定

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class Reading:
    value: float
    lower: float
    upper: float


def classify(reading: Reading) -> str:
    if reading.lower > reading.upper:
        raise ValueError("lower must not exceed upper")
    if reading.value < reading.lower:
        return "low"
    if reading.value > reading.upper:
        return "high"
    return "normal"
```

この関数はファイルも時計もネットワークも参照しない。そのため境界値を素早く検証でき、失敗の原因も限定される。

## 2. プロジェクト構造は小さく始め、役割を分離する

```text
project/
├── pyproject.toml
├── README.md
├── src/
│   └── app/
│       ├── __init__.py
│       ├── domain.py
│       ├── adapters.py
│       └── cli.py
└── tests/
    ├── unit/
    └── integration/
```

`src`レイアウトは、リポジトリのルートが偶然importパスとなり、パッケージングの不具合を覆い隠す事態を減らす。`pyproject.toml`には、ビルドシステム、プロジェクトのメタデータ、ランタイム依存関係、開発ツールの設定をまとめる。

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "example-app"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["httpx>=0.27,<1"]

[project.optional-dependencies]
dev = ["pytest>=8,<9", "ruff>=0.5,<1", "mypy>=1.10,<2"]
```

バージョン範囲はあくまで例である。実際のプロジェクトでは、サポートするPythonバージョンとロックファイル戦略を一つに定め、CIとデプロイで同じものを使わなければならない。

## 3. 設定と機密情報を分離する

設定には三つの種類がある。

| 種類 | 例 | 保存場所 |
|---|---|---|
| コードのデフォルト値 | バッチサイズ、タイムアウトのデフォルト値 | コードまたは公開設定ファイル |
| 環境別設定 | APIアドレス、ログレベル | 環境変数またはデプロイ設定 |
| 機密情報 | トークン、パスワード、秘密鍵 | シークレット管理システム |

`DEBUG=true`のような値も文字列である。暗黙の型変換に頼らず、起動時に一度検証する。

```python
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    api_base_url: str
    timeout_seconds: float


def load_settings() -> Settings:
    base_url = os.environ["API_BASE_URL"]
    timeout = float(os.getenv("HTTP_TIMEOUT_SECONDS", "10"))
    if timeout <= 0:
        raise ValueError("HTTP_TIMEOUT_SECONDS must be positive")
    return Settings(api_base_url=base_url, timeout_seconds=timeout)
```

機密値を例外メッセージ、CLI引数、Git、テストfixture、ノートブック出力に残してはならない。`***`で隠すだけでは不十分であり、そもそもログフィールドに入れないほうが安全だ。

## 4. 型は実行の代わりではなく、契約を説明する

型ヒントは入出力の意図を素早く伝え、リファクタリング時の誤りを減らす。しかし、外部から入ってきたJSON、CSV、環境変数は型ヒントだけでは検証されない。**信頼境界ではランタイム検証、内部では型検査**という二層が必要だ。

- `Any`は段階的な移行区間だけに限定する。
- `dict[str, object]`より意味のある`dataclass`、`TypedDict`、モデル型を使う。
- `None`が正常状態なのかエラー状態なのかを明確にする。
- 単位が異なる数値は名前または別の型で区別する。

## 5. ログは文章ではなく、イベントの構造である

運用ログは、後からフィルタリングして集計できなければならない。

```python
import logging

logger = logging.getLogger(__name__)


def handle(job_id: str) -> None:
    logger.info("job_started", extra={"job_id": job_id})
    try:
        run_job(job_id)
    except TimeoutError:
        logger.exception("job_timed_out", extra={"job_id": job_id})
        raise
```

最低限の共通フィールドは、`event`、`timestamp`、`severity`、`service`、`request_id`または`job_id`、`duration`、`outcome`である。生のリクエスト本文や認証ヘッダーを丸ごと記録してはならない。

## 6. テストはリスクの層に沿って配置する

```python
import pytest

from app.domain import Reading, classify


@pytest.mark.parametrize(
    ("value", "expected"),
    [(9.0, "low"), (10.0, "normal"), (20.0, "normal"), (21.0, "high")],
)
def test_classify_boundaries(value: float, expected: str) -> None:
    assert classify(Reading(value=value, lower=10.0, upper=20.0)) == expected
```

- 単体テスト：純粋なロジック、境界値、不変条件
- 統合テスト：データベース・ファイル・HTTPアダプター
- 契約テスト：要求・応答スキーマとエラー形式
- スモークテスト：デプロイ後に主要経路が動作しているか

すべての実装詳細をmockすると、実際の接続エラーを見逃す。反対に、すべてのテストをE2Eにすると遅くなり、原因の把握も難しい。失敗コストと変更頻度に合わせて層を分ける。

## 7. 終了と再試行もAPIである

CLIやバッチジョブは、成功と失敗を終了コードで区別しなければならない。ネットワークの再試行には最大回数、指数backoff、jitter、全体のdeadlineが必要だ。副作用を伴う処理は、idempotencyを保証せずに自動再試行してはならない。

```python
def main() -> int:
    try:
        settings = load_settings()
        execute(settings)
    except ConfigurationError as exc:
        logger.error("invalid_configuration", extra={"reason": str(exc)})
        return 2
    except Exception:
        logger.exception("unhandled_failure")
        return 1
    return 0
```

## 運用前チェックリスト

- [ ] 新しい環境で、文書に記載されたコマンドだけを使ってインストール・実行できる。
- [ ] Pythonバージョンと依存関係が宣言され、ロック戦略がある。
- [ ] 入力スキーマ、単位、範囲、欠損値ポリシーが検証される。
- [ ] 機密値がコード・Git履歴・ログ・テストデータに含まれていない。
- [ ] 主要なドメインロジックは外部I/Oなしでテストされる。
- [ ] タイムアウト、retry budget、終了コードが明示されている。
- [ ] 構造化ログで一つの要求またはジョブを追跡できる。
- [ ] リリース成果物をクリーンな環境で再度作成できる。

## よくある失敗

- ノートブックでしか成功せず、パッケージのimportとCLIが壊れる。
- グローバル状態とimport時の副作用により、テスト順序によって結果が変わる。
- `except Exception: pass`によって失敗を成功のように扱う。
- 常に最新版をインストールして、昨日の環境を再現できない。
- ログを大量に残したものの、識別子とイベント名がなく検索できない。

運用可能性はコードの行数ではなく、**再インストールし、失敗を再現し、安全に復旧できる度合い**で判断すべきだ。

## 参考資料

- [Python Packaging User Guide — Writing `pyproject.toml`](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/)
- [Python Packaging User Guide — Packaging Python Projects](https://packaging.python.org/tutorials/packaging-projects/)
