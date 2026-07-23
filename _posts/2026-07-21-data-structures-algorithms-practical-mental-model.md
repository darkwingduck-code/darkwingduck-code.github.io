---
title: "자료구조·알고리즘 실전 Mental Model: 복잡도보다 선택 근거"
date: 2026-07-21 10:10:00 +0900
categories: [Computer Science, Algorithms]
tags: [data-structures, algorithms, big-o, amortized-analysis, graph-algorithms, invariants, benchmarking]
description: "Big-O와 상각분석을 실제 비용 모델로 해석하고 array, hash, heap, tree, graph 알고리즘을 요구사항·정확성·측정 근거로 선택하는 법을 정리한다."
math: true
lang: ko-KR
translation_key: data-structures-algorithms-practical-mental-model
---

{% include language-switcher.html %}

자료구조와 알고리즘을 시험용 표로 외우면 “hash는 \(O(1)\), tree는 \(O(\log n)\)” 같은 문장만 남는다. 실제 설계에서는 그보다 먼저 다음을 물어야 한다.

- 데이터가 메모리에 들어가는가?
- 가장 빈번한 연산은 조회, 삽입, 최소값 추출, 범위 질의 중 무엇인가?
- 순서와 중복을 보존해야 하는가?
- worst-case latency가 중요한가, 평균 throughput이 중요한가?
- 데이터 분포와 adversarial input 가능성은 어떤가?
- cache locality, allocation, concurrency 비용은 어떤가?

알고리즘 선택은 이름 맞히기가 아니라 **요구사항을 비용 모델과 correctness invariant로 번역하는 일**이다.

## 1. 분석 전에 크기 변수를 정의한다

복잡도 식의 \(n\)이 무엇인지 모르면 Big-O는 의미가 없다.

- 배열 원소 수 \(n\)
- graph의 vertex 수 \(V\)와 edge 수 \(E\)
- 문자열 길이 \(L\)
- query 수 \(Q\)
- state dimension \(d\)
- 정수 값의 bit 수 \(b\)

예를 들어 graph algorithm을 무조건 \(O(n^2)\)라고 쓰면 sparse graph와 dense graph의 차이가 사라진다. adjacency list 기반 BFS는

$$
\Theta(V+E)
$$

이고 adjacency matrix를 모두 scan하면

$$
\Theta(V^2)
$$

가 된다. algorithm 이름뿐 아니라 representation이 복잡도를 바꾼다.

## 2. Big-O, Big-Theta, Big-Omega

### 상한: \(O(g(n))\)

충분히 큰 \(n\)에서

$$
0\le f(n)\le c\,g(n)
$$

이 되는 상수 \(c\)가 존재하면 \(f(n)=O(g(n))\)다. upper bound이므로 \(\Theta(n)\)인 함수도 \(O(n^2)\)라고 말할 수 있다. 가능하면 tight bound인 \(\Theta\)를 사용해야 정보가 많다.

### 점근적으로 같은 차수: \(\Theta(g(n))\)

$$
c_1g(n)\le f(n)\le c_2g(n)
$$

이면 \(f(n)=\Theta(g(n))\)다.

### 하한: \(\Omega(g(n))\)

충분히 큰 \(n\)에서 \(f(n)\ge c\,g(n)\)이면 lower bound다.

### Worst, average, expected를 붙인다

“hash lookup은 \(O(1)\)”은 보통 적절한 hashing과 load factor를 가정한 expected 또는 amortized 설명이다. 충돌이 집중되면 worst case는 달라진다. 다음을 구분한다.

- worst-case per operation
- expected cost over randomization
- average case under a specified input distribution
- amortized cost over an operation sequence

average와 amortized는 같은 말이 아니다.

## 3. 상각분석: 드문 비싼 연산을 전체 sequence로 나누기

동적 배열의 capacity가 가득 찰 때 더 큰 buffer를 만들고 모든 원소를 복사하면 한 번의 append는 \(\Theta(n)\)일 수 있다. 하지만 capacity를 일정 배수로 늘리면 \(m\)번 append 전체의 복사량은 geometric series로 제한된다.

$$
1+2+4+\cdots < 2m.
$$

따라서 \(m\)번 append 총비용은 \(\Theta(m)\), append당 amortized cost는 \(\Theta(1)\)이다.

상각분석은 “대부분 빨랐다”는 경험적 평균이 아니다. **어떤 입력 sequence에서도 전체 비용이 그 bound를 넘지 않음**을 보이는 분석이다.

대표 증명 방식은 다음과 같다.

- aggregate method: 전체 sequence 비용을 직접 합산
- accounting method: 싼 연산에 credit을 미리 부과
- potential method: 자료구조 상태의 potential 변화를 비용에 포함

latency deadline이 있는 시스템에서는 amortized \(O(1)\)만으로 부족할 수 있다. resize 한 번의 \(O(n)\) pause가 허용되는지, incremental rehashing이나 capacity reservation이 필요한지 본다.

## 4. 복잡도는 다차원 비용이다

시간복잡도 하나로 선택하면 다음을 놓친다.

- auxiliary memory
- allocation 횟수
- cache miss와 pointer chasing
- branch prediction
- serialization size
- parallel contention
- preprocessing time
- update와 query의 비율

같은 \(O(n)\)이어도 contiguous array scan은 linked structure traversal보다 훨씬 빠를 수 있다. 반대로 중간 node를 이미 가리키는 상태에서 unlink하는 연산은 linked list가 유리할 수 있다. 단, node를 찾는 비용을 빼고 말해서는 안 된다.

## 5. 자료구조 선택 지도

### Array / dynamic array

**강점**

- index 접근 \(\Theta(1)\)
- 연속 메모리와 좋은 cache locality
- 끝 append의 amortized \(\Theta(1)\)
- sorting, binary search, vectorized processing에 적합

**약점**

- 중간 삽입·삭제는 원소 이동 때문에 \(\Theta(n)\)
- resize spike와 추가 capacity
- stable pointer가 깨질 수 있음

기본값으로 매우 강하다. 언어의 “list”가 실제로 dynamic array인지 linked list인지 구현을 확인한다.

### Linked list

**강점**

- node 위치를 이미 알 때 삽입·삭제 \(\Theta(1)\)
- splice와 stable node reference가 필요한 구조

**약점**

- index 접근과 탐색 \(\Theta(n)\)
- node별 allocation과 pointer overhead
- cache locality가 나쁨

“삽입이 많다”만으로 선택하지 않는다. 삽입 위치를 찾는 데 \(\Theta(n)\)이면 전체 이점이 사라질 수 있다.

### Hash table

**강점**

- key 기반 lookup/insert/delete의 expected \(\Theta(1)\)
- membership, frequency count, deduplication

**약점**

- key order와 range query에 부적합
- hash quality와 load factor에 의존
- rehash 비용
- adversarial collision과 mutable key 위험

equality와 hash가 일관되어야 한다.

$$
a=b\quad\Longrightarrow\quad hash(a)=hash(b).
$$

key로 사용한 뒤 equality에 관여하는 field를 바꾸면 항목을 찾지 못할 수 있다.

### Balanced search tree

**강점**

- lookup/insert/delete worst-case \(\Theta(\log n)\)
- 정렬 순회
- predecessor/successor
- range query

**약점**

- hash보다 큰 상수와 pointer overhead
- balancing 구현 복잡도

ordered map/set, interval query, predictable worst-case가 필요할 때 적합하다.

### Heap / priority queue

binary heap 기준으로

- 최소/최대값 조회: \(\Theta(1)\)
- push: \(\Theta(\log n)\)
- pop min/max: \(\Theta(\log n)\)
- 전체 unordered 원소에서 임의 key 탐색: \(\Theta(n)\)
- bulk heapify: \(\Theta(n)\)

heap은 “정렬된 container”가 아니다. root의 우선순위만 보장한다. top-\(k\), scheduler, Dijkstra frontier처럼 다음 최우선 항목을 반복 추출할 때 사용한다.

### Deque

양 끝 push/pop이 \(\Theta(1)\)인 queue가 필요할 때 사용한다. BFS에서 array 앞쪽 삭제를 반복해 \(\Theta(n)\) shift를 만들지 않도록 한다.

### Disjoint-set union

집합 합치기와 연결성 질의를 반복할 때 path compression과 union by rank/size를 사용하면 연산당 amortized cost가 사실상 상수에 가까운

$$
O(\alpha(n))
$$

이다. 동적 삭제나 경로 자체가 필요하면 맞지 않는다.

## 6. 목적에서 자료구조로 역추론하기

| 핵심 요구 | 첫 후보 | 확인할 조건 |
|---|---|---|
| index 접근·순차 scan | dynamic array | 중간 수정 빈도, capacity |
| key membership | hash set/map | 순서·worst-case 필요 여부 |
| 정렬된 key·범위 질의 | balanced tree | update/query 비율 |
| 반복적인 최솟값 추출 | heap | 임의 삭제/decrease-key 지원 |
| FIFO | deque | bounded queue, concurrency |
| LIFO | stack / dynamic array | 최대 depth |
| 연결성 merge/query | disjoint set | edge 삭제가 없는가 |
| sparse graph traversal | adjacency list | multiedge, direction |
| dense graph 또는 빠른 edge test | adjacency matrix/bitset | \(V^2\) memory 허용 |

하나의 서비스에서 source of truth와 serving index를 분리할 수 있다. 예를 들어 record는 array에 저장하고 ID lookup용 hash index와 우선순위용 heap을 함께 유지한다. 이 경우 **여러 표현의 동기화 invariant**가 새 비용이 된다.

## 7. Graph representation이 algorithm을 결정한다

### Adjacency list

memory가 \(\Theta(V+E)\)이고 한 vertex의 이웃 순회가 degree에 비례한다. sparse graph의 기본값이다.

### Adjacency matrix

memory가 \(\Theta(V^2)\)지만 edge 존재 여부는 \(\Theta(1)\)이다. dense graph, 작은 graph, bit-parallel operation에 적합할 수 있다.

### Edge list

모든 edge를 한 번 scan하거나 sorting하는 algorithm에 단순하다. 임의 vertex의 이웃 조회는 별도 index 없이는 느리다.

representation을 정할 때 directed/undirected, weighted/unweighted, self-loop, parallel edge, mutable graph, vertex ID density를 함께 정한다.

## 8. BFS, DFS, Dijkstra의 전제

### BFS

BFS는 unweighted graph 또는 모든 edge cost가 같은 graph에서 source로부터 최소 edge 수 거리를 찾는다.

~~~python
from collections import deque

def bfs(graph, source):
    distance = {source: 0}
    parent = {source: None}
    queue = deque([source])

    while queue:
        u = queue.popleft()
        for v in graph[u]:
            if v in distance:
                continue
            distance[v] = distance[u] + 1
            parent[v] = u
            queue.append(v)

    return distance, parent
~~~

vertex를 queue에서 꺼낼 때가 아니라 **넣을 때 visited 처리**해야 같은 vertex가 중복 enqueue되는 것을 막을 수 있다.

위 예시는 이웃으로 등장하는 sink vertex까지 모두 `graph`의 key로 존재한다고 가정한다. 실제 API에서는 이 표현 invariant를 validation하거나 `graph.get(u, ())`처럼 빈 adjacency를 명시적으로 처리한다.

### DFS

DFS는 reachability, connected component, cycle detection, topological sort의 구성 요소다. 그러나 “DFS를 썼다”만으로 cycle 판정이 되지 않는다.

- undirected graph: parent edge를 제외한 visited neighbor가 cycle 신호
- directed graph: 현재 recursion stack 또는 color state의 back edge가 필요
- topological order: directed acyclic graph에서만 유효

DFS tree의 탐색 순서는 adjacency iteration order에 따라 달라질 수 있다. deterministic output이 필요하면 neighbor order를 고정한다.

### Dijkstra

Dijkstra는 **모든 edge weight가 nonnegative**일 때 single-source shortest path를 구한다.

~~~python
from heapq import heappop, heappush
from math import inf, isfinite

def dijkstra(graph, source):
    distance = {v: inf for v in graph}
    distance[source] = 0.0
    heap = [(0.0, source)]

    while heap:
        best, u = heappop(heap)
        if best != distance[u]:
            continue

        for v, weight in graph[u]:
            if not isfinite(weight) or weight < 0:
                raise ValueError("Dijkstra requires finite nonnegative weights")
            candidate = best + weight
            if candidate < distance[v]:
                distance[v] = candidate
                heappush(heap, (candidate, v))

    return distance
~~~

priority queue에 같은 vertex의 오래된 entry가 남을 수 있으므로 stale-entry check가 필요하다. decrease-key를 직접 지원하는 heap이라면 구현이 달라진다.

adjacency list와 binary heap을 사용하면 일반적인 시간복잡도는 \(O((V+E)\log V)\), 연결 graph에서는 흔히 \(O(E\log V)\)로 쓴다. duplicate entry를 허용하는 위 구현에서는 heap memory와 상수 비용도 함께 본다.

### Weight 구조별 선택

| Edge weight | Algorithm 후보 |
|---|---|
| 모두 동일 | BFS |
| 0 또는 1 | 0–1 BFS |
| 모두 nonnegative | Dijkstra |
| negative edge 가능 | Bellman–Ford 계열 |
| DAG | topological-order relaxation |
| all-pairs, dense/small graph | Floyd–Warshall 등을 검토 |

negative cycle이 reachable하면 finite shortest path 자체가 정의되지 않을 수 있다. algorithm 실패가 아니라 문제 정의의 문제다.

## 9. Recursion과 iteration

재귀는 tree·divide-and-conquer 정의를 코드 구조와 가깝게 표현한다. 하지만 다음 비용이 있다.

- call stack depth 제한
- frame allocation과 함수 호출 overhead
- deep/skewed tree에서 stack overflow
- 상태와 error recovery의 암묵성

iteration은 explicit stack/queue로 traversal state를 직접 관리한다.

~~~python
def iterative_dfs(graph, source):
    visited = set()
    stack = [source]

    while stack:
        u = stack.pop()
        if u in visited:
            continue
        visited.add(u)
        for v in reversed(graph[u]):
            if v not in visited:
                stack.append(v)

    return visited
~~~

이 예시는 adjacency가 `reversed`를 지원하는 deterministic sequence라고 가정한다. 재귀 DFS와 같은 방문 순서를 원한다면 stack의 LIFO 성질 때문에 neighbor push 순서를 반대로 해야 할 수 있다. 방문 순서가 correctness에 필요 없는 경우에도 test가 우연히 순서에 의존하지 않는지 확인한다.

선택 기준은 다음과 같다.

- depth가 작고 명확히 bounded: recursion이 읽기 쉬울 수 있음
- 입력이 adversarial하거나 depth가 \(O(n)\): iteration 우선
- traversal을 pause/resume 또는 serialize: explicit state 유리
- post-order 처리: stack frame에 enter/exit state를 함께 저장

tail recursion optimization은 언어와 runtime이 보장하는지 확인해야 한다.

## 10. Correctness invariant로 증명과 코드를 연결하기

algorithm이 “예제에서 됐다”가 아니라 모든 유효 입력에서 맞음을 보이려면 loop invariant를 사용한다.

### 세 단계

1. **Initialization**: loop 시작 전에 invariant가 참이다.
2. **Maintenance**: 한 iteration 후에도 참이다.
3. **Termination**: loop가 끝날 때 invariant가 원하는 결론을 준다.

### Binary search 예시 invariant

half-open interval \([lo,hi)\)를 사용한다면

- 답이 존재하면 항상 \([lo,hi)\) 안에 있다.
- \([0,lo)\)는 조건을 만족하지 않는다.
- \([hi,n)\)는 조건을 만족한다.

같은 boundary convention을 update와 return까지 유지해야 off-by-one을 피한다.

### BFS invariant

queue에서 처리되는 vertex의 distance는 nondecreasing이며, 처음 발견한 경로가 최소 edge 수 경로다. 이는 모든 edge cost가 동일하다는 전제에 의존한다.

### Dijkstra invariant

heap에서 유효한 최소거리로 확정한 vertex의 distance는 최단거리다. nonnegative edge가 있어야 아직 방문하지 않은 경로가 그 값을 나중에 더 작게 만들 수 없다는 증명이 성립한다.

### Heap invariant

min-heap의 각 node key는 자식 key 이하이다. 전체 정렬은 요구하지 않는다. push/pop 후 local repair가 이 invariant를 복원하는지 시험한다.

## 11. Edge case는 나중의 예외가 아니라 설계 입력

### Collection

- empty
- one element
- all equal
- already sorted / reverse sorted
- many duplicates
- capacity boundary 직전·직후
- missing key와 repeated delete

### Numeric

- zero와 negative zero
- min/max representable value
- integer overflow
- NaN과 infinity 허용 여부
- floating equality와 tolerance
- 매우 다른 magnitude

### Graph

- isolated vertex
- disconnected component
- self-loop
- parallel edge
- directed/undirected 혼동
- cycle과 reachable negative cycle
- source가 graph에 없음
- multiple shortest paths

### Resource

- 메모리에 들어가지 않는 입력
- recursion maximum depth
- cancellation과 timeout
- partial read/write
- concurrent mutation

edge case를 test 목록에만 두지 말고 API contract에서 reject, normalize, support 중 하나를 정한다.

## 12. Profiling: 추측 대신 비용의 위치 찾기

복잡도가 좋은 algorithm도 실제 병목이 아닐 수 있다. 최적화 전에 다음 순서를 따른다.

1. end-to-end latency/throughput 목표를 정한다.
2. production과 유사한 workload에서 profile한다.
3. CPU, allocation, I/O wait, lock contention을 분리한다.
4. hot path의 호출 빈도와 per-call cost를 본다.
5. algorithm 또는 representation 변경 후 같은 조건에서 다시 측정한다.

micro-optimization보다 \(O(n^2)\) loop 제거, 불필요한 serialization, 반복 DB query, allocation pattern 변경이 더 큰 효과를 주는 경우가 많다.

## 13. Benchmark를 믿기 위한 조건

### Workload

- 실제 크기 범위를 여러 점에서 측정
- random뿐 아니라 sorted, duplicate-heavy, skewed, adversarial 분포
- read/write ratio와 cache hit ratio 반영
- warm/cold cache를 구분

### Measurement

- warm-up과 JIT/GC 영향 통제
- setup과 timed region 분리
- 여러 반복의 median과 tail percentile
- CPU frequency scaling, background load 기록
- 결과를 소비해 dead-code elimination 방지
- peak memory와 allocation도 측정

### Interpretation

입력 크기별 log-log plot이나 operation count를 보면 crossover를 찾을 수 있다. 작은 \(n\)에서는 단순 algorithm이 빠르고 큰 \(n\)에서 점근적으로 좋은 algorithm이 역전할 수 있다.

benchmark는 보편적 진리를 증명하지 않는다. 측정한 hardware, runtime, input distribution에 대한 증거다.

## 14. 실전 선택 워크플로

1. **연산 목록 작성**: lookup, insert, delete, min, range, traversal의 빈도를 추정한다.
2. **계약 정의**: ordering, duplicates, mutability, concurrency, latency bound를 정한다.
3. **크기와 분포 정의**: \(n,V,E,Q\), sparsity, skew, adversarial 가능성을 적는다.
4. **후보 구조 비교**: 평균/최악/상각 시간과 memory를 표로 만든다.
5. **correctness invariant 작성**: 구조와 algorithm이 유지해야 할 조건을 적는다.
6. **가장 단순한 올바른 구현**을 만든다.
7. **edge/property test**로 invariant를 검증한다.
8. **profile**로 실제 병목을 찾는다.
9. **representative benchmark**로 대안을 비교한다.
10. **선택 근거 기록**: workload 가정과 재평가 threshold를 남긴다.

## 15. 검증 체크리스트

- [ ] 복잡도의 크기 변수를 정의했는가?
- [ ] worst, expected, average, amortized를 구분했는가?
- [ ] 시간뿐 아니라 memory·allocation·locality를 평가했는가?
- [ ] linked list 삽입 비용에 위치 탐색을 포함했는가?
- [ ] hash의 order, collision, mutable key 조건을 확인했는가?
- [ ] heap을 전체 정렬 구조로 오해하지 않았는가?
- [ ] graph representation이 sparsity와 query에 맞는가?
- [ ] BFS/DFS/Dijkstra의 edge-weight·방향 전제를 확인했는가?
- [ ] recursion depth가 입력에 의해 unbounded하지 않은가?
- [ ] loop invariant의 초기화·유지·종료를 설명할 수 있는가?
- [ ] empty, duplicate, overflow, disconnected case를 테스트했는가?
- [ ] profile로 병목을 확인한 뒤 최적화했는가?
- [ ] benchmark workload와 환경을 기록했는가?
- [ ] 평균뿐 아니라 tail latency와 peak memory를 확인했는가?

## 16. 흔한 함정과 한계

### Big-O가 작은 구조가 항상 빠르다

상수, cache locality, allocation, 실제 \(n\)의 범위가 crossover를 결정한다. 점근 분석과 benchmark가 모두 필요하다.

### Library 이름만 보고 복잡도를 추정

같은 이름의 container도 언어별 구현이 다르다. operation guarantee와 invalidation rule을 공식 문서에서 확인한다.

### 정렬된 입력은 쉬운 입력이라는 가정

algorithm에 따라 sorted/reverse-sorted input이 worst case가 될 수 있다. pivot, hash, tree balancing 전제를 본다.

### Dijkstra에 negative edge를 넣고 결과만 확인

작은 예제에서 우연히 맞을 수 있지만 correctness proof의 전제가 깨진다. 입력 validation을 algorithm boundary에 둔다.

### 재귀를 반복문으로 바꾸면 항상 같은 순서

explicit stack에 이웃을 넣는 순서와 visited 처리 시점에 따라 traversal tree가 달라진다.

### Benchmark 하나로 선택을 영구 고정

데이터 크기, read/write ratio, runtime version이 바뀌면 선택 근거도 바뀐다. 재평가 기준을 남긴다.

## 마무리

자료구조·알고리즘의 실전 mental model은 다음 문장으로 압축된다.

> 요구되는 연산과 보장 조건을 먼저 쓰고, 그 조건을 유지하는 가장 단순한 구조를 선택한 뒤, 점근 분석으로 확장성을 확인하고 실제 workload로 측정한다.

Big-O는 후보를 거르는 지도이고, invariant는 정답임을 지키는 계약이며, profiling과 benchmark는 현실 비용을 확인하는 계기판이다. 세 가지가 함께 있을 때 자료구조 선택이 암기가 아니라 엔지니어링 판단이 된다.
