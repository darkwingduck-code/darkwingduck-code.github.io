---
title: "A Practical Mental Model for Data Structures and Algorithms: Rationale Before Complexity"
date: 2026-07-21 10:10:00 +0900
categories: [Computer Science, Algorithms]
tags: [data-structures, algorithms, big-o, amortized-analysis, graph-algorithms, invariants, benchmarking]
description: "How to interpret Big-O and amortized analysis as real cost models, and choose arrays, hashes, heaps, trees, and graph algorithms based on requirements, correctness, and measurement."
math: true
lang: en
hidden: true
translation_key: data-structures-algorithms-practical-mental-model
---

{% include language-switcher.html %}

Memorizing data structures and algorithms as an exam table leaves only sentences such as “a hash is \(O(1)\), while a tree is \(O(\log n)\).” In real design, ask the following questions first.

- Does the data fit in memory?
- Which operation is most frequent: lookup, insertion, extracting the minimum, or range queries?
- Must order and duplicates be preserved?
- Is worst-case latency important, or is average throughput more important?
- What are the data distribution and the possibility of adversarial input?
- What are the costs of cache locality, allocation, and concurrency?

Choosing an algorithm is not a naming exercise. It is **the work of translating requirements into a cost model and correctness invariants**.

## 1. Define Size Variables Before Analysis

Big-O is meaningless if you do not know what \(n\) represents in the complexity expression.

- Number of array elements \(n\)
- Number of vertices \(V\) and edges \(E\) in a graph
- String length \(L\)
- Number of queries \(Q\)
- State dimension \(d\)
- Number of bits \(b\) in an integer value

For example, describing a graph algorithm unconditionally as \(O(n^2)\) erases the distinction between sparse and dense graphs. BFS based on an adjacency list is

$$
\Theta(V+E)
$$

while scanning an entire adjacency matrix is

$$
\Theta(V^2)
$$

Representation, not just the algorithm's name, changes complexity.

## 2. Big-O, Big-Theta, and Big-Omega

### Upper bound: \(O(g(n))\)

If there is a constant \(c\) such that, for sufficiently large \(n\),

$$
0\le f(n)\le c\,g(n)
$$

then \(f(n)=O(g(n))\). Because this is an upper bound, a function in \(\Theta(n)\) can also be described as \(O(n^2)\). Whenever possible, the tight bound \(\Theta\) conveys more information.

### Asymptotically the same order: \(\Theta(g(n))\)

If

$$
c_1g(n)\le f(n)\le c_2g(n)
$$

then \(f(n)=\Theta(g(n))\).

### Lower bound: \(\Omega(g(n))\)

If \(f(n)\ge c\,g(n)\) for sufficiently large \(n\), it is a lower bound.

### Qualify worst, average, and expected

“Hash lookup is \(O(1)\)” is generally an expected or amortized statement that assumes suitable hashing and load factor. The worst case differs when collisions are concentrated. Distinguish the following.

- Worst case per operation
- Expected cost over randomization
- Average case under a specified input distribution
- Amortized cost over an operation sequence

Average and amortized do not mean the same thing.

## 3. Amortized Analysis: Distribute Rare Expensive Operations Across the Full Sequence

When a dynamic array reaches capacity, creating a larger buffer and copying all elements can make one append cost \(\Theta(n)\). But if capacity grows by a constant factor, the total number of copies across \(m\) appends is bounded by a geometric series.

$$
1+2+4+\cdots < 2m.
$$

Therefore, the total cost of \(m\) appends is \(\Theta(m)\), and the amortized cost per append is \(\Theta(1)\).

Amortized analysis is not an empirical average saying that “it was fast most of the time.” It proves that **the total cost does not exceed the bound for any input sequence**.

Representative proof methods are:

- Aggregate method: directly sum the cost of the whole sequence
- Accounting method: charge credit in advance to cheap operations
- Potential method: include changes in the data structure's potential in the cost

In a system with a latency deadline, amortized \(O(1)\) may not be enough. Determine whether one \(O(n)\) pause for a resize is acceptable and whether incremental rehashing or capacity reservation is needed.

## 4. Complexity Is a Multidimensional Cost

Choosing based on time complexity alone misses:

- Auxiliary memory
- Number of allocations
- Cache misses and pointer chasing
- Branch prediction
- Serialization size
- Parallel contention
- Preprocessing time
- Ratio of updates to queries

Even at the same \(O(n)\), scanning a contiguous array can be much faster than traversing a linked structure. Conversely, a linked list can be advantageous for unlinking when a pointer to the middle node is already available. The cost of finding that node must not be omitted.

## 5. A Data-Structure Selection Map

### Array / dynamic array

**Strengths**

- Index access in \(\Theta(1)\)
- Contiguous memory and good cache locality
- Amortized \(\Theta(1)\) append at the end
- Suitable for sorting, binary search, and vectorized processing

**Weaknesses**

- Insertion or deletion in the middle is \(\Theta(n)\) because elements move
- Resize spikes and spare capacity
- Stable pointers may be invalidated

This is a very strong default. Check whether a language's “list” is actually a dynamic array or a linked list.

### Linked list

**Strengths**

- \(\Theta(1)\) insertion and deletion when the node position is already known
- Structures that need splicing and stable node references

**Weaknesses**

- Index access and search in \(\Theta(n)\)
- Per-node allocation and pointer overhead
- Poor cache locality

Do not select one merely because “there are many insertions.” If finding the insertion point costs \(\Theta(n)\), the overall advantage can disappear.

### Hash table

**Strengths**

- Expected \(\Theta(1)\) key-based lookup, insertion, and deletion
- Membership, frequency counting, and deduplication

**Weaknesses**

- Unsuitable for key order and range queries
- Depends on hash quality and load factor
- Rehashing cost
- Risks from adversarial collisions and mutable keys

Equality and hashing must be consistent.

$$
a=b\quad\Longrightarrow\quad hash(a)=hash(b).
$$

Changing a field involved in equality after using an object as a key can make the entry impossible to find.

### Balanced search tree

**Strengths**

- Worst-case \(\Theta(\log n)\) lookup, insertion, and deletion
- Sorted traversal
- Predecessor and successor
- Range queries

**Weaknesses**

- Larger constants and pointer overhead than a hash table
- Complexity of balancing implementations

It is appropriate when an ordered map or set, interval queries, or predictable worst-case behavior is required.

### Heap / priority queue

For a binary heap:

- Inspect minimum or maximum: \(\Theta(1)\)
- Push: \(\Theta(\log n)\)
- Pop minimum or maximum: \(\Theta(\log n)\)
- Search for an arbitrary key among all unordered elements: \(\Theta(n)\)
- Bulk heapify: \(\Theta(n)\)

A heap is not a “sorted container.” It guarantees only the root's priority. Use it when repeatedly extracting the next highest-priority item, as in top-\(k\), schedulers, and the Dijkstra frontier.

### Deque

Use one when a queue needs \(\Theta(1)\) push and pop at both ends. In BFS, avoid repeatedly deleting from the front of an array and causing \(\Theta(n)\) shifts.

### Disjoint-set union

When repeatedly merging sets and querying connectivity, path compression with union by rank or size gives an amortized per-operation cost effectively close to constant:

$$
O(\alpha(n))
$$

It is unsuitable when dynamic deletion or the path itself is required.

## 6. Work Backward from the Goal to the Data Structure

| Core requirement | First candidate | Conditions to verify |
|---|---|---|
| Index access and sequential scan | dynamic array | Frequency of middle modifications, capacity |
| Key membership | hash set/map | Whether order or worst-case guarantees are needed |
| Sorted keys and range queries | balanced tree | Update/query ratio |
| Repeated extraction of minimum | heap | Support for arbitrary deletion/decrease-key |
| FIFO | deque | Bounded queue, concurrency |
| LIFO | stack / dynamic array | Maximum depth |
| Connectivity merge/query | disjoint set | Whether edges are never deleted |
| Sparse graph traversal | adjacency list | Multiedges, direction |
| Dense graph or fast edge test | adjacency matrix/bitset | Whether \(V^2\) memory is acceptable |

A service can separate its source of truth from serving indexes. For example, records can be stored in an array while maintaining a hash index for ID lookup and a heap for priority. In that case, **the synchronization invariant across representations** becomes a new cost.

## 7. Graph Representation Determines the Algorithm

### Adjacency list

Memory is \(\Theta(V+E)\), and iterating over one vertex's neighbors is proportional to its degree. This is the default for sparse graphs.

### Adjacency matrix

Memory is \(\Theta(V^2)\), but testing whether an edge exists takes \(\Theta(1)\). It can suit dense graphs, small graphs, and bit-parallel operations.

### Edge list

This is simple for algorithms that scan or sort every edge once. Looking up an arbitrary vertex's neighbors is slow without a separate index.

When choosing a representation, also decide whether the graph is directed or undirected, weighted or unweighted, whether it permits self-loops and parallel edges, whether it is mutable, and how dense vertex IDs are.

## 8. Preconditions for BFS, DFS, and Dijkstra

### BFS

BFS finds the shortest distance in number of edges from a source in an unweighted graph or a graph whose edge costs are all equal.

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

Mark a vertex as visited when it is **enqueued**, not when it is removed from the queue, to prevent the same vertex from being enqueued repeatedly.

This example assumes that every sink vertex appearing as a neighbor is also a key in `graph`. A real API should validate this representation invariant or explicitly handle an empty adjacency with something like `graph.get(u, ())`.

### DFS

DFS is a building block for reachability, connected components, cycle detection, and topological sorting. But “using DFS” alone does not determine cycles.

- Undirected graph: a visited neighbor other than the parent edge signals a cycle
- Directed graph: a back edge into the current recursion stack or color state is needed
- Topological order: valid only for a directed acyclic graph

Traversal order in a DFS tree can vary with adjacency iteration order. Fix neighbor order when deterministic output is required.

### Dijkstra

Dijkstra finds single-source shortest paths when **every edge weight is nonnegative**.

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

Because stale entries for the same vertex can remain in the priority queue, a stale-entry check is required. An implementation using a heap with direct decrease-key support differs.

With an adjacency list and binary heap, the usual time complexity is \(O((V+E)\log V)\), commonly written as \(O(E\log V)\) for a connected graph. For the implementation above, which permits duplicate entries, also consider heap memory and constant costs.

### Selection by weight structure

| Edge weight | Algorithm candidate |
|---|---|
| All equal | BFS |
| 0 or 1 | 0–1 BFS |
| All nonnegative | Dijkstra |
| Negative edges possible | Bellman–Ford family |
| DAG | Topological-order relaxation |
| All pairs, dense/small graph | Consider Floyd–Warshall and others |

When a negative cycle is reachable, a finite shortest path itself may be undefined. This is a problem-definition issue, not an algorithm failure.

## 9. Recursion and Iteration

Recursion expresses tree and divide-and-conquer definitions close to the structure of the code. It also has these costs.

- Call-stack depth limits
- Frame allocation and function-call overhead
- Stack overflow in deep or skewed trees
- Implicit state and error recovery

Iteration manages traversal state directly with an explicit stack or queue.

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

This example assumes adjacency is a deterministic sequence supported by `reversed`. To match the visitation order of recursive DFS, the LIFO behavior of the stack may require neighbors to be pushed in reverse order. Even when visitation order is irrelevant to correctness, verify that tests do not accidentally depend on it.

Selection criteria include:

- Small and clearly bounded depth: recursion may be easier to read
- Adversarial input or \(O(n)\) depth: prefer iteration
- Pausing, resuming, or serializing traversal: explicit state is advantageous
- Post-order processing: store enter/exit state in the stack frame

Verify whether the language and runtime guarantee tail-call optimization.

## 10. Connect Proofs to Code with Correctness Invariants

To show that an algorithm is correct for every valid input rather than merely “working for the example,” use a loop invariant.

### Three steps

1. **Initialization**: the invariant is true before the loop starts.
2. **Maintenance**: it remains true after an iteration.
3. **Termination**: when the loop finishes, the invariant yields the desired conclusion.

### Example binary-search invariant

When using the half-open interval \([lo,hi)\):

- If an answer exists, it is always inside \([lo,hi)\).
- \([0,lo)\) does not satisfy the condition.
- \([hi,n)\) satisfies the condition.

Maintain the same boundary convention through updates and the return to avoid off-by-one errors.

### BFS invariant

The distances of vertices processed from the queue are nondecreasing, and the first discovered path has the minimum number of edges. This depends on the precondition that every edge cost is equal.

### Dijkstra invariant

The distance of a vertex finalized with the valid minimum from the heap is the shortest distance. Nonnegative edges are required for the proof that an unvisited path cannot later make that value smaller.

### Heap invariant

Every node key in a min-heap is no greater than its children's keys. Total sorting is not required. Test whether local repair after push or pop restores this invariant.

## 11. Edge Cases Are Design Inputs, Not Later Exceptions

### Collections

- Empty
- One element
- All equal
- Already sorted / reverse sorted
- Many duplicates
- Immediately before and after a capacity boundary
- Missing key and repeated deletion

### Numeric

- Zero and negative zero
- Minimum and maximum representable values
- Integer overflow
- Whether NaN and infinity are allowed
- Floating-point equality and tolerance
- Widely differing magnitudes

### Graph

- Isolated vertex
- Disconnected component
- Self-loop
- Parallel edge
- Confusion between directed and undirected
- Cycle and reachable negative cycle
- Source absent from the graph
- Multiple shortest paths

### Resources

- Input that does not fit in memory
- Maximum recursion depth
- Cancellation and timeout
- Partial reads and writes
- Concurrent mutation

Do not leave edge cases only in a test list. Decide in the API contract whether to reject, normalize, or support each one.

## 12. Profiling: Find Where the Cost Is Instead of Guessing

Even an algorithm with good complexity may not be the real bottleneck. Follow this sequence before optimization.

1. Define end-to-end latency or throughput targets.
2. Profile under a production-like workload.
3. Separate CPU, allocation, I/O wait, and lock contention.
4. Inspect call frequency and per-call cost on the hot path.
5. Measure again under the same conditions after changing the algorithm or representation.

Removing an \(O(n^2)\) loop, unnecessary serialization, repeated DB queries, or an allocation pattern often has a much larger effect than micro-optimization.

## 13. Conditions for Trusting a Benchmark

### Workload

- Measure at multiple points across the real size range
- Include sorted, duplicate-heavy, skewed, and adversarial distributions, not only random input
- Reflect read/write and cache-hit ratios
- Distinguish warm and cold caches

### Measurement

- Control warm-up and JIT/GC effects
- Separate setup from the timed region
- Measure the median and tail percentiles across multiple repetitions
- Record CPU frequency scaling and background load
- Consume results to prevent dead-code elimination
- Measure peak memory and allocations as well

### Interpretation

A log-log plot or operation count by input size can reveal the crossover. A simple algorithm may be faster for small \(n\), while an asymptotically better one overtakes it for large \(n\).

A benchmark does not prove a universal truth. It is evidence about the measured hardware, runtime, and input distribution.

## 14. Practical Selection Workflow

1. **List operations**: estimate the frequencies of lookup, insert, delete, minimum, range, and traversal.
2. **Define the contract**: decide ordering, duplicates, mutability, concurrency, and latency bounds.
3. **Define sizes and distributions**: record \(n,V,E,Q\), sparsity, skew, and the possibility of adversarial input.
4. **Compare candidate structures**: tabulate average, worst-case, and amortized time and memory.
5. **Write correctness invariants**: record conditions the structure and algorithm must maintain.
6. Build **the simplest correct implementation**.
7. Verify invariants with **edge and property tests**.
8. Use **profiling** to find the real bottleneck.
9. Compare alternatives with a **representative benchmark**.
10. **Record the rationale**: retain workload assumptions and reevaluation thresholds.

## 15. Verification Checklist

- [ ] Are the size variables in complexity expressions defined?
- [ ] Are worst, expected, average, and amortized distinguished?
- [ ] Are memory, allocation, and locality evaluated as well as time?
- [ ] Does the insertion cost for a linked list include locating the position?
- [ ] Have hash ordering, collision, and mutable-key conditions been checked?
- [ ] Is a heap understood as something other than a fully sorted structure?
- [ ] Does the graph representation fit sparsity and query needs?
- [ ] Have the edge-weight and direction preconditions of BFS, DFS, and Dijkstra been checked?
- [ ] Is recursion depth not unbounded by input?
- [ ] Can initialization, maintenance, and termination of the loop invariant be explained?
- [ ] Are empty, duplicate, overflow, and disconnected cases tested?
- [ ] Was the bottleneck confirmed by profiling before optimization?
- [ ] Are the benchmark workload and environment recorded?
- [ ] Were tail latency and peak memory inspected as well as averages?

## 16. Common Pitfalls and Limitations

### A structure with smaller Big-O is always faster

Constants, cache locality, allocation, and the actual range of \(n\) determine the crossover. Both asymptotic analysis and benchmarks are needed.

### Inferring complexity from a library name alone

Containers with the same name can have different implementations across languages. Check operation guarantees and invalidation rules in official documentation.

### Assuming sorted input is easy input

Depending on the algorithm, sorted or reverse-sorted input can be the worst case. Inspect the assumptions behind pivots, hashes, and tree balancing.

### Giving Dijkstra negative edges and checking only the result

It may happen to work on a small example, but the precondition of its correctness proof is broken. Put input validation at the algorithm boundary.

### Assuming converting recursion to a loop always preserves order

The traversal tree changes with the order in which neighbors are pushed onto the explicit stack and the moment they are marked visited.

### Permanently fixing a choice based on one benchmark

When data size, read/write ratio, or runtime version changes, the rationale can change too. Record criteria for reevaluation.

## Conclusion

The practical mental model for data structures and algorithms can be condensed into this statement.

> First write down the required operations and guarantees, choose the simplest structure that maintains them, check scalability with asymptotic analysis, and measure it under the real workload.

Big-O is a map for filtering candidates, an invariant is a contract that preserves correctness, and profiling and benchmarking are the dashboard for checking real costs. With all three, choosing a data structure becomes an engineering decision rather than an exercise in memorization.
