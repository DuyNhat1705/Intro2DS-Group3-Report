"""Section 3 (cleanup and standardization) tables and charts. Functions return Figure or DataFrame.

Import with ``from src import milestone2_section3 as m2s3`` from the repo root.
"""
import re

import pandas as pd
import matplotlib.pyplot as plt
try:
    from . import _milestone2_data as data
except ImportError:
    import _milestone2_data as data

_FIDELITY_BINS = [-0.1, 50, 80, 90, 95, 99, 99.999, 100]
_FIDELITY_LABELS = ['<50', '50-80', '80-90', '90-95', '95-99', '99-<100', '100']


def cleanup_checks_table(data_dir=None):
    """Residual LaTeX and stray dimensions over all sentences, and abstract/title fidelity.

    Fidelity is computed by the parser's validator for the latest parsed version of each
    paper: ``rapidfuzz.token_set_ratio`` between the parsed text and the Milestone 1
    ``metadata.json`` text, after removing math, commands, accents, case and punctuation.
    """
    v = data.export_json('validation.json', data_dir)
    fid = data.export_csv('fidelity.csv', data_dir)
    sentences = int(v['sentences'])
    residual = round(v['residual_latex_rate'] * sentences)
    found = fid.has_abstract.astype(str).str.lower().eq('true')
    abstract = fid.abstract_fidelity.dropna()
    title = fid.title_fidelity.dropna()
    dimensions, scanned = stray_dimensions(data_dir)
    if scanned != sentences:
        raise ValueError(f'Element tables hold {scanned:,} sentences, validation.json {sentences:,}')
    rows = [
        ('Sentences with a LaTeX command left outside $...$, \\cite and \\ref', residual,
         'Distinct sentences', sentences),
        ('Sentences with a TeX dimension (2pt, 0.5em, ...) left outside $...$', dimensions,
         'Distinct sentences', sentences),
        ('Papers whose abstract was found in the parsed tree', int(found.sum()),
         'Papers with a parsed latest version', len(fid)),
        ('Abstract fidelity of at least 90', int(abstract.ge(90).sum()), 'Abstracts compared', len(abstract)),
        ('Abstract fidelity of at least 99', int(abstract.ge(99).sum()), 'Abstracts compared', len(abstract)),
        ('Title fidelity of at least 90', int(title.ge(90).sum()), 'Titles compared', len(title)),
        ('Title fidelity of at least 99', int(title.ge(99).sum()), 'Titles compared', len(title)),
    ]
    table = pd.DataFrame(rows, columns=['Check', 'Count', 'Base', 'Base size'])
    table['Share of base (%)'] = table.Count / table['Base size'] * 100
    return table


def fidelity_31(data_dir=None):
    """Distribution of abstract and title fidelity scores (0-100)."""
    fid = data.export_csv('fidelity.csv', data_dir)
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), layout='constrained')
    for ax, column, name, color in [(axes[0], 'abstract_fidelity', 'Abstract', '#3b6ea5'),
                                    (axes[1], 'title_fidelity', 'Title', '#5b8c5a')]:
        scores = fid[column].dropna()
        counts = (pd.cut(scores, _FIDELITY_BINS, labels=_FIDELITY_LABELS)
                  .value_counts().reindex(_FIDELITY_LABELS, fill_value=0))
        ax.bar(counts.index.astype(str), counts.to_numpy(), color=color)
        ax.set(title=f'{name} fidelity (median {scores.median():.1f}, n = {len(scores):,})',
               xlabel='Fidelity score', ylabel='Papers')
        data.annotate(ax, len(scores))
    fig.suptitle('Figure 3.1. Parsed abstract and title against the arXiv metadata, latest version of each paper')
    return fig


_MATH_SPAN_RE = re.compile(r'(?<!\\)\$[^$]*?(?<!\\)\$')
_CITEREF_RE = re.compile(r'\\(?:cite|ref)\{[^}]*\}')
_COMMAND_RE = re.compile(r'\\[a-zA-Z]+')

# A TeX dimension left in prose after its command was removed (``\vskip 2pt`` -> ``2pt``,
# ``\parskip=0pt`` -> ``=0pt``): a number glued to a TeX-only unit, not part of a word.
_DIMENSION_COARSE = r'[0-9.](?:pt|em|ex|bp)'
_DIMENSION_RE = re.compile(r'(?<![\w.])=?[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:pt|em|ex|bp)(?![A-Za-z])')


def _has_stray_dimension(sentence):
    rest = _CITEREF_RE.sub(' ', _MATH_SPAN_RE.sub(' ', sentence))
    return _DIMENSION_RE.search(rest) is not None


def stray_dimensions(data_dir=None):
    """Distinct sentences that still hold a TeX dimension outside math, and their total.

    Reads only ``kind`` and ``content`` of ``tables/R*/elements``. A fast RE2 filter keeps the
    candidates, and the exact rule (math and citations removed first) runs on those only.
    The rule can also match a dimension written as prose, e.g. "a 10pt font", so the count is
    approximate.
    """
    import pyarrow.compute as pc
    import pyarrow.parquet as pq

    files = sorted((data.root(data_dir) / 'tables').glob('R*/elements/*.parquet'))
    if not files:
        raise FileNotFoundError('No element tables under statistics_parser/tables')
    sentences = hits = 0
    for path in files:
        table = pq.read_table(path, columns=['kind', 'content'])
        table = table.filter(pc.equal(table['kind'].cast('string'), 'sentence'))
        sentences += table.num_rows
        candidates = table.filter(pc.match_substring_regex(table['content'], _DIMENSION_COARSE))
        hits += sum(_has_stray_dimension(s) for s in candidates['content'].to_pylist() if s)
    return hits, sentences


def _leftover_command(sentence):
    """The first control word outside $...$, \\cite and \\ref (the validator's own rule)."""
    rest = _CITEREF_RE.sub(' ', _MATH_SPAN_RE.sub(' ', sentence))
    match = _COMMAND_RE.search(rest)
    return match.group() if match else None


def residual_examples_table(width=170, data_dir=None):
    """A varied sample of the sentences the validator flagged for residual LaTeX.

    The validator keeps the first 30 flagged sentences, cut to 200 characters, so the
    examples show kinds of failure, not their frequency. Re-applying the rule to the cut
    text only serves to pick sentences that differ; it is not a reliable diagnosis.
    """
    examples = data.export_json('validation.json', data_dir)['examples']['residual_examples']
    rows, seen = [], set()
    for text in examples:
        command = _leftover_command(text)
        if command is None or command in seen:
            continue
        seen.add(command)
        rows.append({'Flagged sentence (cut by the validator)':
                     text[:width] + ('...' if len(text) > width else '')})
    return pd.DataFrame(rows)
