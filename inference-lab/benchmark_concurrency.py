"""Small fixed-length, closed-loop burst benchmark; no external dependencies."""
import concurrent.futures
import datetime
import json
import math
import pathlib
import statistics
import threading
import time
import urllib.request

from chat_server import BASE, MODEL, headers

ROOT = pathlib.Path(__file__).resolve().parent
PROMPT = 'Explain continuous batching for LLM inference, including its benefits and tradeoffs.'


def request_one(barrier=None, prompt=PROMPT, max_tokens=128):
    payload = dict(model=MODEL, messages=[dict(role='user', content=prompt)],
                   temperature=0, max_tokens=max_tokens, ignore_eos=True, stream=True,
                   stream_options=dict(include_usage=True),
                   chat_template_kwargs=dict(enable_thinking=False))
    req = urllib.request.Request(BASE + '/v1/chat/completions',
                                 data=json.dumps(payload).encode(), headers=headers())
    if barrier:
        barrier.wait(timeout=15)
    start = time.perf_counter()
    first = last = None
    usage, reason, done = None, None, False
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            for line in response:
                if not line.startswith(b'data:'):
                    continue
                data = line[5:].strip()
                if data == b'[DONE]':
                    done = True
                    break
                chunk = json.loads(data)
                usage = chunk.get('usage') or usage
                for choice in chunk.get('choices', []):
                    reason = choice.get('finish_reason') or reason
                    if choice.get('delta', {}).get('content'):
                        last = time.perf_counter()
                        first = first or last
        tokens = (usage or {}).get('completion_tokens', 0)
        ok = done and first is not None and tokens == max_tokens
        return dict(ok=ok, ttft_s=first-start if first else None,
                    total_s=time.perf_counter()-start, output_tokens=tokens,
                    tpot_s=(last-first)/(tokens-1) if first and tokens > 1 else None,
                    finish_reason=reason, usage=usage)
    except Exception as error:
        return dict(ok=False, error=type(error).__name__, total_s=time.perf_counter()-start)


def percentile(values, p):
    if p == .5:
        return statistics.median(values) if values else None
    return sorted(values)[max(0, math.ceil(len(values)*p)-1)] if values else None


def main():
    report = dict(timestamp_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  endpoint=BASE, model=MODEL, prompt=PROMPT,
                  config=dict(concurrency=[1, 2, 4, 8], rounds=2, max_tokens=128,
                              temperature=0, ignore_eos=True),
                  caveats=['Client-observed timings include network/proxy overhead.',
                           'Two synchronized bursts per level; not sustained traffic or a capacity limit.',
                           'Repeated prompt may benefit from server prefix caching.',
                           'TPOT is approximate: SSE chunks can contain multiple tokens.',
                           'Forced token length measures serving performance, not answer completeness.'],
                  warmup=request_one(), results=[])
    if not report['warmup']['ok']:
        raise SystemExit('Warmup failed: ' + str(report['warmup']))
    for concurrency in report['config']['concurrency']:
        waves = []
        for _ in range(2):
            barrier = threading.Barrier(concurrency)
            with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
                start = time.perf_counter()
                futures = [pool.submit(request_one, barrier) for _ in range(concurrency)]
                requests = [f.result() for f in futures]
                elapsed = time.perf_counter()-start
            waves.append(dict(elapsed_s=elapsed, requests=requests))
        good = [r for w in waves for r in w['requests'] if r['ok']]
        elapsed = sum(w['elapsed_s'] for w in waves)
        row = dict(concurrency=concurrency, successful=len(good), attempted=2*concurrency,
                   median_ttft_s=percentile([r['ttft_s'] for r in good], .5),
                   p95_ttft_s=percentile([r['ttft_s'] for r in good], .95),
                   median_total_s=percentile([r['total_s'] for r in good], .5),
                   median_tpot_ms=1000*percentile([r['tpot_s'] for r in good], .5) if good else None,
                   output_tokens_per_s=sum(r['output_tokens'] for r in good)/elapsed,
                   good_requests_per_s=sum(r['ttft_s'] <= 1 and r['total_s'] <= 10 for r in good)/elapsed,
                   waves=waves)
        report['results'].append(row)
        (ROOT/'concurrency-results.json').write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps({k:v for k,v in row.items() if k != 'waves'}), flush=True)


if __name__ == '__main__':
    main()
