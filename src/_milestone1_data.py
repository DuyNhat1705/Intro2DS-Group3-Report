"""Shared readers for notebook figures; no output images are written."""
from pathlib import Path
import json
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[1] / 'statistics_data'
WORKERS = ('R1', 'R2', 'R3', 'R4', 'R5')
GIB, MIB = 2**30, 2**20

def root(data_dir=None):
    return Path(data_dir) if data_dir is not None else DEFAULT_DATA_DIR

def exports(name, data_dir=None):
    frames = []
    for worker in WORKERS:
        frame = pd.read_csv(root(data_dir)/'report_exports'/worker/name, dtype={'arxiv_id': 'string'})
        frame['worker'] = worker
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)

def papers(data_dir=None):
    frame = exports('per_paper.csv', data_dir)
    if frame.arxiv_id.isna().any() or frame.arxiv_id.duplicated().any():
        raise ValueError('Expected nonmissing, globally unique paper IDs')
    counts = frame.groupby('worker').size()
    if not counts.eq(5000).all():
        warnings.warn(f'Expected 5,000 papers per range; found {counts.to_dict()}', stacklevel=2)
    frame['paper_success'] = frame.paper_success.astype(str).str.lower().eq('true')
    return frame

def records(name, data_dir=None):
    rows = []
    for worker in WORKERS:
        path = root(data_dir)/'run_logs'/worker/name
        with path.open(encoding='utf-8') as stream:
            for number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f'Invalid JSON at {path}:{number}') from exc
                rows.append({**row, 'worker': worker})
    return pd.DataFrame(rows)

def summaries(data_dir=None):
    return {w: json.loads((root(data_dir)/'report_exports'/w/'summary_stats.json').read_text(encoding='utf-8')) for w in WORKERS}

def parquet(name, columns, data_dir=None):
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise ImportError('Install the Parquet dependency: pip install pyarrow') from exc
    frames = []
    for worker in WORKERS:
        path = root(data_dir)/'tables'/worker/name
        schema = pq.read_schema(path).names
        if set(columns) - set(schema):
            raise ValueError(f'Unexpected schema in {path}: {schema}')
        frame = pd.read_parquet(path, columns=columns, engine='pyarrow')
        frame['worker'] = worker
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)

def paired_sizes(data_dir=None):
    frame = papers(data_dir)
    before, after = frame.size_full_bytes, frame.size_tex_bib_bytes
    valid = np.isfinite(before) & np.isfinite(after) & before.gt(0) & after.ge(0)
    result = frame.loc[valid].copy()
    result['reduction_pct'] = 100*(1-result.size_tex_bib_bytes/result.size_full_bytes)
    return result, int((~valid).sum())

def figure(title, ylabel=None, figsize=(10, 5)):
    fig, ax = plt.subplots(figsize=figsize, layout='constrained')
    ax.set_title(title)
    if ylabel:
        ax.set_ylabel(ylabel)
    return fig, ax

def annotate(ax, denominator=None):
    for container in ax.containers:
        labels = [f'{v:,.0f}' + (f'\n{100*v/denominator:.3f}%' if denominator else '') if v else '' for v in container.datavalues]
        ax.bar_label(container, labels=labels, padding=3, fontsize=9)
    ax.margins(y=.18)

def event_counts(data_dir=None):
    events = records('events.jsonl', data_dir)
    return pd.crosstab(events.worker, events.kind).reindex(WORKERS, fill_value=0)

def runs(data_dir=None):
    frame = exports('runs.csv', data_dir)
    if frame.duplicated(['worker', 'run_id']).any():
        raise ValueError('Duplicate (worker, run_id) sessions')
    return frame

def elapsed(frame):
    """Union of session intervals and calendar span, in seconds."""
    intervals = frame.loc[frame.end.ge(frame.start), ['start', 'end']].dropna().sort_values('start')
    if intervals.empty:
        return np.nan, np.nan
    total, left, right = 0., None, None
    for start, end in intervals.itertuples(index=False, name=None):
        if left is None:
            left, right = start, end
        elif start <= right:
            right = max(right, end)
        else:
            total += right-left
            left, right = start, end
    return total+right-left, intervals.end.max()-intervals.start.min()

def raw_memory(data_dir=None):
    for run in runs(data_dir).itertuples():
        path = root(data_dir)/'run_logs'/run.worker/f'monitor_{run.run_id}.csv'
        if not path.exists():
            warnings.warn(f'Missing raw memory samples: {path}', stacklevel=2)
            continue
        frame = pd.read_csv(path, usecols=['t', 'rss_bytes']).dropna().sort_values('t').drop_duplicates('t', keep='last')
        yield run, frame.loc[frame.t.between(run.start, run.end) & frame.rss_bytes.ge(0)]
