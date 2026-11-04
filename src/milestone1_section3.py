"""Section 3 charts for notebook display. Functions return Figure or DataFrame.

No images are saved. Optional data_dir points to a statistics_data directory.
Import with ``from src import milestone1_section3 as s3`` from the repo root.
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
try:
    from . import _milestone1_data as data
except ImportError:
    import _milestone1_data as data


def success_fail_31(data_dir=None):
    papers = data.papers(data_dir)
    counts = papers.paper_success.value_counts().reindex([True, False], fill_value=0)
    fig, ax = data.figure('Final paper outcomes (all target IDs)', 'Papers')
    ax.bar(['Success', 'Failure'], counts, color=['#298c6b', '#cb574c'])
    data.annotate(ax, len(papers))
    found = papers.metadata.eq('done').sum()
    ax.set_xlabel(f'Metadata found: {found:,}; success among found: {counts[True]/found:.3%}')
    return fig


def outcome_by_range_31(data_dir=None):
    """Exclusive failures and a separate panel to keep rare failures visible."""
    papers = data.papers(data_dir)
    papers['outcome'] = np.select([papers.metadata.ne('done'), papers.source.ne('done')],
                                 ['Metadata incomplete', 'Source incomplete'], default='Success')
    counts = pd.crosstab(papers.worker, papers.outcome).reindex(data.WORKERS, fill_value=0)
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), layout='constrained')
    counts.plot.bar(stacked=True, ax=axes[0], rot=0, title='Final outcomes by range', ylabel='Papers')
    data.annotate(axes[0])
    failures = counts.drop(columns='Success', errors='ignore')
    if failures.empty:
        axes[1].text(.5, .5, 'No final failures', ha='center')
    else:
        failures.plot.bar(ax=axes[1], rot=0, title='Rare final failures', ylabel='Papers')
        data.annotate(axes[1])
    return fig


def retry_errors_31(data_dir=None):
    """Observed event names include control/stop events; counts are not failed papers."""
    counts = data.event_counts(data_dir).sum().sort_values()
    fig, ax = data.figure('Logged event categories (events, not failed papers)')
    ax.barh(counts.index, counts)
    ax.set_xlabel('Logged events')
    ax.bar_label(ax.containers[0], padding=3)
    return fig


def version_outcome_31(data_dir=None):
    columns = ['n_versions_done', 'n_versions_no_tex', 'n_versions_not_found']
    counts = data.papers(data_dir).groupby('worker')[columns].sum()
    counts.columns = ['Completed', 'No TeX', 'Not found']
    fig, ax = data.figure('Recorded version outcomes (versions, not papers)', 'Versions')
    counts.plot.bar(stacked=True, ax=ax, rot=0)
    data.annotate(ax)
    return fig


def extracted_retained_size_32(data_dir=None):
    """Valid paired totals, positive-size boxplots, and log-scale paired scatter."""
    papers, excluded = data.paired_sizes(data_dir)
    before, after = papers.size_full_bytes, papers.size_tex_bib_bytes
    fig, axes = plt.subplots(1, 3, figsize=(17, 5), layout='constrained')
    totals = np.array([before.sum(), after.sum()])/data.GIB
    axes[0].bar(['Extracted', 'Retained TeX/Bib'], totals)
    axes[0].bar_label(axes[0].containers[0], fmt='%.3f GiB')
    axes[0].set(title=f'Corpus reduction: {100*(1-totals[1]/totals[0]):.2f}%', ylabel='GiB (file-content bytes)')
    axes[1].boxplot([before/data.MIB, after[after.gt(0)]/data.MIB], tick_labels=['Extracted', 'Retained'], showfliers=False)
    axes[1].set(yscale='log', ylabel='MiB (log; outliers hidden)', title=f'{after.eq(0).sum():,} retained zeros excluded')
    positive = after.gt(0)
    axes[2].scatter(before[positive]/data.MIB, after[positive]/data.MIB, s=5, alpha=.25)
    if positive.any():
        lo, hi = min(before[positive].min(), after[positive].min())/data.MIB, max(before[positive].max(), after[positive].max())/data.MIB
        axes[2].plot([lo, hi], [lo, hi], 'k--', label='Equal size')
        axes[2].legend()
    axes[2].set(xscale='log', yscale='log', xlabel='Extracted MiB', ylabel='Retained MiB')
    fig.suptitle(f'Source filtering: {len(papers):,} pairs; {excluded:,} invalid/missing/zero-before excluded')
    return fig


def paper_reduction_32(data_dir=None):
    papers, excluded = data.paired_sizes(data_dir)
    fig, ax = data.figure(f'Per-paper source reduction ({len(papers):,} pairs; {excluded:,} excluded)', 'Papers')
    ax.hist(papers.reduction_pct, bins=50, edgecolor='white')
    ax.set_xlabel('100 × (extracted − retained) / extracted (%)')
    ax.axvline(papers.reduction_pct.median(), color='black', linestyle='--', label='Median')
    ax.legend()
    return fig


def reference_count_33(data_dir=None):
    papers = data.papers(data_dir)
    selected = papers.loc[papers.refs.eq('ok') & papers.n_refs.notna()]
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), layout='constrained')
    axes[0].hist(selected.n_refs, bins=60, edgecolor='white')
    axes[0].set(xlabel='Returned references per paper', ylabel='Papers (log frequency)', yscale='log', title=f"refs='ok' only (n={len(selected):,})")
    axes[1].boxplot([selected.loc[selected.worker.eq(w), 'n_refs'] for w in data.WORKERS], tick_labels=data.WORKERS, showfliers=False)
    axes[1].set(ylabel='Returned references', title='Successful lookups; outliers hidden')
    compatible = papers[['n_refs', 'n_refs_arxiv']].dropna()
    coverage = compatible.n_refs_arxiv.sum()/compatible.n_refs.sum() if compatible.n_refs.sum() else np.nan
    fig.suptitle(f'arXiv-linked share of returned references: {coverage:.2%} (compatible nonmissing rows)')
    return fig


def lookup_outcome_33(data_dir=None):
    papers = data.papers(data_dir)
    counts = pd.crosstab(papers.worker, papers.refs.fillna('missing')).reindex(data.WORKERS, fill_value=0)
    fig, ax = data.figure('Final reference lookup outcomes by range', 'Requested papers (%)')
    (counts.div(counts.sum(axis=1), axis=0)*100).plot.bar(stacked=True, ax=ax, rot=0)
    for container, column in zip(ax.containers, counts.columns):
        ax.bar_label(container, labels=[f'{n:,}\n{100*n/total:.2f}%' if n else '' for n, total in zip(counts[column], counts.sum(axis=1))], label_type='center', fontsize=8)
    ax.set_ylim(0, 110)
    return fig


def _present(value):
    if isinstance(value, (list, tuple, np.ndarray)):
        return any(_present(item) for item in value)
    return False if pd.isna(value) else bool(str(value).strip())


def metadata_completeness_33(data_dir=None):
    """Stream all returned reference rows, checking actual schemas before reading."""
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise ImportError('Install the Parquet dependency: pip install pyarrow') from exc
    columns = ['ref_title', 'ref_authors', 'ref_submission_date', 'ref_arxiv_id', 'ref_s2_id']
    totals, n = pd.Series(0, index=columns, dtype='int64'), 0
    for worker in data.WORKERS:
        path = data.root(data_dir)/'tables'/worker/'references_all.parquet'
        schema = pq.read_schema(path).names
        if set(columns)-set(schema):
            raise ValueError(f'Unexpected reference schema in {path}: {schema}')
        for batch in pq.ParquetFile(path).iter_batches(columns=columns):
            frame = batch.to_pandas()
            n += len(frame)
            for column in columns:
                totals[column] += frame[column].map(_present).sum()
    fig, ax = data.figure(f'Reference metadata completeness ({n:,} returned reference rows)')
    ax.barh(columns, totals/n*100 if n else totals.astype(float)*np.nan)
    ax.set(xlabel='Nonempty field (%)', xlim=(0, 120))
    ax.bar_label(ax.containers[0], labels=[f'{v:,}/{n:,}' for v in totals], padding=3)
    return fig


def num_version_34(data_dir=None):
    papers = data.papers(data_dir)
    values = papers.loc[papers.metadata.eq('done'), 'num_versions'].dropna()
    counts = values.value_counts().sort_index()
    fig, ax = data.figure('Versions per metadata-found paper', 'Papers')
    ax.bar(counts.index, counts)
    ax.set_xticks(counts.index)
    ax.set_xlabel(f'Versions; median={values.median():g}, p95={values.quantile(.95):g}, >1={(values>1).mean():.2%}')
    data.annotate(ax)
    return fig


def primary_category_34(data_dir=None, top_n=15):
    if top_n < 1:
        raise ValueError('top_n must be positive')
    categories = data.exports('category_counts.csv', data_dir)
    counts = categories.groupby('primary_category').n_papers.sum().sort_values(ascending=False)
    shown = counts.head(top_n).copy()
    if len(counts)>top_n:
        shown.loc['Other'] = counts.iloc[top_n:].sum()
    fig, axes = plt.subplots(1, 2, figsize=(15, 7), layout='constrained')
    shown.sort_values().plot.barh(ax=axes[0], title='Primary categories (first category only)', xlabel='Papers')
    table = categories.pivot_table(index='primary_category', columns='worker', values='n_papers', aggfunc='sum', fill_value=0)
    table = table.reindex(index=counts.head(top_n).index, columns=data.WORKERS, fill_value=0)
    image = axes[1].imshow(table, aspect='auto', cmap='Blues')
    axes[1].set_xticks(range(len(table.columns)), table.columns)
    axes[1].set_yticks(range(len(table)), table.index)
    axes[1].set_title('Top primary categories by range')
    fig.colorbar(image, ax=axes[1], label='Papers')
    return fig


def sampling_windows_34(data_dir=None):
    """Range-definition table; selected ID windows are not an unbiased sample."""
    return data.exports('ranges.csv', data_dir)[['worker', 'range_label', 'yymm', 'start', 'end']]


def submission_timeline_34(data_dir=None):
    papers = data.parquet('papers.parquet', ['arxiv_id', 'submission_date'], data_dir).drop_duplicates('arxiv_id')
    dates = pd.to_datetime(papers.submission_date, errors='coerce', utc=True)
    counts = dates.dropna().dt.strftime('%Y-%m').value_counts().sort_index()
    fig, ax = data.figure('Initial submission months in the selected sample', 'Unique papers')
    counts.plot.bar(ax=ax, rot=45)
    data.annotate(ax)
    ax.set_xlabel(f'Observed months only; {dates.isna().sum():,} invalid/missing dates. Missing months are not zero arXiv activity.')
    return fig


def revision_history_34(data_dir=None):
    papers = data.parquet('papers.parquet', ['arxiv_id', 'submission_date', 'revised_dates'], data_dir).drop_duplicates('arxiv_id')
    def latest(values):
        if not isinstance(values, (list, tuple, np.ndarray)) or not len(values):
            return pd.NaT
        return pd.to_datetime(list(values), errors='coerce', utc=True).max()
    submitted = pd.to_datetime(papers.submission_date, errors='coerce', utc=True)
    revised = pd.to_datetime(papers.revised_dates.map(latest), errors='coerce', utc=True)
    lag = (revised-submitted).dt.total_seconds()/86400
    valid = lag.notna() & lag.ge(0)
    fig, ax = data.figure(f'Initial submission to latest revision ({valid.sum():,} valid papers)', 'Papers')
    ax.hist(lag[valid], bins=50, edgecolor='white')
    ax.set_xlabel(f'Days; {(~valid).sum():,} absent/invalid/negative intervals excluded')
    return fig
