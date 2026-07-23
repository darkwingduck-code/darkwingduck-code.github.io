---
title: "CUDAの性能と正確性：APOD・メモリ階層・Profilingの実践原則"
date: 2026-07-21 12:29:00 +0900
categories: [GPU, Performance]
tags: [cuda, gpu-programming, profiling, memory-coalescing, numerical-correctness]
description: CUDA kernelを闇雲に最適化せず、正確なCPU基準、APOD cycle、memory traffic、occupancy、profilerの根拠によって改善する方法です。
lang: ja-JP
translation_key: cuda-performance-correctness
math: true
mermaid: true
hidden: true
---

{% include language-switcher.html %}

CUDA最適化はthread数を増やしたりshared memoryを導入したりするだけのテクニックではない。
application全体で価値のあるボトルネックを見つけ、正確性を維持しながらデータ移動と実行効率を改善する反復プロセスである。

## 1. 問題：速いkernelが速いapplicationを保証するわけではない

GPU codeは次のコストから構成される。

- host preprocessing
- host-to-device transfer
- kernel launch
- device computation
- device synchronization
- device-to-host transfer
- postprocessing

kernelだけが数十倍速くなっても、それが全体時間の一部にすぎなければ効果は限られる。
Amdahlの法則は次のとおりである。

$$
S=\frac{1}{(1-p)+p/s}
$$

- (p)：改善対象が占める割合
- (s)：その部分のspeedup

まずprofileで(p)を測定する。

## 2. Mental model：APOD cycle

```mermaid
flowchart LR
    A[Assess] --> B[Parallelize]
    B --> C[Optimize]
    C --> D[Deploy]
    D --> E[実際のworkloadを観測]
    E --> A
```

NVIDIAのAPODアプローチは次の反復を重視する。

- Assess：hotspotと目標を測定する。
- Parallelize：安全に並列化できる部分を選ぶ。
- Optimize：memory、execution、instructionを改善する。
- Deploy：実環境で回帰と移植性を検証する。

最適化ごとに正確性testとprofilerの根拠を残す。

## 3. CPU referenceと数値契約

GPU実装の前に、小さな入力向けのreferenceを用意する。

```cpp
for (int i = 0; i < n; ++i) {
    reference[i] = transform(input[i]);
}
```

検証項目：

- 絶対・相対tolerance
- NaNとInf
- zero-lengthとboundary size
- non-multiple block size
- 非常に大きい値や小さい値
- deterministic requirement
- reductionの順序の違い

浮動小数点加算は結合法則を厳密には満たさない。
parallel reductionはCPUの逐次加算とbitwiseで同一にならない場合がある。

誤差基準の例：

$$
|y_{gpu}-y_{ref}| \le a_{tol}+r_{tol}|y_{ref}|
$$

toleranceは恣意的に大きな値ではなく、dtype、condition number、累積演算数に基づいて定める。

## 4. Thread、block、grid mapping

1次元配列の基本mapping：

```cpp
__global__ void scale(float* y, const float* x, float a, int n) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) {
        y[i] = a * x[i];
    }
}
```

設計上の問い：

- 1つのthreadがどのoutputを所有するか？
- thread間にwrite overlapがあるか？
- block間のsynchronizationが必要か？
- input sizeがgridの上限を超えるか？
- stride loopが必要か？

grid-stride loop：

```cpp
for (int i = blockIdx.x * blockDim.x + threadIdx.x;
     i < n;
     i += blockDim.x * gridDim.x) {
    y[i] = a * x[i];
}
```

これはさまざまなサイズに対応し、launch configurationの実験を容易にする。

## 5. Memory階層とcoalescing

性能は演算回数よりbyte移動に制約されることが多い。

- register：thread-localで高速だが、数に制限がある。
- shared memory：block-localで、明示的な管理とsynchronizationが必要
- L1/L2 cache：hardwareが管理
- global memory：大容量だがlatencyとbandwidthに制約がある
- constant memory：特定のbroadcast patternに有利

warp内で隣接するthreadが隣接アドレスへアクセスするよう、配列layoutを設計する。

悪いstrideの例：

```cpp
float value = matrix[threadIdx.x * leading_dimension + column];
```

threadが連続したcolumnを読むようindexを組み替えられるか検討する。

coalescingされているかは推測せず、memory transactionとthroughput metricで確認する。

## 6. Arithmetic intensityとroofline思考

Arithmetic intensity：

$$
I=\frac{\text{operations}}{\text{bytes transferred}}
$$

低ければmemory-bound、高ければcompute-boundの可能性がある。
rooflineの単純な上限：

$$
P\le \min(P_{peak}, I\times B_{memory})
$$

これは正確な性能予測器ではなく、最適化の方向を定めるためのmental modelである。

- memory-bound：data reuse、coalescing、transferの削減
- compute-bound：instruction mix、math throughput、tensor coreへの適合性
- latency-bound：parallelismとdependencyの分析

## 7. Shared memoryを使うとき

shared memoryはglobal dataを再利用する場合に有利である。

典型的なtile workflow：

1. 各threadがglobal memoryからtileの一部を読む。
2. shared memoryに保存する。
3. `__syncthreads()`でloadの完了をそろえる。
4. tileを複数の演算で再利用する。
5. 次のtileへ移動する。

注意事項：

- すべてのparticipating threadがbarrierに到達しなければならない。
- bank conflictが発生する場合がある。
- block当たりのshared memoryが増えるとresident block数が減る。
- 一度しか読まないデータでは、コピーコストの方が大きい場合がある。

shared memoryの使用前後でglobal loadとkernel timeを比較する。

## 8. Occupancyを目標ではなく制約として捉える

occupancyは、SMにおける理論上の最大数に対するactive warpの比率である。
latency hidingには重要だが、100%が常に最適とは限らない。

occupancyの制限要因：

- block当たりのthread数
- register使用量
- shared memory使用量
- architecture limit

registerを無理に減らすとspillがlocal memory trafficを増やす場合がある。
occupancyが低くてもinstruction-level parallelismとcache reuseが良ければ高速になり得る。

block sizeは32の倍数を出発点として複数の候補を測定する。
公式occupancy APIとprofilerを使うが、最終的にはend-to-end timeで判断する。

## 9. Divergence、atomics、reductions

1つのwarp内のthreadが異なるbranchを実行すると、経路が直列化される場合がある。
ただし短いbranchをなくすために複雑な計算を追加すると、かえって遅くなる可能性がある。

atomicsはcorrectnessに有用だが、contentionがボトルネックになり得る。

reduction改善の階層：

1. thread-local partial result
2. warp-level reduction
3. block-level reduction
4. blockの結果だけをglobal atomicまたは2番目のkernelで処理

すべてのcustom reductionをさまざまなsizeとNaNポリシーでtestする。
library primitiveで十分なら、まずそれを使う。

## 10. Asynchronyとtiming

kernel launchはhostに対して非同期の場合がある。
通常のwall-clockですぐ測定するとlaunch時間だけが計測される可能性がある。

CUDA eventを使用する。

```cpp
cudaEventRecord(start, stream);
kernel<<<grid, block, 0, stream>>>(...);
cudaEventRecord(stop, stream);
cudaEventSynchronize(stop);
cudaEventElapsedTime(&milliseconds, start, stop);
```

性能測定の原則：

- warm-upを行う。
- clock変動と他のprocessの影響を記録する。
- 複数回繰り返して分布を示す。
- 必要なsynchronizationだけを入れる。
- transferを含む時間と含まない時間を区別する。
- input生成と検証のコストを明記する。

## 11. Profiling workflow

### System-level timeline

Nsight SystemsでCPU、transfer、kernel、synchronization、idle gapを確認する。

問い：

- GPUがidleになる区間はどこか？
- 小さなkernel launchが多すぎないか？
- transferとcomputeが重なっているか？
- 不要なsynchronizationがあるか？

### Kernel-level metrics

Nsight Computeで選択したkernelを詳しく調べる。

- achieved memory bandwidth
- memory transaction efficiency
- warp stall reason
- occupancyとregister
- branch efficiency
- instruction throughput

すべてのmetricを一度に収集するとprofiling overheadが大きくなる。
仮説に必要なsectionだけを選ぶ。

## 12. 実践的な最適化手順

1. end-to-end profileでhotspotを見つける。
2. CPU referenceとkernel testを固定する。
3. 不要なtransferとsynchronizationを取り除く。
4. memory access patternを改善する。
5. reuseがある場合はshared memoryまたはfusionを検討する。
6. launchとblock configurationを探索する。
7. instructionとprecisionの最適化は最後に検討する。
8. すべての変更後に正確性・性能の回帰試験を実行する。

kernel fusionはintermediate global memoryとlaunchを減らせる。
ただし、register pressure、code complexity、再利用性の低下も併せて測定する。

## 13. 評価checklist

- [ ] 小さな入力に対する独立したCPU referenceがあるか？
- [ ] toleranceが数値的根拠とともに定義されているか？
- [ ] compute sanitizerまたは同等のツールでmemoryエラーを検査したか？
- [ ] end-to-endのhotspotを先に確認したか？
- [ ] kernel timeとtransferを含む時間を区別したか？
- [ ] warm-upとevent synchronizationを適用したか？
- [ ] global accessがcoalescedかmetricで確認したか？
- [ ] shared memoryに実際のdata reuseがあるか？
- [ ] occupancyとspillを併せて確認しているか？
- [ ] non-multiple sizeとboundaryをtestしたか？
- [ ] 複数のarchitectureで性能と正確性を確認したか？
- [ ] 最適化前後のprofiler evidenceとcommitを関連付けたか？

## 14. よくある失敗と限界

### GPU utilizationだけを見る

高いutilizationだけでは、有用な演算なのかmemory stallなのかは分からない。
application throughputとkernel metricを併せて確認する。

### shared memoryは常に速いと信じる

reuseのないコピーはinstructionとbarrierを増やすだけである。
前後のprofileで判断する。

### occupancy 100%を強制する

register spillとcache reuseの悪化により、かえって遅くなる場合がある。
occupancyは性能要因の一つであり、目的関数ではない。

### fast mathを正確性の検証なしで有効にする

近似演算とcontractionが結果を変える可能性がある。
業務上の許容誤差とstabilityをpipeline全体で評価する。

CUDAの最適値はGPU architectureとtoolkitによって変わる。
ハードコードした設定を恒久的な規則とせず、再測定可能なbenchmarkを維持する。

## 15. 公式参考資料

- [CUDA C++ Programming Guide](https://docs.nvidia.com/cuda/cuda-c-programming-guide/)
- [CUDA C++ Best Practices Guide](https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/)
- [Nsight Systems公式文書](https://docs.nvidia.com/nsight-systems/)
- [Nsight Compute公式文書](https://docs.nvidia.com/nsight-compute/)
- [Compute Sanitizer公式文書](https://docs.nvidia.com/compute-sanitizer/)

## 16. まとめ

CUDA性能はmemory、execution、application構造が生み出す結果である。
APOD cycleと正確性testを共に維持すれば、microbenchmarkの錯覚を避け、実際のworkloadで再現される改善だけを残せる。
