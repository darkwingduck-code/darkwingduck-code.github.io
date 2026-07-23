---
title: "결정론적 시뮬레이션 테스트: 불변량, Property-Based Testing, Replay"
date: 2026-07-21 09:40:00 +0900
categories: [Software Engineering, Simulation Testing]
tags: [determinism, simulation-testing, invariants, property-based-testing, replay, regression-testing, reproducibility]
description: "결정론적 시뮬레이터를 예제 몇 개가 아니라 불변량, 생성형 속성 테스트, 상태 해시, 이벤트 replay로 검증하는 방법을 정리한다."
math: true
lang: ko-KR
translation_key: deterministic-simulation-testing-invariants-replay
---

{% include language-switcher.html %}

시뮬레이션 테스트가 “대표 입력을 실행해 그래프가 비슷한지 본다”에 머물면 작은 변경이 어떤 법칙을 깨뜨렸는지 알기 어렵다. 반대로 출력 파일 전체를 golden file로 고정하면 무해한 부동소수점 차이에도 테스트가 깨지고, 잘못된 기존 결과를 영구 보존할 수 있다.

더 강한 전략은 세 층을 결합하는 것이다.

1. 모든 올바른 실행이 만족해야 하는 **불변량과 관계**
2. 넓은 입력 공간을 자동 탐색하는 **property-based test**
3. 실패를 정확히 되살리는 **seed·event·state replay**

## 1. 세 용어를 먼저 구분한다

### Determinism

동일한 초기 상태, 입력, 설정, 실행 환경에서 동일한 상태 전이를 얻는 성질이다.

$$
s_{t+1}=F(s_t,u_t;\theta)
$$

가 동일한 \(s_t,u_t,\theta\)에 대해 같은 \(s_{t+1}\)을 내야 한다.

### Reproducibility

다른 시점이나 환경에서도 결과를 허용 범위 안에서 다시 만들 수 있는 능력이다. bitwise determinism보다 넓은 개념이며 source, dependency, configuration, data, compiler, hardware 정보가 필요하다.

### Robustness

허용 가능한 입력·환경 변화에도 결론이 안정적인 성질이다. 같은 입력에서 항상 같은 오답을 내는 프로그램은 deterministic하지만 robust하거나 correct하지 않다.

## 2. 결정론을 깨뜨리는 숨은 입력

코드의 함수 인자만 입력이 아니다. 다음 항목도 상태 전이에 영향을 줄 수 있다.

- pseudo-random number generator의 seed와 algorithm
- wall-clock time과 locale
- hash-map iteration order
- thread scheduling과 reduction order
- GPU kernel의 atomic operation
- compiler flag와 fast-math
- BLAS·runtime·driver
- 파일 열거 순서
- 환경변수와 configuration default
- 외부 service 응답
- 초기화되지 않은 메모리

따라서 “seed를 고정했다”만으로 결정론이 완성되지 않는다. random stream을 subsystem별로 분리하고, 실행 순서가 바뀌어도 서로의 난수 소비량에 영향을 주지 않게 설계하는 편이 좋다.

## 3. 테스트 피라미드보다 테스트 격자

시뮬레이터는 여러 종류의 oracle이 필요하다.

| 테스트 종류 | 묻는 질문 | 실패가 잘 드러내는 것 |
|---|---|---|
| unit test | 작은 연산이 정의대로 동작하는가? | 부호, 단위, index, 경계 처리 |
| analytic/benchmark test | 알려진 해에 수렴하는가? | 방정식·scheme 구현 |
| invariant test | 반드시 보존할 법칙을 지키는가? | 누적 drift, 누락된 source |
| property-based test | 넓은 유효 입력에서도 성질이 유지되는가? | 예상 못한 corner case |
| metamorphic test | 입력 변환에 따른 출력 관계가 맞는가? | oracle 없는 문제의 논리 오류 |
| differential test | 독립 구현과 일치하는가? | 구현별 divergence |
| regression/golden test | 승인된 동작이 바뀌지 않았는가? | 비의도적 변경 |
| replay test | 과거 실패를 그대로 재현하는가? | nondeterminism, 상태 누락 |

한 종류가 다른 종류를 대체하지 않는다. 예를 들어 conservation test를 통과해도 공간 분포가 틀릴 수 있고, golden output이 일치해도 기준 자체가 잘못됐을 수 있다.

## 4. 불변량을 executable specification으로 만들기

불변량은 문서 속 문장이 아니라 매 실행에서 평가되는 assertion이어야 한다.

### 보존식

일반 balance를

$$
M_{t+1}
=
M_t+\Delta t\,(I_t-O_t+S_t)+e_t
$$

라고 하면 defect

$$
d_t=M_{t+1}-M_t-\Delta t\,(I_t-O_t+S_t)
$$

가 수치 허용 오차 안에 있어야 한다.

### Bounds와 positivity

확률, 농도, 질량분율처럼 정의역이 제한된 상태는

$$
0\le x_i\le 1
$$

같은 bound를 만족해야 한다. 다만 scheme이 작은 undershoot를 허용하는지, clipping이 conservation을 깨는지 함께 봐야 한다. 단순히 음수를 0으로 자르면 bug를 숨길 수 있다.

### Symmetry와 equivariance

입력 좌표를 회전·반사·순열했을 때 물리적으로 같은 변환이 출력에도 나타나야 한다면

$$
f(Tx)=Tf(x)
$$

를 검사한다. 이 관계는 정답 값을 몰라도 강한 oracle이 된다.

### Dimensional consistency와 scale relation

단위를 바꿔 같은 물리 상태를 표현했을 때 무차원 출력이 같아야 한다. 다만 scale invariance가 실제 governing equation과 boundary condition에서 성립하는지 먼저 유도한다.

### 상태기계 불변량

- 존재하지 않는 entity를 두 번 제거하지 않는다.
- 종료된 event는 다시 처리되지 않는다.
- resource count는 음수가 되지 않는다.
- timestamp는 causal order를 거슬러 감소하지 않는다.
- 각 entity ID의 생명주기는 유효한 state transition만 따른다.

## 5. 절대 tolerance와 상대 tolerance를 함께 쓴다

부동소수점 비교의 기본 형태는

$$
|a-b|
\le
\mathrm{atol}
+\mathrm{rtol}\cdot s
$$

이다. \(s\)는 문제에 맞는 reference scale이다.

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

expected가 0에 가까우면 상대오차만 사용할 수 없고, 큰 값에서는 절대오차만으로 의미를 판단하기 어렵다. tolerance는 테스트가 통과하도록 사후 조정하는 숫자가 아니라 다음 근거에서 나온 예산이어야 한다.

- discretization truncation error
- iterative solver tolerance
- floating-point accumulation bound
- measurement 또는 input precision
- downstream decision threshold

## 6. Property-based testing: 예제가 아니라 성질을 생성한다

example-based test는 사람이 떠올린 점만 검사한다. property-based testing은 유효한 입력을 생성하고, 실패하면 더 단순한 반례로 shrink한다.

아래는 개념적인 형태다.

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

이 숫자들은 특정 프로젝트 기준이 아니라 코드 형태를 보여 주기 위한 예시다. 실제 tolerance는 계산 정밀도와 오차 예산으로 정한다.

### 좋은 generator의 조건

- 물리적으로 유효한 constraint를 만족한다.
- 경계값, 0, 매우 작은 값, 큰 dynamic range를 충분히 생성한다.
- correlated variable을 독립 생성하지 않는다.
- invalid input test와 valid-domain property test를 분리한다.
- 실패 case의 seed뿐 아니라 shrink된 최소 입력을 저장한다.

무작위 입력을 많이 던지는 fuzzing과 달리 property-based testing은 **무엇이 참이어야 하는지**를 명시한다.

## 7. Metamorphic testing: 정답을 몰라도 관계는 안다

복잡한 시뮬레이션은 임의 입력의 정확한 출력을 알기 어렵다. 대신 입력을 변환했을 때 예상되는 출력 관계를 시험한다.

예를 들면 다음과 같다.

- entity 순서를 바꿔도 permutation-invariant aggregate는 같다.
- domain과 source를 함께 대칭 이동하면 출력도 같은 대칭 이동을 한다.
- source가 0인 limiting case는 알려진 단순 상태로 간다.
- 독립된 두 subsystem을 합친 총량은 각각의 총량 합과 일치한다.
- 시간 구간을 분할해 이어 실행한 결과와 한 번에 실행한 결과가 checkpoint 오차 안에서 같다.

마지막 관계는 semigroup property와 checkpoint serialization을 동시에 시험한다.

$$
F_{t_2}\left(F_{t_1}(s_0)\right)
\approx
F_{t_1+t_2}(s_0).
$$

adaptive solver나 event localization에서는 실행 경로가 달라질 수 있으므로 어떤 수준의 동등성을 요구할지 명확히 한다.

## 8. Replay를 가능하게 하는 최소 기록

실패를 재현하려면 로그 메시지보다 **입력 사건과 상태 계보**가 필요하다.

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

예시 placeholder를 실제 값으로 채우되 secret, 사용자 경로, 내부 hostname은 넣지 않는다.

### Event log

event sourcing 형태라면 각 event에 다음을 둔다.

- monotonically increasing sequence number
- simulation time과 logical time
- event type와 schema version
- canonical payload
- pre-state 또는 post-state digest
- causal parent 또는 correlation key

replay engine은 외부 I/O를 기록된 response로 대체하고 event sequence를 같은 순서로 적용한다.

### Checkpoint

긴 실행은 시작부터 replay하기 비싸다. versioned checkpoint와 이후 event log를 함께 저장한다. checkpoint loader는 이전 schema migration을 테스트하거나, 지원하지 않는 version이면 명확히 실패해야 한다.

## 9. State hash의 함정

state hash는 divergence가 시작된 step을 찾는 데 유용하지만 canonicalization 없이는 신뢰하기 어렵다.

- map key를 정렬한다.
- serialization format과 schema version을 고정한다.
- transient cache와 timestamp를 제외한다.
- NaN representation과 signed zero 정책을 정한다.
- float를 문자열로 임의 반올림해 hash하지 않는다.

bitwise equality가 필수인 discrete core와 tolerance 비교가 적절한 numeric field를 분리할 수 있다. 예를 들어 event order와 entity count는 exact compare, 연속 field는 norm과 invariant compare를 사용한다.

## 10. 병렬 계산과 재현 가능한 reduction

부동소수점 덧셈은 결합법칙을 정확히 만족하지 않는다.

$$
(a+b)+c\neq a+(b+c)
$$

일 수 있으므로 thread scheduling에 따라 reduction 결과가 달라진다. 선택지는 다음과 같다.

- 고정된 partition과 reduction tree
- pairwise 또는 compensated summation
- deterministic library mode
- exact accumulator가 필요한 핵심 총량
- bitwise가 아닌 numerically equivalent 판정

성능을 위해 nondeterministic reduction을 허용할 수 있다. 그 경우 결과가 허용 envelope 안에 있는지 statistical 또는 tolerance-based test로 검증하고, exact replay가 불가능하다는 계약을 문서화한다.

## 11. Regression과 golden file을 안전하게 쓰기

golden test는 API·format·대표 trajectory 변경을 감지하는 데 좋지만 다음 원칙이 필요하다.

1. golden 생성 절차도 version control한다.
2. 승인 시 diff를 사람이 해석 가능한 summary로 보여 준다.
3. 전체 대용량 binary보다 핵심 QoI와 invariant를 우선한다.
4. tolerance와 정렬을 명시한다.
5. 기준 갱신을 일반 test 실행과 분리한다.
6. analytic/invariant test 없이 golden만 두지 않는다.

“새 출력으로 기준 파일 자동 덮어쓰기”는 regression test를 무력화한다.

## 12. 실패를 자산으로 바꾸는 워크플로

1. production 또는 생성형 테스트에서 failure를 탐지한다.
2. source revision, manifest, 최소 입력, event log, checkpoint를 보존한다.
3. replay로 failure가 재현되는지 확인한다.
4. divergence가 시작되는 첫 state digest를 찾는다.
5. 원인을 설명하는 가장 작은 invariant/property test를 추가한다.
6. 수정 후 새 테스트와 기존 suite를 모두 통과시킨다.
7. 반례 corpus에 최소 case를 남긴다.
8. nondeterminism 자체가 원인이면 repeated scheduling test를 별도로 추가한다.

## 13. 검증 체크리스트

- [ ] determinism, reproducibility, correctness를 구분했는가?
- [ ] seed 외의 숨은 입력과 실행 환경을 기록했는가?
- [ ] subsystem별 random stream을 분리했는가?
- [ ] 핵심 보존식과 bounds가 runtime assertion 또는 test인가?
- [ ] property generator가 물리 constraint와 경계값을 다루는가?
- [ ] metamorphic relation을 governing rule에서 유도했는가?
- [ ] tolerance에 수치적 근거와 단위가 있는가?
- [ ] exact compare와 approximate compare 대상을 분리했는가?
- [ ] 실패의 shrink된 입력과 seed를 저장했는가?
- [ ] event schema와 checkpoint schema에 version이 있는가?
- [ ] replay 중 외부 I/O를 고정하거나 기록했는가?
- [ ] 병렬 reduction의 determinism 계약을 명시했는가?
- [ ] golden 갱신이 review 없이 자동 수행되지 않는가?

## 14. 함정과 한계

### Property가 틀리면 테스트가 정확한 코드를 실패시킨다

monotonicity, symmetry, positivity는 모델·경계조건·수치 scheme에 따라 깨질 수 있다. property는 직관이 아니라 명세와 수식에서 유도한다.

### Exact replay가 모든 플랫폼에서 가능한 것은 아니다

compiler, instruction set, transcendental function, GPU scheduling이 달라지면 bitwise 결과가 달라질 수 있다. 지원하는 reproducibility tier를 정의하는 편이 현실적이다.

- Tier A: 동일 binary·hardware에서 bitwise
- Tier B: 동일 architecture에서 numeric tolerance
- Tier C: 다른 platform에서 QoI·invariant equivalence

### 모든 상태를 로그로 남기면 비용과 정보노출이 커진다

event log, periodic checkpoint, state digest를 조합하고 retention·redaction 정책을 둔다. 비밀값이나 개인 데이터가 payload에 섞이지 않도록 schema 단계에서 차단한다.

### Deterministic mode가 실제 운영 경로와 다를 수 있다

테스트 전용 single-thread mode만 통과하고 production parallel path가 검증되지 않을 수 있다. deterministic reference mode와 실제 execution mode를 differential test로 비교한다.

## 마무리

강한 시뮬레이션 테스트는 특정 출력값을 외우지 않는다. 대신 **무엇이 절대 깨지면 안 되는지**, **입력을 바꾸면 어떤 관계가 유지되어야 하는지**, **실패를 어떻게 같은 상태에서 다시 시작할지**를 코드로 만든다.

불변량은 물리와 도메인 지식을 executable specification으로 바꾸고, property-based testing은 사람이 놓친 입력을 찾으며, replay는 한 번의 우연한 실패를 영구적인 regression 자산으로 바꾼다.
