# Intro2DS-Group3-Report

> **Course**: CSC14119 - Introduction to Data Science  
> **Group**: Group 3  

---

## Milestone 1: Statistics outputs

Milestone 1 collects arXiv paper metadata, source-processing results, reference
records, and performance measurements for **25,000 target IDs** across five
ranges, `R1`–`R5` (5,000 IDs per range). The files in `statistics_data/` support
the data statistics and performance evaluation in [Reports/Report.ipynb](Reports/Report.ipynb).
These are statistics and metadata outputs; they are not the complete downloaded
paper-source corpus.

```text
statistics_data/
├── report_exports/    # CSV/JSON reporting data, under R1/ through R5/
├── tables/            # Detailed Parquet tables, under R1/ through R5/
├── run_logs/          # Run logs and raw resource samples, under R1/ through R5/
└── .state/            # Per-range scraper progress and source-processing state
```

### `report_exports/` · Reporting data

| File | Contents and uses |
|---|---|
| `per_paper.csv` | One row per target ID. Includes the range, metadata/source/reference statuses, version and reference counts, file sizes before and after filtering, time spent on each stage, and the `paper_success` flag. Use it to calculate success rates and plot distributions across the full dataset. |
| `summary_stats.json` | Summary for the exported scope. Includes the number of target IDs, papers found and successfully processed, success rates, the distribution of version counts, reference statistics, storage, processing time, and memory usage. Also records the configuration and export time. |
| `range_stats.csv` | One row per range, with metrics such as the number of successfully processed papers, version counts, success rates, average file sizes, and average reference counts. Use it to compare R1–R5. |
| `ranges.csv` | Defines each range by its label, month in `YYMM` format, and first and last ID numbers. |
| `category_counts.csv` | Counts papers by primary category, defined as the first category listed in each paper's metadata. |
| `runs.csv` | One row per run, with the worker, start and end times, duration, stop reason, amount of work remaining at the start, machine details, and peak memory usage when available. |
| `monitor.csv` | Memory usage of the scraper process and its child processes, measured as resident set size (RSS). Reports the mean and maximum per minute for each worker and run. This file is exported when samples are available. |
| `disk.csv` | Size of the `data/` directory at each measurement and the number of seconds spent scanning it. |
| `README.md` | Describes the exported files and their main columns. |

### `tables/` · Detailed Parquet tables

| File | Contents and uses |
|---|---|
| `papers.parquet` | Metadata read for the collected papers, including arXiv ID, title, authors, submission date, revision dates, and publication venue. |
| `references_all.parquet` | All collected references, including those without an arXiv ID. Each row links a citing paper to a reference and includes the reference's metadata. |
| `references.parquet` | References with an arXiv ID, deduplicated by citing and cited paper ID. Use this table to analyze citation links between arXiv papers. |

### `run_logs/` · Logs and raw measurements

| File | Contents and uses |
|---|---|
| `runs.jsonl` | A start record for each run and an end record if the scraper had time to write it. Includes configuration, remaining work, duration, stop reason, result counts by status, and arXiv retry counts. |
| `timings.jsonl` | Start time, end time, duration, and status for each ID at the `metadata`, `source`, and `refs` stages. For metadata and reference batches, the batch duration is divided evenly among its IDs. |
| `events.jsonl` | Events such as batch failures, pauses before retrying (`cooldown`), and collection lanes stopping early. |
| `scraper.log` | Text log from the scraper modules, with timestamps, log levels, and detailed messages for troubleshooting. |
| `monitor_<run_id>.csv` | Raw memory samples for one run, including the timestamp, RSS in bytes, and the active phase. |
| `disk_<run_id>.csv` | Raw size measurements for `data/` during one run, including the timestamp, total bytes, and scan duration. |

### `.state/` · Progress for resuming the scraper

| File | Contents and uses |
|---|---|
| `source_state.json` | Source download progress by ID and version, including the status of each version and whether the paper is complete. May include the sizes of the archive, extracted files, and retained `.tex`/`.bib` files. |
| `nb_status.jsonl` | The `metadata` and `source` statuses recorded by the notebook for each ID. When there are multiple records for the same ID and stage, the notebook uses the last one it reads. |
| `refs_done.jsonl` | Reference retrieval status for each ID, such as `ok`, `no_refs`, or `not_found`, plus the reference count when available. The individual references are in the Parquet tables. |

Each `.jsonl` file stores one JSON record per line.

### Combining results for the 25,000-ID report

1. Append the rows from the five `per_paper.csv` files, preserving arXiv IDs as strings (including leading zeroes). Verify that each range has 5,000 rows and that the combined table contains 25,000 unique arXiv IDs.
2. Calculate success rates, medians, and 95th percentiles from the combined rows rather than averaging the five range summaries. The `paper_success` flag indicates that both `metadata` and `source` have status `done`. Reference retrieval outcomes are recorded separately in `refs`. Report the number of target IDs and the number of successfully processed papers separately.
3. Append the rows from the `range_stats.csv` files to compare the five ranges. Sum `n_papers` by `primary_category` across the `category_counts.csv` files to plot the number of papers by category.
4. For performance reporting, append the rows from the corresponding `runs.csv`, `monitor.csv`, and `disk.csv` files. Keep `worker` and `run_id` to distinguish workers and runs. If each worker measured its own data directory, the `disk.csv` samples describe that worker's directory at the time of measurement.
5. If Jupyter Book needs a single `summary_stats.json`, generate it from the combined data and retain the original per-range summaries.

The exported CSVs provide the data for these charts. Keep each `.state/Rx/` directory separate so the scraper can restore its progress. To measure the size of the full corpus directly, measure the combined data directory.

### Interpreting sizes and performance

Retained source sizes measure `.tex`/`.bib` content. The difference between
extracted and retained sizes includes other removed files, so it does not measure
image bytes alone. Use consistent units: MiB = bytes / 2^20 and GiB = bytes / 2^30.

Paper-attributed stage times, summed session durations, and elapsed collection
time have different scopes. Retries are additional attempts, not additional
papers. For attempted-work totals, sum the `duration` field once per timing
record; metadata/reference batch durations are already divided among their IDs.

Memory and disk values are sampled measurements. Missing samples are not zero,
periodic scans can miss brief peaks, and individual worker peaks should not be
summed into a simultaneous peak. Calculate time-weighted RSS within sessions,
without bridging gaps between runs.

### Notebook charts and tables

Notebook visualizations are implemented in
[src/milestone1_section3.py](src/milestone1_section3.py) and
[src/milestone1_section4.py](src/milestone1_section4.py). Chart functions return
Matplotlib figures, while table functions return pandas DataFrames; no image files
are saved. They locate `statistics_data/` automatically, or accept a custom
`data_dir`. Reading the Parquet tables requires `pyarrow`.
