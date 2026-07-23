---
title: "データ構造・アルゴリズムの実践Mental Model：計算量より選定根拠"
date: 2026-07-21 10:10:00 +0900
categories: [Computer Science, Algorithms]
tags: [data-structures, algorithms, big-o, amortized-analysis, graph-algorithms, invariants, benchmarking]
description: "Big-Oと償却解析を実際のコストモデルとして捉え、array、hash、heap、tree、graphアルゴリズムを要件・正しさ・測定根拠から選ぶ方法を整理する。"
math: true
lang: ja-JP
translation_key: data-structures-algorithms-practical-mental-model
hidden: true
---

{% include language-switcher.html %}

データ構造とアルゴリズムを試験用の表として暗記すると、「hashは \(O(1)\)、treeは \(O(\log n)\)」という文だけが残る。実際の設計では、その前に次を問うべきである。

- データはメモリに収まるか。
- 最も頻繁な操作は、検索、挿入、最小値抽出、範囲照会のどれか。
- 順序と重複を保持する必要があるか。
- worst-case latencyと平均throughputのどちらが重要か。
- データ分布とadversarial inputの可能性はどうか。
- cache locality、allocation、concurrencyのコストはどうか。

アルゴリズム選択は名称当てではなく、**要件をコストモデルとcorrectness invariantへ翻訳する作業**である。

## 1. 解析前にサイズ変数を定義する

計算量式の \(n\) が何か分からなければ、Big-Oには意味がない。

- 配列要素数 \(n\)
- graphのvertex数 \(V\) とedge数 \(E\)
- 文字列長 \(L\)
- query数 \(Q\)
- state dimension \(d\)
- 整数値のbit数 \(b\)

たとえばgraph algorithmを一律に \(O(n^2)\) と書けば、sparse graphとdense graphの違いが消える。adjacency listベースのBFSは

$$
\Theta(V+E)
$$

であり、adjacency matrixをすべてscanすれば

$$
\Theta(V^2)
$$

となる。アルゴリズム名だけでなくrepresentationも計算量を変える。

## 2. Big-O、Big-Theta、Big-Omega

### 上界：\(O(g(n))\)

十分大きい \(n\) に対して

$$
0\le f(n)\le c\,g(n)
$$

を満たす定数 \(c\) が存在すれば、\(f(n)=O(g(n))\) である。upper boundなので、\(\Theta(n)\) の関数を \(O(n^2)\) と表すこともできる。可能ならtight boundである \(\Theta\) を用いる方が情報量は多い。

### 漸近的に同じ次数：\(\Theta(g(n))\)

$$
c_1g(n)\le f(n)\le c_2g(n)
$$

ならば \(f(n)=\Theta(g(n))\) である。

### 下界：\(\Omega(g(n))\)

十分大きい \(n\) で \(f(n)\ge c\,g(n)\) ならlower boundである。

### Worst、average、expectedを明記する

「hash lookupは \(O(1)\)」は通常、適切なhashingとload factorを仮定したexpectedまたはamortizedな説明である。衝突が集中すればworst caseは変わる。次を区別する。

- worst-case per operation
- expected cost over randomization
- average case under a specified input distribution
- amortized cost over an operation sequence

averageとamortizedは同義ではない。

## 3. 償却解析：まれな高コスト操作をsequence全体へ配分する

動的配列のcapacityが埋まったとき、より大きなbufferを作って全要素をコピーすると、一回のappendは \(\Theta(n)\) になり得る。しかしcapacityを一定倍率で増やせば、\(m\) 回のappend全体のコピー量はgeometric seriesで制限される。

$$
1+2+4+\cdots < 2m.
$$

したがって \(m\) 回のappendの総コストは \(\Theta(m)\)、append一回当たりのamortized costは \(\Theta(1)\) である。

償却解析は「たいてい速かった」という経験的平均ではない。**どのような入力sequenceでも総コストがそのboundを超えないこと**を示す解析である。

代表的な証明方法は次のとおりである。

- aggregate method：sequence全体のコストを直接合計
- accounting method：安価な操作へ事前にcreditを課す
- potential method：データ構造状態のpotential変化をコストに含める

latency deadlineがあるシステムでは、amortized \(O(1)\) だけでは足りない場合がある。一度のresizeによる \(O(n)\) pauseを許容できるか、incremental rehashingやcapacity reservationが必要かを確認する。

## 4. 計算量は多次元のコストである

時間計算量だけで選ぶと、次を見落とす。

- auxiliary memory
- allocation回数
- cache missとpointer chasing
- branch prediction
- serialization size
- parallel contention
- preprocessing time
- updateとqueryの比率

同じ \(O(n)\) でも、contiguous array scanはlinked structure traversalより大幅に速いことがある。一方、中間nodeをすでに参照している状態でunlinkするならlinked listが有利な場合がある。ただしnodeを見つけるコストを除外して説明してはならない。

## 5. データ構造の選択地図

### Array / dynamic array

**長所**

- indexアクセス \(\Theta(1)\)
- 連続メモリによる良好なcache locality
- 末尾appendのamortized \(\Theta(1)\)
- sorting、binary search、vectorized processingに適する

**短所**

- 中間の挿入・削除は要素移動により \(\Theta(n)\)
- resize spikeと余剰capacity
- stable pointerが無効になる可能性

既定候補として非常に強い。言語の「list」が実際にはdynamic arrayかlinked listか、実装を確認する。

### Linked list

**長所**

- node位置が既知なら挿入・削除は \(\Theta(1)\)
- spliceとstable node referenceが必要な構造

**短所**

- indexアクセスと探索は \(\Theta(n)\)
- nodeごとのallocationとpointer overhead
- cache localityが悪い

「挿入が多い」という理由だけで選ばない。挿入位置の探索が \(\Theta(n)\) なら、利点が消える可能性がある。

### Hash table

**長所**

- keyベースlookup/insert/deleteのexpected \(\Theta(1)\)
- membership、frequency count、deduplication

**短所**

- key orderとrange queryに不向き
- hash qualityとload factorに依存
- rehashコスト
- adversarial collisionとmutable keyの危険

equalityとhashは整合していなければならない。

$$
a=b\quad\Longrightarrow\quad hash(a)=hash(b).
$$

keyとして使った後でequalityに関与するfieldを変更すると、項目を見つけられなくなる場合がある。

### Balanced search tree

**長所**

- lookup/insert/deleteのworst-case \(\Theta(\log n)\)
- ソート順の走査
- predecessor/successor
- range query

**短所**

- hashより大きな定数とpointer overhead
- balancing実装の複雑さ

ordered map/set、interval query、予測可能なworst-caseが必要な場合に適する。

### Heap / priority queue

binary heapでは

- 最小・最大値の参照：\(\Theta(1)\)
- push：\(\Theta(\log n)\)
- pop min/max：\(\Theta(\log n)\)
- 全unordered要素から任意keyを探索：\(\Theta(n)\)
- bulk heapify：\(\Theta(n)\)

heapは「ソート済みcontainer」ではない。rootの優先順位だけを保証する。top-\(k\)、scheduler、Dijkstra frontierのように、次の最優先項目を反復抽出するときに使う。

### Deque

両端のpush/popが \(\Theta(1)\) のqueueが必要なときに使う。BFSでarray先頭の削除を繰り返して \(\Theta(n)\) shiftを発生させない。

### Disjoint-set union

集合の統合と連結性照会を繰り返す場合、path compressionとunion by rank/sizeにより、一操作当たりのamortized costは実質的に定数に近い

$$
O(\alpha(n))
$$

となる。動的削除や経路そのものが必要な場合には適さない。

## 6. 目的からデータ構造を逆算する

| 主要要件 | 最初の候補 | 確認条件 |
|---|---|---|
| indexアクセス・連続scan | dynamic array | 中間変更頻度、capacity |
| key membership | hash set/map | 順序・worst-caseの必要性 |
| ソート済みkey・範囲照会 | balanced tree | update/query比率 |
| 最小値の反復抽出 | heap | 任意削除/decrease-key対応 |
| FIFO | deque | bounded queue、concurrency |
| LIFO | stack / dynamic array | 最大depth |
| 連結性merge/query | disjoint set | edge削除がないか |
| sparse graph traversal | adjacency list | multiedge、direction |
| dense graphまたは高速edge test | adjacency matrix/bitset | \(V^2\) memoryを許容できるか |

一つのサービスでsource of truthとserving indexを分離できる。たとえばrecordはarrayへ保存し、ID lookup用hash indexと優先順位用heapを同時に維持する。この場合は、**複数表現の同期invariant**が新たなコストになる。

## 7. Graph representationがalgorithmを決める

### Adjacency list

memoryは \(\Theta(V+E)\) で、あるvertexの隣接走査はdegreeに比例する。sparse graphの既定候補である。

### Adjacency matrix

memoryは \(\Theta(V^2)\) だが、edgeの存在確認は \(\Theta(1)\) である。dense graph、小規模graph、bit-parallel operationに適する場合がある。

### Edge list

全edgeを一度scanまたはsortingするalgorithmには単純である。任意vertexの隣接照会は、別のindexがなければ遅い。

representationを決める際は、directed/undirected、weighted/unweighted、self-loop、parallel edge、mutable graph、vertex ID densityも同時に決める。

## 8. BFS、DFS、Dijkstraの前提

### BFS

BFSはunweighted graph、または全edge costが同一のgraphで、sourceからの最小edge数距離を求める。

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

vertexをqueueから取り出す時ではなく、**追加する時点でvisitedにする**ことで、同じvertexが重複enqueueされるのを防ぐ。

この例は、隣接先として現れるsink vertexもすべて `graph` のkeyとして存在すると仮定する。実際のAPIでは、このrepresentation invariantをvalidationするか、`graph.get(u, ())` のように空のadjacencyを明示的に処理する。

### DFS

DFSはreachability、connected component、cycle detection、topological sortの構成要素である。しかし「DFSを使った」というだけではcycle判定にならない。

- undirected graph：parent edge以外のvisited neighborがcycleの信号
- directed graph：現在のrecursion stackまたはcolor stateに対するback edgeが必要
- topological order：directed acyclic graphでのみ有効

DFS treeの探索順はadjacency iteration orderにより変わり得る。deterministic outputが必要ならneighbor orderを固定する。

### Dijkstra

Dijkstraは**すべてのedge weightがnonnegative**であるとき、single-source shortest pathを求める。

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

priority queueには同じvertexの古いentryが残り得るため、stale-entry checkが必要である。decrease-keyを直接サポートするheapなら実装は異なる。

adjacency listとbinary heapを使う一般的な時間計算量は \(O((V+E)\log V)\)、連結graphではしばしば \(O(E\log V)\) と書く。duplicate entryを許す上記実装では、heap memoryと定数コストも確認する。

### Weight構造別の選択

| Edge weight | Algorithm候補 |
|---|---|
| すべて同一 | BFS |
| 0または1 | 0–1 BFS |
| すべてnonnegative | Dijkstra |
| negative edgeの可能性 | Bellman–Ford系 |
| DAG | topological-order relaxation |
| all-pairs、dense/small graph | Floyd–Warshallなどを検討 |

到達可能なnegative cycleがあれば、finite shortest path自体が定義できない場合がある。これはalgorithmの失敗ではなく問題定義の問題である。

## 9. Recursionとiteration

再帰はtreeやdivide-and-conquerの定義をコード構造へ近く表現する。ただし次のコストがある。

- call stack depth制限
- frame allocationと関数呼び出しoverhead
- deep/skewed treeでのstack overflow
- 状態とerror recoveryの暗黙性

iterationではexplicit stack/queueによりtraversal stateを直接管理する。

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

この例はadjacencyが `reversed` をサポートするdeterministic sequenceだと仮定する。再帰DFSと同じ訪問順が必要なら、stackのLIFO特性のためneighborをpushする順序を逆にする必要がある。訪問順がcorrectnessに不要でも、testが偶然その順序へ依存していないか確認する。

選択基準は次のとおりである。

- depthが小さく明確にbounded：recursionの方が読みやすい場合がある
- 入力がadversarial、またはdepthが \(O(n)\)：iterationを優先
- traversalをpause/resumeまたはserialize：explicit stateが有利
- post-order処理：stack frameへenter/exit stateも保存

tail recursion optimizationを言語とruntimeが保証するか確認する。

## 10. Correctness invariantで証明とコードを結ぶ

アルゴリズムが「例では動いた」だけでなく、すべての有効入力で正しいことを示すにはloop invariantを使う。

### 三段階

1. **Initialization**：loop開始前にinvariantが真である。
2. **Maintenance**：一回のiteration後も真である。
3. **Termination**：loop終了時にinvariantから望む結論が得られる。

### Binary searchのinvariant例

half-open interval \([lo,hi)\) を使うなら

- 答えが存在するとき、常に \([lo,hi)\) 内にある。
- \([0,lo)\) は条件を満たさない。
- \([hi,n)\) は条件を満たす。

同じboundary conventionをupdateとreturnまで維持し、off-by-oneを避ける。

### BFS invariant

queueで処理されるvertexのdistanceはnondecreasingであり、最初に発見した経路が最小edge数の経路である。これは全edge costが同一という前提に依存する。

### Dijkstra invariant

heapから有効な最小距離で確定したvertexのdistanceは最短距離である。nonnegative edgeがあるため、未訪問経路が後からその値を小さくできない、という証明が成立する。

### Heap invariant

min-heapでは各node keyが子node key以下である。全体のソートは要求しない。push/pop後のlocal repairがこのinvariantを復元するかテストする。

## 11. Edge caseは後付けの例外ではなく設計入力

### Collection

- empty
- one element
- all equal
- already sorted / reverse sorted
- many duplicates
- capacity boundaryの直前・直後
- missing keyとrepeated delete

### Numeric

- zeroとnegative zero
- min/max representable value
- integer overflow
- NaNとinfinityを許可するか
- floating equalityとtolerance
- 大きく異なるmagnitude

### Graph

- isolated vertex
- disconnected component
- self-loop
- parallel edge
- directed/undirectedの混同
- cycleとreachable negative cycle
- sourceがgraphに存在しない
- multiple shortest paths

### Resource

- メモリに収まらない入力
- recursion maximum depth
- cancellationとtimeout
- partial read/write
- concurrent mutation

edge caseをtest一覧に置くだけでなく、API contractでreject、normalize、supportのいずれかを決める。

## 12. Profiling：推測せずコストの位置を特定する

計算量の良いalgorithmでも実際のbottleneckではない場合がある。最適化前に次の順序を取る。

1. end-to-end latency/throughput目標を決める。
2. productionに近いworkloadでprofileする。
3. CPU、allocation、I/O wait、lock contentionを分ける。
4. hot pathの呼び出し頻度とper-call costを見る。
5. algorithmまたはrepresentation変更後、同じ条件で再測定する。

micro-optimizationよりも、\(O(n^2)\) loopの除去、不要なserialization、反復DB query、allocation patternの変更の方が大きな効果を持つことが多い。

## 13. Benchmarkを信頼する条件

### Workload

- 実際のサイズ範囲を複数点で測定
- randomだけでなくsorted、duplicate-heavy、skewed、adversarial分布
- read/write ratioとcache hit ratioを反映
- warm/cold cacheを区別

### Measurement

- warm-upとJIT/GC影響を統制
- setupとtimed regionを分離
- 複数回のmedianとtail percentile
- CPU frequency scaling、background loadを記録
- 結果を消費してdead-code eliminationを防止
- peak memoryとallocationも測定

### Interpretation

入力サイズごとのlog-log plotやoperation countからcrossoverを見つけられる。小さい \(n\) では単純なalgorithmが速く、大きい \(n\) で漸近的に優れたalgorithmが逆転する場合がある。

benchmarkは普遍的真理を証明しない。測定したhardware、runtime、input distributionに対する証拠である。

## 14. 実践的な選択workflow

1. **操作一覧を作る**：lookup、insert、delete、min、range、traversalの頻度を見積もる。
2. **contractを定義する**：ordering、duplicates、mutability、concurrency、latency boundを決める。
3. **サイズと分布を定義する**：\(n,V,E,Q\)、sparsity、skew、adversarial可能性を記す。
4. **候補構造を比較する**：平均・最悪・償却時間とmemoryを表にする。
5. **correctness invariantを書く**：構造とalgorithmが維持すべき条件を記す。
6. **最も単純で正しい実装**を作る。
7. **edge/property test**でinvariantを検証する。
8. **profile**で実際のbottleneckを見つける。
9. **representative benchmark**で代替案を比べる。
10. **選択根拠を記録する**：workload仮定と再評価thresholdを残す。

## 15. 検証チェックリスト

- [ ] 計算量のサイズ変数を定義したか。
- [ ] worst、expected、average、amortizedを区別したか。
- [ ] 時間だけでなくmemory・allocation・localityを評価したか。
- [ ] linked listの挿入コストへ位置探索を含めたか。
- [ ] hashのorder、collision、mutable key条件を確認したか。
- [ ] heapを全体ソート構造と誤解していないか。
- [ ] graph representationがsparsityとqueryに合うか。
- [ ] BFS/DFS/Dijkstraのedge-weight・方向の前提を確認したか。
- [ ] recursion depthが入力によりunboundedにならないか。
- [ ] loop invariantの初期化・維持・終了を説明できるか。
- [ ] empty、duplicate、overflow、disconnected caseをテストしたか。
- [ ] profileでbottleneckを確認してから最適化したか。
- [ ] benchmark workloadと環境を記録したか。
- [ ] 平均だけでなくtail latencyとpeak memoryを確認したか。

## 16. よくある落とし穴と限界

### Big-Oが小さい構造は常に速い

定数、cache locality、allocation、実際の \(n\) の範囲がcrossoverを決める。漸近解析とbenchmarkの両方が必要である。

### Library名だけで計算量を推定する

同名のcontainerでも言語ごとに実装は異なる。operation guaranteeとinvalidation ruleを公式文書で確認する。

### ソート済み入力は簡単な入力だという仮定

algorithmによってはsorted/reverse-sorted inputがworst caseになる。pivot、hash、tree balancingの前提を見る。

### Dijkstraへnegative edgeを入れて結果だけ確認する

小さな例では偶然正しくても、correctness proofの前提が崩れる。入力validationをalgorithm boundaryへ置く。

### 再帰を反復へ変えれば常に同じ順序になる

explicit stackへ隣接要素を入れる順序とvisited処理の時点で、traversal treeは変わる。

### 一つのBenchmarkで選択を永久固定する

データサイズ、read/write ratio、runtime versionが変われば選択根拠も変わる。再評価基準を残す。

## まとめ

データ構造・アルゴリズムの実践mental modelは次の一文に集約できる。

> 必要な操作と保証条件を先に書き、その条件を維持する最も単純な構造を選んだうえで、漸近解析により拡張性を確認し、実際のworkloadで測定する。

Big-Oは候補を絞る地図、invariantは正解を守るcontract、profilingとbenchmarkは現実のコストを確認する計器である。この三つが揃って初めて、データ構造の選択は暗記ではなくengineering judgmentになる。
