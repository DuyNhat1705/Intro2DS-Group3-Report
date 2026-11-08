"""Section 4 notebook figures and tables; no images are saved.

Charts return Matplotlib Figures; hardware_41 and summary_table_44 return
DataFrames. Optional data_dir overrides the repository statistics_data folder.
"""
import json
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
try:
    from . import _milestone1_data as data
except ImportError:
    import _milestone1_data as data

STAGES = ['time_metadata_sec', 'time_source_sec', 'time_refs_sec']
STAGE_NAMES = ['Metadata', 'Source', 'References']


def hardware_41(data_dir=None):
    """One row per session: preserve hardware and configuration changes."""
    starts = data.records('runs.jsonl', data_dir)
    starts = starts.loc[starts.event.eq('start')]
    if starts.duplicated(['worker', 'run_id']).any():
        raise ValueError('Duplicate run-start records')
    rows = []
    for record in starts.to_dict('records'):
        machine, config = record.get('machine', {}), record.get('config', {})
        row = {'worker': record['worker'], 'run_id': record['run_id'],
               'start_UTC': pd.to_datetime(record['t'], unit='s', utc=True),
               'CPU': machine.get('cpu_model'), 'logical_CPUs': machine.get('cpu_count'),
               'RAM_GiB': machine.get('ram_total_bytes', np.nan)/data.GIB,
               'disk_capacity_GiB': machine.get('disk_total_bytes', np.nan)/data.GIB,
               'disk_free_at_start_GiB': machine.get('disk_free_bytes', np.nan)/data.GIB,
               'Colab': machine.get('colab'), 'platform': machine.get('platform'),
               'Python': machine.get('python'), 'packages': machine.get('packages')}
        row.update({key: value for key, value in config.items()})
        rows.append(row)
    return pd.DataFrame(rows).sort_values(['worker', 'start_UTC']).reset_index(drop=True)


PIPELINE_SETTINGS = [
    ('ARXIV_DELAY', 'arXiv base delay between request starts', 'seconds'),
    ('ARXIV_MAX_DELAY', 'arXiv maximum delay after 429 / 5xx', 'seconds'),
    ('METADATA_BATCH_SIZE', 'Metadata batch size', 'IDs per request'),
    ('S2_BATCH_SIZE', 'Semantic Scholar batch size', 'IDs per request'),
    ('S2_DELAY_WITH_KEY', 'Semantic Scholar delay with API key', 'seconds'),
    ('PARALLEL', 'arXiv and Semantic Scholar run in parallel', ''),
    ('KEEP_ARCHIVE', 'Keep source archives on disk', ''),
    ('MAX_RUN_HOURS', 'Time limit per session', 'hours'),
]


def pipeline_config_41(data_dir=None):
    """Settings logged at session start; more than one value means the setting changed."""
    hardware = hardware_41(data_dir)
    rows = []
    for key, setting, unit in PIPELINE_SETTINGS:
        values = hardware[key].dropna().astype(str).unique()
        rows.append({'Setting': setting, 'Value': ', '.join(sorted(values)), 'Unit': unit})
    return pd.DataFrame(rows)


def _has_samples(path):
    return path.exists() and path.stat().st_size > 0 and not pd.read_csv(path, nrows=1).empty


def measurement_coverage_41(data_dir=None):
    """Sessions with usable data per measurement; missing values are not estimated."""
    runs = data.runs(data_dir)
    logs = data.root(data_dir)/'run_logs'

    def sampled(prefix):
        return sum(_has_samples(logs/run.worker/f'{prefix}_{run.run_id}.csv') for run in runs.itertuples())

    timings = data.records('timings.jsonl', data_dir)
    counts = {
        'Session duration': runs.wall_sec.gt(0).sum(),
        'Stage timings': timings.groupby(['worker', 'run_id']).ngroups,
        'RSS samples': sampled('monitor'),
        'data/ size scans': sampled('disk'),
        'Kernel peak RSS': runs.peak_rss_kernel_bytes.notna().sum(),
    }
    return pd.DataFrame({'Measurement': list(counts),
                         f'Sessions with data (of {len(runs)})': [int(count) for count in counts.values()]})


def session_timeline_41(data_dir=None):
    runs = data.runs(data_dir)
    fig, ax = data.figure('Recorded worker sessions (UTC; gaps are downtime)', figsize=(13, 5))
    for i, worker in enumerate(data.WORKERS):
        for run in runs.loc[runs.worker.eq(worker)].itertuples():
            if pd.isna(run.start) or pd.isna(run.end) or run.end < run.start:
                continue
            start = mdates.date2num(pd.to_datetime(run.start, unit='s', utc=True))
            ax.broken_barh([(start, (run.end-run.start)/86400)], (i-.3, .6))
    ax.set_yticks(range(len(data.WORKERS)), data.WORKERS)
    ax.xaxis_date()
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d\n%H:%M'))
    ax.set_xlabel('UTC date / time')
    return fig


def attribute_stage_time_by_range_42(data_dir=None):
    times = data.papers(data_dir).groupby('worker')[STAGES].sum(min_count=1)/3600
    times.columns = STAGE_NAMES
    fig, ax = data.figure('Paper-attributed stage work by range', 'Attributed hours (not wall time)')
    times.plot.bar(ax=ax, rot=0)
    return fig


def stage_duration_per_paper_42(data_dir=None):
    papers = data.papers(data_dir)
    fig, ax = data.figure('Per-paper attributed stage-duration ECDF', 'Fraction of measured papers')
    for column, name in zip(STAGES, STAGE_NAMES):
        values = papers[column].dropna().sort_values()
        values = values.loc[values.ge(0)]
        if len(values):
            ax.step(values, np.arange(1, len(values)+1)/len(values), where='post',
                    label=f'{name}: n={len(values):,}, p50={values.median():.3g}s, p95={values.quantile(.95):.3g}s')
    ax.set_xscale('symlog', linthresh=.1)
    ax.set_xlabel('Attributed seconds (symlog scale includes zero)')
    ax.legend()
    return fig


def _resource_plot(name, time_column, value_columns, divisor, title, ylabel, data_dir):
    frame = data.exports(name, data_dir)
    fig, axes = plt.subplots(len(data.WORKERS), 1, figsize=(13, 12), sharex=True, layout='constrained')
    for ax, worker in zip(axes, data.WORKERS):
        selected = frame.loc[frame.worker.eq(worker)]
        # Separate line per session: never bridge a restart/downtime interval.
        for i, (_, session) in enumerate(selected.groupby('run_id', sort=False)):
            session = session.sort_values(time_column)
            timestamps = pd.to_datetime(session[time_column], unit='s', utc=True)
            for column, label in value_columns:
                ax.plot(timestamps, session[column]/divisor, label=label if i == 0 else None, marker='.', markersize=2)
        ax.set_ylabel(f'{worker}\n{ylabel}')
        ax.legend(loc='upper left')
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter('%m-%d\n%H:%M'))
    axes[-1].set_xlabel('UTC date / time')
    fig.suptitle(title)
    return fig


def memory_over_execution_43(data_dir=None):
    return _resource_plot('monitor.csv', 'minute', [('rss_mean_bytes', 'Minute mean RSS'),
                          ('rss_max_bytes', 'Minute sampled peak RSS')], data.MIB,
                          'Sampled process RSS by worker and session', 'MiB', data_dir)


def directory_size_over_time_43(data_dir=None):
    return _resource_plot('disk.csv', 't', [('data_dir_bytes', 'Sampled data/ size')], data.GIB,
                          'Periodic data/ directory scans (brief peaks can be missed)', 'GiB', data_dir)


def temporary_storage_overhead_43(data_dir=None, final_sizes_bytes=None):
    """Compare sampled peaks with last samples or caller-verified same-scope finals.

    final_sizes_bytes, if supplied, must map each worker to a verified final
    data/ content-byte size. The last scan is explicitly not a verified final.
    """
    disk = data.exports('disk.csv', data_dir).dropna(subset=['t', 'data_dir_bytes'])
    peak = disk.groupby('worker').data_dir_bytes.max().reindex(data.WORKERS)
    if final_sizes_bytes is None:
        final = disk.sort_values('t').groupby('worker').tail(1).set_index('worker').data_dir_bytes.reindex(data.WORKERS)
        label = 'Last sampled size (not verified final)'
    else:
        final = pd.Series(final_sizes_bytes).reindex(data.WORKERS)
        if final.isna().any() or final.lt(0).any():
            raise ValueError('Provide nonnegative verified final bytes for every worker')
        label = 'Verified final data/ content bytes'
    fig, ax = data.figure('Directory storage comparison; sampled peaks may miss transients', 'GiB')
    pd.DataFrame({'Sampled peak': peak, label: final}).div(data.GIB).plot.bar(ax=ax, rot=0)
    return fig


def _memory_summary(data_dir=None):
    weighted, seconds, peak, gaps = 0., 0., np.nan, 0
    for run, samples in data.raw_memory(data_dir):
        if len(samples):
            peak = np.nanmax([peak, samples.rss_bytes.max()])
        if len(samples) < 2:
            continue
        dt = np.diff(samples.t.to_numpy())
        rss = samples.rss_bytes.to_numpy()
        # Trapezoidal integration within sessions only. Do not extrapolate
        # endpoint values or interpolate across unusually long sampling gaps.
        limit = max(5*float(np.median(dt)), 5.)
        valid = (dt > 0) & (dt <= limit)
        gaps += int((~valid).sum())
        weighted += np.sum((rss[:-1][valid]+rss[1:][valid])/2*dt[valid])
        seconds += dt[valid].sum()
    return weighted/seconds if seconds else np.nan, peak, seconds, gaps


def summary_table_44(data_dir=None):
    """Metrics with explicit populations, units, and provenance; no mixed-unit axis."""
    papers, runs = data.papers(data_dir), data.runs(data_dir)
    monitor, disk = data.exports('monitor.csv', data_dir), data.exports('disk.csv', data_dir)
    events = data.records('events.jsonl', data_dir)
    rows = []
    def add(metric, value, unit, scope, source):
        rows.append({'Metric': metric, 'Value': value, 'Unit': unit, 'Population/scope': scope, 'Source': source})
    active, calendar = data.elapsed(runs)
    success = int(papers.paper_success.sum())
    for metric, value in [('Target IDs', len(papers)), ('Metadata found', int(papers.metadata.eq('done').sum())), ('Successful papers', success)]:
        add(metric, value, 'papers', 'All target IDs', 'per_paper.csv')
    add('Overall paper success', 100*success/len(papers), '%', 'Successful / target IDs', 'per_paper.csv')
    for outcome, count in papers.refs.fillna('missing').value_counts().items():
        add(f'Reference outcome: {outcome}', int(count), 'papers', 'All requested papers', 'per_paper.csv')
    add('Reference retrieval success', 100*papers.refs.eq('ok').mean(), '%', 'ok / all requested papers', 'per_paper.csv')
    add('Workers', runs.worker.nunique(), 'workers', 'Recorded sessions', 'runs.csv')
    add('Sessions', len(runs), 'sessions', 'Unique (worker, run_id)', 'runs.csv')
    add('Active collection elapsed', active/3600, 'hours', 'Union of session intervals; downtime excluded', 'runs.csv')
    add('Calendar elapsed', calendar/3600, 'hours', 'First start to latest end; includes gaps', 'runs.csv')
    valid_wall = runs.wall_sec.where(runs.wall_sec.ge(0))
    worker_hours = valid_wall.sum(min_count=1)/3600
    add('Worker time', worker_hours, 'worker-hours', f'{valid_wall.gt(0).sum()} valid session durations; includes same-worker overlaps reported below', 'runs.csv')
    add('Collection throughput', success/(active/3600), 'papers/hour', 'Final successes / active collection elapsed', 'per_paper.csv + runs.csv')
    add('Worker efficiency', success/worker_hours, 'papers/worker-hour', 'Final successes / worker-hours', 'per_paper.csv + runs.csv')
    for worker, group in runs.groupby('worker'):
        worker_union, _ = data.elapsed(group)
        interval_sum = (group.end-group.start).where(group.end.ge(group.start)).sum(min_count=1)
        add('Same-worker interval overlap', interval_sum-worker_union, 'seconds', worker, 'runs.csv')
    for column, label in zip(STAGES, STAGE_NAMES):
        add(f'{label} attributed work', papers[column].sum(min_count=1), 'seconds', f'{papers[column].notna().sum()} measured paper rows', 'per_paper.csv')
    attempts = data.records('timings.jsonl', data_dir)
    for stage, group in attempts.groupby('stage'):
        add(f'{stage} attempted work', group.duration.sum(min_count=1), 'seconds', 'All logged attempts; duration once per row, including amortized batches', 'timings.jsonl')
    values = papers.time_total_sec.dropna()
    for name, value in [('Mean', values.mean()), ('Median', values.median()), ('p95', values.quantile(.95))]:
        add(f'{name} attributed paper time', value, 'seconds', f'{len(values)} measured paper rows; not end-to-end latency', 'per_paper.csv')
    mean, raw_peak, covered, gaps = _memory_summary(data_dir)
    add('Time-weighted sampled RSS', mean/data.MIB, 'MiB', f'Session-time-weighted (overlapping sessions counted separately); {covered:.1f}s covered; {gaps} long/invalid intervals excluded', 'raw monitor_<run_id>.csv')
    add('Raw sampled peak RSS', raw_peak/data.MIB, 'MiB', 'Maximum individual process sample; not fleet sum', 'raw monitor_<run_id>.csv')
    add('Exported sampled peak RSS', monitor.rss_max_bytes.max()/data.MIB, 'MiB', 'Maximum minute sampled peak; not fleet sum', 'monitor.csv')
    add('Kernel-labelled peak RSS', runs.peak_rss_kernel_bytes.max()/data.MIB, 'MiB', 'Maximum recorded session kernel-labelled peak', 'runs.csv')
    for worker in data.WORKERS:
        add('Sampled peak directory size', disk.loc[disk.worker.eq(worker), 'data_dir_bytes'].max()/data.GIB,
            'GiB', f'{worker} data/ scans; not guaranteed true peak', 'disk.csv')
    for worker, summary in data.summaries(data_dir).items():
        for key, label in [('output_size_bytes', 'Final output size'), ('tables_size_bytes', 'Exported tables size')]:
            add(label, summary.get('performance', {}).get(key, np.nan)/data.GIB, 'GiB',
                f'{worker} export snapshot {summary.get("generated_at")}', 'summary_stats.json')
    add('Entry discovery total', papers.time_metadata_sec.sum(min_count=1), 'seconds',
        'Same value as Metadata attributed work; batched requests split evenly', 'per_paper.csv')
    outputs = [s.get('performance', {}).get('output_size_bytes', np.nan)
               for s in data.summaries(data_dir).values()]
    add('Final output size (all ranges)', sum(outputs)/data.GIB, 'GiB',
        'Sum of the 5 range snapshots above; paper folders only', 'summary_stats.json')
    paired, excluded = data.paired_sizes(data_dir)
    before, after = paired.size_full_bytes.sum(), paired.size_tex_bib_bytes.sum()
    for label, value in [('Extracted source', before/data.GIB), ('Retained TeX/Bib', after/data.GIB)]:
        add(label, value, 'GiB', f'{len(paired)} valid pairs; {excluded} excluded; content bytes', 'per_paper.csv')
    add('Corpus source reduction', 100*(1-after/before), '%', 'Ratio of paired totals, not mean paper reduction', 'per_paper.csv')
    for kind, count in events.kind.value_counts().items():
        add(f'Logged events: {kind}', int(count), 'events', 'events.jsonl only; includes control/stop events', 'events.jsonl')
    cooldown = events.loc[events.kind.eq('cooldown')]
    add('Explicit cooldown duration', pd.to_numeric(cooldown.get('seconds', pd.Series(dtype=float)), errors='coerce').sum(min_count=1),
        'seconds', 'Logged cooldown seconds only; no scraper.log duplication', 'events.jsonl')
    for worker, summary in data.summaries(data_dir).items():
        for kind, count in summary.get('performance', {}).get('arxiv_retry_events', {}).items():
            add(f'arXiv retry events: {kind}', count, 'events', f'{worker}; separate run-counter scope, do not add to event-log counts', 'summary_stats.json')
    return pd.DataFrame(rows)


def source_waiting_45(data_dir=None):
    """Use sleep and elapsed from the SAME state stats record, across its retries.

    The remainder is mainly network transfer. Extraction and writing run on the
    background writer thread, so they are mostly outside these timers.
    Exported source attribution is intentionally not mixed into this subtraction.
    """
    rows, excluded = [], 0
    for worker in data.WORKERS:
        state = json.loads((data.root(data_dir)/'.state'/worker/'source_state.json').read_text(encoding='utf-8'))
        for paper in state['papers'].values():
            stats = paper.get('stats', {})
            elapsed, sleep = stats.get('elapsed_sec'), stats.get('sleep_sec')
            if elapsed is None or sleep is None or not np.isfinite([elapsed, sleep]).all() or not 0 <= sleep <= elapsed:
                excluded += 1
                continue
            rows.append({'worker': worker, 'Recorded sleep': sleep, 'Other source time': elapsed-sleep})
    times = pd.DataFrame(rows).groupby('worker')[['Recorded sleep', 'Other source time']].sum()/3600
    fig, ax = data.figure(f'Matching cumulative source-state timers ({len(rows):,} papers; {excluded} excluded)', 'State-attributed hours')
    times.reindex(data.WORKERS).plot.bar(stacked=True, ax=ax, rot=0)
    ax.set_xlabel('Other source time is mainly network transfer; extraction and writing run on a background thread')
    return fig


def source_watiting_45(data_dir=None):
    """Backward-compatible spelling from the original module."""
    return source_waiting_45(data_dir)


def retry_errors_count_45(data_dir=None):
    counts = data.event_counts(data_dir)
    fig, ax = data.figure('Logged event kinds by range (includes stop/control events)', 'Events, not failed papers')
    counts.plot.bar(ax=ax, rot=0)
    return fig


def cooldown_duration_45(data_dir=None):
    events = data.records('events.jsonl', data_dir)
    selected = events.loc[events.kind.eq('cooldown')].copy()
    selected['seconds'] = pd.to_numeric(selected.get('seconds', pd.Series(dtype=float)), errors='coerce')
    if selected.seconds.isna().any():
        warnings.warn('Cooldown events without a duration are excluded from duration totals', stacklevel=2)
    totals = selected.groupby('worker').seconds.sum(min_count=1).reindex(data.WORKERS)
    counts = selected.groupby('worker').size().reindex(data.WORKERS, fill_value=0)
    totals.loc[counts.eq(0)] = 0
    fig, ax = data.figure('Explicit logged cooldown duration (events.jsonl only)', 'Seconds')
    totals.plot.bar(ax=ax, rot=0)
    ax.bar_label(ax.containers[0], labels=[f'{v:,.0f}s\n{n} events' for v, n in zip(totals, counts)], padding=3)
    ax.margins(y=.2)
    return fig
