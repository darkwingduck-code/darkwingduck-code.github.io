---
title: "CUDA Performance and Correctness: Practical Principles for APOD, the Memory Hierarchy, and Profiling"
date: 2026-07-21 12:29:00 +0900
categories: [GPU, Performance]
tags: [cuda, gpu-programming, profiling, memory-coalescing, numerical-correctness]
description: Improve CUDA kernels with an accurate CPU reference, the APOD cycle, memory-traffic analysis, occupancy, and profiler evidence instead of optimizing blindly.
lang: en
hidden: true
translation_key: cuda-performance-correctness
math: true
mermaid: true
---

{% include language-switcher.html %}

CUDA optimization is not a trick of increasing the thread count or adding shared memory.
It is an iterative process of finding worthwhile bottlenecks in the entire application and improving data movement and execution efficiency while preserving correctness.

## 1. The Problem: A Fast Kernel Does Not Guarantee a Fast Application

GPU code consists of the following costs.

- Host preprocessing
- Host-to-device transfer
- Kernel launch
- Device computation
- Device synchronization
- Device-to-host transfer
- Postprocessing

Even if a kernel becomes dozens of times faster, the impact is limited when it represents only a small portion of the total time.
Amdahl's law is as follows.

$$
S=\frac{1}{(1-p)+p/s}
$$

- (p): proportion occupied by the target of improvement
- (s): speedup of that portion

First, measure (p) with a profile.

## 2. Mental Model: The APOD Cycle

```mermaid
flowchart LR
    A[Assess] --> B[Parallelize]
    B --> C[Optimize]
    C --> D[Deploy]
    D --> E[Observe real workloads]
    E --> A
```

NVIDIA's APOD approach emphasizes the following cycle.

- Assess: Measure the hotspots and objectives.
- Parallelize: Select the parts that can be parallelized safely.
- Optimize: Improve memory, execution, and instructions.
- Deploy: Validate regressions and portability in the real environment.

Keep correctness tests and profiler evidence for every optimization.

## 3. CPU Reference and Numerical Contract

Before implementing on the GPU, maintain a reference for small inputs.

```cpp
for (int i = 0; i < n; ++i) {
    reference[i] = transform(input[i]);
}
```

Validation items:

- Absolute and relative tolerance
- NaN and Inf
- Zero length and boundary sizes
- Sizes that are not multiples of the block size
- Extremely large or small values
- Determinism requirements
- Differences in reduction order

Floating-point addition does not exactly satisfy associativity.
A parallel reduction may not be bitwise identical to a sequential CPU sum.

Example error criterion:

$$
|y_{gpu}-y_{ref}| \le a_{tol}+r_{tol}|y_{ref}|
$$

A tolerance should be based on the dtype, condition number, and number of accumulated operations, not set to an arbitrarily large value.

## 4. Thread, Block, and Grid Mapping

Basic mapping for a one-dimensional array:

```cpp
__global__ void scale(float* y, const float* x, float a, int n) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) {
        y[i] = a * x[i];
    }
}
```

Design questions:

- Which output does each thread own?
- Is there write overlap between threads?
- Is synchronization between blocks necessary?
- Does the input size exceed the grid limit?
- Is a strided loop necessary?

Grid-stride loop:

```cpp
for (int i = blockIdx.x * blockDim.x + threadIdx.x;
     i < n;
     i += blockDim.x * gridDim.x) {
    y[i] = a * x[i];
}
```

This handles varying sizes and makes it easier to experiment with launch configurations.

## 5. Memory Hierarchy and Coalescing

Performance is often limited by bytes moved rather than the number of operations.

- Registers: thread-local and fast, but limited in number
- Shared memory: block-local; requires explicit management and synchronization
- L1/L2 cache: managed by hardware
- Global memory: large, but constrained by latency and bandwidth
- Constant memory: advantageous for certain broadcast patterns

Design the array layout so adjacent threads in a warp access adjacent addresses.

Example of a poor stride:

```cpp
float value = matrix[threadIdx.x * leading_dimension + column];
```

Consider whether the index can be rearranged so that threads read contiguous columns.

Do not guess whether accesses are coalesced; confirm it with memory-transaction and throughput metrics.

## 6. Arithmetic Intensity and Roofline Reasoning

Arithmetic intensity:

$$
I=\frac{\text{operations}}{\text{bytes transferred}}
$$

Low intensity suggests a memory-bound workload, while high intensity suggests a compute-bound workload.
A simple roofline upper bound is:

$$
P\le \min(P_{peak}, I\times B_{memory})
$$

This is a mental model for choosing an optimization direction, not an exact performance predictor.

- Memory-bound: data reuse, coalescing, and reduced transfers
- Compute-bound: instruction mix, math throughput, and suitability for tensor cores
- Latency-bound: analysis of parallelism and dependencies

## 7. When to Use Shared Memory

Shared memory is advantageous when global data is reused.

A typical tiled workflow:

1. Each thread reads part of a tile from global memory.
2. Store it in shared memory.
3. Use `__syncthreads()` to synchronize completion of the load.
4. Reuse the tile across several operations.
5. Move to the next tile.

Cautions:

- Every participating thread must reach the barrier.
- Bank conflicts can occur.
- More shared memory per block reduces the number of resident blocks.
- For data read only once, copying may cost more than it saves.

Compare global loads and kernel time before and after using shared memory.

## 8. Treat Occupancy as a Constraint, Not an Objective

Occupancy is the proportion of active warps on an SM relative to the theoretical maximum.
It matters for latency hiding, but 100% is not always optimal.

Factors that limit occupancy:

- Threads per block
- Register usage
- Shared-memory usage
- Architecture limits

Forcing register usage down can cause spilling and increase local-memory traffic.
Low occupancy can still be fast when instruction-level parallelism and cache reuse are good.

Start with block sizes that are multiples of 32 and measure several candidates.
Use the official occupancy API and a profiler, but make the final decision using end-to-end time.

## 9. Divergence, Atomics, and Reductions

When threads in a warp execute different branches, their paths may be serialized.
However, adding complex calculations to eliminate a short branch can be slower.

Atomics are useful for correctness, but contention can become a bottleneck.

Reduction hierarchy:

1. Thread-local partial result
2. Warp-level reduction
3. Block-level reduction
4. A global atomic only for block results, or a second kernel

Test every custom reduction with a variety of sizes and NaN policies.
Use a library primitive first when it is sufficient.

## 10. Asynchrony and Timing

A kernel launch can be asynchronous with respect to the host.
Measuring immediately with a general wall clock may capture only the launch time.

Use CUDA events.

```cpp
cudaEventRecord(start, stream);
kernel<<<grid, block, 0, stream>>>(...);
cudaEventRecord(stop, stream);
cudaEventSynchronize(stop);
cudaEventElapsedTime(&milliseconds, start, stop);
```

Performance-measurement principles:

- Perform a warm-up.
- Record clock variation and interference from other processes.
- Repeat several times and report the distribution.
- Add only the synchronization that is necessary.
- Distinguish timings that include and exclude transfers.
- State the costs of input generation and validation.

## 11. Profiling Workflow

### System-Level Timeline

Use Nsight Systems to inspect CPU activity, transfers, kernels, synchronization, and idle gaps.

Questions:

- Where is the GPU idle?
- Are there too many small kernel launches?
- Do transfers and compute overlap?
- Is there unnecessary synchronization?

### Kernel-Level Metrics

Use Nsight Compute for a detailed view of selected kernels.

- Achieved memory bandwidth
- Memory-transaction efficiency
- Warp stall reasons
- Occupancy and registers
- Branch efficiency
- Instruction throughput

Collecting every metric at once increases profiling overhead.
Select only the sections needed to test the hypothesis.

## 12. Practical Optimization Order

1. Find the hotspot with an end-to-end profile.
2. Freeze the CPU reference and kernel tests.
3. Remove unnecessary transfers and synchronization.
4. Improve memory-access patterns.
5. If reuse exists, consider shared memory or fusion.
6. Explore launch and block configurations.
7. Consider instruction and precision optimizations last.
8. Run correctness and performance regression tests after every change.

Kernel fusion can reduce intermediate global-memory traffic and launches.
However, measure register pressure, code complexity, and reduced reusability as well.

## 13. Evaluation Checklist

- [ ] Is there an independent CPU reference for small inputs?
- [ ] Is tolerance defined with a numerical rationale?
- [ ] Have memory errors been checked with Compute Sanitizer or an equivalent tool?
- [ ] Were end-to-end hotspots identified first?
- [ ] Are kernel time and time including transfers distinguished?
- [ ] Were warm-up and event synchronization applied?
- [ ] Was coalescing of global accesses confirmed with metrics?
- [ ] Is data actually reused in shared memory?
- [ ] Are occupancy and spilling inspected together?
- [ ] Were non-multiple sizes and boundaries tested?
- [ ] Were performance and correctness checked on several architectures?
- [ ] Are profiler evidence and commits linked before and after optimization?

## 14. Common Failures and Limitations

### Looking Only at GPU Utilization

High utilization does not show whether the work is useful computation or a memory stall.
Inspect application throughput and kernel metrics together.

### Assuming Shared Memory Is Always Faster

Copying without reuse adds only instructions and barriers.
Decide from profiles before and after the change.

### Forcing 100% Occupancy

Register spilling and degraded cache reuse can make it slower.
Occupancy is one cause of performance, not the objective function.

### Enabling Fast Math Without Validating Correctness

Approximate operations and contraction can change the result.
Evaluate business tolerances and stability across the entire pipeline.

The optimal CUDA configuration changes with the GPU architecture and toolkit.
Do not treat a hard-coded setting as a permanent rule; maintain a reproducible benchmark.

## 15. Official References

- [CUDA C++ Programming Guide](https://docs.nvidia.com/cuda/cuda-c-programming-guide/)
- [CUDA C++ Best Practices Guide](https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/)
- [Official Nsight Systems documentation](https://docs.nvidia.com/nsight-systems/)
- [Official Nsight Compute documentation](https://docs.nvidia.com/nsight-compute/)
- [Official Compute Sanitizer documentation](https://docs.nvidia.com/compute-sanitizer/)

## 16. Conclusion

CUDA performance is the result of memory behavior, execution, and application structure.
Maintaining the APOD cycle together with correctness tests prevents microbenchmark illusions and retains only improvements that reproduce on real workloads.
