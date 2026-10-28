# Concurrency benchmark — October 28, 2026

Qwen3-8B, vLLM 0.32.0, one A40, Pod `YOUR_POD_ID`. Two synchronized bursts per level, following one excluded warmup. Same prompt, temperature 0, thinking disabled, 128 output tokens forced with ignore_eos. Direct authenticated cloud API requests from the local computer; chat UI/proxy excluded.

| Concurrent requests | Success | Median first text (s) | Median total (s) | Approx. TPOT (ms) | Aggregate output tokens/s |
|---:|---:|---:|---:|---:|---:|
| 1 | 2/2 | 0.243 | 3.926 | 29.0 | 32.6 |
| 2 | 4/4 | 0.310 | 4.004 | 29.1 | 63.7 |
| 4 | 8/8 | 0.246 | 3.964 | 29.3 | 125.4 |
| 8 | 16/16 | 0.271 | 4.013 | 29.5 | 253.1 |

## Interpretation

Aggregate throughput increased approximately 7.8 times from one to eight concurrent requests, with similar per-request duration. This is consistent with effective batching on the existing GPU. Additional replicas are not justified by these measurements alone.

All requests met the exploratory latency targets: first text within 1 second and completion within 10 seconds. These targets define the recorded good_requests_per_s metric; they do not include answer-quality checks. Choose product-specific targets before a capacity decision.

## Limits and next experiment

This is a short burst experiment, not sustained load, a saturation test, or an SLA. The 1-request level has only two samples; p95 values in raw results are not robust tail estimates. Repeated prompt prefixes may benefit from caching. Network and cloud proxy overhead are included. Approximate TPOT uses the first and last content chunks and token count; chunks can contain several tokens. Fixed-length output intentionally reaches the token limit and is not a quality test. GPU utilization, KV-cache occupancy, queue time, and power were not sampled.

Next: repeat with varied realistic prompts and longer contexts, then sustain traffic at 8 and 16 concurrent requests while sampling server/GPU metrics. Compare against a chosen first-text and total-latency target before deciding on hardware or replicas.

## Reproduce

Run `python3 inference-lab/benchmark_concurrency.py` while this Pod is running. The script reads the local .env through chat_server; it does not print the key. It overwrites concurrency-results.json. Raw per-request measurements and settings are in that file. This does not stop the Pod or its ongoing billing.
