---
title: "決定論的シミュレーションテスト：不変条件、Property-Based Testing、Replay"
date: 2026-07-21 09:40:00 +0900
categories: [Software Engineering, Simulation Testing]
tags: [determinism, simulation-testing, invariants, property-based-testing, replay, regression-testing, reproducibility]
description: "決定論的シミュレーターを、少数の例ではなく、不変条件、生成型プロパティテスト、状態ハッシュ、イベントreplayによって検証する方法をまとめる。"
math: true
lang: ja-JP
translation_key: deterministic-simulation-testing-invariants-replay
hidden: true
---

{% include language-switcher.html %}

シミュレーションテストが「代表的な入力を実行し、グラフが似ているかを見る」だけにとどまると、小さな変更がどの法則を壊したのかを突き止めにくい。逆に、出力ファイル全体をgolden fileとして固定すると、無害な浮動小数点差でもテストが失敗し、誤った既存結果を永続的に保存してしまう可能性がある。

より強力な戦略は、次の3層を組み合わせることだ。

1. すべての正しい実行が満たすべき**不変条件と関係**
2. 広い入力空間を自動探索する**property-based test**
3. 失敗を正確に再現する**seed・event・state replay**

## 1. まず3つの用語を区別する

### Determinism

同一の初期状態、入力、設定、実行環境において、同一の状態遷移が得られる性質である。

$$
s_{t+1}=F(s_t,u_t;\theta)
$$

が同じ \(s_t,u_t,\theta\) に対して同じ \(s_{t+1}\) を出力しなければならない。

### Reproducibility

異なる時点や環境でも、許容範囲内で結果を再び作り出せる能力である。bitwise determinismより広い概念であり、source、dependency、configuration、data、compiler、hardwareの情報が必要になる。

### Robustness

許容可能な入力・環境の変化に対しても、結論が安定している性質である。同じ入力に対して常に同じ誤答を返すプログラムはdeterministicではあるが、robustでもcorrectでもない。

## 2. 決定性を壊す隠れた入力

コードの関数引数だけが入力なのではない。次の項目も状態遷移に影響しうる。

- pseudo-random number generatorのseedとalgorithm
- wall-clock timeとlocale
- hash-map iteration order
- thread schedulingとreduction order
- GPU kernelのatomic operation
- compiler flagとfast-math
- BLAS・runtime・driver
- ファイルの列挙順序
- 環境変数とconfiguration default
- 外部serviceの応答
- 初期化されていないメモリ

したがって、「seedを固定した」だけでは決定性は完成しない。random streamをsubsystemごとに分離し、実行順序が変わっても互いの乱数消費量に影響しないよう設計するのが望ましい。

## 3. テストピラミッドではなくテスト格子

シミュレーターには複数種類のoracleが必要である。

| テストの種類 | 問うこと | 失敗から判明しやすいこと |
|---|---|---|
| unit test | 小さな演算が定義どおりに動作するか？ | 符号、単位、index、境界処理 |
| analytic/benchmark test | 既知の解に収束するか？ | 方程式・schemeの実装 |
| invariant test | 必ず保存すべき法則を守るか？ | 累積drift、欠落したsource |
| property-based test | 広範な有効入力でも性質が保たれるか？ | 予想外のcorner case |
| metamorphic test | 入力変換に応じた出力関係が正しいか？ | oracleのない問題の論理エラー |
| differential test | 独立した実装と一致するか？ | 実装ごとのdivergence |
| regression/golden test | 承認済みの動作が変わっていないか？ | 意図しない変更 |
| replay test | 過去の失敗をそのまま再現できるか？ | nondeterminism、状態の欠落 |

ある種類が別の種類を代替することはない。たとえばconservation testに合格しても空間分布が誤っている場合があり、golden outputが一致しても基準自体が間違っている場合がある。

## 4. 不変条件をexecutable specificationにする

不変条件は文書内の一文ではなく、実行のたびに評価されるassertionでなければならない。

### 保存式

一般的なbalanceを

$$
M_{t+1}
=
M_t+\Delta t\,(I_t-O_t+S_t)+e_t
$$

とすると、defect

$$
d_t=M_{t+1}-M_t-\Delta t\,(I_t-O_t+S_t)
$$

が数値許容誤差の範囲内になければならない。

### Boundsとpositivity

確率、濃度、質量分率のように定義域が制限される状態は、

$$
0\le x_i\le 1
$$

のようなboundを満たす必要がある。ただし、schemeがわずかなundershootを許容するか、clippingがconservationを壊すかも併せて確認する必要がある。単純に負数を0へ切り上げると、bugを隠す可能性がある。

### Symmetryとequivariance

入力座標を回転・反射・順列変換したとき、物理的に同じ変換が出力にも現れるべきなら、

$$
f(Tx)=Tf(x)
$$

を検査する。この関係は正解値が分からなくても強力なoracleになる。

### Dimensional consistencyとscale relation

単位を変えて同じ物理状態を表したとき、無次元出力は同じでなければならない。ただし、scale invarianceが実際のgoverning equationとboundary conditionで成立するかを先に導出する。

### 状態機械の不変条件

- 存在しないentityを二度削除しない。
- 終了したeventを再び処理しない。
- resource countが負にならない。
- timestampがcausal orderに逆行して減少しない。
- 各entity IDのライフサイクルは有効なstate transitionだけに従う。

## 5. 絶対toleranceと相対toleranceを併用する

浮動小数点比較の基本形は

$$
|a-b|
\le
\mathrm{atol}
+\mathrm{rtol}\cdot s
$$

である。\(s\) は問題に適したreference scaleである。

~~~python
def assert_close(actual, expected, *, atol, rtol, scale=None):
    reference_scale = abs(expected) if scale is None else abs(scale)
    error = abs(actual - expected)
    limit = atol + rtol * reference_scale
    assert error <= limit, {
        "actual": actual,
        "expected": expected,
        "error": error,
        "limit": limit,
    }
~~~

expectedが0に近い場合は相対誤差だけを使えず、大きな値では絶対誤差だけで意味を判断しにくい。toleranceはテストを通すために後から調整する数値ではなく、次の根拠に基づく予算でなければならない。

- discretization truncation error
- iterative solver tolerance
- floating-point accumulation bound
- measurementまたはinput precision
- downstream decision threshold

## 6. Property-based testing：例ではなく性質を生成する

example-based testは、人が思いついた点だけを検査する。property-based testingは有効な入力を生成し、失敗すると、より単純な反例へshrinkする。

以下は概念的な形である。

~~~python
from hypothesis import given, strategies as st

@given(
    total=st.floats(min_value=0.0, max_value=1.0e3,
                    allow_nan=False, allow_infinity=False),
    fraction=st.floats(min_value=0.0, max_value=1.0,
                       allow_nan=False, allow_infinity=False),
)
def test_partition_conserves_total(total, fraction):
    left, right = partition(total, fraction)

    assert left >= 0.0
    assert right >= 0.0
    assert_close(
        left + right,
        total,
        atol=1.0e-12,
        rtol=1.0e-12,
    )
~~~

これらの数値は特定プロジェクトの基準ではなく、コードの形を示すための例にすぎない。実際のtoleranceは計算精度と誤差予算によって定める。

### 優れたgeneratorの条件

- 物理的に有効なconstraintを満たす。
- 境界値、0、非常に小さい値、大きなdynamic rangeを十分に生成する。
- correlated variableを独立に生成しない。
- invalid input testとvalid-domain property testを分離する。
- 失敗caseのseedだけでなく、shrinkされた最小入力も保存する。

ランダムな入力を大量に投入するfuzzingとは異なり、property-based testingは**何が真であるべきか**を明示する。

## 7. Metamorphic testing：正解を知らなくても関係は分かる

複雑なシミュレーションでは、任意の入力に対する正確な出力を知るのは難しい。代わりに、入力を変換したときに予想される出力関係をテストする。

たとえば次のようなものがある。

- entityの順序を変えてもpermutation-invariant aggregateは同じである。
- domainとsourceを一緒に平行移動すると、出力も同じだけ平行移動する。
- sourceが0のlimiting caseは、既知の単純な状態へ向かう。
- 独立した2つのsubsystemを結合した総量は、それぞれの総量の和と一致する。
- 時間区間を分割して連続実行した結果と、一度に実行した結果がcheckpoint誤差の範囲内で一致する。

最後の関係は、semigroup propertyとcheckpoint serializationを同時にテストする。

$$
F_{t_2}\left(F_{t_1}(s_0)\right)
\approx
F_{t_1+t_2}(s_0).
$$

adaptive solverやevent localizationでは実行経路が異なる場合があるため、どの水準の同等性を要求するかを明確にする。

## 8. Replayを可能にする最小限の記録

失敗を再現するには、ログメッセージよりも**入力イベントと状態の系譜**が必要である。

### Run manifest

~~~yaml
schema_version: 1
run_id: "<opaque-run-id>"
source_revision: "<commit>"
configuration_digest: "<hash>"
input_digest: "<hash>"
dependency_lock_digest: "<hash>"
random_streams:
  initialization: "<seed>"
  events: "<seed>"
execution:
  worker_count: "<count>"
  numeric_mode: "<mode>"
~~~

例のplaceholderを実際の値で埋める一方、secret、ユーザーパス、内部hostnameは含めない。

### Event log

event sourcing形式であれば、各eventに次の情報を持たせる。

- monotonically increasing sequence number
- simulation timeとlogical time
- event typeとschema version
- canonical payload
- pre-stateまたはpost-state digest
- causal parentまたはcorrelation key

replay engineは外部I/Oを記録済みresponseで置き換え、event sequenceを同じ順序で適用する。

### Checkpoint

長時間の実行を最初からreplayするのはコストが高い。versioned checkpointと、それ以降のevent logを一緒に保存する。checkpoint loaderは以前のschema migrationをテストするか、サポートしないversionなら明確に失敗しなければならない。

## 9. State hashの落とし穴

state hashはdivergenceが始まったstepを探すのに役立つが、canonicalizationなしでは信頼しにくい。

- map keyをソートする。
- serialization formatとschema versionを固定する。
- transient cacheとtimestampを除外する。
- NaN representationとsigned zeroの方針を定める。
- floatを文字列へ恣意的に丸めてhashしない。

bitwise equalityが必須のdiscrete coreと、tolerance比較が適切なnumeric fieldを分離できる。たとえばevent orderとentity countはexact compare、連続fieldはnormとinvariant compareを用いる。

## 10. 並列計算と再現可能なreduction

浮動小数点加算は、結合法則を厳密には満たさない。

$$
(a+b)+c\neq a+(b+c)
$$

となりうるため、thread schedulingによってreductionの結果が変わる。選択肢は次のとおりである。

- 固定されたpartitionとreduction tree
- pairwiseまたはcompensated summation
- deterministic library mode
- exact accumulatorが必要な重要総量
- bitwiseではなくnumerically equivalentという判定

性能のためにnondeterministic reductionを許容することもできる。その場合、結果が許容envelope内にあるかをstatisticalまたはtolerance-based testで検証し、exact replayが不可能であるという契約を文書化する。

## 11. Regressionとgolden fileを安全に使う

golden testはAPI・format・代表trajectoryの変更検出に適しているが、次の原則が必要である。

1. goldenの生成手順もversion controlする。
2. 承認時にはdiffを人が解釈できるsummaryで表示する。
3. 大容量binary全体よりも重要なQoIとinvariantを優先する。
4. toleranceと並び順を明示する。
5. 基準の更新を通常のtest実行から分離する。
6. analytic/invariant testなしでgoldenだけを置かない。

「新しい出力で基準ファイルを自動的に上書きする」ことはregression testを無力化する。

## 12. 失敗を資産に変えるワークフロー

1. productionまたは生成型テストでfailureを検出する。
2. source revision、manifest、最小入力、event log、checkpointを保存する。
3. replayでfailureが再現されるか確認する。
4. divergenceが始まる最初のstate digestを見つける。
5. 原因を説明する最小のinvariant/property testを追加する。
6. 修正後、新しいテストと既存suiteの両方に合格させる。
7. 反例corpusに最小caseを残す。
8. nondeterminism自体が原因なら、repeated scheduling testを別途追加する。

## 13. 検証チェックリスト

- [ ] determinism、reproducibility、correctnessを区別したか？
- [ ] seed以外の隠れた入力と実行環境を記録したか？
- [ ] subsystemごとのrandom streamを分離したか？
- [ ] 主要な保存式とboundsがruntime assertionまたはtestになっているか？
- [ ] property generatorが物理constraintと境界値を扱っているか？
- [ ] metamorphic relationをgoverning ruleから導出したか？
- [ ] toleranceに数値的根拠と単位があるか？
- [ ] exact compareとapproximate compareの対象を分離したか？
- [ ] 失敗時のshrinkされた入力とseedを保存したか？
- [ ] event schemaとcheckpoint schemaにversionがあるか？
- [ ] replay中の外部I/Oを固定または記録したか？
- [ ] 並列reductionのdeterminism契約を明示したか？
- [ ] goldenの更新がreviewなしで自動実行されないか？

## 14. 落とし穴と限界

### Propertyが誤っていると、テストが正しいコードを失敗させる

monotonicity、symmetry、positivityは、モデル・境界条件・数値schemeによっては崩れることがある。propertyは直感ではなく、仕様と数式から導出する。

### Exact replayがすべてのプラットフォームで可能とは限らない

compiler、instruction set、transcendental function、GPU schedulingが異なれば、bitwise結果も異なる可能性がある。サポートするreproducibility tierを定義するほうが現実的である。

- Tier A：同一binary・hardwareでbitwise
- Tier B：同一architectureでnumeric tolerance
- Tier C：異なるplatformでQoI・invariant equivalence

### すべての状態をログへ残すと、コストと情報漏えいが増える

event log、periodic checkpoint、state digestを組み合わせ、retention・redaction方針を設ける。秘密値や個人データがpayloadに混入しないようschemaの段階で防ぐ。

### Deterministic modeが実際の運用経路と異なる場合がある

テスト専用single-thread modeだけに合格し、production parallel pathが検証されていない場合がある。deterministic reference modeと実際のexecution modeをdifferential testで比較する。

## まとめ

強力なシミュレーションテストは、特定の出力値を暗記しない。その代わり、**何が絶対に壊れてはならないか**、**入力を変えるとどの関係が維持されるべきか**、**失敗をどのように同じ状態から再開するか**をコードにする。

不変条件は物理とドメイン知識をexecutable specificationへ変え、property-based testingは人が見落とした入力を見つけ、replayは一度きりの偶発的な失敗を永続的なregression資産へ変える。
