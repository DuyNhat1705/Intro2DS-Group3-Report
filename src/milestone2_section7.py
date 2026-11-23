"""Section 7 runtime tables and figures computed from statistics_parser.

Figures are returned for notebook display; no image files are written.
"""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

try:
    from . import milestone2_data as data
except ImportError:
    import milestone2_data as data


def running_time_phases_table(data_dir=None):
    """Non-overlapping outer timing intervals; excludes setup and report export."""
    benchmark = data.benchmark(data_dir)
    staging = sum(
        value for key, value in benchmark.items()
        if key.startswith('tar_create_') or key.startswith('tar_extract_')
    )
    return pd.DataFrame([
        ('Input archive staging', staging),
        ('Input inventory check', benchmark['input_check_s']),
        ('Parser invocation', benchmark['parse_wall_s']),
        ('Final compaction', benchmark['compaction_s']),
    ], columns=['Phase', 'Seconds'])


def running_time_summary_table(data_dir=None):
    """Wall averages are amortized elapsed time, distinct from worker latency."""
    benchmark = data.benchmark(data_dir)
    papers = data.exports('paper_dedup.csv', data_dir)
    count = len(papers)
    parse_and_compact = benchmark['parse_wall_s'] + benchmark['compaction_s']
    frame = pd.DataFrame([
        ('Internal worker-pool wall time', benchmark['wall_s']),
        ('Outer parser invocation', benchmark['parse_wall_s']),
        ('Parser + final compaction (timer sum)', parse_and_compact),
        ('Staging + check + parser + compaction (timer sum)', running_time_phases_table(data_dir)['Seconds'].sum()),
    ], columns=['Measurement', 'Seconds'])
    frame['Minutes'] = frame['Seconds'] / 60
    frame['Wall ms per publication'] = frame['Seconds'] * 1000 / count
    return frame


def processing_time_statistics_table(data_dir=None):
    """Elapsed worker/publication and non-empty version timers, not CPU time."""
    papers = data.exports('paper_dedup.csv', data_dir)
    versions = data.exports('timing.csv', data_dir)
    rows = []
    for population, values in [
        ('Publication worker timer (all publications)', papers['elapsed_ms']),
        ('Version parser timer (non-empty versions)', versions['elapsed_ms']),
    ]:
        rows.append({
            'Population': population,
            'Records': len(values),
            'Mean (ms)': values.mean(),
            'Median (ms)': values.median(),
            # Match the run logger's nearest-observation percentile rule.
            '95th percentile (ms)': values.quantile(0.95, interpolation='nearest'),
            '99th percentile (ms)': values.quantile(0.99, interpolation='nearest'),
            'Maximum (ms)': values.max(),
        })
    return pd.DataFrame(rows)


def processing_time_distributions_72(data_dir=None):
    """Show the complete timing tails without clipping or omitting empty papers."""
    papers = data.exports('paper_dedup.csv', data_dir)
    versions = data.exports('timing.csv', data_dir)
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5), layout='constrained')
    for ax, values, title, ylabel in [
        (axes[0], papers['elapsed_ms'], 'Elapsed worker time per publication', 'Publications'),
        (axes[1], versions['elapsed_ms'], 'Parser time per non-empty version', 'Versions'),
    ]:
        positive = values.loc[values.gt(0)]
        lo, hi = positive.min(), positive.max()
        if lo == hi:
            lo, hi = lo / 10, hi * 10
        ax.hist(positive, bins=np.geomspace(lo, hi, 45), color='#4E79A7', edgecolor='white')
        median = values.median()
        p95 = values.quantile(0.95, interpolation='nearest')
        ax.axvline(median, color='#F28E2B', linestyle='--', label=f'Median: {median:,.2f} ms')
        ax.axvline(p95, color='#E15759', linestyle=':', label=f'95th percentile: {p95:,.2f} ms')
        ax.set_xscale('log')
        ax.set_xlabel('Elapsed time (ms, log scale)')
        ax.set_ylabel(ylabel)
        ax.set_title(f'{title}\n(n={len(values):,})')
        ax.legend(loc='upper left', fontsize=8)
        ax.grid(axis='y', alpha=0.2)
        ax.set_axisbelow(True)
    return fig


def stage_time_statistics_table(data_dir=None):
    """Deduplication is attributed across versions; stage timers are not wall time."""
    versions = data.exports('timing.csv', data_dir)
    columns = {
        'gather_ms': 'Multi-file gathering',
        'preprocess_ms': 'Macro preprocessing',
        'hierarchy_ms': 'Hierarchy + cleanup + sentences',
        'bib_ms': 'Bibliography extraction',
        'dedup_ms': 'Cross-version deduplication',
    }
    totals = versions[list(columns)].sum() / 1000
    frame = totals.rename(index=columns).rename_axis('Stage').rename('Seconds').reset_index()
    frame['Share of instrumented stages'] = frame['Seconds'] / frame['Seconds'].sum()
    return frame


def running_time_breakdown_72(data_dir=None):
    """Separate sequential phase wall times from summed worker-stage timings."""
    phases = running_time_phases_table(data_dir)
    stages = stage_time_statistics_table(data_dir)
    fig, axes = plt.subplots(1, 2, figsize=(14, 4.8), layout='constrained')
    for ax, frame, label, title, xlabel in [
        (axes[0], phases, 'Phase', 'Sequential workflow phase timers', 'Wall time (s)'),
        (axes[1], stages, 'Stage', 'Instrumented processing stages', 'Summed stage time (s; not wall time)'),
    ]:
        bars = ax.barh(frame[label], frame['Seconds'], color='#4E79A7')
        ax.invert_yaxis()
        ax.set_xlim(0, frame['Seconds'].max() * 1.35)
        ax.set_title(title)
        ax.set_xlabel(xlabel)
        for bar in bars:
            ax.annotate(
                f'{bar.get_width():,.2f} s',
                (bar.get_width(), bar.get_y() + bar.get_height() / 2),
                xytext=(4, 0), textcoords='offset points', va='center', fontsize=9,
            )
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda value, _: f'{value:,.0f}'))
        ax.grid(axis='x', alpha=0.2)
        ax.set_axisbelow(True)
    return fig
