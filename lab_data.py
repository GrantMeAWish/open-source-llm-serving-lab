"""Historical benchmark data transformations. No network or credentials required."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent / 'inference-lab'
EXPERIMENTS = {
    'Short prompt · burst batching': 'concurrency-results.json',
    'Longer inputs · 1, 8, 16 concurrent': 'sustained-results.json',
    'Longer inputs · 2, 4 concurrent': 'sustained-2-4-results.json',
    'Longer answers · 512 output tokens': 'sustained-512-results.json',
    'Short inputs · ~234 tokens': 'context-short-results.json',
    'Long inputs · ~3,000 tokens': 'context-long-results.json',
    'Instrumented run · 8 concurrent': 'instrumented-load-results.json',
}


def load(name):
    return json.loads((ROOT / EXPERIMENTS[name]).read_text())


def observations(row):
    return row.get('requests', [r for wave in row.get('waves', []) for r in wave['requests']])


def elapsed(row):
    return row.get('elapsed_s') or sum(w['elapsed_s'] for w in row['waves'])


def summarize(row, first_target=1.0, total_target=10.0):
    requests = observations(row)
    met = sum(r['ok'] and r['ttft_s'] <= first_target and r['total_s'] <= total_target for r in requests)
    return {
        'Concurrent requests': row['concurrency'],
        'Requests': row['attempted'],
        'Successful': row['successful'],
        'Median first text (s)': row['median_ttft_s'],
        'Median completion (s)': row['median_total_s'],
        'Total output tokens/s': row['output_tokens_per_s'],
        'Completed requests/s': row['successful'] / elapsed(row),
        'Meeting targets (%)': 100 * met / len(requests),
        'Latency-qualified requests/s': met / elapsed(row),
    }


def output_cost(hourly, output_tps, utilization=1.0):
    if hourly < 0 or output_tps <= 0 or not 0 < utilization <= 1:
        raise ValueError('Costs must be nonnegative; throughput and utilization must be positive.')
    return hourly * 1_000_000 / (3600 * output_tps * utilization)
