---
title: "최소제곱을 제대로 쓰는 법: 투영, 조건수, QR, SVD"
date: 2026-07-21 09:10:00 +0900
categories: [Mathematics, Numerical Linear Algebra]
tags: [least-squares, projection, conditioning, qr, svd, pseudoinverse, regularization]
description: "최소제곱을 직교투영 문제로 해석하고 조건수, QR, SVD, 의사역행렬, 정규화를 수치 안정성 관점에서 연결한다."
math: true
lang: ko-KR
translation_key: least-squares-projection-conditioning-svd
---

{% include language-switcher.html %}

관측식 \(Ax=b\)가 정확히 풀리지 않을 때 흔히 “양변에 \(A^\mathsf T\)를 곱한다”고 배운다. 하지만 최소제곱의 본질은 공식 암기가 아니라 세 가지 질문에 있다.

1. 무엇을 최소화하고 있는가?
2. 해가 왜 column space로의 직교투영과 연결되는가?
3. 같은 수학적 해를 어떤 알고리즘으로 계산해야 안정적인가?

이 글은 최소제곱의 기하학, normal equation의 위험, QR과 SVD의 역할, rank deficiency와 regularization을 하나의 흐름으로 정리한다.

## 1. 최소제곱 문제의 정의

\(A\in\mathbb R^{m\times n}\), \(b\in\mathbb R^m\)에 대해 overdetermined system \(Ax=b\)는 일반적으로 정확한 해를 갖지 않는다. 최소제곱은 residual

$$
r(x)=b-Ax
$$

의 Euclidean norm을 최소화한다.

$$
x_\star
=
\arg\min_x \|Ax-b\|_2^2.
$$

\(Ax\)는 항상 \(\mathcal C(A)\), 즉 \(A\)의 column space 안에 있다. 따라서 문제는 \(b\)와 가장 가까운 column-space 원소 \(\hat b=Ax_\star\)를 찾는 문제다.

## 2. 직교투영과 normal equation

가장 가까운 점에서는 residual \(r_\star=b-Ax_\star\)가 column space의 모든 방향과 직교한다.

$$
A^\mathsf T r_\star=0.
$$

이를 전개하면 normal equation을 얻는다.

$$
A^\mathsf T A x_\star=A^\mathsf T b.
$$

\(A\)가 full column rank이면 \(A^\mathsf T A\)는 양의 정부호이고 해는 유일하다.

$$
x_\star=(A^\mathsf T A)^{-1}A^\mathsf T b.
$$

그러나 이 식은 **수학적 표현**이지 권장 계산 절차가 아니다. 실제 코드에서 inverse를 명시적으로 만드는 것도, 정확도를 중시하는 문제에서 무조건 normal equation을 푸는 것도 피하는 편이 좋다.

투영행렬은

$$
P=A(A^\mathsf T A)^{-1}A^\mathsf T
$$

이고 \(\hat b=Pb\)다. full column rank일 때 \(P\)는

$$
P^\mathsf T=P,\qquad P^2=P
$$

를 만족한다. 대칭성은 직교투영임을, idempotence는 한 번 투영한 것을 다시 투영해도 변하지 않음을 뜻한다.

## 3. 간단한 회귀 예시

일차 모델 \(y\approx\beta_0+\beta_1t\)를 여러 점에 맞춘다고 하자. design matrix는

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

최소제곱 해는 데이터 점과 직선 사이의 **수직 거리**를 최소화하는 것이 아니라, 지정한 \(y\) 방향 residual의 제곱합을 최소화한다. 두 축 모두 오차가 있다면 orthogonal distance regression이나 errors-in-variables model이 더 적절할 수 있다.

또한 \(t\)의 절댓값이 매우 크거나 범위가 한쪽에 몰리면 intercept column과 slope column의 수치적 구분이 어려워질 수 있다. \(t\)를 중심화하고 적절히 scaling하면 조건수와 계수 해석이 개선된다.

## 4. 조건수: 입력 오차가 해에서 얼마나 증폭되는가

가역 정사각행렬의 2-norm 조건수는

$$
\kappa_2(A)
=
\|A\|_2\|A^{-1}\|_2
=
\frac{\sigma_{\max}}{\sigma_{\min}}
$$

이다. 직사각 full-column-rank 행렬에서도 가장 큰 singular value와 가장 작은 nonzero singular value의 비로 같은 의미를 갖는다.

조건수가 크면 다음 현상이 나타난다.

- 입력 \(b\)의 작은 오차가 \(x\)에서 크게 증폭된다.
- 서로 거의 같은 column이 있어 계수가 크게 흔들린다.
- residual은 작아도 parameter estimate는 불안정할 수 있다.
- 부동소수점 반올림 오차의 영향이 커진다.

normal equation에는 결정적인 문제가 있다.

$$
\kappa_2(A^\mathsf T A)=\kappa_2(A)^2.
$$

즉 이미 나쁜 조건수가 제곱된다. 또한 \(A^\mathsf T A\)를 만드는 과정에서 유효 숫자를 잃을 수 있다.

> 작은 residual과 정확한 parameter는 같은 뜻이 아니다. \(b\)가 column space에 가깝더라도 column들이 거의 종속이면 서로 매우 다른 계수가 비슷한 예측을 만들 수 있다.

## 5. QR로 최소제곱 풀기

\(A\)가 full column rank이고

$$
A=QR,
$$

여기서 \(Q\in\mathbb R^{m\times n}\)의 열이 직교정규이고 \(R\in\mathbb R^{n\times n}\)이 upper triangular이라고 하자. 그러면

$$
\|Ax-b\|_2^2
=
\|Rx-Q^\mathsf Tb\|_2^2
+\|(I-QQ^\mathsf T)b\|_2^2.
$$

두 번째 항은 \(x\)와 무관하므로

$$
Rx=Q^\mathsf T b
$$

를 back substitution으로 풀면 된다.

실전에서는 classical Gram–Schmidt보다 Householder QR이 일반적으로 더 안정적이다. rank가 의심되면 column-pivoted QR

$$
AP=QR
$$

을 사용해 중요한 column을 앞쪽으로 모으고 effective rank를 진단할 수 있다.

## 6. SVD와 의사역행렬

SVD는

$$
A=U\Sigma V^\mathsf T
$$

로 행렬을 분해한다. \(U\)와 \(V\)의 열은 직교정규이고, \(\Sigma\)의 대각 원소 \(\sigma_i\)는 singular value다.

Moore–Penrose pseudoinverse는

$$
A^+=V\Sigma^+U^\mathsf T
$$

이며 최소제곱 해 중 최소 norm 해는

$$
x_\star=A^+b
=
\sum_{\sigma_i>0}
\frac{u_i^\mathsf Tb}{\sigma_i}v_i
$$

다.

이 식은 ill-conditioning의 원인을 직접 보여 준다. 작은 \(\sigma_i\) 방향에서는 \(u_i^\mathsf Tb\)의 작은 잡음도 \(1/\sigma_i\)만큼 증폭된다.

### SVD가 특히 유용한 경우

- rank deficiency가 있거나 의심될 때
- null space와 identifiable direction을 보고 싶을 때
- 최소 norm 해가 필요할 때
- singular spectrum으로 조건을 진단할 때
- truncated SVD 같은 regularization을 적용할 때

SVD는 진단력이 가장 높지만 QR보다 계산량과 메모리 비용이 클 수 있다. 문제 크기, sparsity, 필요한 정확도에 따라 선택한다.

## 7. rank deficiency와 해의 비유일성

\(\operatorname{rank}(A)<n\)이면 서로 다른 \(x\)가 같은 \(Ax\)를 만들 수 있다. \(z\in\mathcal N(A)\)이면

$$
A(x+z)=Ax
$$

이므로 최소제곱 해가 하나라면 \(x+z\)도 같은 residual을 갖는다. pseudoinverse 해는 이들 중 \(\|x\|_2\)가 가장 작은 해를 고른다.

수치 데이터에서는 rank가 이진적이지 않다. singular value cutoff를 \(\tau\)라 할 때

$$
\sigma_i\le\tau
$$

인 방향을 버릴 수 있지만, \(\tau\)는 단순 구현 세부사항이 아니라 어떤 방향을 식별 불가능하다고 볼지 정하는 모델링 선택이다. scale, noise 수준, 목적을 반영해야 한다.

## 8. weighted least squares와 covariance

residual 성분의 분산이 다르거나 서로 상관되어 있다면 일반 최소제곱의 동일 가중치 가정이 맞지 않는다. 오차 covariance가 \(\Sigma_b\)라면

$$
x_\star
=
\arg\min_x
(Ax-b)^\mathsf T\Sigma_b^{-1}(Ax-b).
$$

\(W^\mathsf TW=\Sigma_b^{-1}\)인 whitening matrix를 사용하면

$$
\min_x\|W(Ax-b)\|_2^2
$$

로 바뀐다. 여기서 가중치는 편의상 정하는 점수가 아니라 residual의 확률 구조와 연결되어야 한다.

## 9. regularization은 수치 트릭이 아니라 추가 가정이다

Tikhonov regularization은

$$
x_\lambda
=
\arg\min_x
\left(
\|Ax-b\|_2^2
+\lambda^2\|L(x-x_0)\|_2^2
\right)
$$

로 쓸 수 있다.

- \(x_0\): prior 또는 기준 해
- \(L\): penalize할 구조
- \(\lambda\): 데이터 적합과 prior 사이의 균형

\(L=I\), \(x_0=0\)이면 ridge 형태다. regularization은 분산을 줄이는 대신 bias를 도입한다. 따라서 “조건수가 나쁘니 작은 값을 아무거나 더한다”가 아니라, 어떤 해가 더 그럴듯한지 명시하는 모델링 단계로 다뤄야 한다.

\(\lambda\)는 cross-validation, discrepancy principle, L-curve, generalized cross-validation 등으로 정할 수 있다. 어떤 방법이든 선택 기준과 평가 데이터의 독립성을 기록한다.

## 10. 알고리즘 선택 가이드

| 상황 | 우선 고려 | 이유 |
|---|---|---|
| dense, full rank, 보통 조건 | Householder QR | 안정성과 비용의 균형 |
| rank 불명확, 진단 중요 | SVD | singular spectrum과 null space 확인 |
| column rank 판정 필요 | pivoted QR 또는 SVD | effective rank 추정 |
| 매우 큰 sparse 문제 | iterative least-squares solver | 행렬 분해 비용 회피 |
| covariance 구조 존재 | whitened/weighted least squares | 오차 모델 반영 |
| ill-posed inverse problem | regularized solver | 불안정 방향 억제 |
| 속도가 절대적이고 조건 양호 | Cholesky on normal equations를 신중히 검토 | 빠르지만 조건수 제곱 위험 |

“inverse를 계산한 뒤 곱한다”보다 선형시스템을 직접 푸는 함수가 기본 선택이다. library의 `solve`, `lstsq`, sparse solver는 내부 factorization과 예외 처리를 활용한다.

## 11. 실전 워크플로

1. **목적 정의**: prediction이 중요한가, parameter interpretation이 중요한가?
2. **차원과 단위 확인**: \(A\), \(x\), \(b\)의 shape와 물리 단위를 적는다.
3. **scaling**: column norm, 변수 범위, 단위를 점검하고 필요하면 중심화·표준화한다.
4. **rank 진단**: QR pivot 또는 singular spectrum을 확인한다.
5. **solver 선택**: 기본은 QR, rank/ill-conditioning 진단은 SVD를 고려한다.
6. **residual 분석**: norm 하나가 아니라 구조, bias, heteroscedasticity, correlation을 본다.
7. **orthogonality 검증**: \(A^\mathsf Tr\)가 tolerance 내에서 0인지 확인한다.
8. **민감도 확인**: 입력을 허용 범위에서 교란했을 때 계수와 예측이 얼마나 변하는지 본다.
9. **불확실성 보고**: noise model과 covariance 가정이 타당할 때 parameter uncertainty를 계산한다.
10. **재현성 기록**: solver, tolerance, scaling, rank cutoff, regularization 선택법을 남긴다.

## 12. 검증 체크리스트

- [ ] 최소화하는 norm과 가중치를 명시했는가?
- [ ] \(Ax_\star\)가 column space에 있고 \(A^\mathsf Tr\approx0\)인가?
- [ ] full rank를 가정했다면 실제로 확인했는가?
- [ ] \(A^\mathsf TA\)의 inverse를 명시적으로 만들지 않았는가?
- [ ] column scaling 전후의 조건수를 비교했는가?
- [ ] singular value와 cutoff를 함께 기록했는가?
- [ ] residual 크기와 parameter 안정성을 별도로 평가했는가?
- [ ] regularization parameter를 평가 데이터에 과적합하지 않았는가?
- [ ] weighted least squares의 weight가 오차 모델과 일치하는가?
- [ ] 예측 구간과 parameter 신뢰구간을 혼동하지 않았는가?

## 13. 함정과 한계

### \(R^2\)가 높으면 문제가 잘 풀렸다는 오해

높은 설명력은 잔차 독립성, 모델 적합성, parameter identifiability를 보장하지 않는다. extrapolation에서는 특히 위험하다.

### 입력 단위를 바꾸고 계수 크기를 직접 비교

coefficient magnitude는 변수 scale에 의존한다. 중요도 비교 전에 단위와 scaling을 맞춰야 한다.

### pseudoinverse가 “진짜 해”를 복원한다는 오해

pseudoinverse는 명확한 최적화 기준에 따른 대표 해를 선택할 뿐, 데이터가 잃어버린 null-space 정보를 되살리지는 못한다.

### regularization으로 모델 구조 오류를 숨김

regularization은 ill-posedness를 완화하지만 누락된 변수, 잘못된 observation operator, systematic bias를 해결하지 않는다.

### 선형화된 최소제곱의 한계

비선형 모델 \(f(x)\)에서는 local linearization과 반복 최적화가 필요하다. 초기값, local minimum, Jacobian conditioning이 추가로 중요해진다.

## 마무리

최소제곱은 “오차 제곱합을 줄이는 공식”이 아니라 **부분공간으로의 투영 문제**다. QR은 그 투영을 안정적으로 계산하는 기본 도구이고, SVD는 rank와 불안정 방향을 드러내는 진단 도구다. 조건수는 계산이 믿을 만한지 묻는 지표이며, regularization은 부족한 정보 대신 어떤 가정을 추가했는지 명시하는 장치다.

결과 숫자 하나보다 residual orthogonality, singular spectrum, scaling, solver, tolerance를 함께 남길 때 최소제곱은 재현 가능한 분석이 된다.
