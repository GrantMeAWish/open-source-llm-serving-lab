# Output-length experiment — October 28, 2026

Qwen3-8B on the existing A40 Pod; two concurrent closed-loop workers, 40-second admission windows plus drain, approximately 1,400 input tokens. Same synthetic prompt generator, temperature 0, thinking disabled, forced output length with ignore_eos. The 128-token baseline comes from the preceding run, not a simultaneous or randomized comparison. No server or UI settings changed.

| Output budget | Success | Median first text | Median completion | Aggregate output tokens/s | Completed requests/s | Meet both targets |
|---:|---:|---:|---:|---:|---:|---:|
| 128 | 20/20 | 0.52s | 4.37s | 58.2 | 0.455 | 20/20 |
| 512 | 6/6 | 0.34s | 15.65s | 65.5 | 0.128 | 0/6 |

Targets: first text within 1 second and full completion within 10 seconds. All six 512-token requests met the first-text target; none met completion target.

## Product finding

Four times the output tokens took about 3.6 times as long to complete. Completed-request throughput fell from approximately 0.46 to 0.13 requests/second, while aggregate token throughput stayed around 58–66 tokens/second. Token throughput alone hides a substantial fall in completed user tasks. First text remained quick in this run; the small non-randomized sample does not establish that longer output improves first-text speed.

This does not mean a smaller max_tokens setting alone makes every answer faster. These requests were forced to produce the full budget. Real answers may end early. Concise instructions can reduce actual output without truncating needed content; the UI should still flag length-limited responses.

## Limits and next experiment

Six long requests are insufficient for reliable tail estimates. Input lengths and serving settings were held comparable, but prompt instances, cache state and time differed. No answer quality or server/GPU/queue telemetry was measured. Do not infer production capacity, memory limits or a proven hardware bottleneck.

Next useful measurement: keep output length fixed and compare short versus long inputs at the same concurrency, then instrument server queue/prefill/decode and KV-cache metrics. This separates input processing costs from generation costs before considering replicas.

Reproduce the longer run: `python3 inference-lab/benchmark_sustained.py --concurrency 2 --seconds 40 --max-tokens 512 --output sustained-512-results.json`. Baseline raw data: sustained-2-4-results.json. Long-output raw data: sustained-512-results.json. Pod remains running; script does not manage billing or lifecycle.
