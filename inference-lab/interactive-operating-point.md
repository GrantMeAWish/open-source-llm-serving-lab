# Interactive operating point — October 28, 2026

Follow-up on the same A40 / Qwen3-8B endpoint. Two sequential closed-loop tests at concurrency 2 and 4, with 40-second admission windows plus drain. Approximately 1,400 input tokens, fixed 128 output tokens, temperature 0, thinking disabled. No deployment settings changed.

| Concurrency | Successful | Median first text | p95 first text | Median total | Aggregate tokens/s | Meet both targets |
|---:|---:|---:|---:|---:|---:|---:|
| 2 | 20/20 | 0.52s | 0.69s | 4.37s | 58 | 20/20 |
| 4 | 36/36 | 0.75s | 1.04s | 4.82s | 106 | 33/36 |

Targets are provisional: first text within 1 second and total completion within 10 seconds. All 56 requests succeeded. All 20 requests at concurrency 2 met both targets; 33/36 (91.7%) at concurrency 4 did.

## Product implication

Concurrency 2 is a conservative candidate for this workload under a goal of at least 95% of requests receiving first text within 1 second. Concurrency 4 is a throughput-oriented candidate if approximately 92% meeting that target is acceptable, or a slightly looser target is chosen. Neither is a verified production limit. Do not interpret concurrency as number of registered users or requests per second.

Four concurrent requests delivered about 82% more total tokens/second than two. Latency-qualified request rate rose from 0.46 to 0.76 requests/second, even though the fraction meeting the target declined. This is the distinction between maximizing total throughput, qualified throughput, and percentage of users meeting an SLO.

No application concurrency cap has been applied: a queue could itself add first-text delay. Choose admission, queue, or overload behavior only after measuring arrival patterns and waiting time.

## Limits and next steps

One short run per level, small samples, client/network timings and no randomized ordering. p95 is a nearest-rank sample statistic, not a reliable production tail estimate. Unique synthetic prefixes limit but do not prove absence of caching. No GPU, KV-cache, or server-queue telemetry collected. Output length is forced for comparability; answer quality not measured.

Next experiment: repeat concurrency 2 and 4 for longer runs with server metrics, then compare 128 versus 512 output tokens and realistic context lengths. This helps separate prefill delay from generation load. Replica and GPU decisions should wait for confirmed workload and latency targets.

Reproduce: `python3 inference-lab/benchmark_sustained.py --concurrency 2 4 --seconds 40 --output sustained-2-4-results.json`. Raw results are saved beside this report. The previous sustained-results.json is preserved. Pod left running.
