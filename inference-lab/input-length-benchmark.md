# Input-length experiment — October 28, 2026

Same Qwen3-8B/A40 endpoint, concurrency 2, forced output 128 tokens, temperature 0, thinking disabled. Short and long inputs each use a 30-second closed-loop admission window followed by drain. Prompt generator uses 5 versus 75 fictional service-log rows. API usage provides actual token counts. No deployment setting changed.

| Input tokens | Success | Median first text | Median completion | Aggregate output tokens/s | Meet targets |
|---:|---:|---:|---:|---:|---:|
| 232–236 | 16/16 | 0.26s | 3.97s | 63.9 | 16/16 |
| 2996–2998 | 14/14 | 0.93s | 5.00s | 51.2 | 7/14 |

Targets: first text within 1 second; completion within 10 seconds. All 30 requests succeeded. All short requests met both targets; 7/14 long requests did. All completed within 10 seconds.

## Interpretation

Longer inputs increased median first-text latency from 0.26 to 0.93 seconds and completion time from 3.97 to 5.00 seconds despite identical output lengths. This is consistent with more input-processing work and a larger attention context; server phase timings were not collected, so the delay cannot be attributed exclusively to prefill. Aggregate output rate declined about 20%.

PM implication: size capacity around input and output lengths, not requests per second alone. A chat workload with brief messages can meet latency targets on hardware where document-heavy requests miss them. Consider context budgets, retrieval that selects relevant passages, and workload-specific latency targets before changing hardware.

## Limits and next step

Single short run per condition, 16 versus 14 observations; no randomized order or independent repetitions. Synthetic prefixes differ by case and input size to reduce prefix sharing, but cache hits are not measured. Output is forced to a fixed length; quality not assessed. Network/proxy delays included; no server queue, prefill/decode, GPU or KV-cache telemetry. This is a learning experiment, not a production SLA.

Next: add read-only server telemetry to distinguish queue wait, prefill, decode and KV-cache behavior. Then confirm candidate workload/latency targets with repeated longer runs before scaling.

Reproduce: run benchmark_sustained.py with --concurrency 2 --seconds 30 --input-rows 5 or 75, with distinct --output filenames. Raw files: context-short-results.json and context-long-results.json. Pod left running.
