"""Shared readers for the Milestone 2 report; no output images are written.

All inputs come from ``statistics_parser/`` in this repository (the exports of the
parser run over the whole corpus, R1-R5). Optional ``data_dir`` points to another
directory with the same layout.
"""
from pathlib import Path
import re

import pandas as pd
import matplotlib.pyplot as plt

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[1] / 'statistics_parser'
SCOPE = 'all'


def root(data_dir=None):
    return Path(data_dir) if data_dir is not None else DEFAULT_DATA_DIR


def parse_status(columns=None, data_dir=None):
    """One row per (paper, version): status, gathering counts, timings and notes."""
    path = root(data_dir) / '.state' / SCOPE / 'parse_status'
    files = sorted(path.glob('*.parquet'))
    if not files:
        raise FileNotFoundError(f'No parse_status shards in {path}')
    frame = pd.concat([pd.read_parquet(f, columns=columns, engine='pyarrow') for f in files],
                      ignore_index=True)
    if {'arxiv_id', 'version'} <= set(frame.columns) and frame.duplicated(['arxiv_id', 'version']).any():
        raise ValueError('Expected one parse_status row per (arxiv_id, version)')
    return frame


def export_json(name, data_dir=None):
    """A JSON file of ``report_exports/all`` (summary, validation, benchmark, ...)."""
    import json
    path = root(data_dir) / 'report_exports' / SCOPE / name
    return json.loads(path.read_text(encoding='utf-8'))


def export_csv(name, data_dir=None):
    """A CSV file of ``report_exports/all``; arXiv IDs stay strings."""
    return pd.read_csv(root(data_dir) / 'report_exports' / SCOPE / name, dtype={'arxiv_id': 'string'})


def has_token(values, key):
    """True where a ``;``-joined field (notes, failure_reason) contains ``key`` or ``key:...``."""
    pattern = rf'(?:^|;){re.escape(key)}(?::|;|$)'
    return values.fillna('').astype(str).str.contains(pattern, regex=True)


def figure(title, ylabel=None, figsize=(10, 5)):
    fig, ax = plt.subplots(figsize=figsize, layout='constrained')
    ax.set_title(title)
    if ylabel:
        ax.set_ylabel(ylabel)
    return fig, ax


def annotate(ax, denominator=None):
    for container in ax.containers:
        labels = [f'{v:,.0f}' + (f'\n{100*v/denominator:.1f}%' if denominator else '') if v else ''
                  for v in container.datavalues]
        ax.bar_label(container, labels=labels, padding=3, fontsize=9)
    ax.margins(y=.18)
