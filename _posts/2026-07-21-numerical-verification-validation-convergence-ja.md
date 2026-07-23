---
title: "数値解析結果を信頼するためのV&V：収束性、格子・時間刻み独立性、保存性"
date: 2026-07-21 09:20:00 +0900
categories: [Scientific Computing, Verification and Validation]
tags: [verification, validation, convergence, mesh-independence, time-step, conservation, numerical-error]
description: "コード検証、解検証、実験的validationを区別し、収束性・格子および時間刻み独立性・保存性から数値結果の信頼性を評価する手順を整理する。"
math: true
lang: ja-JP
hidden: true
translation_key: numerical-verification-validation-convergence
---

{% include language-switcher.html %}

もっともらしいcontourや滑らかな曲線は、正確さの証拠ではない。数値シミュレーションを信頼するには、少なくとも次の問いを分けなければならない。

- コードは方程式を正しく解いているか。
- この計算の離散化誤差・反復誤差は十分に小さいか。
- 選択した方程式と入力は、現実の関心量を十分に説明しているか。
- この結論は、利用目的と許容誤差の範囲内で有効か。

これらの問いを「検証」という一語にまとめると、何を確認し、何が残っているのか分からなくなる。Verificationとvalidationを区別する理由はここにある。

## 1. Verificationとvalidationの境界

| 層 | 中心となる問い | 代表的な根拠 |
|---|---|---|
| code verification | 方程式を意図どおりに実装したか。 | exact solution, manufactured solution, benchmark, unit test |
| solution verification | 現在の計算の数値誤差はいくらか。 | iterative convergence, mesh/time-step refinement, error estimate |
| validation | モデルは現実の関心量を目的に合う形で再現するか。 | 独立した測定との比較、validation uncertainty、applicability |
| calibration | 未知のparameterをデータから推定したか。 | objective/likelihood, posterior, identifiability |

簡潔に言えば、verificationは「方程式を正しく解いたか」、validationは「正しい方程式を選んだか」に近い。ただし、validationはモデルが絶対的に真であることを証明しない。**特定の利用目的、条件範囲、関心量に対する証拠**を積み重ねるものだ。

Calibrationデータとvalidationデータを同じものにすると、モデルが一度見たデータに再び適合することになる。可能なら分離し、データ不足で再利用した場合は、独立した検証ではないという限界を明記しなければならない。

## 2. まず誤差を分解する

計算結果と現実との差は、複数の原因が混ざった結果である。

$$
\text{total discrepancy}
=
\text{model-form error}
+\text{parameter/input uncertainty}
+\text{discretization error}
+\text{iterative error}
+\text{implementation error}
+\text{measurement error}.
$$

この式は、各項が単純に加算され互いに独立であるという厳密な確率モデルではなく、原因を見落とさないための概念的な分解である。互いに相互作用することもあり、観測だけでは完全に分離できない場合もある。

優れたV&V計画では、まずquantity of interest（QoI）を定める。field全体ではなく、どの平均、最大値、積分量、到達時間、境界fluxが意思決定に使われるかを記す。格子収束性とvalidation結果はQoIごとに異なり得る。

## 3. Code verification：実装誤りを見つける段階

### Exact solutionとbenchmark

単純化した境界条件や幾何形状にanalytic solutionが存在する場合、計算誤差を直接比較できる。複雑なproduction caseとは異なっていても、演算子、境界条件、source termの実装を切り分けて試験する価値がある。

### Method of Manufactured Solutions

任意の滑らかな関数\(u_m(x,t)\)を先に選び、governing equationの演算子\(\mathcal L\)に代入してsource

$$
f_m=\mathcal L(u_m)
$$

を作る。コードが

$$
\mathcal L(u)=f_m
$$

を解くように設定すれば、正解\(u_m\)が既知の状態で、interior operator、boundary condition、時間積分、observed orderをまとめて試験できる。

manufactured solutionは現実の現象を表現する必要はない。その代わり、次を満たす必要がある。

- コード経路の主要な項をすべて有効にする。
- 過度な対称性によってbugを覆い隠さない。
- 必要な微分可能性を備える。
- 境界条件とsourceを整合的に導出する。

### 独立した実装とlimiting case

異なるコードが同じ答えを出すことは有用な証拠だが、共通の仮定や共通のbugを共有している可能性がある。したがって、項を0に近づけた極限、symmetry、次元解析、保存式など、別種の証拠と組み合わせる。

## 4. Solution verification：現在の計算における数値誤差

### Iterative errorとdiscretization errorを分ける

非線形・線形solverが十分に収束していない状態で格子を変えると、iterative errorとdiscretization errorが混ざる。各格子でresidual toleranceを離散化による差より十分小さくし、residualだけでなくQoIの安定性も確認する。

algebraic residualの減少が、そのままsolution errorの減少を保証するわけではない。badly conditioned systemでは、小さなresidualと大きなsolution errorが共存し得る。

### 漸近収束領域

格子間隔を\(h\)、理論上の次数を\(p\)とすると、十分に細かい領域では

$$
\phi(h)=\phi_0+Ch^p+\mathcal O(h^{p+1})
$$

という形が期待される。\(\phi\)は一つのQoIである。refinement ratioが一定で、

$$
h_3=rh_2=r^2h_1,\qquad r>1
$$

かつ\(h_1\)が最も細かいとき、observed orderは

$$
p_{\mathrm{obs}}
=
\frac{
\ln\left|
(\phi_3-\phi_2)/(\phi_2-\phi_1)
\right|
}{
\ln r
}
$$

で推定できる。漸近領域にあり単調収束するなら、Richardson extrapolationは

$$
\phi_{\mathrm{ext}}
=
\phi_1+
\frac{\phi_1-\phi_2}{r^{p_{\mathrm{obs}}}-1}
$$

を与える。

三つの値が振動収束する場合や、差がnoise水準にある場合、この式は不安定になる。無条件に一つのapparent orderを出力するのではなく、まず収束の形と前提が満たされているかを報告する。

## 5. 「格子独立」という表現に注意すべき理由

有限の格子でdiscretization errorが厳密に0になることはまれである。したがって「独立」よりも、次の項目を具体的に報告するほうがよい。

- 使用したrefinement familyとcharacteristic \(h\)
- refinement ratio
- 各格子のcell/DOF規模
- 格子qualityと境界層の解像度
- 各QoIの値と相対変化
- observed orderまたはerror estimate
- 最終格子を選択した許容基準

二つの格子の値が似ているという事実だけでは不十分だ。偶然の誤差相殺、non-monotonic convergence、同じ解像度のボトルネックが存在し得る。可能なら三水準以上を使い、格子がtopologyとstretching ruleを共有するsystematic refinement familyであることを確認する。

### 局所量と積分量は異なる形で収束する

domain averageやintegral fluxが安定していても、point maximum、gradient、不連続位置は収束が遅い場合がある。mesh studyは報告対象のQoIごとに行う。異なる格子で「最大値の位置」が移動するなら、同じindexのcell値を直接比較してはならない。

## 6. 時間刻み独立性と空間・時間誤差の組み合わせ

時間刻み\(\Delta t\)についても、

$$
\phi(\Delta t)=\phi_0+C_t(\Delta t)^q+\cdots
$$

という形のrefinement studyを実施できる。ただし、空間誤差が大きい状態では時間刻みを小さくしても変化が現れず、その逆も同様である。

実用的な順序は次のとおりだ。

1. 十分に小さい\(\Delta t\)を用いて空間refinementを評価する。
2. 選択したfine meshで\(\Delta t\) refinementを評価する。
3. 最終的な組み合わせの周辺でmeshと\(\Delta t\)を同時に変え、interactionを確認する。
4. adaptive time steppingを用いる場合は、nominal step一つではなく、tolerance、accepted step history、rejected stepを記録する。

安定性条件を満たすことと、精度が十分であることは別である。implicit methodが大きな時間刻みで発散しないからといって、transient phaseとpeak timeを正確に解像しているとは限らない。

## 7. 保存性：収束グラフとは独立した強い証拠

保存型問題のcontrol volume \(\Omega\)における一般的なbalanceは、

$$
\frac{d}{dt}\int_{\Omega}U\,d\Omega
+
\int_{\partial\Omega}F\cdot n\,dS
=
\int_{\Omega}S\,d\Omega
$$

である。discrete calculationでは、一定の時間区間について

$$
\Delta \text{storage}
+\text{net outflow}
-\text{source}
=
\text{balance defect}
$$

を計算する。

絶対defectだけを報告すると、規模が異なるcaseを比較しにくい。代表的なfluxまたはstorage changeで割ったnormalized balance errorも併せて調べる。ただしdenominatorが0に近いと相対誤差が発散するため、絶対値とscaleを一緒に示す。

保存性は必要条件であって十分条件ではない。異なる位置に同じ総量を誤って分配しても、global conservationは成立し得る。したがって、次の層を区別する。

- local cell balance
- 境界ごとのflux balance
- global domain balance
- 種・成分ごとのbalance
- エネルギー・質量・運動量などのcoupled balance

## 8. Validation比較の設計方法

### validation metricを事前に定める

図を見て「似ている」と判断せず、QoIとmetricを先に定める。例：

- biasとnormalized error
- profile norm
- peak magnitudeと位置
- integral quantity
- temporal phase error
- coverageまたはprobabilistic score

### 不確実性を合成する

計算と測定の差

$$
E=S-D
$$

を解釈するときは、simulation numerical uncertainty、input uncertainty、measurement uncertaintyを併せて考慮する。\(|E|\)が小さいというだけでモデルが正しいと断定することはできず、uncertainty bandが非常に広く、差を覆い隠していないかも確認すべきである。

### validation domainを明示する

検証した条件範囲の外へextrapolateすると、根拠の強さは低下する。入力空間、boundary regime、dimensionless group、material/stateの範囲を記録し、prediction pointがvalidation domainからどれほど離れているかを評価する。

## 9. 推奨V&Vワークフロー

1. **利用目的と許容誤差の定義**：どの意思決定にどのQoIを使うかを記す。
2. **モデル階層の作成**：governing equation、closure、boundary/initial condition、parameter sourceを区別する。
3. **code verification**：unit test、exact/MMS、limiting case、benchmarkで実装を試験する。
4. **iterative convergence**：equation residualとQoI historyを併せて確認する。
5. **空間refinement**：systematic mesh familyで三水準以上を比較する。
6. **時間refinement**：temporal QoI、phase、peak timingを含める。
7. **保存性検査**：local・boundary・global balanceを自動計算する。
8. **入力不確実性の伝播**：validation comparisonにinput uncertaintyを反映する。
9. **独立したvalidation**：calibrationに使っていないデータと事前定義したmetricで比較する。
10. **適用範囲と限界の記録**：検証されていないregimeとdominant uncertaintyを明らかにする。

## 10. 検証チェックリスト

- [ ] verification、validation、calibrationを区別したか。
- [ ] 意思決定に使うQoIとtoleranceを先に定義したか。
- [ ] analytic/MMS testがproduction codeの主要なtermを有効にしているか。
- [ ] iterative errorが格子間の差より十分に小さいか。
- [ ] 最低三水準のsystematic refinementを使ったか。
- [ ] theoretical orderだけでなくobserved orderも確認したか。
- [ ] monotonic、oscillatory、divergent convergenceを区別したか。
- [ ] 空間と時間のrefinementをそれぞれ実施したか。
- [ ] globalだけでなくlocal/boundary conservationも確認したか。
- [ ] calibrationとvalidationのデータを分離したか。
- [ ] measurement・input・numerical uncertaintyを併せて報告したか。
- [ ] validation domain外へのextrapolationを明示したか。

## 11. よくある落とし穴

### Residualが小さいため正解だという結論

residualが示すのは、discrete algebraic equationをどの程度正確に解いたかだけであり、discretization errorやmodel-form errorは分からない。

### 格子を二つだけ比較して独立性を宣言

二つの値の偶然の一致は、収束次数や漸近領域を立証しない。三水準以上と収束パターンが必要である。

### すべてのfieldを一つのmetricで評価

平均値がよく一致しても、peak、gradient、phaseが誤っている場合がある。目的に合う複数のQoIが必要だ。

### Calibration性能をvalidation性能として報告

parameterを合わせたデータに対する適合度はcalibrationの結果である。predictive adequacyを調べるには独立した情報が必要だ。

### より細かい格子は常により正確だという仮定

誤ったboundary condition、緩いiterative tolerance、低いmesh quality、不安定なschemeがあれば、DOFを増やすだけでは精度は保証されない。

## 12. 限界と報告原則

複雑な非線形・マルチスケール問題では、明確な漸近領域に到達できないことがある。discontinuity、moving interface、chaotic dynamics、adaptive meshは、単純なRichardson解析の前提を弱める。この場合、「正確な誤差を一つ」無理に示すのではなく、複数の解像度で結論がどの程度安定しているか、どの誤差源が支配的か、何を確認できなかったかを透明性をもって報告する。

V&Vの成果物は合格印ではない。**結論を支える証拠のネットワーク**である。図よりもsolver tolerance、refinement family、balance defect、uncertainty、適用範囲が重要なのはそのためだ。
