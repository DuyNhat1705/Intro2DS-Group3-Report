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


def stage_time_by_range_table(data_dir=None):
    """Sum each recorded stage once, without interpreting it as wall time."""
    papers = data.papers(data_dir)
    times = papers.groupby('worker')[STAGES].sum(min_count=1) / 3600
    times.loc['Total'] = papers[STAGES].sum(min_count=1) / 3600
    times.columns = [f'{name} (hours)' for name in STAGE_NAMES]
    times['Total attributed stage time (hours)'] = times.sum(axis=1, min_count=len(STAGES))
    return times.rename_axis('Range').reset_index()


def entry_discovery_time_table(data_dir=None):
    """Final paper attribution and all logged metadata attempts have distinct scopes.

    Batch durations in timings.jsonl are already amortized across IDs. Sum
    duration once per row; multiplying by batch_size would double-count work.
    """
    papers = data.papers(data_dir)
    attempts = data.records('timings.jsonl', data_dir)
    attempts = attempts.loc[attempts.stage.eq('metadata')]
    rows = []
    for label, frame in [*papers.groupby('worker'), ('Total', papers)]:
        logged = attempts if label == 'Total' else attempts.loc[attempts.worker.eq(label)]
        values = frame.time_metadata_sec.where(
            np.isfinite(frame.time_metadata_sec) & frame.time_metadata_sec.ge(0))
        duration = pd.to_numeric(logged.duration, errors='coerce')
        duration = duration.where(np.isfinite(duration) & duration.ge(0))
        total = values.sum(min_count=1)
        rows.append({
            'Range': label, 'Target papers': len(frame), 'Measured papers': int(values.count()),
            'Final attributed discovery (s)': total,
            'Final attributed discovery (min)': total / 60,
            'Mean attributed discovery (s/paper)': values.mean(),
            'Logged attempt rows': len(logged),
            'Measured attempt rows': int(duration.count()),
            'All logged discovery attempts (s)': duration.sum(min_count=1),
        })
    return pd.DataFrame(rows)


def _paper_stage_times(data_dir=None):
    papers = data.papers(data_dir).copy()
    stages = papers[STAGES].apply(pd.to_numeric, errors='coerce')
    stages = stages.where(np.isfinite(stages) & stages.ge(0))
    papers[STAGES] = stages
    # Require every stage: a missing source timer is not zero processing time.
    papers['complete_attributed_sec'] = stages.sum(axis=1, min_count=len(STAGES))
    return papers


def paper_processing_time_table(data_dir=None):
    """Per-stage distributions and strict complete-stage totals, in seconds."""
    papers = _paper_stage_times(data_dir)
    rows = []
    for column, name in [*zip(STAGES, STAGE_NAMES),
                         ('complete_attributed_sec', 'Total (all stages measured)')]:
        values = papers[column].dropna()
        rows.append({
            'Measure': name, 'Measured papers': len(values),
            'Excluded papers': len(papers) - len(values),
            'Sum (s)': values.sum(min_count=1), 'Mean (s/paper)': values.mean(),
            'Median (s)': values.median(), '95th percentile (s)': values.quantile(.95),
            'Maximum (s)': values.max(),
        })
    return pd.DataFrame(rows)


def paper_time_by_range_table(data_dir=None):
    papers = _paper_stage_times(data_dir)
    rows = []
    for label, frame in [*papers.groupby('worker'), ('Total', papers)]:
        values = frame.complete_attributed_sec.dropna()
        rows.append({'Range': label, 'Target papers': len(frame),
                     'Complete timing rows': len(values),
                     'Incomplete timing rows': len(frame) - len(values),
                     'Mean total attributed (s/paper)': values.mean(),
                     'Median total attributed (s)': values.median(),
                     '95th percentile total attributed (s)': values.quantile(.95)})
    return pd.DataFrame(rows)


def paper_timing_examples_table(data_dir=None, n=5):
    """Show the slowest complete rows for inspection; ties are resolved by ID."""
    papers = _paper_stage_times(data_dir).dropna(subset=['complete_attributed_sec'])
    selected = papers.sort_values(['complete_attributed_sec', 'arxiv_id'], ascending=[False, True]).head(n)
    columns = ['worker', 'arxiv_id', 'num_versions', *STAGES, 'complete_attributed_sec']
    return selected[columns].rename(columns=dict(zip(
        columns, ['Range', 'arXiv ID', 'Versions', 'Metadata (s)', 'Source (s)',
                  'References (s)', 'Total attributed (s)']))).reset_index(drop=True)


def collection_wall_time_table(data_dir=None):
    """Whole-system elapsed measures, kept separate from paper-attributed times."""
    runs = data.runs(data_dir)
    active, calendar = data.elapsed(runs)
    worker = runs.wall_sec.where(runs.wall_sec.ge(0)).sum(min_count=1)
    return pd.DataFrame([
        {'Measure': 'Calendar elapsed', 'Hours': calendar / 3600,
         'Scope': 'First session start to last end, including downtime'},
        {'Measure': 'Active collection elapsed', 'Hours': active / 3600,
         'Scope': 'Union of all worker session intervals; overlaps counted once'},
        {'Measure': 'Worker time', 'Hours': worker / 3600,
         'Scope': 'Sum of session durations; simultaneous workers counted separately'},
    ])


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

def session_duration_41(data_dir=None):
    runs = data.runs(data_dir)

    fig, axes = plt.subplots(
        len(data.WORKERS),
        1,
        figsize=(12, 3 * len(data.WORKERS)),
        sharey=True,
        layout="constrained",
        squeeze=False,
    )

    for ax, worker in zip(axes[:, 0], data.WORKERS):
        selected = runs.loc[
            runs.worker.eq(worker)
            & runs.start.notna()
            & runs.end.notna()
            & runs.end.ge(runs.start)
        ].sort_values("start")

        durations = (selected.end - selected.start) / 3600
        sessions = np.arange(1, len(selected) + 1)

        ax.bar(
            sessions,
            durations,
            color="#427aab",
            edgecolor="white",
        )

        ax.set(
            title=f"{worker} — session durations",
            xlabel="Session (ordered by start time)",
            ylabel="Duration (hours)",
        )
        ax.set_ylim(bottom=0)
        ax.xaxis.set_major_locator(
            plt.MaxNLocator(integer=True, nbins=15)
        )
        ax.grid(axis="y", alpha=0.3)
        ax.set_axisbelow(True)

        if selected.empty:
            ax.text(
                0.5, 0.5, "No valid sessions",
                transform=ax.transAxes,
                ha="center",
            )

    return fig

def session_timeline_41(data_dir=None):
    runs = data.runs(data_dir)

    valid = runs.loc[
        runs.worker.isin(data.WORKERS)
        & runs.start.notna()
        & runs.end.notna()
        & runs.end.ge(runs.start)
    ].sort_values("start")

    if len(valid) < 2:
        raise ValueError("At least two valid sessions are required.")

    starts = valid.start.to_numpy(dtype=float)
    ends = valid.end.to_numpy(dtype=float)

    # Tìm gap giữa các session, có xét session chồng lấn.
    running_end = np.maximum.accumulate(ends)
    gaps = starts[1:] - running_end[:-1]
    split = int(np.argmax(gaps))

    if gaps[split] <= 0:
        raise ValueError("No gap available for a broken time axis.")

    gap_start = running_end[split]
    gap_end = starts[split + 1]
    gap_days = (gap_end - gap_start) / 86400

    windows = [
        (starts.min(), gap_start),
        (gap_end, ends.max()),
    ]

    fig, axes = plt.subplots(
        1, 2,
        figsize=(13, 5),
        sharey=True,
        gridspec_kw={"width_ratios": [4, 1]},
    )
    fig.subplots_adjust(wspace=0.08, bottom=0.22, top=0.82)

    for panel, (ax, (lower, upper)) in enumerate(zip(axes, windows)):
        color = "#427aab" if panel == 0 else "#d68a32"

        for i, worker in enumerate(data.WORKERS):
            selected = valid.loc[
                valid.worker.eq(worker)
                & valid.end.ge(lower)
                & valid.start.le(upper)
            ]

            intervals = [
                (
                    mdates.date2num(
                        pd.to_datetime(run.start, unit="s", utc=True)
                    ),
                    (run.end - run.start) / 86400,
                )
                for run in selected.itertuples()
            ]

            if intervals:
                ax.broken_barh(
                    intervals,
                    (i - 0.3, 0.6),
                    facecolors=color,
                )
            if panel == 1:
                for run in selected.itertuples():
                    midpoint = pd.to_datetime(
                        (run.start + run.end) / 2,
                        unit="s",
                        utc=True,
                    )
                    duration_minutes = (run.end - run.start) / 60

                    ax.text(
                        mdates.date2num(midpoint),
                        i + 0.36,
                        f"{duration_minutes:.2f} min",
                        ha="center",
                        fontsize=9,
                    )

        margin = max((upper - lower) * 0.05, 60)

        ax.set_xlim(
            mdates.date2num(
                pd.to_datetime(lower - margin, unit="s", utc=True)
            ),
            mdates.date2num(
                pd.to_datetime(upper + margin, unit="s", utc=True)
            ),
        )

        locator = mdates.AutoDateLocator(
            minticks=3, maxticks=7 if panel == 0 else 3
        )
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(
            mdates.DateFormatter("%m-%d\n%H:%M", tz="UTC")
        )
        ax.grid(axis="x", alpha=0.2)
        ax.set_axisbelow(True)
        ax.set_xlabel("UTC date / time")

    axes[0].set_yticks(range(len(data.WORKERS)), data.WORKERS)
    axes[0].set_ylim(-0.6, len(data.WORKERS) - 0.4)
    axes[0].set_title("Main collection")
    axes[1].set_title("Later session - zoomed")

    # Ẩn cạnh nối và thêm dấu ngắt trục.
    axes[0].spines["right"].set_visible(False)
    axes[1].spines["left"].set_visible(False)
    axes[1].tick_params(axis="y", left=False, labelleft=False)

    for ax, x in [(axes[0], 1), (axes[1], 0)]:
        ax.plot(
            [x, x], [0, 1],
            transform=ax.transAxes,
            marker=[(-1, -0.6), (1, 0.6)],
            markersize=12,
            linestyle="none",
            color="black",
            clip_on=False,
        )

    fig.suptitle("Recorded worker sessions (UTC)")
    fig.text(
        0.5, 0.03,
        f"{gap_days:.2f} days without recorded sessions omitted; "
        "panels use different time scales.",
        ha="center",
        fontsize=9,
    )

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


def _resource_plot(
    name, time_column, value_columns,
    divisor, title, ylabel, data_dir
):
    frame = data.exports(name, data_dir)

    fig, axes = plt.subplots(
        len(data.WORKERS),
        1,
        figsize=(13, 12),
        sharex=False,
        layout="constrained",
        squeeze=False,
    )

    colors = plt.get_cmap("tab10").colors

    for ax, worker in zip(axes[:, 0], data.WORKERS):
        selected = (
            frame.loc[frame.worker.eq(worker)]
            .dropna(subset=[time_column, "run_id"])
            .sort_values(time_column)
        )

        offset = 0.0

        # Session được sắp theo thời điểm có mẫu đầu tiên.
        for i, (_, session) in enumerate(
            selected.groupby("run_id", sort=False)
        ):
            session = session.sort_values(time_column)

            elapsed = (
                session[time_column] - session[time_column].iloc[0]
            ) / 3600

            x = offset + elapsed

            # Đánh dấu ranh giới giữa các session.
            if i > 0:
                ax.axvline(
                    offset,
                    color="gray",
                    linestyle=":",
                    linewidth=0.8,
                    alpha=0.5,
                )

            for j, (column, label) in enumerate(value_columns):
                ax.plot(
                    x,
                    session[column] / divisor,
                    color=colors[j % len(colors)],
                    label=label if i == 0 else None,
                    marker=".",
                    markersize=2,
                    linewidth=1,
                )

            offset += elapsed.iloc[-1]

        ax.set(
            title=worker,
            xlabel="Cumulative observed session time (hours)",
            ylabel=ylabel,
        )
        ax.set_xlim(left=0)
        ax.grid(alpha=0.2)
        ax.set_axisbelow(True)

        if not selected.empty:
            ax.legend(loc="upper left", fontsize=8)
        else:
            ax.text(
                0.5, 0.5, "No recorded samples",
                transform=ax.transAxes,
                ha="center",
            )

    fig.suptitle(title)

    return fig


def memory_over_execution_43(data_dir=None):
    return _resource_plot(
        "monitor.csv",
        "minute",
        [
            ("rss_mean_bytes", "Minute mean RSS"),
            ("rss_max_bytes", "Minute sampled peak RSS"),
        ],
        data.MIB,
        "Sampled process RSS over observed session time",
        "MiB",
        data_dir,
    )


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
