---
title: "수치해석 결과를 믿기 위한 V&V: 수렴성, 격자·시간간격 독립성, 보존성"
date: 2026-07-21 09:20:00 +0900
categories: [Scientific Computing, Verification and Validation]
tags: [verification, validation, convergence, mesh-independence, time-step, conservation, numerical-error]
description: "코드 검증, 해 검증, 실험적 validation을 구분하고 수렴성·격자 및 시간간격 독립성·보존성으로 수치 결과의 신뢰도를 평가하는 절차를 정리한다."
math: true
lang: ko-KR
translation_key: numerical-verification-validation-convergence
---

{% include language-switcher.html %}

그럴듯한 contour와 매끄러운 곡선은 정확성의 증거가 아니다. 수치 시뮬레이션이 믿을 만하려면 적어도 다음 질문을 분리해야 한다.

- 방정식을 코드가 올바르게 풀고 있는가?
- 이 계산의 이산화·반복 오차는 충분히 작은가?
- 선택한 방정식과 입력이 현실의 관심량을 충분히 설명하는가?
- 이 결론은 사용 목적과 허용 오차 안에서 유효한가?

이 질문을 한 단어 “검증”으로 뭉치면 무엇을 확인했고 무엇이 남았는지 알 수 없다. Verification과 validation을 구분하는 이유가 여기에 있다.

## 1. Verification과 validation의 경계

| 층위 | 핵심 질문 | 대표 근거 |
|---|---|---|
| code verification | 방정식을 의도대로 구현했는가? | exact solution, manufactured solution, benchmark, unit test |
| solution verification | 현재 계산의 수치 오차가 얼마인가? | iterative convergence, mesh/time-step refinement, error estimate |
| validation | 모델이 현실의 관심량을 목적에 맞게 재현하는가? | 독립된 측정과 비교, validation uncertainty, applicability |
| calibration | 알 수 없는 parameter를 데이터로 추정했는가? | objective/likelihood, posterior, identifiability |

짧게 표현하면 verification은 “방정식을 맞게 풀었는가”, validation은 “맞는 방정식을 골랐는가”에 가깝다. 다만 validation은 모델이 절대적으로 참임을 증명하지 않는다. **특정 사용 목적, 조건 범위, 관심량에 대한 증거**를 축적한다.

Calibration 데이터와 validation 데이터를 같게 쓰면 모델이 본 데이터를 다시 맞히는 셈이다. 가능하면 분리하고, 데이터가 부족해 재사용했다면 독립 검증이 아니라는 한계를 명시해야 한다.

## 2. 오차를 먼저 분해하라

계산 결과와 현실 사이 차이는 여러 원인이 섞인 결과다.

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

이 식은 각 항이 단순 가산되고 독립이라는 엄밀한 확률모형이 아니라, 원인을 빠뜨리지 않기 위한 개념적 분해다. 서로 상호작용할 수 있으며 관측만으로 완전히 분리되지 않을 수도 있다.

좋은 V&V 계획은 먼저 quantity of interest(QoI)를 정한다. field 전체가 아니라 어떤 평균, 최대값, 적분량, 도달 시간, 경계 flux가 의사결정에 쓰이는지 적는다. 격자 수렴성과 validation 결과는 QoI마다 다를 수 있다.

## 3. Code verification: 구현 오류를 찾는 단계

### Exact solution과 benchmark

단순화된 경계조건이나 기하에서 analytic solution이 존재하면 계산 오차를 직접 비교할 수 있다. 복잡한 production case와 달라도 연산자, 경계조건, source term 구현을 격리해 시험하는 데 가치가 있다.

### Method of Manufactured Solutions

원하는 매끄러운 함수 \(u_m(x,t)\)를 먼저 고른 뒤 governing equation의 연산자 \(\mathcal L\)에 대입해 source

$$
f_m=\mathcal L(u_m)
$$

를 만든다. 코드가

$$
\mathcal L(u)=f_m
$$

을 풀도록 설정하면 정답 \(u_m\)을 알고 있는 상태에서 interior operator, boundary condition, 시간적분, observed order를 함께 시험할 수 있다.

manufactured solution은 실제 현상을 표현할 필요가 없다. 대신 다음을 만족해야 한다.

- 코드 경로의 주요 항을 모두 활성화한다.
- 지나친 대칭으로 bug를 가리지 않는다.
- 필요한 미분 가능성을 가진다.
- 경계조건과 source를 일관되게 유도한다.

### 독립 구현과 limiting case

서로 다른 코드가 같은 답을 내는 것은 유용한 증거지만 공통 가정이나 공통 bug를 공유할 수 있다. 따라서 term을 0으로 보낸 극한, symmetry, 차원 분석, 보존식 등 다른 종류의 증거와 결합한다.

## 4. Solution verification: 지금 계산의 수치 오차

### Iterative error와 discretization error를 분리

비선형·선형 solver가 충분히 수렴하지 않은 상태에서 격자를 바꾸면 iterative error와 discretization error가 섞인다. 각 격자에서 residual tolerance를 이산화 차이보다 충분히 작게 만들고, residual뿐 아니라 QoI의 안정성도 확인한다.

algebraic residual 감소가 곧 solution error 감소를 보장하지는 않는다. badly conditioned system에서는 작은 residual과 큰 solution error가 공존할 수 있다.

### 점근 수렴 영역

격자 간격을 \(h\), 이론적 차수를 \(p\)라 하면 충분히 미세한 영역에서

$$
\phi(h)=\phi_0+Ch^p+\mathcal O(h^{p+1})
$$

형태를 기대한다. \(\phi\)는 하나의 QoI다. refinement ratio가 일정하고

$$
h_3=rh_2=r^2h_1,\qquad r>1
$$

이며 \(h_1\)이 가장 미세할 때 observed order는

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

로 추정할 수 있다. 점근 영역이고 단조 수렴한다면 Richardson extrapolation은

$$
\phi_{\mathrm{ext}}
=
\phi_1+
\frac{\phi_1-\phi_2}{r^{p_{\mathrm{obs}}}-1}
$$

을 준다.

세 값이 진동 수렴하거나 차이가 noise 수준이면 이 공식은 불안정해진다. 무조건 하나의 apparent order를 출력하기보다 수렴 형태와 전제 충족 여부를 먼저 보고한다.

## 5. “격자 독립”이라는 표현을 조심해야 하는 이유

유한한 격자에서 discretization error가 정확히 0이 되는 일은 드물다. 따라서 “독립”보다 다음을 구체적으로 보고하는 편이 낫다.

- 사용한 refinement family와 characteristic \(h\)
- refinement ratio
- 각 격자의 cell/DOF 규모
- 격자 quality와 경계층 해상도
- 각 QoI의 값과 상대 변화
- observed order 또는 error estimate
- 최종 격자를 선택한 허용 기준

두 격자의 값이 비슷하다는 사실만으로는 부족하다. 우연한 오차 상쇄, non-monotonic convergence, 같은 해상도 병목이 있을 수 있다. 가능하면 세 수준 이상을 사용하고 격자가 topology와 stretching rule을 공유하는 systematic refinement family인지 확인한다.

### 국소량과 적분량은 다르게 수렴한다

domain average나 integral flux는 안정적이어도 point maximum, gradient, discontinuity 위치는 느리게 수렴할 수 있다. mesh study는 보고 싶은 QoI별로 수행한다. 서로 다른 격자의 “최대값 위치”가 이동한다면 같은 index의 cell 값을 직접 비교해서는 안 된다.

## 6. 시간간격 독립성과 공간·시간 오차의 결합

시간간격 \(\Delta t\)에 대해서도

$$
\phi(\Delta t)=\phi_0+C_t(\Delta t)^q+\cdots
$$

형태의 refinement study를 수행할 수 있다. 다만 공간 오차가 큰 상태에서는 시간간격을 줄여도 변화가 보이지 않고, 반대도 마찬가지다.

실용적인 순서는 다음과 같다.

1. 충분히 작은 \(\Delta t\)를 사용해 공간 refinement를 평가한다.
2. 선택한 fine mesh에서 \(\Delta t\) refinement를 평가한다.
3. 최종 조합 주변에서 mesh와 \(\Delta t\)를 함께 바꿔 interaction을 확인한다.
4. adaptive time stepping이면 nominal step 하나가 아니라 tolerance, accepted step history, rejected step을 기록한다.

안정성 조건을 만족하는 것과 정확도가 충분한 것은 다르다. implicit method가 큰 시간간격에서 발산하지 않는다고 해서 transient phase와 peak time을 정확히 해상한 것은 아니다.

## 7. 보존성: 수렴 그래프와 독립적인 강한 증거

보존형 문제의 control volume \(\Omega\)에서 일반적인 balance는

$$
\frac{d}{dt}\int_{\Omega}U\,d\Omega
+
\int_{\partial\Omega}F\cdot n\,dS
=
\int_{\Omega}S\,d\Omega
$$

이다. discrete calculation에서는 일정 시간 구간에 대해

$$
\Delta \text{storage}
+\text{net outflow}
-\text{source}
=
\text{balance defect}
$$

를 계산한다.

절대 defect만 보고하면 규모가 다른 case를 비교하기 어렵다. 대표 flux나 storage change로 나눈 normalized balance error도 함께 본다. 단, denominator가 0에 가까우면 상대오차가 폭발하므로 절대값과 scale을 같이 제시한다.

보존성은 필요조건이지 충분조건은 아니다. 서로 다른 위치에 같은 총량을 잘못 분배해도 global conservation은 맞을 수 있다. 따라서 다음 층위를 구분한다.

- local cell balance
- boundary별 flux balance
- global domain balance
- 종별·성분별 balance
- 에너지·질량·운동량 등 coupled balance

## 8. Validation 비교를 설계하는 법

### validation metric을 사전에 정한다

그림을 보고 “비슷하다”고 판단하지 말고 QoI와 metric을 먼저 정한다. 예:

- bias와 normalized error
- profile norm
- peak magnitude와 위치
- integral quantity
- temporal phase error
- coverage 또는 probabilistic score

### 불확실성을 합성한다

계산-측정 차이

$$
E=S-D
$$

를 해석할 때 simulation numerical uncertainty, input uncertainty, measurement uncertainty를 함께 고려한다. \(|E|\)가 작다는 것만으로 모델이 맞다고 단정할 수 없고, uncertainty band가 매우 넓어 차이를 가린 것인지도 봐야 한다.

### validation domain을 명시한다

검증한 조건 범위 밖으로 extrapolate하면 근거 강도가 낮아진다. 입력 공간, boundary regime, dimensionless group, material/state 범위를 기록하고 prediction point가 validation domain에서 얼마나 떨어져 있는지 평가한다.

## 9. 권장 V&V 워크플로

1. **사용 목적과 허용 오차 정의**: 어떤 의사결정에 어떤 QoI를 쓸지 적는다.
2. **모델 계층 작성**: governing equation, closure, boundary/initial condition, parameter source를 구분한다.
3. **code verification**: unit test, exact/MMS, limiting case, benchmark로 구현을 시험한다.
4. **iterative convergence**: equation residual과 QoI history를 함께 본다.
5. **공간 refinement**: systematic mesh family에서 세 수준 이상 비교한다.
6. **시간 refinement**: temporal QoI, phase, peak timing을 포함한다.
7. **보존성 검사**: local·boundary·global balance를 자동 계산한다.
8. **입력 불확실성 전파**: validation comparison에 input uncertainty를 반영한다.
9. **독립 validation**: calibration에 쓰지 않은 데이터와 사전 정의 metric으로 비교한다.
10. **적용 범위와 한계 기록**: 검증되지 않은 regime와 dominant uncertainty를 밝힌다.

## 10. 검증 체크리스트

- [ ] verification, validation, calibration을 구분했는가?
- [ ] 의사결정에 쓰이는 QoI와 tolerance를 먼저 정의했는가?
- [ ] analytic/MMS test가 production code의 주요 term을 활성화하는가?
- [ ] iterative error가 격자 간 차이보다 충분히 작은가?
- [ ] 최소 세 수준의 systematic refinement를 사용했는가?
- [ ] theoretical order가 아니라 observed order도 확인했는가?
- [ ] monotonic, oscillatory, divergent convergence를 구분했는가?
- [ ] 공간과 시간 refinement를 각각 수행했는가?
- [ ] global뿐 아니라 local/boundary conservation도 확인했는가?
- [ ] calibration과 validation 데이터를 분리했는가?
- [ ] measurement·input·numerical uncertainty를 함께 보고했는가?
- [ ] validation domain 밖 extrapolation을 표시했는가?

## 11. 흔한 함정

### Residual이 작으니 정답이라는 결론

residual은 discrete algebraic equation을 얼마나 잘 풀었는지 말할 뿐, discretization error와 model-form error를 알려 주지 않는다.

### 격자 두 개만 비교하고 독립 선언

두 값의 우연한 일치는 수렴 차수나 점근 영역을 입증하지 않는다. 세 수준 이상과 수렴 패턴이 필요하다.

### 모든 field를 한 metric으로 평가

평균값이 잘 맞아도 peak, gradient, phase는 틀릴 수 있다. 목적에 맞는 여러 QoI가 필요하다.

### Calibration 성능을 validation 성능으로 보고

parameter를 맞춘 데이터에 대한 적합도는 calibration 결과다. predictive adequacy를 보려면 독립 정보가 필요하다.

### 더 미세한 격자는 항상 더 정확하다는 가정

잘못된 boundary condition, 낮은 iterative tolerance, 나쁜 mesh quality, 불안정한 scheme이 있으면 DOF 증가만으로 정확성이 보장되지 않는다.

## 12. 한계와 보고 원칙

복잡한 비선형·다중스케일 문제에서는 깨끗한 점근 영역에 도달하지 못할 수 있다. discontinuity, moving interface, chaotic dynamics, adaptive mesh는 단순 Richardson 분석의 전제를 약화한다. 이때 “정확한 오차 하나”를 억지로 제시하기보다 여러 해상도에서 결론이 얼마나 안정적인지, 어떤 오차원이 지배적인지, 무엇을 확인하지 못했는지를 투명하게 보고한다.

V&V의 산출물은 통과 도장이 아니다. **결론을 지지하는 증거의 연결망**이다. 그림보다 solver tolerance, refinement family, balance defect, uncertainty, 적용 범위가 더 중요한 이유다.
