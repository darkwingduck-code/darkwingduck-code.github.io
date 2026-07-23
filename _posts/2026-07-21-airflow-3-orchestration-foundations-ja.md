---
title: "Airflow 3オーケストレーションの基礎：時間、状態、再実行可能性の設計"
date: 2026-07-21 10:10:00 +0900
categories: [Data Engineering, Orchestration]
tags: [airflow, orchestration, data-pipelines, idempotency, observability]
description: Airflow 3のDag・task・data intervalを基準に、XCom、Connection、Variable、retry、backfill、deferrable sensor、asset schedulingと運用検証を設計します。
lang: ja-JP
translation_key: airflow-3-orchestration-foundations
hidden: true
---

{% include language-switcher.html %}

## 問題：taskを順番につなぐだけでは運用可能なpipelineにならない

Airflowはbatch workflowを開発・スケジュール・観察するオーケストレーターである。実際の計算engineや大容量データの転送経路を代替するものではない。この境界を見失うと、次の問題が生じる。

- 実行時刻と処理対象期間を混同し、誤ったpartitionを読む。
- task再試行時にappendが繰り返され、データが重複する。
- dataframeをXComで渡してmetadata databaseが肥大化する。
- sensorがworker slotを長時間占有する。
- `catchup=False`を過去データの再処理禁止と誤解する。
- secretとruntime設定をDag sourceへ直接記述する。
- Dagは成功したのに成果物のfreshnessと品質は失敗する。

運用可能なAirflow workflowは、次の3つの問いに明確に答えなければならない。

1. このDag runは**どのデータ区間**を処理するのか。
2. 同じtaskを再実行しても**同じ最終状態**を作るか。
3. 失敗時にAirflowの状態だけでなく、**利用者向け成果物が正常か**をどう確認するか。

本稿のAirflow 3に関するAPIと動作は、執筆時点の[Apache Airflow stable 3.x公式ドキュメント](https://airflow.apache.org/docs/apache-airflow/stable/)を基準とする。minor versionとprovider versionによってpublic APIやoperator argumentが変わり得るため、実際にデプロイするversionの文書も併せて固定する。

## Mental model：Dag runは時間またはeventに対応するorchestration instanceである

### Dag、task、task instance、Dag runを区別する

- **Dag**：schedule、task、dependency、callbackを含むworkflow定義
- **task**：処理のtemplate。Operator、Sensor、TaskFlow `@task`などで宣言
- **Dag run**：特定の論理区間またはeventに対するDag実行instance
- **task instance**：特定のDag run内でtaskが実際に実行されるinstance

同じtask定義が毎日1回実行される場合、taskは1つだが、task instanceは日付別のDag runごとに作られる。retryは同じtask instanceの新しい試行であり、backfillは過去区間に新たなDag runを生成する処理である。

Airflow 3の作成用public interfaceは`airflow.sdk`を中心に提供される。Dagファイルから内部metadata modelを直接操作せず、public APIとprovider operatorを使う。基本概念は公式の[DagsとTasksの文書](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/)で確認できる。

### logical dateは実際の実行時刻ではない

時間ベースのscheduleには**data interval**がある。日次Dag runの処理区間が`[2026-01-01 00:00, 2026-01-02 00:00)`なら、schedulerは通常、その区間が終わってからrunを作成する。このrunのlogical dateはdata intervalの開始を表し、wall-clock上の実行開始時刻ではない。

公式の[Dag Runs文書](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/dag-run.html)では、scheduled runは該当data intervalの終了後に作成され、logical dateはdata intervalの開始を表すと説明している。したがって、taskで`now()`を使って処理partitionを選ぶと、queue遅延、retry、backfillの際に異なるデータを読む可能性がある。

時間ベースのtaskは、次の値を基準にすべきである。

- `data_interval_start`：含める区間の開始
- `data_interval_end`：含めない区間の終端
- `run_id`：同じintervalに対する手動再実行・backfill instanceの区別

区間を半開区間`[start, end)`に統一すると、境界eventの重複と欠落を減らせる。

### dependencyは実行順序であり、データ転送経路ではない

`extract >> transform`は、transformがextractの成功後に実行可能になるというcontrol dependencyを表す。大容量データがworker memory間で受け渡されるという意味ではない。

推奨data plane：

```text
task A -> object/table/stream에 데이터 기록
       -> XCom에는 URI, partition, row count, checksum만 기록
task B -> 해당 URI와 metadata를 받아 외부 저장소에서 읽기
```

Airflow metadata databaseはorchestration stateのための場所である。実際のdataset、model binary、dataframeは、目的に合ったobject storage、database、compute engineへ置く。

## 実践パターン：intervalベースのidempotent taskを先に作る

### 安全なlocal例でdata intervalとatomic publishを理解する

次のDagは`/tmp`配下にinterval別ファイルを作成し、同じintervalを再実行すると同一targetをatomic replaceする。学習・local test用であり、実運用ではobject storageのconditional write、table transaction、atomic renameの特性に合わせて変更する。

```python
from __future__ import annotations

import hashlib
import json
from datetime import timedelta
from pathlib import Path

import pendulum
from airflow.sdk import DAG, Asset, get_current_context, task


OUTPUT_ROOT = Path("/tmp/airflow-orchestration-example")
PUBLISHED_ASSET = Asset("local-example://orchestration/partitions")


with DAG(
    dag_id="interval_aware_example",
    schedule="@daily",
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
    max_active_runs=1,
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=2),
    },
) as dag:

    @task(outlets=[PUBLISHED_ASSET])
    def publish_partition() -> dict[str, str]:
        context = get_current_context()
        interval_start = context["data_interval_start"]
        interval_end = context["data_interval_end"]
        run_id = context["run_id"]

        partition = interval_start.format("YYYY-MM-DD")
        target = OUTPUT_ROOT / f"date={partition}" / "result.json"
        target.parent.mkdir(parents=True, exist_ok=True)

        # run_id를 그대로 파일명에 쓰지 않고 안정된 제한 길이 ID로 만든다.
        attempt_id = hashlib.sha256(run_id.encode("utf-8")).hexdigest()[:12]
        staging = target.with_name(f".{target.name}.{attempt_id}.tmp")

        payload = {
            "data_interval_start": interval_start.isoformat(),
            "data_interval_end": interval_end.isoformat(),
        }
        staging.write_text(
            json.dumps(payload, sort_keys=True),
            encoding="utf-8",
        )
        staging.replace(target)

        # XCom에는 작은 metadata만 반환한다.
        return {
            "path": str(target),
            "partition": partition,
        }

    @task
    def verify_partition(metadata: dict[str, str]) -> None:
        path = Path(metadata["path"])
        if not path.is_file() or path.stat().st_size == 0:
            raise RuntimeError(f"published partition is invalid: {metadata['partition']}")

    verify_partition(publish_partition())


if __name__ == "__main__":
    dag.test()
```

公式の[Dag debugging文書](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/debug.html)は、`dag.test()`によりtaskを1つのprocess内でfail-fast実行する方法を提供している。localでの成功だけではexecutor、network、permission、secret backendまで検証されないため、別途integration環境が必要である。

### idempotencyはretryとbackfillの前提である

idempotent taskは、同じ論理入力で複数回実行しても同じ最終状態を作る。「2回目の実行も成功する」より強い条件である。

実践パターン：

- output keyをwall clockではなく`data_interval_start/end`で決定する
- appendの代わりにpartition overwrite、merge/upsert、replaceを目的に応じて使う
- stagingで完成させてからatomic publishする
- 外部APIへdeterministic idempotency keyを渡す
- side effectと完了markerをtransactionまたはcompare-and-setで結合する
- taskが部分完了したときの再開位置とクリーンアップ責任を明示する

たとえばメール送信、決済、外部ticket作成では、単純なretryによりside effectが重複する。Airflowのretry設定だけに頼らず、外部システムのidempotency keyと結果照会APIを使う。

再現性のため、taskは次の入力をlogに残す。ただしsecretは除外する。

- Dag ID、task ID、run ID、try number
- data interval start/end
- source partition/versionとoutput URI
- code/image revision
- row count、checksum、data quality結果

### retryは一時的なエラーだけに使う

retryが適するエラー：

- 一時的なnetwork timeout
- rate limitと明示的なretry-after
- 一時的にunavailableなdependency
- workerのpreemptionやprocess crash

retryでは解決できないエラー：

- schemaとcodeの不一致
- 誤ったcredentialまたは権限
- 無効な入力
- deterministic bug
- storage quotaが継続的に超過した状態

retryには試行回数の上限、exponential backoff、最大delay、task execution timeoutを設ける。すべてのtaskへ一律に大きなretry回数を設定すると、障害の検知を遅らせ、dependencyにretry stormを引き起こす。

Airflowで再試行する前にtask内のlibraryもretryするなら、総試行回数が乗算され得る。どの階層が高速なnetwork retryを担当し、どの階層がworkflow-levelの再実行を担当するのか、budgetを定める。

## XCom、Connection、Variable、Paramsを役割別に分離する

| ツール | scopeと目的 | 適した値 | 避けるべき値 |
|---|---|---|---|
| XCom | task instance/Dag run内の通信 | URI、partition、小さなJSON metadata | dataframe、大型binary、retry checkpoint |
| Connection | 外部システムendpointと認証接続 | host、schema、conn ID、credential reference | task結果、business parameter |
| Variable | インストールまたはteam範囲のruntime構成 | 緊急runtime switch、デプロイ別の小さな設定 | version管理すべき定数、run別入力、大型JSON |
| Params | Dag run別の検証可能な入力 | 処理mode、制限された日付・option | 長期secret、task間の結果 |

公式の[XCom文書](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/xcoms.html)は、XComが小さなserializable値向けであり、dataframeのような大きな値には適さないと明記している。Airflow 3では他taskのXComを取得する際に`task_ids`を指定する必要があり、失敗taskのretry前にXComが削除され得るため、durable checkpointとして使ってはならない。

TaskFlow returnは便利だが、返却object全体がXComへserializeされる可能性がある。外部処理の実結果ではなく、次のようなmanifestを返す。

```python
{
    "uri": "object://<BUCKET>/<KEY>",
    "partition": "2026-01-01",
    "checksum": "sha256:<DIGEST>",
    "row_count": 1234,
}
```

Connectionは`conn_id`という論理名で外部接続を参照し、Hook/providerが実際のcredential処理を担当する。Dag sourceにURI原文やpasswordを書かない。概念とpublic APIは[Connections & Hooks文書](https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/connections.html)を基準とする。

Variableはglobal runtime key/value storeである。公式の[Variables文書](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/variables.html)は、可能な設定をDag sourceへ置いてversion管理し、Variableは真にruntime-dependentな値へ限定することを推奨している。Dag parseのtop-levelで`Variable.get()`を繰り返すとmetadata/secret backendの照会がparsing性能と可用性に結合するため、task runtimeまたはtemplateで読む。

## secretはDagではなく実行identityとsecrets backendで管理する

Airflow ConnectionやVariable名を使うだけで、値が自動的に安全になるわけではない。metadata database、environment variable、log、serialized Dag、task environmentへ露出する経路を検討する。

推奨原則：

- Dagには`conn_id`とsecretの論理名だけを記録する
- 外部secrets backendまたはworkload identityを使う
- scheduler、Dag processor、API server、workerが必要とするsecret範囲を分離する
- worker taskごとのcloud roleとnamespace権限を最小化する
- 長期access keyより短寿命credentialを使う
- secret原文、Connection URI、environment全体をlogへ出力しない

Airflow 3ではworker用secrets backendを別途構成できる。lookup順序とkey collisionがあるため、migration時に同じ名前が複数backendへ存在しないよう確認する。詳細な動作は公式の[Secrets Backend文書](https://airflow.apache.org/docs/apache-airflow/stable/security/secrets/secrets-backend/index.html)に従う。

Fernet encryptionやUI maskingはsecret lifecycle全体を守らない。task codeが値を読んだ瞬間、worker processには平文が存在する。worker isolation、log redaction、egress制限、rotation、auditも必要である。

## 待機をworker slotから分離する

### poke、reschedule、deferrableの違い

| 方式 | 待機中のworker slot | 適した状況 | 主なtrade-off |
|---|---:|---|---|
| sensor `poke` | 継続占有 | 非常に短く、頻繁な確認が必要な待機 | 長時間待機でworkerを浪費 |
| sensor `reschedule` | checkの間は返却 | 分単位のpollingを許容する待機 | schedulerの再スケジュールoverhead |
| deferrable operator | triggererへ渡して返却 | 長時間のexternal event待機 | triggerer運用とprovider対応が必要 |

公式の[Sensors文書](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/sensors.html)は、`poke`と`reschedule`のslot利用の違いを説明する。[Deferrable Operators & Triggers文書](https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/deferring.html)によれば、deferral中のpollingはtriggererのasync triggerが担い、taskはworker slotを解放する。

provider sensorが`deferrable=True`をサポートするかは、該当provider versionの文書で確認する。すべてのsensorへ任意にargumentを追加できるわけではない。custom triggerへblocking I/OやCPU計算を入れない。1つのtriggerがevent loopを塞ぐと、多数のdeferred taskが同時に遅延し得る。

待機taskには次を必ず設定する。

- 全体`timeout`
- polling intervalまたはtrigger semantics
- timeout時にsoft failかhard failか
- stale eventと新eventを区別する基準
- 外部条件がすでに満たされている場合の即時成功
- triggerer healthとdeferred task ageの観測

pollingせざるを得ない場合、「ファイルが存在するか」だけでなくexpected partition、checksum・完了marker、event timestampを確認する。以前のrunの古いファイルを新たな成功と誤認してはならない。

## catchupとbackfillは過去区間を扱う異なる制御である

### catchup

時間ベースscheduleで`catchup=True`なら、schedulerは`start_date`以後にまだ作られていないdata intervalのDag runを作成できる。古い`start_date`を持つ新しいDagをデプロイすると、大量のrunが一斉に生成され得る。

`catchup=False`は、通常のschedulerが過去の欠落intervalを自動生成しない選択であって、taskが`now()`を使ってよいという意味でも、過去の再処理が不可能という意味でもない。

### backfill

backfillは、明示した過去の日付範囲にDag runを作る運用操作である。Airflow 3の公式[Backfill文書](https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/backfill.html)は、reprocessing behavior、独立した`max_active_runs`、実行順序とdry-runを提供する。

まず、生成されるintervalをdry-runで確認する。

```bash
export DAG_ID='interval_aware_example'
export FROM_DATE='2026-01-01'
export TO_DATE='2026-01-07'

airflow backfill create \
  --dag-id "$DAG_ID" \
  --from-date "$FROM_DATE" \
  --to-date "$TO_DATE" \
  --reprocess-behavior failed \
  --max-active-runs 2 \
  --dry-run
```

実際に作成する前の確認事項：

- source retentionが過去intervalをまだ保持しているか。
- 現在のcodeが過去schemaと互換か。
- output overwriteがdownstreamと同時に競合しないか。
- API quota、database load、pool capacityは十分か。
- reprocess behaviorが既存の成功runを上書きする意図と合うか。
- 最新intervalを先に処理するか、過去から処理するかをdependencyが許すか。

backfill concurrencyがproduction trafficと同じpoolを無制限に奪い合わないよう、別poolまたはquotaで制限する。成功判定はtask stateだけでなく、partition count、checksum、data quality、downstream freshnessで行う。

## assetとevent-driven schedulingを使うとき

時間scheduleは「毎日この時刻以後に前日区間を処理する」という契約に強い。upstreamの完了時刻が大きく変動する、または複数producer間のdata dependencyを表す必要があるなら、asset-aware scheduleの方が直接的な場合がある。

producerがoutput assetを宣言して成功すると、consumer Dagをscheduleできる。

```python
import pendulum
from airflow.sdk import DAG, Asset, task


CURATED_ASSET = Asset("object://<BUCKET>/curated/<DATASET>")


with DAG(
    dag_id="asset_producer_example",
    schedule="@daily",
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
):
    @task(outlets=[CURATED_ASSET])
    def publish() -> None:
        # 실제 구현은 output을 완전히 검증한 뒤 atomic publish해야 한다.
        pass

    publish()


with DAG(
    dag_id="asset_consumer_example",
    schedule=[CURATED_ASSET],
    start_date=pendulum.datetime(2026, 1, 1, tz="UTC"),
    catchup=False,
):
    @task
    def consume() -> None:
        pass

    consume()
```

公式の[Asset-Aware Scheduling文書](https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/asset-scheduling.html)によれば、producer taskが成功したときにasset updateが記録され、consumer Dagがscheduleされる。複数assetのAND/OR条件や時間scheduleとの組み合わせも可能だが、複雑な論理ではevent順序、重複、coalescing、replayの意味を先に定義する。

Airflow 3で追加された[event-driven scheduling](https://airflow.apache.org/docs/apache-airflow/stable/authoring-and-scheduling/event-scheduling.html)は、外部eventをasset updateへ結び付けられる。すべての`BaseTrigger`がevent scheduleに適するわけではなく、互換triggerが必要である。message queueがat-least-once deliveryなら、同じeventが複数回来ても結果が重複しないよう、event IDとidempotencyを設計する。

assetはdata catalog全体を自動生成するものではない。URI naming、owner、schema、freshness、partition、quality contractを別途管理する。機密credentialや個人識別情報をasset URIと`extra`へ入れない。公式文書は、asset URI/extraが暗号化されない可能性を前提に、公開可能な識別子を使うよう案内している。

## Dag parsingとbusiness logicを分離する

schedulerとDag processorはDagファイルを繰り返しimportする。top-level Python codeで次を実行すると、parsingが遅く不安定になる。

- 外部APIとdatabaseの呼び出し
- 大型dataframeの読み込み
- Variable/Connectionの反復照会
- 重いmachine learning libraryのimport
- 現在時刻によってtask構造を非決定的に変更

Dagファイルはgraph宣言と薄いadapterに集中し、domain logicは通常のPython packageへ分離して、Airflowなしでunit testする。

```text
repository/
├── dags/
│   └── curated_pipeline.py
├── src/
│   └── pipeline_core/
│       ├── extract.py
│       ├── transform.py
│       └── contracts.py
└── tests/
    ├── test_dag_structure.py
    └── test_transform.py
```

providerとAirflowのdependency conflictが大きい、または計算が重い場合、taskから別container/jobをsubmitする。Airflow workerへすべてのworkload dependencyをインストールするとimageが大きくなり、Dag間のdependency conflictとupgradeリスクが増す。

## Observability：Airflow control planeとdata productを併せて見る

### control planeシグナル

- schedulerとDag processorのheartbeat
- Dag import errorとparse duration
- queued/scheduled task age
- executorとpoolのopen/queued/running slot
- deferred task数とtriggerer health
- metadata databaseのlatency、connection、storage増加
- remote task log転送失敗

公式の[Airflow metrics文書](https://airflow.apache.org/docs/apache-airflow/stable/administration-and-deployment/logging-monitoring/metrics.html)は、`scheduler_heartbeat`、`dag_processor_heartbeat`、`dag_processing.import_errors`、pool・executor・task状態metricなどを提供する。導入したexecutorとtelemetry backendに合う名前とtagを、実際のversionで確認する。

### workflowシグナル

- Dag run success/failureとduration
- task retry・timeout・zombie/heartbeat failure
- schedule delay：logical interval終了からrun開始まで
- queue delay：taskがschedulableになってから実際に開始するまで
- end-to-end completion：interval終了からoutput publishまで

### data productシグナル

- freshnessと最後の成功partition
- expected/actual row countとvolume anomaly
- schema/contract違反
- null、duplicate、referential integrity
- source-to-output reconciliationとchecksum

Airflow Dagが成功しても空ファイルを正常publishしたなら、data productは失敗である。反対に、taskが1回retryした後で正しいoutputを期限内に作ったなら、利用者SLOは守られ得る。on-call pageはtask失敗数より、重要成果物のfreshnessとcorrectnessへの影響に結び付ける。

logにはDag/task/run/try/data interval/output revisionを構造化して残す。secret、Connection URI、元record全体は残さない。disposable workerを使う場合はremote loggingを構成し、log backend障害も観測する。production構成の基本的な注意事項は公式の[Production Deployment文書](https://airflow.apache.org/docs/apache-airflow/stable/administration-and-deployment/production-deployment.html)を参照する。

## local testとCI検証チェックリスト

### 高速な検証階層

1. 通常のPython domain logic unit test
2. すべてのDag importとparse errorの検査
3. Dag ID、task ID、dependency、schedule、retry方針の構造test
4. `dag.test()`による代表intervalのlocal実行
5. stagingで実際のConnection、secret backend、executor、storageをintegration
6. productionデプロイ後のsynthetic Dagとfreshness観測

公式の[Best PracticesにあるTesting a Dag](https://airflow.apache.org/docs/apache-airflow/stable/best-practices.html#testing-a-dag)は、Dag loader test、unit test、self-check、staging検証を区別している。

CIのDagBag test例：

```python
from airflow.dag_processing.dagbag import DagBag


def test_all_dags_import_without_errors() -> None:
    dagbag = DagBag(dag_folder="dags", include_examples=False)
    assert dagbag.import_errors == {}


def test_critical_dag_contract() -> None:
    dagbag = DagBag(dag_folder="dags", include_examples=False)
    dag = dagbag.get_dag("interval_aware_example")

    assert dag is not None
    assert dag.catchup is False
    assert set(dag.task_ids) == {"publish_partition", "verify_partition"}
    assert dag.get_task("publish_partition").downstream_task_ids == {
        "verify_partition"
    }
```

`airflow.dag_processing.dagbag`は公式test例に登場するがinternal package pathであるため、Airflow minor versionを上げるときはtest importも確認する。production Dag codeではAirflow 3のpublic interfaceを優先する。

CIコマンド例：

```bash
python -m compileall -q dags src tests
python -m pytest -q
airflow dags list
airflow dags list-import-errors
```

実際のCI imageはproductionと同じAirflow core、provider、Python dependency lockを使う。Airflowはapplicationとlibraryの性質を併せ持つため、公式constraintsと組織のlock戦略を併用し、coreとproviderのcompatibilityをstagingで検証する。

Dag review：

- [ ] schedule、timezone、`start_date`、catchupの意味が明確である。
- [ ] taskが`data_interval_start/end`でpartitionを決定する。
- [ ] retryとbackfillでもoutputが重複しない。
- [ ] timeout、retry、pool、concurrencyがdependency容量と合う。
- [ ] XComは小さなmetadataだけを渡す。
- [ ] Connection、Variable、Paramsが役割に応じて分離されている。
- [ ] secret原文がsource、log、XCom、asset URIにない。
- [ ] 長時間待機をreschedule/deferrable/event方式でworkerから分離する。
- [ ] top-level parseにnetwork/DB/大型importがない。
- [ ] leaf taskとtrigger ruleがDag run全体の状態を誤解させない。

運用review：

- [ ] backfill dry-run、concurrency、reprocessing behaviorを検討する。
- [ ] source retentionと過去schemaのcompatibilityを確認する。
- [ ] scheduler、Dag processor、triggerer、executor、metadata DBを観測する。
- [ ] 利用者向け成果物のfreshnessとcorrectnessに対するアラートがある。
- [ ] log retentionとmetadata databaseのクリーンアップ方針がある。
- [ ] upgrade前にmetadata backup、migration、provider compatibility、stagingを試験する。
- [ ] task clear/retry/backfillの権限と監査logが制限されている。

## 失敗事例と限界

### Airflowをdata processing engineとして使う

worker memoryで大規模dataframeを処理してXComで渡すと、拡張性と分離が崩れる。AirflowはSpark、warehouse、container jobのような外部computeをorchestrationし、小さなmetadataを追跡する役割へ集中する。

### `now()`をpartition keyに使う

retry、queue遅延、manual run、backfillの際に異なるpartitionを読み書きする。論理入力はdata intervalと明示的なParamsから作る。

### task成功をoutput commitより先に記録する

非同期の外部jobをsubmitし、完了確認なしにtaskが成功すると、downstreamが未完成データを読む。deferrable operatorまたは別sensorでterminal stateとoutput qualityを確認してから成功とする。

### XComをdurable state storeとして使う

XComはtask通信向けの小さな値であり、retry時に削除され得る。長期checkpointと大型payloadは外部storageでversion付きで保持し、XComにはreferenceだけを置く。

### retry回数を増やして不安定性を隠す

一時エラーには役立つが、deterministic failureの発見を遅らせ、dependency負荷を増やす。error taxonomyとretry budgetを定め、使い切ったら人が行動できるcontextとともに失敗させる。

### すべてのdependencyをsensor pollingで表現する

workerとschedulerの負荷、polling latencyが増える。sourceがeventを提供するならasset/event scheduleを検討し、pollingが必要ならdeferrable sensorとtimeoutを使う。

### asset eventをexactly-once deliveryと誤解する

producerの再実行、外部eventの重複、consumer失敗後の再処理は起こり得る。assetはdependencyの表現であってbusiness transactionではない。outputとconsumerの双方をidempotentにする必要がある。

### Airflowがstreamingを代替すると考える

Airflowはbatch-oriented orchestrationに適している。低latencyの継続的event処理、per-event state、backpressureが中心なら、stream processorとmessage systemがdata planeを担当し、Airflowはbatch補正・管理workflowを担う方が自然である。

Airflow運用の核心は華やかなDag graphではない。処理区間を正確に定義し、taskを再実行可能にし、小さなorchestration metadataと実data planeを分離し、過去の再処理と障害対応を最初から設計することである。
