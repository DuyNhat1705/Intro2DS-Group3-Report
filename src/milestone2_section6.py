"""Section 6 charts and tables. Functions return Matplotlib figures or DataFrames.

No images are saved. Optional data_dir points to a statistics_parser directory.
Import with ``from src import milestone2_section6 as m2s6`` from the repo root.
"""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

try:
    from . import milestone2_data as data
except ImportError:
    import milestone2_data as data


def _parsing_outcome_counts(data_dir=None):
    """Include zero-count terminal outcomes and verify the expected inventory."""
    coverage = data.exports('version_coverage.csv', data_dir)
    statuses = data.exports('status_counts.csv', data_dir).groupby('status')['versions'].sum()
    statuses = statuses.reindex(
        ['ok', 'partial', 'empty', 'failed', 'missing', 'root_fallback'], fill_value=0,
    ).astype('int64')
    expected = int(coverage['n_versions'].sum())
    if int(statuses.sum()) != expected:
        raise ValueError('Parser status counts do not cover the expected version inventory.')
    return statuses


def parsing_outcomes_table(data_dir=None):
    """Section 6.1: terminal outcomes, with all expected versions as denominator."""
    counts = _parsing_outcome_counts(data_dir)
    # Root-fallback output is shown if it occurs in a selected export.
    shown = counts.drop('root_fallback') if counts['root_fallback'] == 0 else counts
    frame = shown.rename_axis('Status').rename('Versions').reset_index()
    frame['Share of expected versions'] = frame['Versions'] / counts.sum()
    return frame


def parsing_success_rates_table(data_dir=None):
    """Distinguish output generation, strict ok status, and end-to-end coverage."""
    counts = _parsing_outcome_counts(data_dir)
    produced = int(counts[['ok', 'partial', 'root_fallback']].sum())
    nonempty = produced + int(counts['failed'])
    rows = [
        ('Output generation among non-empty versions', produced, nonempty),
        ('Strict ok rate among non-empty versions', int(counts['ok']), nonempty),
        ('Output coverage among all expected versions', produced, int(counts.sum())),
    ]
    frame = pd.DataFrame(rows, columns=['Metric', 'Numerator', 'Denominator'])
    frame['Rate'] = frame['Numerator'] / frame['Denominator'].where(frame['Denominator'].ne(0))
    return frame


def parsing_outcomes_61(data_dir=None):
    """Version outcomes and overlapping partial-output diagnostics from exports."""
    outcomes = parsing_outcomes_table(data_dir)
    reasons = data.exports('failure_reasons.csv', data_dir)
    reasons = reasons.loc[reasons['status'].eq('partial')].sort_values('versions')
    partial_count = int(_parsing_outcome_counts(data_dir)['partial'])
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.3), layout='constrained')
    colors = {
        'ok': '#59A14F', 'partial': '#F28E2B', 'empty': '#9C9C9C',
        'failed': '#E15759', 'missing': '#B07AA1', 'root_fallback': '#76B7B2',
    }
    bars = axes[0].barh(
        outcomes['Status'], outcomes['Versions'],
        color=[colors[status] for status in outcomes['Status']],
    )
    axes[0].invert_yaxis()
    axes[0].set_xlim(0, max(1, outcomes['Versions'].max()) * 1.32)
    axes[0].set_title('Final parsing outcomes by version')
    axes[0].set_xlabel('Versions (all expected versions)')
    for bar, share in zip(bars, outcomes['Share of expected versions']):
        axes[0].annotate(
            f'{int(bar.get_width()):,} ({share:.2%})',
            (bar.get_width(), bar.get_y() + bar.get_height() / 2),
            xytext=(4, 0), textcoords='offset points', va='center', fontsize=9,
        )
    labels = reasons['reason'].str.replace('_', ' ', regex=False)
    bars = axes[1].barh(labels, reasons['versions'], color='#F28E2B')
    axes[1].set_xlim(0, max(1, reasons['versions'].max()) * 1.4)
    axes[1].set_title(f'Diagnostics among {partial_count:,} partial versions')
    axes[1].set_xlabel('Versions with each diagnostic (reasons can overlap)')
    for bar in bars:
        count = int(bar.get_width())
        share = f'{count / partial_count:.1%}' if partial_count else 'N/A'
        axes[1].annotate(
            f'{count:,} ({share})',
            (count, bar.get_y() + bar.get_height() / 2),
            xytext=(4, 0), textcoords='offset points', va='center', fontsize=9,
        )
    for ax in axes:
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda value, _: f'{value:,.0f}'))
        ax.grid(axis='x', alpha=0.2)
        ax.set_axisbelow(True)
    return fig


def publication_version_coverage_table(data_dir=None):
    """Complete per-publication inventory; preserve IDs and undefined input rates."""
    raw = data.exports('version_coverage.csv', data_dir, dtype={'arxiv_id': str})
    statuses = ['ok', 'root_fallback', 'partial', 'empty', 'missing', 'failed']
    if raw['arxiv_id'].duplicated().any():
        raise ValueError('The version inventory contains duplicate publication IDs.')
    if raw[statuses].lt(0).any().any() or raw['n_versions'].le(0).any():
        raise ValueError('Version counts must be nonnegative, with positive expected counts.')
    if not raw[statuses].sum(axis=1).eq(raw['n_versions']).all():
        raise ValueError('Version outcomes do not reconcile for every publication.')
    frame = raw.rename(columns={
        'arxiv_id': 'arXiv ID', 'n_versions': 'Expected versions',
        'ok': 'Ok', 'root_fallback': 'Root fallback', 'partial': 'Partial',
        'empty': 'Empty', 'missing': 'Missing', 'failed': 'Failed',
    })
    frame['Output versions'] = frame[['Ok', 'Root fallback', 'Partial']].sum(axis=1)
    frame['Versions with TeX'] = frame['Output versions'] + frame['Failed']
    frame['Output coverage'] = frame['Output versions'] / frame['Expected versions']
    denominator = frame['Versions with TeX'].where(frame['Versions with TeX'].ne(0))
    frame['Non-empty output rate'] = frame['Output versions'] / denominator
    return frame[[
        'arXiv ID', 'Expected versions', 'Versions with TeX', 'Ok', 'Partial',
        'Root fallback', 'Failed', 'Empty', 'Missing', 'Output versions',
        'Output coverage', 'Non-empty output rate',
    ]].sort_values('arXiv ID').reset_index(drop=True)


def publication_coverage_summary_table(data_dir=None):
    """Exclusive publication groups based on output over expected versions."""
    frame = publication_version_coverage_table(data_dir)
    coverage = frame['Output coverage']
    counts = [coverage.eq(1).sum(), coverage.between(0, 1, inclusive='neither').sum(), coverage.eq(0).sum()]
    result = pd.DataFrame({
        'Coverage group': ['All expected versions', 'Some expected versions', 'No output versions'],
        'Publications': counts,
    })
    result['Share'] = result['Publications'] / len(frame)
    return result


def publication_version_coverage_62(data_dir=None):
    """Publication coverage groups and their shares by expected version count."""
    frame = publication_version_coverage_table(data_dir)
    summary = publication_coverage_summary_table(data_dir)
    colors = ['#59A14F', '#F28E2B', '#9C9C9C']
    coverage = frame['Output coverage']
    groups = np.select(
        [coverage.eq(1), coverage.gt(0)], summary['Coverage group'].iloc[:2],
        default=summary['Coverage group'].iloc[2],
    )
    grouped = pd.crosstab(frame['Expected versions'], groups).reindex(
        columns=summary['Coverage group'], fill_value=0,
    )
    totals = grouped.sum(axis=1)
    percentages = grouped.div(totals, axis=0) * 100
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8), layout='constrained')
    bars = axes[0].barh(summary['Coverage group'], summary['Publications'], color=colors)
    axes[0].invert_yaxis()
    axes[0].set_xlim(0, max(1, summary['Publications'].max()) * 1.35)
    axes[0].set_xlabel('Publications')
    axes[0].set_title('Output coverage of expected versions')
    for bar, share in zip(bars, summary['Share']):
        axes[0].annotate(
            f'{int(bar.get_width()):,} ({share:.2%})',
            (bar.get_width(), bar.get_y() + bar.get_height() / 2),
            xytext=(4, 0), textcoords='offset points', va='center', fontsize=9,
        )
    bottom = np.zeros(len(grouped))
    for label, color in zip(summary['Coverage group'], colors):
        axes[1].bar(grouped.index, percentages[label], bottom=bottom, color=color, label=label)
        bottom += percentages[label].to_numpy()
    axes[1].set_xticks(grouped.index)
    axes[1].set_ylim(0, 116)
    axes[1].set_yticks(range(0, 101, 20))
    axes[1].set_xlabel('Expected versions per publication')
    axes[1].set_ylabel('Publications within each group (%)')
    axes[1].set_title('Coverage by revision count')
    axes[1].legend(loc='lower left', fontsize=8)
    for version_count, count in totals.items():
        axes[1].text(version_count, 103, f'n={count:,}', ha='center', fontsize=8)
    axes[0].xaxis.set_major_formatter(plt.FuncFormatter(lambda value, _: f'{value:,.0f}'))
    for ax in axes:
        ax.grid(axis='y' if ax is axes[1] else 'x', alpha=0.2)
        ax.set_axisbelow(True)
    return fig


def publication_coverage_inventory(frame=None, data_dir=None, page_size=25):
    """Self-contained searchable HTML table; all records are embedded, not sampled."""
    import json
    from uuid import uuid4
    from IPython.display import HTML

    if page_size < 1:
        raise ValueError('page_size must be positive')
    if frame is None:
        frame = publication_version_coverage_table(data_dir)
    rate_columns = ['Output coverage', 'Non-empty output rate']
    rate_indices = [frame.columns.get_loc(column) for column in rate_columns]
    records = frame.astype(object).where(pd.notna(frame), None).values.tolist()
    payload = json.dumps(records, ensure_ascii=False, allow_nan=False, separators=(',', ':'))
    # Escape markup delimiters so data cannot terminate the script element.
    payload = payload.replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    preview = frame.head(page_size).to_html(
        index=False, border=0, na_rep='N/A', classes='coverage-table',
        formatters={column: lambda value: f'{value:.2%}' for column in rate_columns},
    )
    template = r'''
<div id="__ROOT__" class="coverage-inventory">
  <style>
    #__ROOT__ {font: 14px sans-serif; margin: 1em 0;}
    #__ROOT__ .controls {display:flex; flex-wrap:wrap; gap:12px; align-items:center; margin:10px 0;}
    #__ROOT__ .scroll {overflow-x:auto; max-height:620px; overflow-y:auto;}
    #__ROOT__ table {border-collapse:collapse; width:100%; white-space:nowrap;}
    #__ROOT__ th, #__ROOT__ td {padding:7px 10px; border-bottom:1px solid #ddd; text-align:right;}
    #__ROOT__ th {position:sticky; top:0; background:#f2f4f6; color:#222;}
    #__ROOT__ th:first-child, #__ROOT__ td:first-child {text-align:left;}
  </style>
  <p><strong>Complete publication version inventory: __COUNT__ publications.</strong>
  Output coverage = output versions / expected versions. N/A means there is no non-empty input denominator.</p>
  <div class="controls">
    <label>arXiv ID <input class="search" type="search" placeholder="Search by arXiv ID"></label>
    <label>Coverage <select class="filter"><option value="all">All publications</option>
      <option value="full">All expected versions</option><option value="some">Some expected versions</option>
      <option value="none">No output versions</option></select></label>
    <button class="download" type="button">Download all rows (CSV)</button>
  </div>
  <div class="scroll">__PREVIEW__</div>
  <div class="controls"><button class="previous" type="button">Previous</button>
    <span class="page-status"></span><button class="next" type="button">Next</button></div>
  <noscript>Pagination requires JavaScript. All rows are also available in the publication_coverage DataFrame.</noscript>
</div>
<script>
(() => {
  const root = document.getElementById('__ROOT__');
  const rows = __DATA__;
  const columns = __COLUMNS__;
  const rates = new Set(__RATES__);
  const coverageIndex = columns.indexOf('Output coverage');
  const size = __PAGE_SIZE__;
  let selected = rows, page = 0;
  const query = root.querySelector('.search'), filter = root.querySelector('.filter');
  const previous = root.querySelector('.previous'), next = root.querySelector('.next');
  const format = (value, index) => value === null ? 'N/A' : rates.has(index)
    ? (value * 100).toFixed(2) + '%' : typeof value === 'number' ? value.toLocaleString('en-US') : value;
  function render() {
    const pages = Math.max(1, Math.ceil(selected.length / size));
    page = Math.max(0, Math.min(page, pages - 1));
    const body = root.querySelector('tbody');
    body.replaceChildren();
    for (const row of selected.slice(page * size, (page + 1) * size)) {
      const tr = document.createElement('tr');
      row.forEach((value, index) => {
        const td = document.createElement('td');
        td.textContent = format(value, index); tr.appendChild(td);
      });
      body.appendChild(tr);
    }
    root.querySelector('.page-status').textContent = selected.length
      ? `${page * size + 1}-${Math.min((page + 1) * size, selected.length)} of ${selected.length.toLocaleString('en-US')} publications (page ${page + 1}/${pages})`
      : 'No matching publications';
    previous.disabled = page === 0; next.disabled = page >= pages - 1;
  }
  function applyFilter() {
    const term = query.value.trim().toLowerCase(), group = filter.value;
    selected = rows.filter(row => String(row[0]).toLowerCase().includes(term) &&
      (group === 'all' || group === 'full' && row[coverageIndex] === 1 ||
       group === 'some' && row[coverageIndex] > 0 && row[coverageIndex] < 1 ||
       group === 'none' && row[coverageIndex] === 0));
    page = 0; render();
  }
  query.addEventListener('input', applyFilter); filter.addEventListener('change', applyFilter);
  previous.addEventListener('click', () => {page--; render();});
  next.addEventListener('click', () => {page++; render();});
  root.querySelector('.download').addEventListener('click', () => {
    const quote = value => '"' + String(value).replaceAll('"', '""') + '"';
    const csv = [columns.map(quote).join(','), ...rows.map(row => row.map((value, index) => quote(format(value, index))).join(','))].join('\r\n');
    const url = URL.createObjectURL(new Blob(['\ufeff', csv], {type:'text/csv;charset=utf-8'}));
    const link = document.createElement('a'); link.href = url; link.download = 'publication_version_coverage.csv';
    link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  render();
})();
</script>'''
    return HTML(template.replace('__ROOT__', 'coverage-' + uuid4().hex)
                .replace('__COUNT__', f'{len(frame):,}')
                .replace('__PREVIEW__', preview)
                .replace('__DATA__', payload)
                .replace('__COLUMNS__', json.dumps(frame.columns.tolist()))
                .replace('__RATES__', json.dumps([int(index) for index in rate_indices]))
                .replace('__PAGE_SIZE__', str(page_size)))


def element_kind_statistics_table(data_dir=None):
    """Distinct stored elements by kind; shares include every exported kind."""
    frame = data.exports('kind_counts.csv', data_dir).sort_values(
        'elements', ascending=False,
    ).rename(columns={'kind': 'Kind', 'elements': 'Stored elements'})
    frame['Share'] = frame['Stored elements'] / frame['Stored elements'].sum()
    return frame.reset_index(drop=True)


def cleaned_elements_by_kind_63(data_dir=None):
    """Figure 6.1(a): all element kinds after cross-version deduplication."""
    kinds = element_kind_statistics_table(data_dir).iloc[::-1]
    fig, ax = plt.subplots(figsize=(11, 6.4), layout='constrained')
    bars = ax.barh(kinds['Kind'], kinds['Stored elements'], color='#2c3e50')
    ax.set_xscale('log')
    ax.set_xlim(right=kinds['Stored elements'].max() * 14)
    ax.set_xlabel('Distinct stored elements (log scale)')
    ax.set_title('Figure 6.1(a): Stored elements by kind')
    ax.grid(axis='x', alpha=0.2)
    ax.set_axisbelow(True)
    for bar, share in zip(bars, kinds['Share']):
        share_label = f'{share:.2%}' if share >= 0.0001 else '<0.01%'
        ax.annotate(
            f'{int(bar.get_width()):,} ({share_label})',
            (bar.get_width(), bar.get_y() + bar.get_height() / 2),
            xytext=(5, 0), textcoords='offset points', va='center', fontsize=8,
        )
    return fig


def hierarchy_depth_63(data_dir=None):
    """Figure 6.1(b): each nonempty version contributes one maximum tree depth."""
    versions = data.parse_status(data_dir)
    trees = versions.loc[versions['n_nodes'].gt(0)]
    depths = trees['max_depth'].value_counts().sort_index()
    depths = depths.reindex(range(0, int(depths.index.max()) + 1), fill_value=0)
    fig, ax = plt.subplots(figsize=(11, 4.6), layout='constrained')
    bars = ax.bar(depths.index, depths.values, color='#2980b9')
    ax.set_ylim(0, depths.max() * 1.2)
    ax.set_xticks(depths.index)
    ax.set_xlabel('Maximum depth of a version tree (document root = 0)')
    ax.set_ylabel('Versions')
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda value, _: f'{value:,.0f}'))
    ax.set_title('Figure 6.1(b): Maximum hierarchy depth per version')
    ax.text(
        0.98, 0.96,
        f'{len(trees):,} versions with a tree\n'
        f'{versions["n_nodes"].eq(0).sum():,} empty versions excluded',
        transform=ax.transAxes, ha='right', va='top', fontsize=9,
    )
    ax.grid(axis='y', alpha=0.2)
    ax.set_axisbelow(True)
    for bar in bars:
        count = int(bar.get_height())
        if count:
            ax.annotate(
                f'{count:,}', (bar.get_x() + bar.get_width() / 2, count),
                xytext=(0, 4), textcoords='offset points',
                ha='center', fontsize=8,
            )
    return fig


def hierarchy_size_statistics_table(data_dir=None):
    """Sizes include zero-output papers/versions; nodes count document roots."""
    papers = data.exports('paper_dedup.csv', data_dir)
    versions = data.parse_status(data_dir)
    rows = []
    for scope, values in [
        ('Nodes per publication (all versions, before dedup)', papers['nodes_before']),
        ('Stored elements per publication (after dedup)', papers['elements_after']),
        ('Nodes per expected version (before dedup)', versions['n_nodes']),
    ]:
        rows.append({
            'Population': scope,
            'Records': len(values),
            'Zero output': int(values.eq(0).sum()),
            'Mean': values.mean(),
            'Median': values.median(),
            '95th percentile': values.quantile(0.95),
            'Maximum': int(values.max()),
        })
    return pd.DataFrame(rows)


def element_counts_per_paper_version_63(data_dir=None):
    """Figure 6.1(c): overlapping publication counts, plus per-version sizes."""
    papers = data.exports('paper_dedup.csv', data_dir)
    versions = data.parse_status(data_dir)
    fig, axes = plt.subplots(1, 2, figsize=(14, 5), layout='constrained')

    before = papers.loc[papers['nodes_before'].gt(0), 'nodes_before']
    after = papers.loc[papers['elements_after'].gt(0), 'elements_after']
    values = np.concatenate([before.to_numpy(), after.to_numpy()])
    lo, hi = values.min(), values.max()
    if lo == hi:
        lo, hi = lo / 10, hi * 10
    bins = np.geomspace(lo, hi, 35)
    axes[0].hist(
        before, bins=bins, alpha=0.6, color='#F28E2B',
        label='Node occurrences before dedup',
    )
    axes[0].hist(
        after, bins=bins, alpha=0.6, color='#4E79A7',
        label='Stored elements after dedup',
    )
    axes[0].set_title('Publication counts before and after deduplication')
    axes[0].set_xlabel('Elements/node occurrences per publication (log scale)')
    axes[0].set_ylabel('Publications')
    axes[0].legend(loc='upper right', fontsize=8)
    axes[0].text(
        0.03, 0.96,
        f'{len(before):,} positive before / {len(after):,} positive after\n'
        f'{papers["nodes_before"].eq(0).sum():,} zero before / '
        f'{papers["elements_after"].eq(0).sum():,} zero after omitted',
        transform=axes[0].transAxes, va='top', fontsize=8,
    )

    node_counts = versions['n_nodes']
    positive = node_counts[node_counts.gt(0)]
    version_bins = np.geomspace(
        positive.min(), max(positive.max(), positive.min() + 1), 35,
    )
    axes[1].hist(positive, bins=version_bins, color='#4E79A7', edgecolor='white')
    axes[1].set_title('Nodes per version before dedup')
    axes[1].set_xlabel('Node occurrences per version (log scale)')
    axes[1].set_ylabel('Versions')
    axes[1].text(
        0.03, 0.96,
        f'{len(positive):,} positive outputs\n'
        f'{node_counts.eq(0).sum():,} zero outputs omitted',
        transform=axes[1].transAxes, va='top', fontsize=9,
    )
    for ax in axes:
        ax.set_xscale('log')
        ax.grid(alpha=0.3)
        ax.set_axisbelow(True)
    fig.suptitle('Figure 6.1(c): Publication and version size distributions')
    return fig


def deduplication_results_table(data_dir=None):
    """Section 6.4: corpus counts and reductions from the parser's dedup export."""
    counts = data.dedup_counts(data_dir)
    frame = pd.DataFrame([
        {
            'Data': 'Content nodes / stored elements',
            'Before': counts['nodes_before'],
            'After': counts['elements_after'],
        },
        {
            'Data': 'Cited bibliography entries',
            'Before': counts['bib_cited_before_dedup'],
            'After': counts['bib_after'],
        },
    ])
    frame['Removed'] = frame['Before'] - frame['After']
    frame['Reduction'] = 1 - frame['After'] / frame['Before'].where(frame['Before'].ne(0))
    return frame


def cleaned_elements_by_kind_65(data_dir=None):
    """Figure 6.1: the six most common kinds, with shares of all stored elements."""
    kinds = data.exports('kind_counts.csv', data_dir).sort_values(
        by='elements', ascending=False
    )
    top_kinds = kinds.head(6)
    fig, ax = plt.subplots(figsize=(10, 4.2))
    bars = ax.barh(
        top_kinds['kind'][::-1], top_kinds['elements'][::-1],
        color='#2c3e50', height=0.55,
    )
    ax.set_title(
        'Figure 6.1: Distribution of Cleaned Elements by Structural Kind',
        fontsize=11, fontweight='bold', pad=12,
    )
    ax.set_xlabel('Number of Elements (Millions)', fontsize=10)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x*1e-6:.1f}M'))
    for bar in bars:
        width = bar.get_width()
        share = width / kinds['elements'].sum() * 100
        ax.text(
            width + 1e5, bar.get_y() + bar.get_height()/2,
            f'{width*1e-6:.2f}M ({share:.1f}%)',
            va='center', ha='left', fontsize=8.5, color='#333333',
        )
    fig.tight_layout()
    return fig


def cross_version_deduplication_65(data_dir=None):
    """Figure 6.2: counts and reduction rates computed from deduplication exports."""
    counts = data.dedup_counts(data_dir)
    categories = [
        'Full-text Content Elements\n(Nodes → Cleaned Elements)',
        'Cited Bibliographic Entries\n(Before → After Dedup)',
    ]
    before = [counts['nodes_before'], counts['bib_cited_before_dedup']]
    after = [counts['elements_after'], counts['bib_after']]
    x = [0, 1]
    width = 0.35
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.bar(
        [i - width/2 for i in x], before, width,
        label='Before Dedup', color='#7f8c8d',
    )
    ax.bar(
        [i + width/2 for i in x], after, width,
        label='After Dedup', color='#27ae60',
    )
    ax.set_title(
        'Figure 6.2: Cross-Version Deduplication Compression Impact',
        fontsize=11, fontweight='bold', pad=12,
    )
    ax.set_xticks(x)
    ax.set_xticklabels(categories, fontsize=9.5)
    ax.set_ylabel('Count', fontsize=10)
    ax.legend(frameon=True, facecolor='#f8f9fa')
    ax.yaxis.set_major_formatter(plt.FuncFormatter(
        lambda y, p: f'{y*1e-6:.1f}M' if y >= 1e6 else f'{int(y):,}'
    ))
    fig.tight_layout()
    return fig


def reference_ingestion_65(data_dir=None):
    """Figure 6.3: ingestion methods and top six types; shares use all entries."""
    methods = data.exports('bib_methods.csv', data_dir)
    types = data.exports('entry_types.csv', data_dir).sort_values(
        by='entries', ascending=False
    )
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4.2))
    colors = ['#1f77b4', '#2ca02c', '#9467bd', '#d62728']
    bars1 = ax1.bar(methods['parse_method'], methods['entries'], color=colors, width=0.5)
    ax1.set_title('Reference Ingestion by Method', fontsize=11, fontweight='bold', pad=12)
    ax1.set_ylabel('Extracted Entries (Log Scale)', fontsize=10)
    ax1.set_yscale('log')
    top_types = types.head(6)
    bars2 = ax2.bar(top_types['entry_type'], top_types['entries'], color='#2980b9', width=0.5)
    ax2.set_title('Top 6 Bibliographic Entry Types', fontsize=11, fontweight='bold', pad=12)
    ax2.set_ylabel('Entries (Log Scale)', fontsize=10)
    ax2.set_yscale('log')
    for ax, bars, total in [
        (ax1, bars1, methods['entries'].sum()),
        (ax2, bars2, types['entries'].sum()),
    ]:
        for bar in bars:
            count = bar.get_height()
            share = count / total * 100
            ax.text(
                bar.get_x() + bar.get_width()/2, count * 1.2,
                f'{int(count):,}\n({share:.1f}%)',
                ha='center', va='bottom', fontsize=8.5,
            )
    fig.suptitle(
        'Figure 6.3: Bibliographic Ingestion Breakdown and Entry Taxonomy',
        fontsize=12, fontweight='bold', y=1.03,
    )
    fig.tight_layout()
    return fig
