---
title: "最小二乗法を正しく使う：射影、条件数、QR、SVD"
date: 2026-07-21 09:10:00 +0900
categories: [Mathematics, Numerical Linear Algebra]
tags: [least-squares, projection, conditioning, qr, svd, pseudoinverse, regularization]
description: "最小二乗法を直交射影問題として解釈し、条件数、QR、SVD、擬似逆行列、正則化を数値安定性の観点から結び付ける。"
math: true
lang: ja-JP
translation_key: least-squares-projection-conditioning-svd
hidden: true
---

{% include language-switcher.html %}

観測式 \(Ax=b\) を厳密に解けない場合、一般に「両辺に \(A^\mathsf T\) を掛ける」と教わる。しかし、最小二乗法の本質は公式の暗記ではなく、三つの問いにある。

1. 何を最小化しているのか。
2. なぜ解がcolumn spaceへの直交射影と結び付くのか。
3. 同じ数学的な解を、どのアルゴリズムで計算すれば安定するのか。

本稿では、最小二乗法の幾何学、normal equationの危険性、QRとSVDの役割、rank deficiencyとregularizationを一つの流れに沿って整理する。

## 1. 最小二乗問題の定義

\(A\in\mathbb R^{m\times n}\)、\(b\in\mathbb R^m\) に対して、overdetermined system \(Ax=b\) は一般に厳密解を持たない。最小二乗法はresidual

$$
r(x)=b-Ax
$$

のEuclidean normを最小化する。

$$
x_\star
=
\arg\min_x \|Ax-b\|_2^2.
$$

\(Ax\) は常に \(\mathcal C(A)\)、すなわち \(A\) のcolumn space内にある。したがって、この問題は \(b\) に最も近いcolumn-spaceの要素 \(\hat b=Ax_\star\) を見つける問題である。

## 2. 直交射影とnormal equation

最も近い点では、residual \(r_\star=b-Ax_\star\) はcolumn spaceのすべての方向と直交する。

$$
A^\mathsf T r_\star=0.
$$

これを展開すると、normal equationが得られる。

$$
A^\mathsf T A x_\star=A^\mathsf T b.
$$

\(A\) がfull column rankであれば、\(A^\mathsf T A\) は正定値であり、解は一意である。

$$
x_\star=(A^\mathsf T A)^{-1}A^\mathsf T b.
$$

ただし、この式は**数学的表現**であり、推奨される計算手順ではない。実際のコードでinverseを明示的に作ることも、精度を重視する問題で無条件にnormal equationを解くことも、避ける方がよい。

射影行列は

$$
P=A(A^\mathsf T A)^{-1}A^\mathsf T
$$

であり、\(\hat b=Pb\) である。full column rankの場合、\(P\) は

$$
P^\mathsf T=P,\qquad P^2=P
$$

を満たす。対称性は直交射影であることを、idempotenceは一度射影したものを再び射影しても変わらないことを意味する。

## 3. 単純な回帰の例

一次モデル \(y\approx\beta_0+\beta_1t\) を複数の点に適合させるとする。design matrixは

$$
A=
\begin{bmatrix}
1&t_1\\
1&t_2\\
\vdots&\vdots\\
1&t_m
\end{bmatrix},
\qquad
x=
\begin{bmatrix}\beta_0\\\beta_1\end{bmatrix},
\qquad
b=
\begin{bmatrix}y_1\\y_2\\\vdots\\y_m\end{bmatrix}.
$$

最小二乗解が最小化するのは、データ点と直線の間の**垂直距離**ではなく、指定した \(y\) 方向のresidualの二乗和である。両軸に誤差がある場合は、orthogonal distance regressionやerrors-in-variables modelの方が適切なことがある。

また、\(t\) の絶対値が非常に大きい場合や、範囲が一方に偏っている場合、intercept columnとslope columnを数値的に区別しにくくなることがある。\(t\) を中心化し、適切にscalingすれば、条件数と係数の解釈が改善する。

## 4. 条件数：入力誤差が解でどれだけ増幅されるか

可逆正方行列の2-norm条件数は

$$
\kappa_2(A)
=
\|A\|_2\|A^{-1}\|_2
=
\frac{\sigma_{\max}}{\sigma_{\min}}
$$

である。長方形のfull-column-rank行列でも、最大のsingular valueと最小のnonzero singular valueの比として、同じ意味を持つ。

条件数が大きいと、次の現象が生じる。

- 入力 \(b\) の小さな誤差が \(x\) で大きく増幅される。
- 互いにほぼ同じcolumnが存在し、係数が大きく変動する。
- residualは小さくても、parameter estimateは不安定な場合がある。
- 浮動小数点の丸め誤差の影響が大きくなる。

normal equationには決定的な問題がある。

$$
\kappa_2(A^\mathsf T A)=\kappa_2(A)^2.
$$

すなわち、すでに悪い条件数が二乗される。また、\(A^\mathsf T A\) を作る過程で有効桁を失う可能性がある。

> 小さなresidualと正確なparameterは、同じ意味ではない。\(b\) がcolumn spaceに近くても、column同士がほぼ従属していれば、大きく異なる係数が似た予測を生み出し得る。

## 5. QRで最小二乗問題を解く

\(A\) がfull column rankであり、

$$
A=QR,
$$

ここで \(Q\in\mathbb R^{m\times n}\) の列が正規直交し、\(R\in\mathbb R^{n\times n}\) がupper triangularであるとする。このとき、

$$
\|Ax-b\|_2^2
=
\|Rx-Q^\mathsf Tb\|_2^2
+\|(I-QQ^\mathsf T)b\|_2^2.
$$

第2項は \(x\) に依存しないため、

$$
Rx=Q^\mathsf T b
$$

をback substitutionで解けばよい。

実践では、classical Gram–SchmidtよりHouseholder QRの方が一般に安定している。rankが疑われる場合は、column-pivoted QR

$$
AP=QR
$$

を用いて重要なcolumnを前方に集め、effective rankを診断できる。

## 6. SVDと擬似逆行列

SVDは、

$$
A=U\Sigma V^\mathsf T
$$

として行列を分解する。\(U\) と \(V\) の列は正規直交し、\(\Sigma\) の対角要素 \(\sigma_i\) はsingular valueである。

Moore–Penrose pseudoinverseは

$$
A^+=V\Sigma^+U^\mathsf T
$$

であり、最小二乗解のうち最小norm解は

$$
x_\star=A^+b
=
\sum_{\sigma_i>0}
\frac{u_i^\mathsf Tb}{\sigma_i}v_i
$$

である。

この式は、ill-conditioningの原因を直接示している。小さな \(\sigma_i\) の方向では、\(u_i^\mathsf Tb\) の小さなノイズも \(1/\sigma_i\) 倍に増幅される。

### SVDが特に有用な場合

- rank deficiencyがある場合、または疑われる場合
- null spaceとidentifiable directionを確認したい場合
- 最小norm解が必要な場合
- singular spectrumで条件を診断する場合
- truncated SVDのようなregularizationを適用する場合

SVDは診断能力が最も高いが、QRより計算量とメモリコストが大きい場合がある。問題の大きさ、sparsity、必要な精度に応じて選択する。

## 7. rank deficiencyと解の非一意性

\(\operatorname{rank}(A)<n\) であれば、異なる \(x\) が同じ \(Ax\) を生成し得る。\(z\in\mathcal N(A)\) なら、

$$
A(x+z)=Ax
$$

であるため、ある最小二乗解に対して \(x+z\) も同じresidualを持つ。pseudoinverse解は、その中から \(\|x\|_2\) が最も小さい解を選ぶ。

数値データでは、rankは二値的ではない。singular value cutoffを \(\tau\) とすると、

$$
\sigma_i\le\tau
$$

となる方向を捨てることができるが、\(\tau\) は単なる実装上の詳細ではなく、どの方向を識別不能と見なすかを決めるモデリング上の選択である。scale、noiseの水準、目的を反映する必要がある。

## 8. weighted least squaresとcovariance

residual成分の分散が異なる場合や、互いに相関している場合、一般最小二乗法の等しい重みという仮定は適切でない。誤差covarianceを \(\Sigma_b\) とすると、

$$
x_\star
=
\arg\min_x
(Ax-b)^\mathsf T\Sigma_b^{-1}(Ax-b).
$$

\(W^\mathsf TW=\Sigma_b^{-1}\) であるwhitening matrixを用いれば、

$$
\min_x\|W(Ax-b)\|_2^2
$$

に変わる。ここで重みは便宜的に決めるスコアではなく、residualの確率構造と結び付いていなければならない。

## 9. regularizationは数値的な小細工ではなく追加の仮定である

Tikhonov regularizationは、

$$
x_\lambda
=
\arg\min_x
\left(
\|Ax-b\|_2^2
+\lambda^2\|L(x-x_0)\|_2^2
\right)
$$

と書ける。

- \(x_0\)：priorまたは基準解
- \(L\)：penalizeする構造
- \(\lambda\)：データ適合とpriorの間のバランス

\(L=I\)、\(x_0=0\) ならridge形式である。regularizationは分散を減らす代わりにbiasを導入する。したがって、「条件数が悪いから任意の小さな値を足す」のではなく、どのような解がより妥当かを明示するモデリング段階として扱う必要がある。

\(\lambda\) はcross-validation、discrepancy principle、L-curve、generalized cross-validationなどで決定できる。どの方法でも、選択基準と評価データの独立性を記録する。

## 10. アルゴリズム選択ガイド

| 状況 | 優先的に検討 | 理由 |
|---|---|---|
| dense, full rank, 通常の条件 | Householder QR | 安定性とコストのバランス |
| rankが不明確, 診断が重要 | SVD | singular spectrumとnull spaceの確認 |
| column rankの判定が必要 | pivoted QRまたはSVD | effective rankの推定 |
| 非常に大規模なsparse問題 | iterative least-squares solver | 行列分解コストの回避 |
| covariance構造が存在 | whitened/weighted least squares | 誤差モデルの反映 |
| ill-posed inverse problem | regularized solver | 不安定な方向の抑制 |
| 速度が最優先で条件が良好 | Cholesky on normal equationsを慎重に検討 | 高速だが条件数を二乗するリスク |

「inverseを計算してから掛ける」より、線形システムを直接解く関数が基本的な選択となる。libraryの `solve`、`lstsq`、sparse solverは、内部のfactorizationと例外処理を活用する。

## 11. 実践ワークフロー

1. **目的の定義**：predictionが重要か、parameter interpretationが重要か。
2. **次元と単位の確認**：\(A\)、\(x\)、\(b\) のshapeと物理単位を記す。
3. **scaling**：column norm、変数の範囲、単位を点検し、必要に応じて中心化・標準化する。
4. **rank診断**：QR pivotまたはsingular spectrumを確認する。
5. **solver選択**：基本はQRとし、rank/ill-conditioningの診断にはSVDを検討する。
6. **residual分析**：norm一つだけでなく、構造、bias、heteroscedasticity、correlationを見る。
7. **orthogonalityの検証**：\(A^\mathsf Tr\) がtolerance内で0か確認する。
8. **感度の確認**：入力を許容範囲内で摂動させたとき、係数と予測がどれだけ変化するかを見る。
9. **不確実性の報告**：noise modelとcovarianceの仮定が妥当な場合、parameter uncertaintyを計算する。
10. **再現性の記録**：solver、tolerance、scaling、rank cutoff、regularizationの選択方法を残す。

## 12. 検証チェックリスト

- [ ] 最小化するnormと重みを明示したか。
- [ ] \(Ax_\star\) がcolumn space内にあり、\(A^\mathsf Tr\approx0\) か。
- [ ] full rankを仮定した場合、実際に確認したか。
- [ ] \(A^\mathsf TA\) のinverseを明示的に作っていないか。
- [ ] column scaling前後の条件数を比較したか。
- [ ] singular valueとcutoffを併せて記録したか。
- [ ] residualの大きさとparameterの安定性を別々に評価したか。
- [ ] regularization parameterを評価データに過適合させていないか。
- [ ] weighted least squaresのweightが誤差モデルと一致しているか。
- [ ] 予測区間とparameter信頼区間を混同していないか。

## 13. 落とし穴と限界

### \(R^2\) が高ければ問題をうまく解けたという誤解

高い説明力は、残差の独立性、モデルの適合性、parameter identifiabilityを保証しない。extrapolationでは特に危険である。

### 入力の単位を変えて係数の大きさを直接比較する

coefficient magnitudeは変数のscaleに依存する。重要度を比較する前に、単位とscalingを揃える必要がある。

### pseudoinverseが「真の解」を復元するという誤解

pseudoinverseは、明確な最適化基準に基づいて代表解を選択するだけであり、データが失ったnull-spaceの情報を復活させるものではない。

### regularizationでモデル構造の誤りを隠す

regularizationはill-posednessを緩和するが、欠落した変数、誤ったobservation operator、systematic biasを解決するものではない。

### 線形化された最小二乗法の限界

非線形モデル \(f(x)\) では、local linearizationと反復最適化が必要である。初期値、local minimum、Jacobian conditioningも追加で重要になる。

## まとめ

最小二乗法は「誤差二乗和を減らす公式」ではなく、**部分空間への射影問題**である。QRはその射影を安定して計算する基本ツールであり、SVDはrankと不安定な方向を明らかにする診断ツールである。条件数は計算を信頼できるかを問う指標であり、regularizationは不足した情報の代わりに、どのような仮定を追加したかを明示する仕組みである。

結果の数値一つよりも、residual orthogonality、singular spectrum、scaling、solver、toleranceを併せて残すことで、最小二乗法は再現可能な分析となる。
