---
title: "DOE부터 UQ·Calibration까지: 시뮬레이션 연구 설계의 전체 지도"
date: 2026-07-21 09:30:00 +0900
categories: [Scientific Computing, Research Methods]
tags: [doe, sensitivity-analysis, uncertainty-quantification, calibration, identifiability, surrogate-model]
description: "실험계획법, 국소·전역 민감도, 불확실성 전파, parameter calibration을 구분하고 하나의 재현 가능한 시뮬레이션 연구 절차로 연결한다."
math: true
lang: ko-KR
translation_key: doe-sensitivity-uq-calibration
---

{% include language-switcher.html %}

시뮬레이션 입력을 몇 개 바꾸고 출력 곡선을 비교하는 것만으로는 강한 결론을 만들기 어렵다. 변수 효과, interaction, 입력 불확실성, parameter 추정, 모델 오차가 한꺼번에 섞이기 때문이다.

이를 분리하려면 네 가지 도구의 역할을 먼저 구분해야 한다.

- **Design of Experiments(DOE)**: 어느 입력 조합에서 계산하거나 측정할지 정한다.
- **Sensitivity analysis(SA)**: 출력 변동을 어떤 입력이 얼마나 설명하는지 묻는다.
- **Uncertainty Quantification(UQ)**: 입력·모델의 불확실성이 출력 불확실성으로 어떻게 전파되는지 묻는다.
- **Calibration**: 관측을 이용해 알 수 없는 parameter를 추정한다.

이들은 서로 보완하지만 대체 관계가 아니다. DOE를 잘했다고 uncertainty가 자동으로 정량화되지 않고, calibration이 잘 맞았다고 validation이 끝난 것도 아니다.

## 1. 가장 먼저 만들 표: 입력과 불확실성의 분류

모든 입력 \(x=(x_1,\dots,x_d)\)를 한 종류로 다루지 않는다.

| 분류 | 의미 | 대표 처리 |
|---|---|---|
| controllable factor | 설계자가 수준을 선택 | factorial, optimal design |
| scenario/context variable | 관심 범위는 있으나 직접 제어하지 않음 | blocking, stratification |
| aleatory variable | 본질적 변동으로 모델링 | 확률분포와 forward propagation |
| epistemic parameter | 지식 부족으로 불확실 | calibration, interval/prior update |
| nuisance parameter | 관심 대상은 아니나 결과에 영향 | marginalization, profiling |
| model discrepancy | 방정식 구조가 현실과 다른 부분 | 별도 discrepancy model 또는 bias budget |

같은 물리량도 목적에 따라 분류가 달라질 수 있다. 중요한 것은 이름보다 **어떤 정보를 이용해 어떻게 갱신할 것인지**를 사전에 정하는 것이다.

각 입력에는 최소한 다음 metadata가 필요하다.

- 정의와 단위
- 허용 범위와 근거
- 분포 또는 설계 수준
- 입력 간 상관·제약
- 고정값인지 추정값인지
- 측정 가능한지
- 모델의 어느 위치에 들어가는지

## 2. DOE: 실행 예산을 정보로 바꾸는 설계

### One-factor-at-a-time의 한계

한 번에 한 변수만 바꾸는 OFAT는 이해하기 쉽지만 interaction을 놓친다. 예를 들어

$$
y=\beta_0+\beta_1x_1+\beta_2x_2+\beta_{12}x_1x_2
$$

에서 \(\beta_{12}\)가 크면 \(x_1\)의 효과는 \(x_2\) 수준에 따라 달라진다. 기준점 하나에서의 OFAT로는 이 구조를 식별하기 어렵다.

### 설계 종류와 목적

| 설계 | 장점 | 주의점 |
|---|---|---|
| full factorial | main effect와 interaction을 체계적으로 추정 | 차원이 늘면 실행 수 폭증 |
| fractional factorial | 적은 실행으로 screening | alias structure를 반드시 해석 |
| central composite / Box–Behnken | quadratic response surface에 효율적 | 지정 영역 밖 extrapolation 취약 |
| Latin hypercube | 각 축을 고르게 층화 | projection quality와 correlation 확인 |
| low-discrepancy sequence | integration·global SA에 유리 | 독립 random replicate와 구분 |
| D-/I-optimal design | 특정 회귀모형 목적에 최적화 | 가정한 모델이 틀리면 효율 저하 |
| adaptive/sequential design | 불확실하거나 중요한 영역에 예산 집중 | stopping rule과 selection bias 관리 |

DOE는 “공간을 고르게 채우기”만을 뜻하지 않는다. screening, surrogate 학습, 최적화, parameter 식별, validation 중 무엇이 목적인지에 따라 좋은 설계가 달라진다.

### Randomization, replication, blocking

- **Randomization**은 시간 drift나 순서 효과가 특정 factor와 confounding되는 것을 줄인다.
- **Replication**은 동일 조건의 변동을 추정한다. 완전 deterministic simulator라면 같은 binary·환경에서 단순 반복은 새 정보를 주지 않지만, stochastic solver나 nondeterministic execution이면 필요하다.
- **Blocking**은 장비, batch, 날짜, mesh family처럼 제거하기 어려운 nuisance variation을 분리한다.

simulation campaign에서도 run order, compute environment, solver version이 block 또는 provenance 변수가 될 수 있다.

## 3. Sensitivity analysis: 영향의 정의부터 선택한다

“가장 중요한 변수”는 metric에 따라 달라진다.

### Local sensitivity

기준점 \(x_0\) 주변의 미분

$$
S_i^{\mathrm{local}}
=
\left.
\frac{\partial f}{\partial x_i}
\right|_{x=x_0}
$$

은 작은 perturbation의 영향을 말한다. 단위가 다르면

$$
S_i^{\mathrm{scaled}}
=
\frac{x_i}{f}
\frac{\partial f}{\partial x_i}
$$

같은 무차원 지표를 고려할 수 있다.

local derivative는 gradient 기반 최적화와 linearized uncertainty에 효율적이지만 nonlinearity, threshold, interaction, 기준점 의존성을 놓칠 수 있다.

### Screening: Morris 계열

각 입력을 여러 위치에서 한 번씩 이동시킨 elementary effect를 모으면 평균 절댓값은 전반적 영향, 분산은 nonlinearity나 interaction 가능성을 나타낸다. 고차원에서 중요하지 않은 변수를 거르는 데 유용하지만 정확한 variance decomposition은 아니다.

### Global variance-based sensitivity

입력들이 독립이라고 가정할 때 출력 분산은 ANOVA 형태로 분해할 수 있다.

$$
\operatorname{Var}(Y)
=
\sum_i V_i
+\sum_{i<j}V_{ij}
+\cdots
$$

first-order Sobol index와 total-effect index는

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

로 쓸 수 있다. \(S_i\)는 \(X_i\) 단독 효과, \(S_{T_i}\)는 \(X_i\)가 관여한 모든 interaction을 포함한다. \(S_{T_i}-S_i\)가 크면 interaction이 중요하다는 신호다.

### 상관 입력의 함정

표준 Sobol 분해의 해석은 독립 입력을 전제로 한다. 실제 가능한 입력 조합에 상관이나 물리 제약이 있다면 독립 sampling이 불가능한 상태를 만들 수 있다. 이 경우 conditional sampling, grouped indices, Shapley effect 등 의존 구조를 존중하는 방법을 검토하고 사용한 joint distribution을 명시한다.

## 4. UQ: 불확실성을 출력 분포로 전파하기

forward UQ의 기본 문제는

$$
X\sim p_X(x),\qquad Y=f(X)
$$

에서 \(Y\)의 분포, 평균, 분산, quantile, failure probability를 추정하는 것이다.

### Monte Carlo

독립 sample \(x^{(j)}\)를 생성해 \(y^{(j)}=f(x^{(j)})\)를 계산한다. 차원에 비교적 둔감하고 구현이 단순하지만 rare event나 expensive simulation에서는 비용이 크다. sample 수뿐 아니라 Monte Carlo standard error 또는 confidence interval을 함께 보고한다.

### Surrogate 기반 UQ

원 모델이 비싸면 response surface, Gaussian process, polynomial chaos, neural surrogate 등을 사용한다. 이때 총 오차는 적어도 다음으로 나뉜다.

$$
\text{UQ error}
=
\text{sampling error}
+\text{surrogate error}
+\text{input-model error}
+\text{simulation numerical error}.
$$

surrogate test error 하나만 작다고 tail probability와 sensitivity index까지 정확한 것은 아니다. UQ 목적에 중요한 영역, 특히 경계·tail·constraint 부근의 오차를 따로 확인한다.

### Rare event

failure probability가 작으면 crude Monte Carlo에서 실패 sample이 거의 나오지 않는다. importance sampling, subset simulation, splitting, adaptive surrogate 같은 방법이 필요할 수 있다. proposal을 outcome을 본 뒤 임의로 조정했다면 estimator bias와 weight 계산을 점검한다.

## 5. Calibration: inverse problem으로 parameter를 추정

관측 \(d\), simulator \(f(\theta,z)\), parameter \(\theta\), 관측 조건 \(z\)가 있을 때

$$
d=f(\theta,z)+\delta(z)+\varepsilon
$$

로 쓸 수 있다.

- \(\delta(z)\): model discrepancy
- \(\varepsilon\): measurement noise

### Optimization 관점

가중 최소제곱은

$$
\hat\theta
=
\arg\min_\theta
(d-f(\theta))^\mathsf T
\Sigma^{-1}
(d-f(\theta))
$$

로 표현한다. bounds, regularization, prior penalty가 추가될 수 있다.

### Bayesian 관점

$$
p(\theta\mid d)
\propto
p(d\mid\theta)p(\theta)
$$

에서 likelihood는 측정·모델 residual 구조를, prior는 관측 전 정보를 나타낸다. 결과는 점 추정 하나가 아니라 posterior distribution이다.

Bayesian 방법도 likelihood와 discrepancy model이 틀리면 자동으로 올바른 uncertainty를 주지 않는다. posterior가 좁다는 사실은 모델 가정 아래에서 정보가 집중됐다는 뜻이지 현실의 모든 오차가 작다는 뜻이 아니다.

## 6. Identifiability: 최적화 성공과 parameter 학습은 다르다

### Structural identifiability

잡음이 전혀 없고 연속 관측이 가능하다고 가정해도 서로 다른 parameter가 같은 출력을 만들면 구조적으로 식별 불가능하다.

### Practical identifiability

이론적으로 식별 가능해도 관측 위치, 범위, noise, 입력 excitation이 부족하면 실제 데이터로 구분하기 어렵다.

진단에는 다음이 도움이 된다.

- Jacobian 또는 Fisher information의 singular spectrum
- parameter profile likelihood
- posterior correlation
- 여러 초기값에서의 최적화
- synthetic recovery test
- 새로운 관측 조건에 대한 expected information

parameter가 강하게 상관되면 개별 값은 불안정해도 특정 조합이나 prediction은 안정적일 수 있다. 목적이 parameter 자체인지 prediction인지 구분해야 한다.

## 7. Model discrepancy와 parameter의 confounding

모델 구조 오차 \(\delta(z)\)를 무시하면 parameter가 그 오차를 대신 흡수할 수 있다. 이 “effective parameter”는 calibration 조건에서는 잘 맞지만 새로운 조건에서 물리적 의미나 예측력이 사라질 수 있다.

반대로 매우 유연한 discrepancy model을 허용하면 어떤 mismatch도 \(\delta\)가 설명해 parameter를 학습하지 못한다. parameter와 discrepancy를 동시에 자유롭게 추정하는 문제는 본질적으로 confounded될 수 있다.

완화 전략은 다음과 같다.

- 다양한 조건과 관측 종류를 포함한다.
- parameter별로 민감한 QoI를 설계한다.
- 물리적 prior와 bounds를 근거와 함께 사용한다.
- discrepancy의 smoothness·구조를 제한한다.
- calibration과 validation 조건을 분리한다.
- parameter uncertainty와 predictive discrepancy를 따로 보고한다.

## 8. 하나로 연결한 권장 워크플로

### 단계 1: 목적과 출력 정의

의사결정, QoI, 허용 오차, 관심 입력 범위를 먼저 고정한다. “모델을 잘 맞춘다”가 아니라 어떤 prediction을 어느 범위에서 지원할지 적는다.

### 단계 2: 입력 audit

입력의 단위, 범위, joint distribution, 물리 제약, 정보 출처를 표로 만든다. epistemic과 aleatory를 구분하되 경계가 애매하면 여러 해석을 scenario로 둔다.

### 단계 3: screening DOE

차원이 크면 factorial/fractional design, Morris, derivative screening 등으로 영향이 작은 변수를 거른다. 이때 screening threshold와 놓칠 수 있는 interaction을 기록한다.

### 단계 4: space-filling 또는 목적지향 DOE

surrogate, global SA, calibration 중 목적에 맞게 LHS, low-discrepancy, optimal design을 선택한다. 물리적으로 불가능한 조합은 constraint-aware sampling으로 제외한다.

### 단계 5: numerical quality control

각 run의 convergence, conservation, failure code, mesh/time-step provenance를 기록한다. solver failure를 단순 삭제하면 feasible region 추정이 왜곡될 수 있으므로 failure 자체를 outcome으로 관리한다.

### 단계 6: surrogate 검증

training과 독립된 test design을 사용한다. 평균 오차뿐 아니라 worst region, tail, derivative, calibration posterior가 집중될 영역을 확인한다.

### 단계 7: global SA와 forward UQ

joint input model을 명시하고 sensitivity index의 Monte Carlo uncertainty도 계산한다. input importance 순위가 sample size와 surrogate choice에 안정적인지 본다.

### 단계 8: calibration

likelihood, prior, bounds, discrepancy 가정, optimizer/sampler 진단을 기록한다. synthetic recovery와 multi-start를 통해 identifiability를 확인한다.

### 단계 9: validation

사용하지 않은 조건·QoI에서 predictive distribution과 관측을 비교한다. calibration residual이 아니라 out-of-sample prediction을 평가한다.

### 단계 10: sequential update

현재 uncertainty를 가장 많이 줄일 다음 run 또는 measurement를 선택한다. acquisition rule과 stopping criterion을 미리 정해 무한 탐색을 막는다.

## 9. 검증 체크리스트

- [ ] DOE, sensitivity, UQ, calibration의 목적을 섞지 않았는가?
- [ ] 입력 범위와 분포에 기술적 근거가 있는가?
- [ ] 상관과 물리적 constraint를 joint sampling에 반영했는가?
- [ ] OFAT만으로 interaction이 없다고 결론내리지 않았는가?
- [ ] deterministic/stochastic 여부에 맞게 replication을 설계했는가?
- [ ] sensitivity metric의 정의와 전제를 명시했는가?
- [ ] sensitivity index 자체의 sampling uncertainty를 보고했는가?
- [ ] surrogate error를 UQ 결과에 포함하거나 별도 정량화했는가?
- [ ] calibration parameter의 identifiability를 진단했는가?
- [ ] model discrepancy가 parameter에 흡수될 가능성을 검토했는가?
- [ ] calibration과 validation 데이터를 분리했는가?
- [ ] random seed, design generator, 실행 순서, 실패 run을 보존했는가?

## 10. 흔한 함정과 한계

### 범위를 넓게 잡을수록 보수적이라는 오해

근거 없이 넓은 독립 uniform distribution을 주면 현실에 불가능한 조합이 생기고 sensitivity 순위가 인위적으로 바뀔 수 있다. 범위는 보수성뿐 아니라 joint feasibility를 반영해야 한다.

### 상관계수를 넣었으니 의존 구조를 모두 표현했다는 오해

선형 상관은 tail dependence, nonlinear constraint, multimodality를 설명하지 못할 수 있다.

### Surrogate의 평균 test score만 신뢰

작은 global RMSE가 threshold 주변, tail, gradient의 정확성을 보장하지 않는다. downstream task에 맞춘 validation metric이 필요하다.

### Parameter posterior를 물리 상수로 해석

model discrepancy를 무시한 calibration parameter는 조건 의존적인 보정값일 수 있다.

### 민감하지 않은 변수를 무조건 제거

현재 출력과 범위에서 민감하지 않다는 뜻일 뿐, 다른 QoI·regime·tail event에서도 중요하지 않다는 보장은 없다.

### 계산 예산이 작을 때 과도한 차원

고차원 global SA와 flexible calibration을 적은 run으로 동시에 수행하면 추정량이 불안정해진다. screening, 구조적 차원축소, informative measurement가 먼저다.

## 마무리

강한 시뮬레이션 연구는 많은 run보다 **정보 흐름이 분리된 run**에서 나온다. DOE는 어디를 볼지 정하고, sensitivity analysis는 무엇이 중요한지 설명하며, UQ는 결론의 폭을 계산하고, calibration은 관측으로 미지의 parameter를 갱신한다.

마지막으로 validation은 이 모든 가정 아래의 prediction이 새로운 정보에서도 목적에 맞는지 묻는다. 네 단계의 질문과 데이터를 분리하는 것만으로도 과적합, 가짜 정밀도, 해석 불가능한 parameter를 크게 줄일 수 있다.
