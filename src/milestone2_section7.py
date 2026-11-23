"""Section 7 (performance evaluation) tables and charts. Functions return Figure or DataFrame.

Sources, all under ``statistics_parser/`` except the input size:

* ``report_exports/all/benchmark.json``: what the Colab notebook measured around the run
  (tar extraction, input check, parser wall time, compaction, output size, CPU count);
* ``run_logs/all/<run_id>.json``: the parser's own run summary (``src.m2.run``);
* ``report_exports/all/timing.csv`` and ``.state/all/parse_status``: per-version stage times;
* ``statistics_data/report_exports/R*/per_paper.csv``: the Milestone 1 ``.tex``/``.bib`` size,
  which is the parser's input.

Import with ``from src import milestone2_section7 as m2s7`` from the repo root.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
try:
    from . import _milestone2_data as data
except ImportError:
    import _milestone2_data as data

MIB = 2**20
_M1_DIR = Path(__file__).resolve().parents[1] / 'statistics_data' / 'report_exports'
_STAGES = {
    'gather_ms': 'Gathering',
    'preprocess_ms': 'Macros and conditionals',
    'hierarchy_ms': 'Tree, cleanup, math, sentences',
    'bib_ms': 'BibTeX extraction',
}


def benchmark(data_dir=None):
    return data.export_json('benchmark.json', data_dir)


def run_log(data_dir=None):
    """The run summary with the most finished papers (the benchmark run)."""
    logs = sorted((data.root(data_dir) / 'run_logs' / data.SCOPE).glob('*.json'))
    if not logs:
        raise FileNotFoundError('No parser run log')
    runs = [json.loads(p.read_text(encoding='utf-8')) for p in logs]
    return max(runs, key=lambda r: r.get('done', 0))


def input_bytes():
    """Size of the retained .tex/.bib files from Milestone 1 (the parser's input)."""
    frames = [pd.read_csv(_M1_DIR / r / 'per_paper.csv', usecols=['size_tex_bib_bytes'])
              for r in ('R1', 'R2', 'R3', 'R4', 'R5')]
    return float(pd.concat(frames).size_tex_bib_bytes.sum())


def _versions(data_dir=None):
    return data.parse_status(['arxiv_id', 'version', 'status', 'reused_from_prev'], data_dir)


def setup_table(data_dir=None):
    b, run = benchmark(data_dir), run_log(data_dir)
    versions = _versions(data_dir)
    tex = versions.status.astype(str).ne('empty')
    rows = [
        ('Testbed', 'Google Colab' if b.get('colab') else 'Not Colab', 'benchmark.json'),
        ('Runtime type', 'CPU-only', 'Declared by the team'),
        ('Logical CPUs', f"{b['cpus']}", 'benchmark.json'),
        ('Worker processes', f"{run['workers']}", 'Run log'),
        ('Parser version', run.get('parser_version', 'Not recorded'), 'Run log'),
        ('Run ID', run.get('run_id', 'Not recorded'), 'Run log'),
        ('Papers', f"{run['papers']:,}", 'Run log'),
        ('Versions (with TeX sources)', f"{len(versions):,} ({int(tex.sum()):,})", 'parse_status'),
        ('Input size (.tex and .bib from Milestone 1)', f"{input_bytes() / MIB:,.0f} MiB", 'Milestone 1 per_paper.csv'),
        ('CPU model, RAM and disk capacity', 'Not recorded', '-'),
    ]
    return pd.DataFrame(rows, columns=['Item', 'Value', 'Source'])


def wall_time_table(data_dir=None):
    """End-to-end wall time by phase, as timed by the Colab notebook."""
    b = benchmark(data_dir)
    extract = sum(v for k, v in b.items() if k.startswith('tar_extract_'))
    create = sum(v for k, v in b.items() if k.startswith('tar_create_'))
    phases = [
        ('Pack input on Drive (tar)', create, 'Once per range; a tar that already exists is reused'),
        ('Copy input to the local disk (untar)', extract, 'Five ranges, from Drive to /content'),
        ('Input check', b['input_check_s'], 'List papers and versions'),
        ('Parsing (python -m src.m2.run)', b['parse_wall_s'], 'Includes discovery, pool start and shard writes'),
        ('Compaction into 8 shards per table', b['compaction_s'], 'Separate --compact-only call'),
    ]
    table = pd.DataFrame(phases, columns=['Phase', 'Seconds', 'Note'])
    total = table.Seconds.sum()
    table['Share (%)'] = table.Seconds / total * 100
    table.loc[len(table)] = ['End to end', total, '', 100.0]
    table['Minutes'] = table.Seconds / 60
    return table[['Phase', 'Seconds', 'Minutes', 'Share (%)', 'Note']]


def time_per_unit_table(data_dir=None):
    """Average time per publication: throughput (wall / papers) and time inside a worker."""
    run = run_log(data_dir)
    papers, wall, workers = run['done'], run['wall_s'], run['workers']
    efficiency = papers * run['paper_ms_mean'] / (workers * wall * 1000)
    rows = [
        ('Worker time per paper', run['paper_ms_mean'], run['paper_ms_median'], run['paper_ms_p95']),
        ('Worker time per version', run['version_ms_mean'], run['version_ms_median'], run['version_ms_p95']),
    ]
    table = pd.DataFrame(rows, columns=['Measure', 'Mean (ms)', 'Median (ms)', 'p95 (ms)'])
    throughput = pd.DataFrame([
        ('Pool wall time (inside the parse phase of Table 7.2)', wall, 's'),
        ('Average wall time per paper (pool wall time / papers)', wall / papers * 1000, 'ms'),
        ('Papers per minute', papers / wall * 60, 'papers'),
        ('Parallel efficiency: worker time / (workers x pool wall time)', efficiency * 100, '%'),
    ], columns=['Measure', 'Value', 'Unit'])
    return table, throughput


def _timing(data_dir=None):
    return data.export_csv('timing.csv', data_dir)


def stage_table(data_dir=None):
    """Total worker time by stage, summed over all versions.

    ``elapsed_ms`` of a version covers every per-version stage (the files are read before the
    clock starts). The remainder after the named stages is not timed on its own: it holds the
    coverage check, which scans the body once more, the resolution and hashing of the ``.bib``
    files for the version signature, and the status bookkeeping. Paper-level work
    (reference deduplication, \\cite renaming, element deduplication and row building)
    is timed once per paper and stored as ``dedup_ms`` split over its versions.
    """
    tm = _timing(data_dir)
    totals = {name: tm[col].sum() / 1000 for col, name in _STAGES.items()}
    totals['Other per-version work (coverage check, bookkeeping)'] = (
        tm.elapsed_ms.sum() / 1000 - sum(totals.values()))
    totals['Paper level: dedup, \\cite renaming, rows'] = tm.dedup_ms.sum() / 1000
    table = pd.Series(totals, name='Worker seconds').rename_axis('Stage').reset_index()
    table['Share (%)'] = table['Worker seconds'] / table['Worker seconds'].sum() * 100
    return table


def timing_71(data_dir=None):
    """Distribution of the time per version (log scale) and total time by stage."""
    tm = _timing(data_dir)
    parsed = tm[~tm.reused.astype(str).str.lower().eq('true')]
    stages = stage_table(data_dir)
    fig, axes = plt.subplots(1, 2, figsize=(14, 5), layout='constrained')
    bins = np.logspace(np.log10(max(parsed.elapsed_ms.min(), 1)), np.log10(parsed.elapsed_ms.max()), 60)
    axes[0].hist(parsed.elapsed_ms, bins=bins, color='#3b6ea5')
    axes[0].set_xscale('log')
    for q, style in [(0.5, '-'), (0.95, '--'), (0.99, ':')]:
        x = parsed.elapsed_ms.quantile(q)
        axes[0].axvline(x, color='#333333', linestyle=style, linewidth=1, label=f'p{int(q*100)} = {x:,.0f} ms')
    axes[0].legend(loc='upper right', fontsize=9)
    axes[0].set(title=f'Worker time per version ({len(parsed):,} versions parsed in full)',
                xlabel='Milliseconds (log scale)', ylabel='Versions')
    order = stages.sort_values('Worker seconds')
    axes[1].barh(order.Stage, order['Worker seconds'], color='#c07a2c')
    for y, (s, share) in enumerate(zip(order['Worker seconds'], order['Share (%)'])):
        axes[1].text(s, y, f' {s:,.0f} s ({share:.1f}%)', va='center', fontsize=9)
    axes[1].set(title='Total worker time by stage', xlabel='Worker seconds (summed over both workers)')
    axes[1].margins(x=0.3)
    fig.suptitle('Figure 7.1. Where the parsing time goes')
    return fig


def memory_storage_table(data_dir=None):
    b, run = benchmark(data_dir), run_log(data_dir)
    out = run['output_bytes']
    repo_tables = sum(f.stat().st_size for f in (data.root(data_dir) / 'tables').rglob('*.parquet'))
    rows = [
        ('Memory', 'Peak RSS, parent and workers together', run['peak_rss_mb'], 'MiB'),
        ('Memory', 'Peak RSS of the workers alone', run['peak_workers_rss_mb'], 'MiB'),
        ('Storage', 'Input: .tex and .bib from Milestone 1', input_bytes() / MIB, 'MiB'),
        ('Storage', 'elements, before compaction', out['elements'] / MIB, 'MiB'),
        ('Storage', 'hierarchy, before compaction', out['hierarchy'] / MIB, 'MiB'),
        ('Storage', 'bibtex, before compaction', out['bibtex'] / MIB, 'MiB'),
        ('Storage', 'Three tables, before compaction', run['output_bytes_total'] / MIB, 'MiB'),
        ('Storage', 'Three tables, final (compacted, zstd)', b['tables_size_MB'], 'MiB'),
        ('Storage', 'Checkpoints and internal working data', b['checkpoints_and_internal_data_MB'], 'MiB'),
        ('Storage', 'Copy of the tables in this repository (split by range, snappy)', repo_tables / MIB, 'MiB'),
    ]
    return pd.DataFrame(rows, columns=['Group', 'Measure', 'Value', 'Unit'])


def size_vs_time_72(data_dir=None):
    """Worker time per version against the number of tree nodes and of compiled files."""
    ps = data.parse_status(['status', 'reused_from_prev', 'n_nodes', 'n_compile_files', 'elapsed_ms'], data_dir)
    ps = ps[ps.status.astype(str).ne('empty') & ~ps.reused_from_prev.astype(bool) & ps.n_nodes.gt(0)]
    fig, axes = plt.subplots(1, 2, figsize=(14, 5), layout='constrained')
    for ax, column, label in [(axes[0], 'n_nodes', 'Tree nodes in the version'),
                              (axes[1], 'n_compile_files', 'Compiled .tex files in the version')]:
        rho = ps[[column, 'elapsed_ms']].corr(method='spearman').iloc[0, 1]
        slope = np.polyfit(np.log10(ps[column]), np.log10(ps.elapsed_ms), 1)[0]
        hb = ax.hexbin(ps[column], ps.elapsed_ms, xscale='log', yscale='log', gridsize=45,
                       bins='log', mincnt=1, cmap='Blues')
        ax.set(title=f'{label}\nSpearman rho = {rho:.2f}, log-log slope = {slope:.2f}', xlabel=f'{label} (log scale)',
               ylabel='Worker time per version, ms (log scale)')
        fig.colorbar(hb, ax=ax, label='Versions (log scale)')
    fig.suptitle(f'Figure 7.2. Time per version against version size ({len(ps):,} versions parsed in full)')
    return fig


def tail_table(data_dir=None, top=5):
    """How concentrated the time is: share of the slowest papers, and the slowest versions.

    The papers are those with at least one parsed version (``timing.csv``), and their time is
    the sum of their per-version worker times. For each of the slowest versions, the size of
    its tree is placed among the versions parsed in full, and the stage that took longest is
    named.
    """
    tm = _timing(data_dir)
    paper = tm.groupby('arxiv_id').elapsed_ms.sum().sort_values(ascending=False)
    rows = []
    for share in (0.01, 0.05, 0.10):
        k = max(1, int(round(len(paper) * share)))
        rows.append({'Slowest papers': f'{share:.0%} ({k:,} papers)',
                     'Share of per-version worker time (%)': paper.head(k).sum() / paper.sum() * 100})

    ps = data.parse_status(['arxiv_id', 'version', 'status', 'reused_from_prev', 'n_nodes'], data_dir)
    ps = ps[ps.status.astype(str).ne('empty') & ~ps.reused_from_prev.astype(bool)]
    nodes = ps.set_index(['arxiv_id', 'version']).n_nodes
    sorted_nodes = np.sort(nodes.to_numpy())

    slow = tm.sort_values('elapsed_ms', ascending=False).head(top).copy()
    slow['n_nodes'] = [int(nodes.get((a, int(v)), 0)) for a, v in zip(slow.arxiv_id, slow.version)]
    slow['node_pct'] = np.searchsorted(sorted_nodes, slow.n_nodes, side='left') / len(sorted_nodes) * 100
    stage_cols = list(_STAGES)
    slow['stage'] = [
        f"{_STAGES[col]} ({row[col] / 1000:,.1f} s)"
        for col, (_, row) in zip(slow[stage_cols].idxmax(axis=1), slow.iterrows())]
    slow = slow[['arxiv_id', 'version', 'status', 'elapsed_ms', 'n_nodes', 'node_pct', 'stage']].rename(columns={
        'arxiv_id': 'arXiv ID', 'version': 'Version', 'status': 'Status', 'elapsed_ms': 'Worker time (ms)',
        'n_nodes': 'Tree nodes', 'node_pct': 'Node-count percentile', 'stage': 'Longest stage'})
    return pd.DataFrame(rows), slow.reset_index(drop=True)
