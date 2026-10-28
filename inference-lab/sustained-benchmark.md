# Longer-input sustained concurrency test — October 28, 2026

Model: Qwen3-8B on the existing A40 Pod YOUR_POD_ID. Direct authenticated API calls; no deployment settings changed. Inputs: 1,400–1,403 tokens of fictional service logs, with a unique case prefix per request. Output fixed at 128 tokens, temperature 0, thinking disabled, ignore_eos true. Same generation settings as the burst benchmark.

Closed-loop workers immediately send another request after completion. At each concurrency level, admit requests for 20 seconds and then drain outstanding work. Throughput denominator includes drain time. Levels run sequentially at 1, 8, 16. No separate warmup; the existing service was already loaded.

| Concurrency | Success | Median first text | Median total | Total output tokens/s | Meet both targets |
|---:|---:|---:|---:|---:|---:|
| 1 | 5/5 | 0.49s | 4.22s | 31 | 5/5 |
| 8 | 32/32 | 1.28s | 5.79s | 175 | 11/32 |
| 16 | 48/48 | 1.86s | 7.77s | 261 | 9/48 |

Targets: first text within 1 second and completion within 10 seconds. These are provisional product targets, not externally established requirements. All successful requests completed within 10 seconds; first-text delay drove target misses.

## Finding

85/85 requests succeeded. Aggregate throughput rises with concurrency, while responsiveness degrades. From 8 to 16, throughput increases about 49%, but median first-text delay increases about 45% and median completion time about 34%. Requests meeting both latency targets per second fall from 0.47 to 0.38. This illustrates why maximizing token throughput alone can hurt interactive experience.

This workload differs from the earlier short repeated prompt in input length and content variation, so cross-test changes cannot be attributed to input length alone. Input token counts were read from API usage. Prompts vary slightly per worker; order and cache state are not randomized.

## Limits and next steps

Short load windows and small samples, especially at concurrency 1, do not establish production capacity or reliable tail latency. Closed-loop load does not simulate independent user arrivals or reveal unbounded queue growth. Network/proxy overhead is included. The output is forced to a fixed length; answer quality is not assessed. Server queue time, KV-cache occupancy and GPU utilization were not sampled, so the underlying bottleneck is not proven.

Next: choose a product latency target; test concurrency 2 and 4 with this same workload to locate a candidate operating point. Then confirm with longer repeated runs, realistic output lengths and server metrics before changing GPU hardware or adding replicas.

Reproduce with `python3 inference-lab/benchmark_sustained.py`. Raw data: sustained-results.json. The script overwrites that file and leaves the Pod running.
