---
title: "CUDA 성능과 정확성: APOD·메모리 계층·Profiling의 실전 원칙"
date: 2026-07-21 12:29:00 +0900
categories: [GPU, Performance]
tags: [cuda, gpu-programming, profiling, memory-coalescing, numerical-correctness]
description: CUDA kernel을 무작정 최적화하지 않고 정확한 CPU 기준, APOD cycle, memory traffic, occupancy, profiler 증거로 개선하는 방법입니다.
lang: ko-KR
translation_key: cuda-performance-correctness
math: true
mermaid: true
---

{% include language-switcher.html %}

CUDA 최적화는 thread 수를 늘리거나 shared memory를 넣는 요령이 아니다.
전체 application에서 가치 있는 병목을 찾고, 정확성을 유지하면서 데이터 이동과 실행 효율을 개선하는 반복 과정이다.

## 1. 문제: 빠른 kernel이 빠른 application을 보장하지 않는다

GPU code는 다음 비용으로 구성된다.

- host preprocessing
- host-to-device transfer
- kernel launch
- device computation
- device synchronization
- device-to-host transfer
- postprocessing

kernel만 수십 배 빨라져도 전체 시간의 작은 부분이면 효과가 제한된다.
Amdahl의 법칙은 다음과 같다.

$$
S=\frac{1}{(1-p)+p/s}
$$

- (p): 개선 대상이 차지하는 비율
- (s): 그 부분의 speedup

먼저 profile로 (p)를 측정한다.

## 2. Mental model: APOD cycle

```mermaid
flowchart LR
    A[Assess] --> B[Parallelize]
    B --> C[Optimize]
    C --> D[Deploy]
    D --> E[실제 workload 관측]
    E --> A
```

NVIDIA의 APOD 접근은 다음 반복을 강조한다.

- Assess: hotspot과 목표를 측정한다.
- Parallelize: 안전하게 병렬화할 부분을 고른다.
- Optimize: memory, execution, instruction을 개선한다.
- Deploy: 실제 환경에서 회귀와 이식성을 검증한다.

최적화마다 정확성 test와 profiler 증거를 남긴다.

## 3. CPU reference와 수치 계약

GPU 구현 전에 작은 입력용 reference를 둔다.

```cpp
for (int i = 0; i < n; ++i) {
    reference[i] = transform(input[i]);
}
```

검증 항목:

- 절대·상대 tolerance
- NaN과 Inf
- zero-length와 boundary size
- non-multiple block size
- 매우 크거나 작은 값
- deterministic requirement
- reduction 순서 차이

부동소수점 덧셈은 결합법칙을 정확히 만족하지 않는다.
parallel reduction은 CPU 순차 합과 bitwise 동일하지 않을 수 있다.

오차 기준 예:

$$
|y_{gpu}-y_{ref}| \le a_{tol}+r_{tol}|y_{ref}|
$$

tolerance는 임의의 큰 값이 아니라 dtype, condition number, 누적 연산 수에 근거한다.

## 4. Thread, block, grid mapping

1차 배열의 기본 mapping:

```cpp
__global__ void scale(float* y, const float* x, float a, int n) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) {
        y[i] = a * x[i];
    }
}
```

설계 질문:

- 한 thread가 어떤 output을 소유하는가?
- thread 간 write overlap이 있는가?
- block 사이 synchronization이 필요한가?
- input size가 grid 한계를 넘는가?
- stride loop가 필요한가?

grid-stride loop:

```cpp
for (int i = blockIdx.x * blockDim.x + threadIdx.x;
     i < n;
     i += blockDim.x * gridDim.x) {
    y[i] = a * x[i];
}
```

이는 다양한 크기에 대응하고 launch configuration 실험을 쉽게 한다.

## 5. Memory 계층과 coalescing

성능은 연산 수보다 byte 이동에 제한되는 경우가 많다.

- register: thread-local, 빠르지만 수가 제한된다.
- shared memory: block-local, 명시적 관리와 synchronization 필요
- L1/L2 cache: hardware 관리
- global memory: 크지만 latency와 bandwidth 제약
- constant memory: 특정 broadcast pattern에 유리

warp의 인접 thread가 인접 주소에 접근하도록 배열 layout을 설계한다.

나쁜 stride 예:

```cpp
float value = matrix[threadIdx.x * leading_dimension + column];
```

thread가 연속 column을 읽도록 index를 재배치할 수 있는지 검토한다.

coalescing 여부는 추측하지 말고 memory transaction과 throughput metric으로 확인한다.

## 6. Arithmetic intensity와 roofline 사고

Arithmetic intensity:

$$
I=\frac{\text{operations}}{\text{bytes transferred}}
$$

낮으면 memory-bound, 높으면 compute-bound일 가능성이 있다.
roofline의 단순 상한:

$$
P\le \min(P_{peak}, I\times B_{memory})
$$

이는 정확한 성능 예측기가 아니라 최적화 방향을 잡는 mental model이다.

- memory-bound: data reuse, coalescing, transfer 감소
- compute-bound: instruction mix, math throughput, tensor core 적합성
- latency-bound: parallelism과 dependency 분석

## 7. Shared memory를 사용할 때

shared memory는 global data를 재사용할 때 유리하다.

전형적 tile workflow:

1. 각 thread가 global memory에서 tile 일부를 읽는다.
2. shared memory에 저장한다.
3. `__syncthreads()`로 load 완료를 맞춘다.
4. tile을 여러 연산에서 재사용한다.
5. 다음 tile로 이동한다.

주의:

- 모든 participating thread가 barrier에 도달해야 한다.
- bank conflict가 생길 수 있다.
- block당 shared memory가 커지면 resident block 수가 줄어든다.
- 한 번만 읽는 데이터는 복사 비용이 더 클 수 있다.

shared memory 사용 전후 global load와 kernel time을 비교한다.

## 8. Occupancy를 목표가 아니라 제약으로 본다

occupancy는 SM에서 활성 warp의 이론적 최대 대비 비율이다.
latency hiding에 중요하지만 100%가 항상 최적은 아니다.

occupancy 제한 요인:

- block당 thread 수
- register 사용량
- shared memory 사용량
- architecture limit

register를 억지로 줄이면 spill이 local memory traffic을 늘릴 수 있다.
낮은 occupancy라도 instruction-level parallelism과 cache reuse가 좋으면 빠를 수 있다.

block size는 32의 배수를 출발점으로 여러 후보를 측정한다.
공식 occupancy API와 profiler를 사용하되 end-to-end time으로 최종 판단한다.

## 9. Divergence, atomics, reductions

한 warp 안 thread가 다른 branch를 실행하면 경로가 직렬화될 수 있다.
하지만 짧은 branch를 없애려고 복잡한 계산을 추가하면 더 느릴 수 있다.

atomics는 correctness에 유용하지만 contention이 병목이 될 수 있다.

reduction 개선 계층:

1. thread-local partial result
2. warp-level reduction
3. block-level reduction
4. block 결과만 global atomic 또는 두 번째 kernel

모든 custom reduction은 다양한 size와 NaN 정책을 test한다.
library primitive가 충분하면 먼저 사용한다.

## 10. Asynchrony와 timing

kernel launch는 host에 대해 비동기일 수 있다.
일반 wall-clock으로 바로 측정하면 launch 시간만 볼 수 있다.

CUDA event를 사용한다.

```cpp
cudaEventRecord(start, stream);
kernel<<<grid, block, 0, stream>>>(...);
cudaEventRecord(stop, stream);
cudaEventSynchronize(stop);
cudaEventElapsedTime(&milliseconds, start, stop);
```

성능 측정 원칙:

- warm-up을 수행한다.
- clock 변동과 다른 process 영향을 기록한다.
- 여러 번 반복하고 분포를 제시한다.
- 필요한 synchronization만 넣는다.
- transfer 포함·제외 시간을 구분한다.
- input 생성과 검증 비용을 명시한다.

## 11. Profiling workflow

### System-level timeline

Nsight Systems로 CPU, transfer, kernel, synchronization, idle gap을 본다.

질문:

- GPU가 idle인 구간은 어디인가?
- 작은 kernel launch가 지나치게 많은가?
- transfer와 compute가 겹치는가?
- 불필요한 synchronization이 있는가?

### Kernel-level metrics

Nsight Compute로 선택한 kernel을 깊게 본다.

- achieved memory bandwidth
- memory transaction efficiency
- warp stall reason
- occupancy와 register
- branch efficiency
- instruction throughput

모든 metric을 한 번에 수집하면 profiling overhead가 커진다.
가설에 필요한 section만 선택한다.

## 12. 실전 최적화 순서

1. end-to-end profile로 hotspot을 찾는다.
2. CPU reference와 kernel test를 고정한다.
3. 불필요한 transfer와 synchronization을 제거한다.
4. memory access pattern을 개선한다.
5. reuse가 있으면 shared memory 또는 fusion을 검토한다.
6. launch와 block configuration을 탐색한다.
7. instruction과 precision 최적화를 마지막에 검토한다.
8. 모든 변경 후 정확성·성능 회귀를 실행한다.

kernel fusion은 intermediate global memory와 launch를 줄일 수 있다.
하지만 register pressure, code complexity, 재사용성 저하를 함께 측정한다.

## 13. 평가 checklist

- [ ] 작은 입력의 독립 CPU reference가 있는가?
- [ ] tolerance가 수치 근거와 함께 정의됐는가?
- [ ] compute sanitizer 또는 동등 도구로 memory 오류를 검사했는가?
- [ ] end-to-end hotspot을 먼저 확인했는가?
- [ ] kernel time과 transfer 포함 시간을 구분했는가?
- [ ] warm-up과 event synchronization을 적용했는가?
- [ ] global access가 coalesced인지 metric으로 확인했는가?
- [ ] shared memory에 실제 data reuse가 있는가?
- [ ] occupancy와 spill을 함께 보는가?
- [ ] non-multiple size와 boundary를 test했는가?
- [ ] 여러 architecture에서 성능과 정확성을 확인했는가?
- [ ] 최적화 전후 profiler evidence와 commit을 연결했는가?

## 14. 흔한 실패와 한계

### GPU utilization만 본다

높은 utilization은 유용한 연산인지, memory stall인지 설명하지 않는다.
application throughput과 kernel metric을 함께 본다.

### shared memory는 항상 빠르다고 믿는다

reuse 없는 복사는 instruction과 barrier만 추가한다.
전후 profile로 판단한다.

### occupancy 100%를 강제한다

register spill과 cache reuse 악화로 더 느려질 수 있다.
occupancy는 성능 원인의 하나이지 목표 함수가 아니다.

### fast math를 정확성 검증 없이 켠다

근사 연산과 contraction이 결과를 바꿀 수 있다.
업무 허용 오차와 stability를 전체 pipeline에서 평가한다.

CUDA 최적값은 GPU architecture와 toolkit에 따라 달라진다.
하드코딩한 설정을 영구 규칙으로 보지 말고 재측정 가능한 benchmark를 유지한다.

## 15. 공식 참고자료

- [CUDA C++ Programming Guide](https://docs.nvidia.com/cuda/cuda-c-programming-guide/)
- [CUDA C++ Best Practices Guide](https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/)
- [Nsight Systems 공식 문서](https://docs.nvidia.com/nsight-systems/)
- [Nsight Compute 공식 문서](https://docs.nvidia.com/nsight-compute/)
- [Compute Sanitizer 공식 문서](https://docs.nvidia.com/compute-sanitizer/)

## 16. 마무리

CUDA 성능은 memory, execution, application 구조가 만든 결과다.
APOD cycle과 정확성 test를 함께 유지하면 microbenchmark의 착시를 피하고 실제 workload에서 재현되는 개선만 남길 수 있다.
