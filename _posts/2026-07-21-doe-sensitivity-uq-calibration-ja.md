---
title: "DOEからUQ・Calibrationまで：シミュレーション研究設計の全体像"
date: 2026-07-21 09:30:00 +0900
categories: [Scientific Computing, Research Methods]
tags: [doe, sensitivity-analysis, uncertainty-quantification, calibration, identifiability, surrogate-model]
description: "実験計画法、局所・大域感度、不確実性の伝播、parameter calibrationを区別し、一つの再現可能なシミュレーション研究手順として結び付ける。"
math: true
lang: ja-JP
translation_key: doe-sensitivity-uq-calibration
hidden: true
---

{% include language-switcher.html %}

シミュレーション入力をいくつか変更して出力曲線を比較するだけでは、強い結論を導くのは難しい。変数の効果、interaction、入力の不確実性、parameter推定、モデル誤差が一度に混ざり合うからである。

これらを切り分けるには、まず四つのツールの役割を区別する必要がある。

- **Design of Experiments（DOE）**：どの入力の組み合わせで計算または測定するかを決める。
- **Sensitivity analysis（SA）**：出力変動をどの入力がどの程度説明するかを問う。
- **Uncertainty Quantification（UQ）**：入力・モデルの不確実性が出力の不確実性へどのように伝播するかを問う。
- **Calibration**：観測を用いて未知のparameterを推定する。

これらは相互に補完するが、代替関係にはない。DOEを適切に行ってもuncertaintyが自動的に定量化されるわけではなく、calibrationがよく適合してもvalidationが完了したわけではない。

## 1. 最初に作る表：入力と不確実性の分類

すべての入力 \(x=(x_1,\dots,x_d)\)を一種類として扱ってはならない。

| 分類 | 意味 | 代表的な処理 |
|---|---|---|
| controllable factor | 設計者が水準を選択 | factorial, optimal design |
| scenario/context variable | 関心範囲はあるが直接は制御しない | blocking, stratification |
| aleatory variable | 本質的な変動としてモデル化 | 確率分布とforward propagation |
| epistemic parameter | 知識不足により不確実 | calibration, interval/prior update |
| nuisance parameter | 関心対象ではないが結果に影響 | marginalization, profiling |
| model discrepancy | 方程式構造が現実と異なる部分 | 別個のdiscrepancy modelまたはbias budget |

同じ物理量でも、目的に応じて分類が変わり得る。重要なのは名称より、**どの情報を利用してどのように更新するか**を事前に決めることである。

各入力には少なくとも次のmetadataが必要である。

- 定義と単位
- 許容範囲と根拠
- 分布または設計水準
- 入力間の相関・制約
- 固定値か推定値か
- 測定可能か
- モデルのどの位置に入るか

## 2. DOE：実行予算を情報に変える設計

### One-factor-at-a-timeの限界

一度に一つの変数だけを変えるOFATは理解しやすいが、interactionを見落とす。例えば

$$
y=\beta_0+\beta_1x_1+\beta_2x_2+\beta_{12}x_1x_2
$$

において \(\beta_{12}\)が大きければ、\(x_1\)の効果は \(x_2\)の水準によって変わる。一つの基準点でのOFATではこの構造を識別しにくい。

### 設計の種類と目的

| 設計 | 長所 | 注意点 |
|---|---|---|
| full factorial | main effectとinteractionを体系的に推定 | 次元が増えると実行数が急増 |
| fractional factorial | 少ない実行でscreening | alias structureを必ず解釈 |
| central composite / Box–Behnken | quadratic response surfaceに効率的 | 指定領域外のextrapolationに弱い |
| Latin hypercube | 各軸を均等に層化 | projection qualityとcorrelationを確認 |
| low-discrepancy sequence | integration・global SAに有利 | 独立random replicateと区別 |
| D-/I-optimal design | 特定の回帰モデルの目的に最適化 | 仮定したモデルが誤っていれば効率低下 |
| adaptive/sequential design | 不確実または重要な領域へ予算を集中 | stopping ruleとselection biasを管理 |

DOEは「空間を均等に埋める」ことだけを意味しない。screening、surrogate学習、最適化、parameter識別、validationのうち何を目的とするかによって、適切な設計は異なる。

### Randomization, replication, blocking

- **Randomization**は、時間driftや順序効果が特定のfactorとconfoundingするのを抑える。
- **Replication**は同一条件での変動を推定する。完全にdeterministicなsimulatorなら、同じbinary・環境での単純な反復は新しい情報を与えないが、stochastic solverやnondeterministic executionでは必要である。
- **Blocking**は、装置、batch、日付、mesh familyのように取り除きにくいnuisance variationを分離する。

simulation campaignでも、run order、compute environment、solver versionがblockまたはprovenance変数になり得る。

## 3. Sensitivity analysis：まず影響の定義を選ぶ

「最も重要な変数」はmetricによって変わる。

### Local sensitivity

基準点 \(x_0\)周辺の微分

$$
S_i^{\mathrm{local}}
=
\left.
\frac{\partial f}{\partial x_i}
\right|_{x=x_0}
$$

は小さなperturbationの影響を表す。単位が異なる場合は

$$
S_i^{\mathrm{scaled}}
=
\frac{x_i}{f}
\frac{\partial f}{\partial x_i}
$$

のような無次元指標を検討できる。

local derivativeはgradientベースの最適化とlinearized uncertaintyに効率的だが、nonlinearity、threshold、interaction、基準点への依存を見落とすことがある。

### Screening：Morris系

各入力を複数の位置で一度ずつ動かしたelementary effectを集めると、絶対値の平均は全般的な影響を、分散はnonlinearityやinteractionの可能性を示す。高次元で重要でない変数を除くのに有用だが、正確なvariance decompositionではない。

### Global variance-based sensitivity

入力が独立していると仮定すると、出力分散はANOVA形式で分解できる。

$$
\operatorname{Var}(Y)
=
\sum_i V_i
+\sum_{i<j}V_{ij}
+\cdots
$$

first-order Sobol indexとtotal-effect indexは

$$
S_i=\frac{V_i}{\operatorname{Var}(Y)},
\qquad
S_{T_i}
=
1-
\frac{
\operatorname{Var}_{X_{\sim i}}
\left(
\mathbb E[Y\mid X_{\sim i}]
\right)
}{
\operatorname{Var}(Y)
}
$$

と書ける。\(S_i\)は \(X_i\)単独の効果を、\(S_{T_i}\)は \(X_i\)が関与するすべてのinteractionを含む。\(S_{T_i}-S_i\)が大きければ、interactionが重要だというシグナルである。

### 相関入力の落とし穴

標準的なSobol分解の解釈は、独立入力を前提とする。実際に可能な入力の組み合わせに相関や物理的制約がある場合、独立samplingは実現不可能な状態を生成することがある。この場合はconditional sampling、grouped indices、Shapley effectなど、依存構造を尊重する手法を検討し、使用したjoint distributionを明示する。

## 4. UQ：不確実性を出力分布へ伝播する

forward UQの基本問題は

$$
X\sim p_X(x),\qquad Y=f(X)
$$

において、\(Y\)の分布、平均、分散、quantile、failure probabilityを推定することである。

### Monte Carlo

独立sample \(x^{(j)}\)を生成し、\(y^{(j)}=f(x^{(j)})\)を計算する。次元に比較的鈍感で実装は単純だが、rare eventやexpensive simulationではコストが大きい。sample数だけでなく、Monte Carlo standard errorまたはconfidence intervalも併せて報告する。

### SurrogateベースのUQ

元のモデルが高価なら、response surface、Gaussian process、polynomial chaos、neural surrogateなどを使用する。このとき総誤差は、少なくとも次のように分けられる。

$$
\text{UQ error}
=
\text{sampling error}
+\text{surrogate error}
+\text{input-model error}
+\text{simulation numerical error}.
$$

surrogate test errorが一つ小さいだけでは、tail probabilityとsensitivity indexまで正確だとは限らない。UQの目的に重要な領域、とりわけ境界・tail・constraint付近の誤差を別途確認する。

### Rare event

failure probabilityが小さい場合、crude Monte Carloでは失敗sampleがほとんど得られない。importance sampling、subset simulation、splitting、adaptive surrogateのような手法が必要になることがある。結果を見た後でproposalを恣意的に調整した場合は、estimator biasとweightの計算を点検する。

## 5. Calibration：inverse problemとしてparameterを推定する

観測 \(d\)、simulator \(f(\theta,z)\)、parameter \(\theta\)、観測条件 \(z\)があるとき

$$
d=f(\theta,z)+\delta(z)+\varepsilon
$$

と書ける。

- \(\delta(z)\)：model discrepancy
- \(\varepsilon\)：measurement noise

### Optimizationの観点

重み付き最小二乗は

$$
\hat\theta
=
\arg\min_\theta
(d-f(\theta))^\mathsf T
\Sigma^{-1}
(d-f(\theta))
$$

と表される。bounds、regularization、prior penaltyが加わる場合もある。

### Bayesianの観点

$$
p(\theta\mid d)
\propto
p(d\mid\theta)p(\theta)
$$

において、likelihoodは測定・モデルのresidual構造を、priorは観測前の情報を表す。結果は一つの点推定ではなくposterior distributionである。

Bayesian手法も、likelihoodとdiscrepancy modelが誤っていれば自動的に正しいuncertaintyを与えるわけではない。posteriorが狭いという事実は、モデル仮定の下で情報が集中したという意味であり、現実におけるすべての誤差が小さいという意味ではない。

## 6. Identifiability：最適化の成功とparameterの学習は異なる

### Structural identifiability

noiseが一切なく連続観測が可能だと仮定しても、異なるparameterが同じ出力を生むなら、構造的に識別不可能である。

### Practical identifiability

理論上は識別可能でも、観測位置、範囲、noise、入力excitationが不足していれば、実データで区別することは難しい。

診断には次が役立つ。

- JacobianまたはFisher informationのsingular spectrum
- parameter profile likelihood
- posterior correlation
- 複数の初期値からの最適化
- synthetic recovery test
- 新しい観測条件に対するexpected information

parameter間の相関が強い場合、個々の値は不安定でも、特定の組み合わせやpredictionは安定していることがある。目的がparameter自体なのかpredictionなのかを区別する必要がある。

## 7. Model discrepancyとparameterのconfounding

モデルの構造誤差 \(\delta(z)\)を無視すると、parameterがその誤差を代わりに吸収することがある。この「effective parameter」はcalibration条件ではよく適合しても、新しい条件では物理的意味や予測力を失う場合がある。

反対に、非常に柔軟なdiscrepancy modelを許容すると、あらゆるmismatchを \(\delta\)が説明し、parameterを学習できなくなる。parameterとdiscrepancyを同時に自由に推定する問題は、本質的にconfoundedとなり得る。

緩和策は次のとおりである。

- 多様な条件と観測種類を含める。
- parameterごとに感度の高いQoIを設計する。
- 物理的なpriorとboundsを根拠とともに使用する。
- discrepancyのsmoothness・構造を制限する。
- calibration条件とvalidation条件を分離する。
- parameter uncertaintyとpredictive discrepancyを分けて報告する。

## 8. 一つにつないだ推奨ワークフロー

### ステップ1：目的と出力の定義

意思決定、QoI、許容誤差、関心のある入力範囲を先に固定する。「モデルをうまく合わせる」ではなく、どのpredictionをどの範囲で支援するかを記す。

### ステップ2：入力audit

入力の単位、範囲、joint distribution、物理的制約、情報源を表にまとめる。epistemicとaleatoryを区別するが、境界が曖昧なら複数の解釈をscenarioとして設定する。

### ステップ3：screening DOE

次元が大きい場合は、factorial/fractional design、Morris、derivative screeningなどで影響の小さい変数を除く。その際、screening thresholdと見落とす可能性があるinteractionを記録する。

### ステップ4：space-fillingまたは目的指向DOE

surrogate、global SA、calibrationのうち目的に合わせてLHS、low-discrepancy、optimal designを選択する。物理的に不可能な組み合わせはconstraint-aware samplingで除外する。

### ステップ5：numerical quality control

各runのconvergence、conservation、failure code、mesh/time-step provenanceを記録する。solver failureを単に削除するとfeasible regionの推定が歪む可能性があるため、failure自体をoutcomeとして管理する。

### ステップ6：surrogate検証

trainingとは独立したtest designを使用する。平均誤差だけでなく、worst region、tail、derivative、calibration posteriorが集中する領域を確認する。

### ステップ7：global SAとforward UQ

joint input modelを明示し、sensitivity indexのMonte Carlo uncertaintyも計算する。input importanceの順位がsample sizeとsurrogate choiceに対して安定しているかを確認する。

### ステップ8：calibration

likelihood、prior、bounds、discrepancyの仮定、optimizer/samplerの診断を記録する。synthetic recoveryとmulti-startによってidentifiabilityを確認する。

### ステップ9：validation

使用していない条件・QoIでpredictive distributionと観測を比較する。calibration residualではなくout-of-sample predictionを評価する。

### ステップ10：sequential update

現在のuncertaintyを最も大きく減らす次のrunまたはmeasurementを選択する。acquisition ruleとstopping criterionをあらかじめ定め、際限のない探索を防ぐ。

## 9. 検証チェックリスト

- [ ] DOE、sensitivity、UQ、calibrationの目的を混同していないか？
- [ ] 入力範囲と分布に技術的な根拠があるか？
- [ ] 相関と物理的constraintをjoint samplingに反映したか？
- [ ] OFATだけでinteractionがないと結論付けていないか？
- [ ] deterministic/stochasticかどうかに合わせてreplicationを設計したか？
- [ ] sensitivity metricの定義と前提を明示したか？
- [ ] sensitivity index自体のsampling uncertaintyを報告したか？
- [ ] surrogate errorをUQ結果に含めるか、別途定量化したか？
- [ ] calibration parameterのidentifiabilityを診断したか？
- [ ] model discrepancyがparameterに吸収される可能性を検討したか？
- [ ] calibrationデータとvalidationデータを分離したか？
- [ ] random seed、design generator、実行順序、失敗runを保存したか？

## 10. よくある落とし穴と限界

### 範囲を広くするほど保守的だという誤解

根拠なく広い独立uniform distributionを与えると、現実には不可能な組み合わせが生じ、sensitivityの順位が人為的に変わることがある。範囲には保守性だけでなくjoint feasibilityも反映しなければならない。

### 相関係数を入れれば依存構造をすべて表現できるという誤解

線形相関では、tail dependence、nonlinear constraint、multimodalityを説明できない場合がある。

### Surrogateの平均test scoreだけを信頼する

小さなglobal RMSEは、threshold付近、tail、gradientの正確性を保証しない。downstream taskに合わせたvalidation metricが必要である。

### Parameter posteriorを物理定数として解釈する

model discrepancyを無視したcalibration parameterは、条件依存の補正値である場合がある。

### 感度の低い変数を無条件に取り除く

現在の出力と範囲で感度が低いという意味にすぎず、別のQoI・regime・tail eventでも重要でないという保証はない。

### 計算予算が少ないときの過剰な次元

高次元global SAとflexible calibrationを少ないrunで同時に実行すると、推定量が不安定になる。screening、構造的な次元削減、informative measurementを先に行うべきである。

## まとめ

強いシミュレーション研究は、多数のrunではなく、**情報の流れが分離されたrun**から生まれる。DOEはどこを見るかを決め、sensitivity analysisは何が重要かを説明し、UQは結論の幅を計算し、calibrationは観測によって未知のparameterを更新する。

最後にvalidationは、これらすべての仮定の下でのpredictionが新しい情報に対しても目的に適合するかを問う。四段階の問いとデータを分けるだけでも、overfitting、偽の精度、解釈不能なparameterを大幅に減らせる。
