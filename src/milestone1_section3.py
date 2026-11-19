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
    columns = ["n_versions_done", "n_versions_no_tex", "n_versions_not_found"]
    counts = data.papers(data_dir).groupby("worker")[columns].sum()
    counts.columns = ["Completed", "No TeX", "Not found"]

    fig, ax = plt.subplots(figsize=(10, 5))
    counts.plot.bar(stacked=True, ax=ax, rot=0)
    ax.set_title("Recorded version outcomes")
    ax.set_ylabel("Versions")
    ax.set_xlabel("")
    fig.tight_layout()
    return fig


def extracted_retained_size_32(data_dir=None):
    """Compare total sizes and extracted/retained size distributions."""
    papers, excluded = data.paired_sizes(data_dir)

    if papers.empty:
        raise ValueError("No valid size pairs to plot.")

    before = papers.size_full_bytes
    after = papers.size_tex_bib_bytes

    fig, axes = plt.subplots(
        1, 2, figsize=(14, 5), layout="constrained"
    )

    # Biểu đồ 1: Tổng dung lượng
    totals = np.array([before.sum(), after.sum()]) / data.GIB
    bars = axes[0].bar(["Extracted", "Retained TeX/Bib"], totals)

    axes[0].bar_label(bars, fmt="%.3f GiB")
    axes[0].set(
        title=f"Corpus reduction: {100 * (1 - totals[1] / totals[0]):.2f}%",
        ylabel="GiB (file-content bytes)",
    )

    # Biểu đồ 2: Histogram chồng, dùng chung các khoảng dung lượng
    after_positive = after[after.gt(0)]
    values = np.concatenate([
        before.to_numpy(),
        after_positive.to_numpy(),
    ])

    lo, hi = values.min(), values.max()
    if lo == hi:
        lo, hi = lo / 10, hi * 10

    bins = np.geomspace(lo, hi, 35)

    axes[1].hist(
        before,
        bins=bins,
        alpha=0.6,
        color="#F28E2B",
        label="Extracted",
    )
    axes[1].hist(
        after_positive,
        bins=bins,
        alpha=0.6,
        color="#4E79A7",
        label="Retained TeX/Bib",
    )

    axes[1].set(
        xscale="log",
        xlabel="Paper size (bytes)",
        ylabel="Papers",
        title="Paper size before and after source filtering",
    )
    axes[1].legend()
    axes[1].grid(alpha=0.3)
    axes[1].set_axisbelow(True)


def paper_reduction_32(data_dir=None):
    papers, excluded = data.paired_sizes(data_dir)
    fig, ax = data.figure(f'Per-paper source reduction ({len(papers):,} pairs; {excluded:,} excluded)', 'Papers')
    ax.hist(papers.reduction_pct, bins=50, edgecolor='white')
    ax.set_xlabel('100 × (extracted − retained) / extracted (%)')
    ax.axvline(papers.reduction_pct.median(), color='black', linestyle='--', label='Median')
    ax.legend()
    return fig


def size_concentration_32(data_dir=None):
    """Show storage concentration and the empirical distribution of savings."""
    papers, excluded = data.paired_sizes(data_dir)
    fig, axes = plt.subplots(1, 2, figsize=(14, 5), layout='constrained')
    for column, label in [('size_full_bytes', 'Extracted'), ('size_tex_bib_bytes', 'Retained TeX/Bib')]:
        values = papers[column].sort_values(ascending=False).to_numpy()
        x = np.arange(1, len(values)+1)/len(values)*100
        y = np.cumsum(values)/values.sum()*100
        axes[0].plot(np.r_[0, x], np.r_[0, y], label=label)
    axes[0].plot([0, 100], [0, 100], '--', color='grey', label='Equal size per paper')
    axes[0].set(xlabel='Largest papers by each respective size measure (%)',
                ylabel='Cumulative share of bytes (%)', xlim=(0, 100), ylim=(0, 100),
                title='How concentrated is storage?')
    axes[0].legend()
    reduction = papers.reduction_pct.sort_values().to_numpy()
    axes[1].step(reduction, np.arange(1, len(reduction)+1)/len(reduction)*100, where='post')
    for threshold in [50, 90, 95]:
        share = papers.reduction_pct.ge(threshold).mean()*100
        axes[1].axvline(threshold, linestyle=':', alpha=.6, label=f'{share:.1f}% save at least {threshold}%')
    axes[1].set(xlabel='Per-paper reduction (%)', ylabel='Papers with reduction at or below x (%)',
                xlim=(0, 100), ylim=(0, 100), title='Distribution of filtering savings (ECDF)')
    axes[1].legend(loc='upper left', fontsize=8)
    fig.suptitle(f'{len(papers):,} valid size pairs; {excluded:,} excluded; size rankings are independent')
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
    if "not_found" in counts.columns:
        not_found = counts.pop("not_found")
        counts["not_found"] = not_found

    colors = {
        "no_refs": "tab:blue",
        "ok": "tab:green",
        "not_found": "tab:orange",
    }

    fig, ax = data.figure(
        "Final reference lookup outcomes by range", "Requested papers (%)"
    )
    percentages = counts.div(counts.sum(axis=1), axis=0) * 100
    percentages.plot.bar(
        stacked=True,
        ax=ax,
        rot=0,
        color=[colors.get(column, "tab:gray") for column in counts.columns],
    )
    for container, column in zip(ax.containers, counts.columns):
        ax.bar_label(container, labels=[f'{n:,}\n{100*n/total:.2f}%' if n/total >= .01 else '' for n, total in zip(counts[column], counts.sum(axis=1))], label_type='center', fontsize=8)
    if 'not_found' in counts:
        for i, n in enumerate(counts.not_found):
            ax.text(i, 102, f'not_found: {n}', ha='center', fontsize=8)
    ax.set_ylim(0, 110)
    ax.set_xlabel('Range')
    ax.legend(title='Outcome', loc='upper left', bbox_to_anchor=(1.01, 1))
    return fig


def reference_profiles_33(data_dir=None):
    """Separate nonempty lookup rates, reference yield, and arXiv link coverage."""
    papers = data.papers(data_dir)
    groups = papers.groupby('worker')
    rate = groups.refs.agg(lambda values: values.eq('ok').mean()*100).reindex(data.WORKERS)
    mean_ok = papers.loc[papers.refs.eq('ok')].groupby('worker').n_refs.mean().reindex(data.WORKERS)
    returned_per_target = (groups.n_refs.sum()/groups.size()).reindex(data.WORKERS)
    coverage = (groups.n_refs_arxiv.sum()/groups.n_refs.sum()*100).reindex(data.WORKERS)
    fig, axes = plt.subplots(1, 3, figsize=(16, 5), layout='constrained')
    colors = ['#427aab']*4+['#d68a32']
    axes[0].bar(data.WORKERS, rate, color=colors)
    axes[0].set(title='Nonempty reference lookups', ylabel='ok / 5,000 target IDs (%)', ylim=(0, 105))
    axes[0].bar_label(axes[0].containers[0], fmt='%.2f%%', padding=3)
    x = np.arange(len(data.WORKERS))
    axes[1].bar(x-.19, mean_ok, .38, label='Mean among ok lookups')
    axes[1].bar(x+.19, returned_per_target, .38, label='Returned references / target ID')
    axes[1].set(xticks=x, xticklabels=data.WORKERS, title='Conditional mean versus realized yield', ylabel='References per paper or target ID')
    axes[1].legend(fontsize=8)
    axes[1].margins(y=.22)
    for container in axes[1].containers:
        axes[1].bar_label(container, fmt='%.1f', padding=3, fontsize=8)
    axes[2].bar(data.WORKERS, coverage, color=colors)
    axes[2].set(title='arXiv-linked reference coverage', ylabel='Linked / all returned references (%)', ylim=(0, 105))
    axes[2].bar_label(axes[2].containers[0], fmt='%.2f%%', padding=3)
    fig.suptitle('Different denominators reveal different aspects of reference collection')
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
    fig, ax = data.figure('Versions per paper', 'Papers')
    ax.bar(counts.index, counts)
    ax.set_xticks(counts.index)
    ax.set_xlabel(f'Versions')
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
    axes[0].bar_label(axes[0].containers[0], labels=[f'{n:,} ({n/counts.sum():.1%})' for n in shown.sort_values()], padding=3, fontsize=8)
    axes[0].margins(x=.28)
    table = categories.pivot_table(index='primary_category', columns='worker', values='n_papers', aggfunc='sum', fill_value=0)
    table = table.reindex(index=counts.head(top_n).index, columns=data.WORKERS, fill_value=0)
    percentages = table.div(categories.groupby('worker').n_papers.sum(), axis=1)*100
    image = axes[1].imshow(percentages, aspect='auto', cmap='Blues', vmin=0)
    axes[1].set_xticks(range(len(table.columns)), table.columns)
    axes[1].set_yticks(range(len(table)), table.index)
    axes[1].set_title('Category share of all papers in each range')
    for row in range(len(table)):
        for col in range(len(table.columns)):
            value = percentages.iloc[row, col]
            axes[1].text(col, row, f'{value:.1f}%', ha='center', va='center', fontsize=8,
                         color='white' if value > percentages.to_numpy().max()*.55 else 'black')
    fig.colorbar(image, ax=axes[1], label='Papers in range (%)')
    return fig


def version_storage_profile_34(data_dir=None):
    """Compare storage shares on valid size pairs only."""
    paired, _ = data.paired_sizes(data_dir)
    multi = paired.num_versions.gt(1)

    shares = np.array([
        paired.loc[multi, "size_full_bytes"].sum()
        / paired.size_full_bytes.sum(),

        paired.loc[multi, "size_tex_bib_bytes"].sum()
        / paired.size_tex_bib_bytes.sum(),
    ]) * 100

    fig, ax = data.figure(
        "Revision multiplicity and storage contribution",
        "Share within each population (%)",
        figsize=(8, 5),
    )

    labels = ["Extracted bytes", "Retained bytes"]

    ax.bar(
        labels, 100 - shares,
        label="Single-version papers",
        color="#427aab",
    )
    ax.bar(
        labels, shares,
        bottom=100 - shares,
        label="Multi-version papers",
        color="#d68a32",
    )

    for container in ax.containers:
        ax.bar_label(
            container,
            labels=[f"{v:.2f}%" for v in container.datavalues],
            label_type="center",
        )

    ax.set_ylim(0, 112)
    ax.legend(
        loc="upper center",
        bbox_to_anchor=(.5, 1.02),
        ncol=2,
        fontsize=9,
    )
    ax.set_xlabel(f"Storage: {len(paired):,} valid size pairs")

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
    fig, axes = plt.subplots(1, 2, figsize=(14, 5), layout='constrained')
    axes[0].hist(lag[valid], bins=50, edgecolor='white')
    axes[0].axvline(lag[valid].median(), color='black', linestyle='--', label=f'Median: {lag[valid].median():g} days')
    axes[0].set(xlabel='Days from initial submission to latest observed revision', ylabel='Papers', title='Observed revision intervals')
    axes[0].legend()
    axes[1].boxplot([lag[valid & papers.worker.eq(w)] for w in data.WORKERS], tick_labels=data.WORKERS, showfliers=True)
    axes[1].set(ylabel='Days', title='Revision intervals by range')
    fig.suptitle(f'{valid.sum():,} valid revised papers; {(~valid).sum():,} absent/invalid intervals excluded; unequal observation windows')
    return fig
