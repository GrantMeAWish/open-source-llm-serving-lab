"""Sample vLLM metrics during one bounded longer-input benchmark."""
import json
import pathlib
import subprocess
import sys
import time
import urllib.request
from chat_server import BASE, headers

ROOT = pathlib.Path(__file__).resolve().parent


def snapshot():
    with urllib.request.urlopen(urllib.request.Request(BASE+'/metrics', headers=headers()), timeout=10) as response:
        raw = response.read().decode()
    values = {}
    for line in raw.splitlines():
        if not line or line.startswith('#'):
            continue
        fields = line.split()
        name = fields[0].split('{', 1)[0]
        if name.startswith('vllm:') and not name.endswith('_created'):
            try:
                values[name] = values.get(name, 0) + float(fields[1])
            except ValueError:
                pass
    return {'timestamp': time.time(), 'values': values}


def main():
    before = snapshot()
    process = subprocess.Popen([sys.executable, str(ROOT/'benchmark_sustained.py'),
        '--concurrency', '8', '--seconds', '30', '--input-rows', '35',
        '--output', 'instrumented-load-results.json'])
    samples, errors = [], []
    while process.poll() is None:
        try:
            samples.append(snapshot())
        except Exception as error:
            errors.append(type(error).__name__)
        time.sleep(2)
    if process.returncode:
        raise SystemExit(process.returncode)
    after = snapshot()
    delta = {k: after['values'][k]-v for k, v in before['values'].items()
             if k in after['values'] and (k.endswith('_total') or k.endswith('_sum') or k.endswith('_count'))}
    phases = {}
    for phase in ['queue', 'prefill', 'decode', 'inference']:
        key = 'vllm:request_'+phase+'_time_seconds'
        count = delta.get(key+'_count', 0)
        phases[phase] = delta.get(key+'_sum', 0)/count if count else None
    gauges = {}
    for key in ['vllm:num_requests_running', 'vllm:num_requests_waiting', 'vllm:kv_cache_usage_perc']:
        observations = [s['values'][key] for s in samples if key in s['values']]
        gauges[key] = {'min': min(observations), 'max': max(observations)} if observations else None
    report = dict(before=before, after=after, samples=samples, scrape_errors=errors,
                  counter_deltas=delta, mean_server_phase_seconds=phases, sampled_gauges=gauges,
                  note='Global metric deltas; other concurrent traffic would contaminate attribution. Gauges sampled about every 2s; peaks can be missed.')
    (ROOT/'instrumented-metrics.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(phases=phases, gauges=gauges, scrape_errors=errors)), flush=True)


if __name__ == '__main__':
    main()
