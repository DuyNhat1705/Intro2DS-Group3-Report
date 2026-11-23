"""Shared readers for Milestone 2 reporting exports."""
import json
from pathlib import Path

import pandas as pd


DEFAULT_DATA_DIR = Path(__file__).resolve().parents[1] / 'statistics_parser'


def root(data_dir=None):
    """Return the statistics_parser directory, independent of the working directory."""
    return Path(data_dir) if data_dir is not None else DEFAULT_DATA_DIR


def exports(name, data_dir=None, **read_csv_kwargs):
    """Read a CSV from report_exports/all under the selected data directory."""
    return pd.read_csv(root(data_dir) / 'report_exports' / 'all' / name, **read_csv_kwargs)


def dedup_counts(data_dir=None):
    path = root(data_dir) / 'report_exports' / 'all' / 'dedup_counts.json'
    return json.loads(path.read_text(encoding='utf-8'))


def benchmark(data_dir=None):
    """Read the run summary and outer notebook timing measurements."""
    path = root(data_dir) / 'report_exports' / 'all' / 'benchmark.json'
    return json.loads(path.read_text(encoding='utf-8'))


def parse_status(data_dir=None):
    """Read the compacted per-version inventory, including empty versions."""
    directory = root(data_dir) / '.state' / 'all' / 'parse_status'
    files = sorted(directory.glob('*.parquet'))
    if not files:
        raise FileNotFoundError(f'No parser status shards found in {directory}')
    columns = ['arxiv_id', 'version', 'status', 'n_nodes', 'max_depth']
    return pd.concat(
        [pd.read_parquet(path, columns=columns) for path in files],
        ignore_index=True,
    )
