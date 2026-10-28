"""Bounded closed-loop load: 20-second admission windows, then drain."""
import concurrent.futures
import argparse
import datetime
import json
import pathlib
import threading
import time

from benchmark_concurrency import request_one, percentile
from chat_server import BASE, MODEL

ROOT = pathlib.Path(__file__).resolve().parent


def prompt(level, worker, index, input_rows=35):
    # Unique prefix reduces reuse of a common cached document prefix.
    rows = [f'Case {input_rows}-{level}-{worker}-{index}. Review this fictional inference service log.']
    for n in range(input_rows):
        rows.append(f'Interval {n}: arrivals {2+(n+worker+index)%12}, input tokens {400+n*13}, '
                    f'output tokens {80+n%5*20}, first token delay {200+n*9} ms, '
                    f'GPU utilization {45+n%45} percent.')
    rows.append('Explain the likely serving bottlenecks and suggest two next experiments.')
    return '\n'.join(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--concurrency', type=int, nargs='+', default=[1, 8, 16])
    parser.add_argument('--seconds', type=int, default=20)
    parser.add_argument('--output', default='sustained-results.json')
    parser.add_argument('--max-tokens', type=int, choices=[128, 512], default=128)
    parser.add_argument('--input-rows', type=int, choices=[5, 35, 75], default=35)
    args = parser.parse_args()
    if any(c < 1 or c > 16 for c in args.concurrency) or not 1 <= args.seconds <= 60:
        parser.error('Use concurrency 1–16 and admission windows 1–60 seconds.')
    if pathlib.Path(args.output).name != args.output or not args.output.endswith('.json'):
        parser.error('Output must be a JSON filename within inference-lab.')
    report = dict(timestamp_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  endpoint=BASE, model=MODEL, admission_window_s=args.seconds,
                  concurrency=args.concurrency, output_tokens=args.max_tokens,
                  input_rows=args.input_rows,
                  targets=dict(ttft_s=1, total_s=10), results=[])
    for level in report['concurrency']:
        barrier = threading.Barrier(level+1)
        deadline = [0]
        def worker(worker_id):
            barrier.wait()
            observations = []
            while time.perf_counter() < deadline[0]:
                result = request_one(prompt=prompt(level, worker_id, len(observations), args.input_rows),
                                     max_tokens=args.max_tokens)
                result['worker'] = worker_id
                observations.append(result)
            return observations
        with concurrent.futures.ThreadPoolExecutor(max_workers=level) as pool:
            jobs = [pool.submit(worker, i) for i in range(level)]
            start = time.perf_counter()
            deadline[0] = start+args.seconds
            barrier.wait()
            requests = [r for job in jobs for r in job.result()]
            elapsed = time.perf_counter()-start
        good = [r for r in requests if r['ok']]
        meets = [r for r in good if r['ttft_s'] <= 1 and r['total_s'] <= 10]
        row = dict(concurrency=level, elapsed_s=elapsed, attempted=len(requests),
                   successful=len(good), meeting_latency_targets=len(meets),
                   median_ttft_s=percentile([r['ttft_s'] for r in good], .5),
                   p95_ttft_s=percentile([r['ttft_s'] for r in good], .95),
                   median_total_s=percentile([r['total_s'] for r in good], .5),
                   p95_total_s=percentile([r['total_s'] for r in good], .95),
                   output_tokens_per_s=sum(r['output_tokens'] for r in good)/elapsed,
                   good_requests_per_s=len(meets)/elapsed,
                   input_tokens_range=[min(r['usage']['prompt_tokens'] for r in good),
                                       max(r['usage']['prompt_tokens'] for r in good)] if good else None,
                   requests=requests)
        report['results'].append(row)
        (ROOT/args.output).write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps({k:v for k,v in row.items() if k != 'requests'}), flush=True)


if __name__ == '__main__':
    main()
