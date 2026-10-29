"""Public results explorer: historical measurements, no inference endpoint calls."""
import json
import altair as alt
import pandas as pd
import streamlit as st
from lab_data import ROOT, EXPERIMENTS, load, summarize, output_cost

st.set_page_config(page_title='Inside an LLM Serving Lab', page_icon='⚡', layout='wide')
st.markdown('''<style>
.block-container {max-width:1200px;padding-top:2.4rem;}
h1 {letter-spacing:-.045em;} h2 {letter-spacing:-.025em;}
[data-testid="stMetric"] {background:#f1f5f9;padding:18px;border-radius:12px;}
[data-testid="stMetricLabel"] {color:#334155;}
</style>''', unsafe_allow_html=True)
st.caption('INFERENCE SERVING LAB  /  PROJECT 01')
st.title('What makes an LLM feel fast?')
st.markdown('I deployed **Qwen3-8B on one A40 GPU** and measured what happens when more people, '
            'longer documents, and longer answers compete for the same machine.')
st.caption('Runpod · Docker · vLLM 0.32.0 · BF16 · Measurements: October 28, 2026')

with st.sidebar:
    st.header('Explore the tradeoffs')
    st.write('Choose the response times you would accept for your product.')
    first = st.slider('First text within (seconds)', 0.25, 3.0, 1.0, 0.25)
    total = st.slider('Full response within (seconds)', 5, 30, 10)
    st.caption('These controls recalculate latency-qualified goodput from recorded requests. '
               'They do not run new GPU tests.')
    st.divider()
    st.write('AI infrastructure learning through product decisions.')
    st.caption('Historical results explorer. No live inference or API credentials required.')

story, experiments, costs, evidence = st.tabs(['The findings', 'Explore experiments', 'Cost tradeoffs', 'How it was measured'])

with story:
    st.subheader('More tokens per second doesn’t always mean happier users.')
    a,b,c = st.columns(3)
    a.metric('Short-prompt throughput gain', '7.8×', help='Aggregate output tokens/s: 253.1 at eight concurrent requests / 32.6 at one.')
    b.metric('Long-answer completion time', '15.65s', help='Median for forced 512-token outputs at concurrency two.')
    c.metric('Sampled KV-cache peak', '7.9%', help='Final eight-concurrent instrumented run; sampled about every two seconds.')
    st.write('With short prompts, batching let eight requests share the GPU with little individual slowdown. '
             'With longer inputs, throughput still grew, but users waited longer for the first text.')
    rows=[]
    for name in ['Longer inputs · 1, 8, 16 concurrent', 'Longer inputs · 2, 4 concurrent']:
        rows.extend(summarize(r, first, total) for r in load(name)['results'])
    frame=pd.DataFrame(rows).sort_values('Concurrent requests')
    left,right=st.columns(2)
    with left:
        st.markdown('**The system serves more text**')
        chart=alt.Chart(frame).mark_bar(color='#2563eb', cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
            x=alt.X('Concurrent requests:O', sort='ascending'), y=alt.Y('Total output tokens/s:Q'),
            tooltip=['Concurrent requests','Total output tokens/s','Requests'])
        st.altair_chart(chart, use_container_width=True)
    with right:
        st.markdown('**Each user waits longer**')
        chart=alt.Chart(frame).mark_line(point=True, color='#0f766e').encode(
            x=alt.X('Concurrent requests:O',sort='ascending'), y='Median first text (s):Q',
            tooltip=['Concurrent requests','Median first text (s)','Meeting targets (%)'])
        rule=alt.Chart(pd.DataFrame({'target':[first]})).mark_rule(strokeDash=[5,4],color='#d97706').encode(y='target:Q')
        st.altair_chart(chart+rule,use_container_width=True)
    st.caption('Same longer-input workload family (~1,400 tokens), output fixed at 128 tokens. '
               'Levels 1/8/16 used 20-second admission windows; 2/4 used 40 seconds. '
               'Sequential short runs, not a controlled production capacity curve. Dashed line: your first-text target.')
    st.markdown('''**Three product decisions this changed**

- Define both first-text and full-completion targets. Streaming can start quickly while an answer takes 15 seconds to finish.
- Describe the workload before choosing hardware: input length, output length and concurrency all matter.
- Use latency-qualified goodput alongside total throughput. Serving more tokens can coexist with fewer users meeting their targets.
''')
    st.info('A candidate starting point: two concurrent document-sized requests met the original targets in 20/20 trials. '
            'At four, 33/36 met them. These are exploratory observations, not a production guarantee.')

with experiments:
    name=st.selectbox('Experiment',list(EXPERIMENTS))
    report=load(name)
    table=pd.DataFrame([summarize(r,first,total) for r in report['results']])
    st.dataframe(table.round(3),hide_index=True,width='stretch')
    st.caption(f'Latency-qualified means first text ≤ {first:.2f}s and completion ≤ {total}s. '
               'Successful transport and the requested token count do not establish answer quality.')
    st.markdown('**Reading the metrics**')
    st.write('First text is the client-observed proxy for TTFT and includes network delay. Completion is the full stream duration. '
             'Total output tokens/s is aggregate across requests; completed requests/s counts full successful responses. '
             'Latency-qualified requests/s counts only responses meeting both selected targets.')
    if name=='Short prompt · burst batching':
        st.dataframe(pd.DataFrame([{'Concurrent requests':r['concurrency'],'Approximate TPOT (ms)':r['median_tpot_ms']} for r in report['results']]).round(2),hide_index=True)
        st.caption('TPOT uses first/last content chunk timestamps and token counts. Chunks can contain several tokens, so this is approximate.')
    st.download_button('Download recorded results (JSON)',json.dumps(report,indent=2),file_name=EXPERIMENTS[name],mime='application/json')

with costs:
    st.subheader('The economics depend on how busy the GPU stays.')
    st.write('Observed compute rate: **$0.59/hour** for this Pod on October 28, 2026. '
             'Allocated GPU time bills even when no requests arrive. The estimates below exclude storage and other costs.')
    cost_name=st.selectbox('Workload for cost estimate',list(EXPERIMENTS),index=2)
    cost_report=load(cost_name)
    choices=cost_report['results']
    selected=st.selectbox('Concurrent requests in measured run',range(len(choices)),format_func=lambda i:str(choices[i]['concurrency']))
    hourly=st.number_input('Compute price ($/hour)',min_value=0.01,value=0.59,step=0.01)
    busy=st.slider('Time spent serving this workload (%)',10,100,100,5)
    row=choices[selected]
    estimate=output_cost(hourly,row['output_tokens_per_s'],busy/100)
    x,y=st.columns(2)
    x.metric('Estimated compute / million output tokens',f'${estimate:.2f}')
    y.metric('Measured aggregate output rate',f"{row['output_tokens_per_s']:.1f} tokens/s")
    st.code('$/million output tokens = hourly compute price × 1,000,000\n                         ÷ (3,600 × measured output tokens/s × busy fraction)',language=None)
    st.warning('An extrapolation, not an invoice or API price comparison. It assumes the measured rate holds while busy. '
               'Input processing is reflected in the observed rate, but the denominator counts output tokens only. '
               'Storage, idle scheduling effects, startup, retries, quality acceptance and production variability are excluded.')
    st.write('Batching improves utilization on the same GPU. A larger GPU is vertical scaling. '
             'More independent replicas add capacity and redundancy, plus routing and duplicated model memory. '
             'Kubernetes can help orchestrate larger deployments; traffic growth alone does not require it.')

with evidence:
    st.subheader('A small deployed system, with evidence you can inspect.')
    st.markdown('**Architecture:** local browser → local Python proxy → authenticated Runpod HTTPS proxy → vLLM → Qwen3-8B. '
                'Benchmarks call the inference API directly; this public explorer reads saved results only.')
    metrics=json.loads((ROOT/'instrumented-metrics.json').read_text())
    st.markdown('**Final instrumented run:** 48/48 requests succeeded at concurrency eight.')
    st.dataframe(pd.DataFrame([{'Server phase':'Queue','Mean seconds':metrics['mean_server_phase_seconds']['queue']},
                              {'Server phase':'Input processing (prefill)','Mean seconds':metrics['mean_server_phase_seconds']['prefill']},
                              {'Server phase':'Generation (decode)','Mean seconds':metrics['mean_server_phase_seconds']['decode']}]).round(3),hide_index=True)
    st.write('Sampled waiting requests peaked at three; KV-cache usage peaked at 7.9%. '
             'The cache was not close to full in this run. That does not prove spare compute capacity. '
             'Reliable GPU utilization was unavailable, so GPU saturation is not established.')
    st.markdown('''**Methodology and limits**

- One A40, BF16 Qwen3-8B, pinned model revision, vLLM 0.32.0, 4,096-token context and 16 active sequences.
- Fixed-length experiments forced 128 or 512 output tokens by ignoring normal end-of-answer stopping. The original chat demo allows early completion.
- Short closed-loop tests refill each worker after completion. They do not simulate independent arrivals, long-duration load or unbounded queues.
- Server phase values are means from histogram deltas. They are not additive parts of the client median. Global metrics can include unrelated traffic; gauge sampling can miss peaks.
- Small samples, sequential ordering, caching and synthetic prompts limit generalization. Quality evaluation was separate and user-scored.
''')
    st.markdown('**Completed:** concurrency, input/output lengths, client TTFT, approximate TPOT, latency-qualified goodput, '
                'server queue/prefill/decode, sampled KV usage, and modeled compute cost per million output tokens.')
    st.markdown('**Future work:** quantization, deliberate KV-cache pressure, longer realistic load tests, and replica/failure testing. '
                'The existing AI Inference Advisor could use these workload dimensions; an integration has not been built.')
    for label,file in [('Instrumented report','instrumented-benchmark.md'),('Quality evaluation','quality-evaluation.md')]:
        with st.expander(label):
            st.markdown((ROOT/file).read_text())
    st.markdown('[vLLM metrics](https://docs.vllm.ai/en/latest/design/metrics/) · '
                '[Qwen3-8B](https://huggingface.co/Qwen/Qwen3-8B) · '
                '[Runpod pricing](https://docs.runpod.io/pods/pricing)')

st.divider()
st.caption('An inference serving lab · Evidence before infrastructure complexity · Version 1')
