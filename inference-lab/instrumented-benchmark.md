# Instrumented test — October 28, 2026

One A40, Qwen3-8B, vLLM 0.32.0. Eight closed-loop workers, 30-second admission window plus drain, 1,403–1,404 input tokens, forced 128 output tokens. 48/48 requests succeeded. Median client first text: 1.26s; completion: 5.77s; aggregate output: 176.2 tokens/s. 17/48 met the provisional first-text <=1s and completion <=10s targets.

| Server measurement | Observation |
|---|---:|
| Mean queue time | 0.268s |
| Mean prefill time | 0.621s |
| Mean decode time | 4.638s |
| Maximum sampled running requests | 8 |
| Maximum sampled waiting requests | 3 |
| Maximum sampled KV-cache usage | 7.91% |

Means come from before/after histogram sum/count deltas. Gauges were sampled about every two seconds; transient peaks can be missed. No scrape errors. Global success-count delta: 48.0. Global metrics are not request-scoped: unrelated traffic could contaminate deltas. These are server means, not additive components of the reported client median.

Observed queueing and input processing contribute to startup delay; decode dominates full completion duration. The sampled KV cache was far from full, so this run does not support KV exhaustion as its explanation. Low KV usage does not prove spare compute capacity. GPU utilization was not available from /metrics. A Runpod runtime read during the run reported utilization 0; it is not treated as trustworthy GPU activity evidence. No GPU saturation claim is made.

This short run is diagnostic evidence, not production capacity or a tail-latency guarantee. No infrastructure settings changed. Further tests are optional after the first portfolio version.

Reproduce: `python3 inference-lab/benchmark_instrumented.py`. Raw server data: instrumented-metrics.json; client data: instrumented-load-results.json. Requires an already-running endpoint. The script does not stop the Pod.

Metric reference: [official vLLM metrics](https://docs.vllm.ai/en/latest/design/metrics/).
