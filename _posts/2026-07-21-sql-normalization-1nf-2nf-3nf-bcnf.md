---
title: "SQL 정규화의 원리와 실전 타협: 1NF·2NF·3NF·BCNF"
date: 2026-07-21 09:50:00 +0900
categories: [Data Engineering, Database Design]
tags: [sql, normalization, 1nf, 2nf, 3nf, bcnf, functional-dependency, data-modeling]
description: "함수 종속성과 후보키에서 출발해 1NF·2NF·3NF·BCNF를 판정하고, 무손실 분해·종속성 보존·반정규화의 실전 기준까지 정리한다."
math: true
---

정규화는 표를 많이 쪼개는 규칙이 아니다. 핵심은 **하나의 사실을 한 곳에서만 관리해 갱신 이상을 줄이는 것**이다. 이를 제대로 적용하려면 column 이름이 아니라 업무 규칙인 함수 종속성(functional dependency)을 먼저 적어야 한다.

이 글은 다음 흐름으로 정규형을 판정한다.

$$
\text{업무 규칙}
\rightarrow
\text{함수 종속성}
\rightarrow
\text{후보키}
\rightarrow
\text{정규형}
\rightarrow
\text{무손실·종속성 보존 분해}
$$

## 1. 정규화가 막는 세 가지 이상

한 relation에 서로 다른 사실을 중복 저장하면 다음 문제가 생긴다.

- **Update anomaly**: 같은 사실이 여러 row에 있어 일부만 수정된다.
- **Insert anomaly**: 다른 사실이 없으면 독립적인 사실을 등록할 수 없다.
- **Delete anomaly**: 한 row를 지우면서 별개의 유일한 사실도 함께 사라진다.

예를 들어 주문 row마다 고객 표시 이름을 반복 저장하면 이름 변경 시 과거 모든 row를 갱신해야 한다. 반면 “주문 당시 표시 이름”을 보존하려는 요구라면 반복이 아니라 의도된 snapshot일 수 있다. 정규화 여부는 column 모양이 아니라 **그 값이 현재 사실인지 역사적 사실인지**에 달려 있다.

## 2. 함수 종속성: 데이터가 아니라 규칙

relation \(R\)의 attribute 집합 \(X,Y\)에 대해

$$
X\to Y
$$

는 같은 \(X\) 값을 가진 두 tuple이 항상 같은 \(Y\) 값을 가져야 한다는 뜻이다. \(X\)가 \(Y\)를 함수적으로 결정한다.

주의할 점은 현재 sample에서 우연히 중복이 없다고 함수 종속성이 생기는 것은 아니라는 사실이다. 종속성은 앞으로 들어올 모든 유효 데이터에 적용되는 업무 규칙이어야 한다.

### Trivial dependency

\(Y\subseteq X\)이면 \(X\to Y\)는 trivial하다. 예를 들어

$$
\{A,B\}\to A
$$

는 값의 의미와 무관하게 항상 성립한다.

### Closure

attribute 집합 \(X\)의 closure \(X^+\)는 주어진 함수 종속성으로 \(X\)가 결정할 수 있는 모든 attribute다. 후보키 판정은 closure로 수행한다.

1. \(X^+=X\)에서 시작한다.
2. \(Y\to Z\)에서 \(Y\subseteq X^+\)이면 \(Z\)를 \(X^+\)에 추가한다.
3. 더 이상 변하지 않을 때까지 반복한다.
4. \(X^+=R\)이면 \(X\)는 superkey다.
5. \(X\)의 어떤 proper subset도 superkey가 아니면 candidate key다.

## 3. 키 용어를 정확히 구분하기

- **Superkey**: row를 유일하게 식별하는 attribute 집합. 불필요한 attribute를 포함할 수 있다.
- **Candidate key**: 더 줄일 수 없는 minimal superkey.
- **Primary key**: 후보키 중 구현에서 대표로 선택한 키.
- **Alternate key**: 선택되지 않은 나머지 후보키.
- **Prime attribute**: 적어도 하나의 후보키에 포함되는 attribute.
- **Foreign key**: 다른 relation의 candidate/unique key를 참조하는 attribute.

자동 증가 ID를 primary key로 추가해도 원래의 업무 후보키와 함수 종속성이 사라지지 않는다. 예를 들어 중복을 금지해야 하는 자연키에는 별도 `UNIQUE` constraint가 필요하다.

## 4. 1NF: attribute가 relation 안에서 하나의 값

First Normal Form은 각 tuple과 attribute 교차점이 해당 domain의 단일 값을 가져야 한다는 관계형 원칙이다. 반복 column과 한 cell 안의 가변 길이 목록은 별도 relation로 분리하는 것이 일반적이다.

잘못된 형태:

| item_id | labels |
|---|---|
| 하나의 식별자 | 쉼표로 연결된 여러 label |

정규화한 형태:

~~~sql
CREATE TABLE item (
    item_id BIGINT PRIMARY KEY
);

CREATE TABLE label (
    label_id BIGINT PRIMARY KEY,
    label_name TEXT NOT NULL UNIQUE
);

CREATE TABLE item_label (
    item_id BIGINT NOT NULL REFERENCES item(item_id),
    label_id BIGINT NOT NULL REFERENCES label(label_id),
    PRIMARY KEY (item_id, label_id)
);
~~~

### “Atomic”은 자료형 크기가 아니라 질의 의미다

날짜를 연·월·일 세 column으로 쪼개야 1NF가 되는 것은 아니다. 날짜 domain을 하나의 값으로 다루면 날짜 column은 atomic하다. 반대로 주소 문자열 전체를 하나의 값으로 저장하는 것이 1NF 위반은 아닐 수 있지만, 도시별 검색과 검증이 필요하면 별도 구조가 더 적절하다.

JSON이나 array type의 사용도 곧바로 1NF 위반이라고 단정하기보다 다음을 묻는다.

- 내부 원소를 관계형 constraint와 join 대상으로 다뤄야 하는가?
- 일부 원소만 독립적으로 갱신하는가?
- cardinality와 중복 규칙을 DB가 보장해야 하는가?
- schema evolution이 필요한 외부 payload인가?

## 5. 2NF: 복합 후보키의 일부에만 의존하는 사실 제거

Second Normal Form은

1. 1NF이고
2. 모든 non-prime attribute가 어떤 후보키의 proper subset에도 함수적으로 종속되지 않는 상태다.

즉 partial dependency를 제거한다. 후보키가 단일 attribute뿐이면 2NF 위반은 발생하지 않는다.

다음 relation을 생각하자.

~~~text
order_line(
  order_id,
  product_id,
  order_time,
  customer_id,
  customer_name,
  product_name,
  quantity,
  agreed_unit_price
)
~~~

한 주문에서 같은 상품이 한 줄만 존재한다면 후보키는 \((order\_id, product\_id)\)다. 업무 규칙이 다음과 같다고 하자.

$$
order\_id\to order\_time, customer\_id
$$

$$
product\_id\to product\_name
$$

$$
(order\_id,product\_id)
\to quantity,agreed\_unit\_price.
$$

`order_time`과 `customer_id`는 키의 일부인 `order_id`에만, `product_name`은 `product_id`에만 의존하므로 2NF를 위반한다.

이를 다음으로 분리한다.

- order_header(order_id, order_time, customer_id)
- product(product_id, product_name)
- order_line(order_id, product_id, quantity, agreed_unit_price)

여기서 agreed unit price는 상품의 현재 가격이 아니라 해당 주문 줄의 합의 가격이므로 복합키 전체에 의존한다. 이름이 비슷하다는 이유로 product relation로 옮기면 역사적 사실이 깨진다.

## 6. 3NF: 비키 attribute를 통한 간접 종속 제거

Third Normal Form의 직관은 non-key attribute가 key가 아닌 다른 attribute를 통해 간접적으로 결정되지 않게 하는 것이다.

위 예시에서

$$
order\_id\to customer\_id
$$

이고

$$
customer\_id\to customer\_name
$$

이라면

$$
order\_id\to customer\_name
$$

이라는 transitive dependency가 생긴다. 고객의 현재 이름을 주문마다 저장하면 갱신 이상이 생기므로

- customer(customer_id, current_name)
- order_header(order_id, order_time, customer_id)

로 분리한다.

### 3NF의 정확한 판정식

모든 nontrivial 함수 종속성 \(X\to A\)에 대해 다음 중 하나가 참이면 3NF다.

1. \(X\)가 superkey다.
2. \(A\)가 prime attribute다.

“non-key가 non-key를 결정하면 무조건 위반”이라는 암기보다 이 정의가 후보키가 여러 개인 relation에서 정확하다.

## 7. BCNF: 모든 determinant가 superkey

Boyce–Codd Normal Form은 모든 nontrivial 함수 종속성 \(X\to Y\)에서 \(X\)가 superkey일 것을 요구한다.

$$
X\to Y\text{ nontrivial}
\quad\Longrightarrow\quad
X\text{ is a superkey}.
$$

BCNF는 3NF보다 강하다.

$$
\mathrm{BCNF}\subseteq\mathrm{3NF}.
$$

모든 BCNF relation은 3NF지만, 모든 3NF relation이 BCNF는 아니다.

### 3NF지만 BCNF가 아닌 예시

relation

~~~text
assignment(student, course, instructor)
~~~

에 다음 규칙이 있다고 하자.

1. 한 학생은 한 course에서 한 instructor에게 배정된다.
2. 각 instructor는 정확히 한 course만 담당한다.

함수 종속성은

$$
(student,course)\to instructor
$$

$$
instructor\to course
$$

이다. 후보키는 \((student,course)\)와 \((student,instructor)\)다. 따라서 모든 attribute가 prime이고 3NF 조건은 만족한다.

그러나 `instructor` 단독은 superkey가 아닌데 `course`를 결정하므로 BCNF는 위반한다.

BCNF 분해는

- instructor_course(instructor, course)
- student_instructor(student, instructor)

가 될 수 있다. 중복은 줄지만 원래의 \((student,course)\to instructor\) constraint를 개별 table의 local constraint만으로 검사하기 어려울 수 있다. 여기서 BCNF와 dependency preservation 사이의 tradeoff가 나타난다.

## 8. 좋은 분해의 두 조건

### Lossless join

분해한 relation을 natural join했을 때 가짜 tuple 없이 원래 relation을 복원할 수 있어야 한다.

두 relation \(R_1,R_2\)로 분해하는 경우 다음 중 하나가 함수 종속성 closure에서 성립하면 lossless하다.

$$
(R_1\cap R_2)\to R_1
$$

또는

$$
(R_1\cap R_2)\to R_2.
$$

공통 attribute가 적어도 한쪽 relation의 key 역할을 해야 한다는 직관이다.

### Dependency preservation

원래 함수 종속성을 join 없이 각 relation의 local constraint로 강제할 수 있으면 dependency-preserving이다.

3NF synthesis는 lossless join과 dependency preservation을 함께 달성하는 데 유리하다. BCNF decomposition은 lossless하게 만들 수 있지만 모든 종속성을 항상 보존하지는 않는다. 따라서 “더 높은 정규형이 무조건 더 좋은 schema”는 아니다.

## 9. 실전 정규화 워크플로

### 단계 1: 사실의 문장을 쓴다

ERD보다 먼저 다음 형태로 업무 규칙을 적는다.

- 하나의 A는 여러 B를 가질 수 있다.
- 각 B는 정확히 하나의 C에 속한다.
- 가격은 현재 속성인가, 거래 시점 snapshot인가?
- 식별자는 전 기간에 걸쳐 재사용되지 않는가?

### 단계 2: 후보키와 함수 종속성을 적는다

primary key만 보지 말고 모든 후보키를 찾는다. unique constraint, nullable column, 시간 유효성까지 포함한다.

### 단계 3: minimal cover를 구한다

- 우변을 단일 attribute로 분리한다.
- 좌변의 불필요한 attribute를 제거한다.
- 다른 종속성으로 유도되는 중복 종속성을 제거한다.

### 단계 4: 정규형을 판정한다

1NF에서 시작해 2NF, 3NF, BCNF 순으로 올라간다. 각 위반에는 실제 update/insert/delete anomaly 예시를 하나 연결한다.

### 단계 5: 분해 품질을 확인한다

lossless join과 dependency preservation을 검증한다. constraint가 여러 table에 걸치면 transaction, trigger, assertion 대안, application invariant를 명시한다.

### 단계 6: 물리 schema를 설계한다

PK, UNIQUE, FK, NOT NULL, CHECK, index를 추가한다. FK column에 index가 자동 생성된다고 가정하지 말고 사용하는 DBMS를 확인한다.

### 단계 7: 실제 query와 write path로 평가한다

query plan, cardinality, lock, write amplification, storage를 측정한다. 성능 문제가 확인된 지점만 의도적으로 denormalize한다.

## 10. 반정규화가 합리적인 경우

정규화는 logical source of truth를 설계하는 기본값이다. 다음 경우에는 파생 표현을 둘 수 있다.

### 읽기 성능

빈번한 aggregate나 여러 join이 실제 병목이면 materialized view, indexed view, summary table을 고려한다. 원본 relation과 refresh 정책을 명시한다.

### 분석 모델

OLAP의 star schema는 fact와 dimension을 중심으로 query 단순성과 scan 효율을 우선한다. 이것은 OLTP source schema를 그대로 대체하기보다 변환된 serving model로 보는 편이 안전하다.

### Event와 snapshot

변경 불가능한 event payload는 당시 상태를 보존하기 위해 일부 값을 중복할 수 있다. 현재 master data와 과거 event truth를 구분한다.

### 외부 문서 보존

외부 API payload를 원형으로 저장할 필요가 있다면 raw JSON과 정규화한 query table을 함께 둘 수 있다. raw payload를 유일한 query model로 사용하면 constraint와 migration이 어려워질 수 있다.

반정규화에는 반드시 다음을 함께 둔다.

- authoritative source
- 갱신 주체
- 동기/비동기 refresh 방식
- 허용 staleness
- 재구축 절차
- 불일치 탐지 query

## 11. 시간과 이력은 별도의 차원

“고객의 이름”은 현재값 하나가 아닐 수 있다.

- 현재 canonical name
- 주문 당시 표시 name
- 특정 유효기간의 legal name
- 원본 event에 들어온 raw name

temporal requirement가 있으면 `valid_from`, `valid_to`, system time, event time을 구분한다. 현재 table을 정규화한 뒤 history가 필요할 때 단순 덮어쓰기를 하면 재현성이 사라진다.

## 12. 검증 체크리스트

- [ ] 함수 종속성이 sample 우연이 아니라 업무 규칙인가?
- [ ] primary key 외의 모든 후보키를 찾았는가?
- [ ] surrogate key가 자연키 중복을 숨기지 않는가?
- [ ] 1NF의 atomicity를 사용 목적과 domain 기준으로 판단했는가?
- [ ] 복합키의 partial dependency를 검사했는가?
- [ ] non-key를 통한 transitive dependency를 검사했는가?
- [ ] 3NF의 prime-attribute 예외를 정확히 적용했는가?
- [ ] BCNF 분해가 dependency preservation을 잃는지 확인했는가?
- [ ] 분해가 lossless join인지 검증했는가?
- [ ] PK·UNIQUE·FK·CHECK로 규칙을 실제 강제했는가?
- [ ] current fact와 historical snapshot을 구분했는가?
- [ ] 반정규화한 값의 source와 refresh 정책이 있는가?
- [ ] performance 판단을 실제 query plan으로 확인했는가?

## 13. 흔한 함정

### 모든 table에 ID 하나를 붙이면 2NF라는 오해

surrogate primary key가 단일 column이라는 이유로 원래 업무 후보키의 partial dependency가 사라지는 것은 아니다. anomaly는 그대로 남는다.

### NULL이 함수 종속성을 단순하게 만든다는 오해

SQL의 NULL과 three-valued logic, UNIQUE의 NULL 처리 방식은 DBMS별 의미를 확인해야 한다. 필수 업무 식별자를 nullable하게 두면 후보키 논리가 흐려진다.

### 무조건 join을 줄이려는 설계

join은 관계형 DB의 기본 연산이다. 중복 갱신 비용과 일관성 위험을 무시한 채 read query 하나만 보고 합치면 전체 시스템 비용이 커질 수 있다.

### 정규화로 모든 무결성이 해결된다는 오해

정규형은 함수 종속성과 중복을 다룬다. 범위 constraint, cross-row aggregate, 시간 겹침, 상태 전이 같은 규칙에는 추가 constraint와 transaction 설계가 필요하다.

### BCNF를 기계적으로 최우선

dependency preservation을 잃어 join이나 복잡한 trigger 없이는 규칙을 검사하지 못할 수 있다. 3NF에 머무는 것이 운영상 더 안전한 경우도 있다.

## 마무리

1NF, 2NF, 3NF, BCNF는 암기 순서가 아니라 서로 다른 중복 원인을 제거하는 판정 체계다.

- 1NF: 한 attribute 위치에 관계적으로 하나의 값
- 2NF: 복합 후보키 일부에만 의존하는 non-prime 사실 제거
- 3NF: key가 아닌 attribute를 통한 간접 종속 통제
- BCNF: 모든 determinant를 superkey로 제한

실전의 목표는 가장 높은 숫자가 아니다. **업무 규칙을 DB가 일관되게 강제하고, 분해가 무손실이며, 필요한 종속성을 운영 가능한 방식으로 보존하는 schema**가 목표다.
