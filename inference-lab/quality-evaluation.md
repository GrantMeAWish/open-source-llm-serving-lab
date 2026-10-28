# Manual quality evaluation — October 28, 2026

User-reported observations from Qwen3-8B on Runpod A40, served through the local
chat UI. Non-thinking mode, temperature 0.7, output cap 512 tokens. Responses were
not independently reviewed; scores reflect the user's assessment. Single-request
timings include client/network overhead and are not a concurrency benchmark.

| Test | User verdict | First text (s) | Total (s) | Output tokens | Observation |
|---|---|---:|---:|---:|---|
| Explain GPU memory | Pass | 0.27 | 2.72 | 85 | Concise and to the point |
| Batching vs replicas | Partial | 0.33 | 15.23 | 512 | Long response cut off midway; reached configured output cap |
| Exactly three bullets about TTFT | Pass | 0.33 | 2.90 | 89 | Short and followed bullet instructions |
| Article summary | Partial / unverified | 0.42 | 1.33 | 32 | User uncertain whether URL was read; app has no browsing or retrieval tool. Retest with pasted article text |
| Extract JSON | Pass | 0.34 | 1.21 | 31 | User judged output successful; strict JSON parsing not independently checked |
| Compute cost arithmetic | Pass | 0.35 | 3.09 | 95 | User judged calculation correct |
| Ambiguous GPU recommendation | Partial | 0.27 | 15.16 | 512 | Listed GPUs without clarifying needs; reached output cap |
| Unknown company revenue | Pass | 0.26 | 6.38 | 211 | Asked for company information; did not invent revenue |
| Recall $20 budget | Pass | 0.37 | 1.83 | 51 | Recalled budget in same conversation; UI resends chat history |
| Release note | Pass | 0.28 | 1.33 | 37 | Short sentence with header |

## Interpretation

- Seven passes, three partials by user assessment; small exploratory sample.
- First-text latency ranged from 0.26 to 0.42 seconds (median 0.33 seconds).
- Both incomplete responses reached exactly 512 tokens, matching the application's
  max_tokens setting. Finish reasons were not recorded for these user requests,
  so this is strong evidence of output-limit truncation rather than a proven
  runtime failure. The UI should display when generation hits its token limit.
- The app passes messages directly to vLLM and has no search, browser, URL-fetching,
  or tool-calling integration. A summary from a URL alone is not grounded in a
  fetched article; correctness cannot be established without the source text.
- Asking clarifying questions needs improvement for vague GPU recommendations.
- Budget recall demonstrates conversation history handling, not durable memory.

## Next controlled iteration

1. Show output-limit finish reasons in the UI so truncation is explicit.
2. Compare the two capped prompts with concise instructions and with a larger
   output budget, keeping other settings constant; record latency and completion.
3. Retest summarization using pasted source text and check factual fidelity.
4. Test an instruction to ask about workload, budget, context and concurrency
   before recommending a GPU. Compare against the current baseline.
5. Then benchmark concurrency with fixed prompts and output lengths.

No deployment settings or prompt behavior were changed when recording this evaluation.

## Round 2 — user-reported retests

All three used a 1,024-token response limit. The user also supplied an instruction
before the GPU recommendation prompt; its exact text and message role were not
captured. The app itself was not changed to inject a system instruction.

| Test | User verdict | First text (s) | Total (s) | Output tokens | Interpretation |
|---|---|---:|---:|---:|---|
| Summary with pasted article text | Pass | 0.29 | 2.94 | 92 | User judged summary successful with source text available; no browsing involved |
| Ambiguous GPU recommendation with prior instruction | Pass | 0.24 | 2.40 | 75 | User judged instructed response successful; exact answer not captured |
| Batching vs replicas | Pass | 0.31 | 30.19 | 1024 | Token-limit warning displayed correctly, but generation still hit the cap; answer completeness remains unresolved |

The first two answers were under 512 tokens, so a higher cap alone does not
explain their improvement. Source text and prior instruction are the relevant
changes, though this small uncontrolled comparison cannot isolate causality.
The batching output doubled from 512 to 1024 tokens and elapsed time rose from
15.23 to 30.19 seconds, while first-text time remained similar (0.33 vs 0.31 s).
This illustrates that quick first text can coexist with a long or truncated answer.

Next targeted retest: new chat, 512-token limit, ask "Compare continuous batching
and adding GPU replicas for LLM inference in at most 150 words. Explain when to use
each and one tradeoff for each." Check completeness, factual quality, warning
absence, and latency. Preserve these exploratory results separately from future
controlled concurrency benchmarks.

## Round 3 — concise batching comparison

User reports PASS for: "Compare continuous batching and adding GPU replicas for
LLM inference in at most 150 words. Explain when to use each and one tradeoff for
each." First text: 0.39 s; total: 4.88 s; output: 155 tokens. The suggested test
setting was 512 tokens; the user did not explicitly reconfirm the selected limit.
The output is below either available cap. Word count and factual correctness were
not independently inspected; pass is the user's assessment.

Compared with the 1,024-token capped response (30.19 s), this answer finished about
84% sooner and used about 85% fewer output tokens. This is a comparison of single
user-reported trials, not a controlled performance estimate. Clear scope and
length instructions produced a user-accepted result without needing more output
capacity. Manual quality exploration is ready to progress to controlled concurrency
testing with fixed prompts, output budgets, and repeated measurements.
