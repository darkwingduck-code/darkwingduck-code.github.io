---
title: "有限要素法の骨格：弱形式、要素、数値積分とメッシュ収束"
date: 2026-07-21 12:43:00 +0900
categories: [Scientific Computing, Finite Element Method]
tags: [fem, weak-form, galerkin, finite-element, quadrature, mesh-convergence]
description: "強形式から弱形式を導出し、関数空間・境界条件・要素補間・数値積分・組立・線形解法・メッシュ収束まで、FEMの中核構造を結び付ける。"
math: true
mermaid: true
lang: ja-JP
translation_key: fem-weak-form-elements-quadrature-mesh-convergence
hidden: true
---

{% include language-switcher.html %}

有限要素法（FEM）は、形状を小さな断片に分割するだけの手法ではない。
微分方程式を積分可能な弱い形に変換し、無限次元関数空間の問題を有限次元部分空間へ射影する方法である。
この観点を身に付けると、要素の種類とsolver optionが一つの数学的構造として結び付く。

## 1. 強形式から始める

Poisson問題を例に取る。

$$
-\nabla\cdot(k\nabla u)=f \quad \text{in }\Omega,
$$

$$
u=g_D \quad \text{on }\Gamma_D,
\qquad
-k\nabla u\cdot n=g_N \quad \text{on }\Gamma_N.
$$

強形式は、(u) が各点で十分に微分可能であり、方程式と境界条件を各点で満たすことを要求する。
複雑な係数、不連続な材料、非平滑なdomainでは、この要求が強すぎる場合がある。

## 2. 試験関数と部分積分

Dirichlet境界で0となる試験関数 (v) を掛けて積分する。

$$
\int_\Omega -v\nabla\cdot(k\nabla u)\,d\Omega
=\int_\Omega vf\,d\Omega.
$$

部分積分またはGreen identityを適用すると、

$$
\int_\Omega k\nabla v\cdot\nabla u\,d\Omega
-\int_{\partial\Omega}v k\nabla u\cdot n\,d\Gamma
=\int_\Omega vf\,d\Omega.
$$

Neumann条件を代入すると、弱形式は

$$
a(u,v)=\ell(v)
$$

$$
a(u,v)=\int_\Omega k\nabla v\cdot\nabla u\,d\Omega,
$$

$$
\ell(v)=\int_\Omega vf\,d\Omega+\int_{\Gamma_N}vg_N\,d\Gamma
$$

となる。
(u) の微分次数は2階から1階へ下がり、natural boundary conditionは境界積分に組み込まれた。

## 3. essentialとnatural boundary condition

- Dirichlet条件はtrial spaceそのものを制限するため、essential conditionと呼ばれる。
- Neumann条件は弱形式の右辺に自然に現れるため、natural conditionと呼ばれる。

この区別は実装でも重要である。
Dirichlet自由度を行列から除去する場合やconstraintとして扱う場合は、symmetryとreactionの計算を保つ必要がある。

純粋なNeumann問題では、定数分だけ移動した解がすべて許されるため、nullspaceが生じる。
compatibility condition

$$
\int_\Omega f\,d\Omega+\int_{\Gamma_N}g_N\,d\Gamma=0
$$

と、平均値constraintまたはreferenceが必要になる。

## 4. 関数空間の意味

Poisson問題の自然な空間はSobolev空間 (H^1(\Omega)) である。

$$
H^1(\Omega)=
\{v\in L^2(\Omega):\nabla v\in[L^2(\Omega)]^d\}.
$$

すなわち、関数と1階弱微分が二乗可積分であればよい。
各点での滑らかさよりも、積分可能なenergy normが重要である。

Galerkin FEMでは、trialとtest spaceに同じ有限次元部分空間を使用する。

$$
V_h=\mathrm{span}\{N_1,\ldots,N_n\}.
$$

## 5. 要素補間と自由度

近似解を

$$
u_h(\mathbf x)=\sum_{j=1}^{n}N_j(\mathbf x)U_j
$$

と表す。
各 (N_j) はshape functionで、(U_j) はnodal valueまたは一般化自由度である。

各basis (N_i) を試験関数に代入すると、

$$
K_{ij}=\int_\Omega k\nabla N_i\cdot\nabla N_j\,d\Omega,
\qquad
F_i=\ell(N_i)
$$

となり、全体システムは

$$
\mathbf K\mathbf U=\mathbf F
$$

となる。

## 6. reference elementとmapping

実要素 (Omega_e) をreference element (hat\Omega) からmappingする。

$$
\mathbf x(\boldsymbol\xi)=
\sum_a N_a(\boldsymbol\xi)\mathbf x_a.
$$

Jacobianは

$$
J=\frac{\partial\mathbf x}{\partial\boldsymbol\xi}
$$

であり、gradientとvolume elementを変換する。

$$
\nabla_x N=J^{-T}\nabla_\xi N,
\qquad
d\Omega=|\det J|d\hat\Omega.
$$

(det J\le0) の要素は反転しているか、退化している。
小さなdeterminantと大きなcondition numberは、gradientの計算とstiffness conditioningを悪化させる。

## 7. 数値積分はモデルの一部である

要素積分をquadratureで近似する。

$$
\int_{\hat\Omega}g(\xi)d\xi
\approx
\sum_{q=1}^{n_q}w_q g(\xi_q).
$$

積分次数が低すぎると、stiffnessとinternal forceを正確に構成できず、hourglassまたはzero-energy modeが生じる可能性がある。
反対に、過剰なquadratureはコストを増すだけで、lockingを解決できない場合がある。

### reduced integrationとselective integration

reduced integrationはlockingを緩和できるが、spurious modeのリスクがある。
stabilizationが物理エネルギーを汚染していないか確認する必要がある。

### 非線形材料と数値積分点

内部状態変数は、通常quadrature pointで更新される。
consistent tangentを用いると、Newton収束を大幅に改善できる。
state update、rollback、load-step retryの整合性が重要である。

## 8. 組立はlocal-to-globalの保存規約である

各要素行列 (mathbf K^e) とベクトル (mathbf F^e) を、自由度mappingによって全体システムに加える。

```mermaid
flowchart LR
  A[reference element] --> B[geometry mapping]
  B --> C[quadrature pointでの評価]
  C --> D[element matrix/vector]
  D --> E[local-to-global assembly]
  E --> F[constraintsとboundary terms]
  F --> G[linear/nonlinear solve]
  G --> H[errorとbalanceの検査]
```

共有nodeの自由度には、隣接要素からの寄与を合算する。
符号とorientationを持つedge/face elementでは、local orientationを全体規約と一致させなければならない。

## 9. 適合性、安定性、locking

単にpolynomial orderが高ければ、すべての問題が解決するわけではない。

- **conformity**：近似空間が必要な連続性を満たしているか。
- **coercivity/inf-sup stability**：離散問題は安定しているか。
- **locking**：薄い構造やほぼ非圧縮の条件で、過度にstiffになっていないか。
- **spurious mode**：物理的なエネルギーを伴わずに変形するmodeが存在するか。

混合型問題では、displacementとpressureの空間の組み合わせがinf-sup条件を満たさなければならない。
同一次数のinterpolationを無条件に使用すると、pressure oscillationが生じる可能性がある。

## 10. h-、p-、hp-refinement

- h-refinement：要素サイズを小さくする。
- p-refinement：basisの次数を高める。
- hp-refinement：smoothnessに応じて両者を組み合わせる。

energy normにおける典型的な誤差は、十分なregularityのもとで

$$
\|u-u_h\|_{H^1}\le C h^p|u|_{H^{p+1}}
$$

という形になる。
corner singularity、discontinuous coefficient、contactではregularityが低く、nominal orderが現れない場合がある。

## 11. a prioriとa posteriori error

a priori estimateは、解のregularityとmesh sizeによって収束率を説明する。
a posteriori estimatorは、計算された解のresidualとjumpに基づいて、どこをrefineするかを決定する。

概念的なresidual estimatorは、

$$
\eta^2=\sum_e h_e^2\|R_e\|^2
+\sum_f h_f\|J_f\|^2
$$

のように、element residual (R_e) とinter-element flux jump (J_f) を組み合わせる。
effectivity indexが問題群に対して安定しているか、benchmarkで確認する必要がある。

## 12. 非線形問題とNewton法

残差ベクトルを (mathbf R(\mathbf U)=0) とすると、Newton stepは

$$
\mathbf J(\mathbf U^k)\Delta\mathbf U
=-\mathbf R(\mathbf U^k),
$$

$$
\mathbf U^{k+1}=\mathbf U^k+\alpha\Delta\mathbf U
$$

となる。
consistent Jacobian、line search、load/time increment control、state rollbackがロバスト性を左右する。

## 13. 推奨ワークフロー

1. 強形式、domain、boundary partitionを明示する。
2. 試験関数を掛け、部分積分して弱形式を手で導出する。
3. trial/test spaceとessential constraintを定義する。
4. reference element、mapping、shape functionを検証する。
5. quadrature orderをintegrandと非線形性に合わせる。
6. element-level patch testとmanufactured solutionを実施する。
7. 全体balance、reaction、energyを検査する。
8. 3水準以上のsystematic refinementを実施する。
9. QoIごとの収束とerror estimatorを報告する。

## 14. 検証チェックリスト

- [ ] 弱形式の境界項の符号を再導出した。
- [ ] essentialとnatural boundary conditionを区別した。
- [ ] pure Neumann nullspaceとcompatibilityを処理した。
- [ ] reference-to-physical Jacobianの方向が一貫している。
- [ ] すべての要素のdeterminantが正で、十分に大きい。
- [ ] rigid-body modeとexpected nullspaceを確認した。
- [ ] patch testとconstant-state testに合格した。
- [ ] quadrature order sensitivityを評価した。
- [ ] reactionの総和と外力がbalanceしている。
- [ ] strain energyとworkの整合性を確認した。
- [ ] hまたはp refinementでobserved orderを計算した。
- [ ] point singularityの値を、収束したQoIとして報告しない。

## 15. よくある失敗パターンと限界

### meshを細かくするだけ

distorted elementを増やしたり、singularityに一様refinementだけを適用したりすると、コストに対する効果は低い。

### contourが滑らかなら正確だと判断する

後処理のnodal averagingにより、discontinuous stressが滑らかに見える場合がある。
元のquadrature-point値とequilibriumを確認する必要がある。

### reduced integrationを万能の解決策として使う

lockingを減らす代わりに、hourglass modeが生じる可能性がある。
stabilization energyとmesh sensitivityを併せて確認する。

### solver toleranceとdiscretization errorを混同する

linear residualが小さくても、mesh errorは大きい場合がある。
反対に、algebraic errorが大きい状態でmesh refinementを比較すると、observed orderが汚染される。

### 特定pointの最大応力だけを比較する

re-entrant cornerやconcentrated loadでは、point stressが発散する可能性がある。
integral、averaged、fracture parameterのようなwell-defined QoIを選択する。

## 16. 公式資料・原典

- Galerkin, B. G., “Series Solution of Some Problems of Elastic Equilibrium,” 1915.
- Courant, R., “Variational Methods for the Solution of Problems of Equilibrium and Vibrations,” 1943.
- Ciarlet, P. G., *The Finite Element Method for Elliptic Problems*.
- NIST, [OOF finite-element analysis documentation](https://www.ctcms.nist.gov/oof/oof2/).
- PETSc, [Finite element and discretization interfaces](https://petsc.org/release/manual/dmplex/).
- The FEniCS Project, [Official documentation](https://docs.fenicsproject.org/).

FEMの核心は要素の形状ではなく、**弱形式、関数空間、数値積分、組立、誤差推定が一つの一貫した近似問題を構成しているか**にある。
