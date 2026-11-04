# Data sources and Python chart plan for `Contents.md`

This document maps every section in `Contents.md` to the data available in `statistics_data/`, the calculations needed for writing, and charts that can be drawn in Python. It follows `statistics_data_desc.md` and checks the actual CSV columns, summary files, and representative raw log/state records. It is a writing and visualization plan; it does not generate the charts.

## Reading the file paths

`Rx` means each of `R1`, `R2`, `R3`, `R4`, and `R5`. For example, `statistics_data/report_exports/Rx/per_paper.csv` means append the five files with that name. Keep a range/worker identifier when combining them.

| Data level | Files | Main purpose |
|---|---|---|
| Final paper outcomes | `statistics_data/report_exports/Rx/per_paper.csv` | Paper-level success, sizes, references, versions, and attributed stage times. |
| Export summaries | `statistics_data/report_exports/Rx/summary_stats.json`, `range_stats.csv` | Cross-check calculations and compare ranges; do not add means or percentages. |
| Dataset composition | `statistics_data/report_exports/Rx/ranges.csv`, `category_counts.csv`; `statistics_data/tables/Rx/papers.parquet` | Range boundaries, primary categories, and paper metadata/dates. |
| Reference records | `statistics_data/tables/Rx/references_all.parquet`, `references.parquet` | Reference metadata and citation links; the latter is restricted to deduplicated arXiv links. |
| Run-level measurements | `statistics_data/report_exports/Rx/runs.csv`, `monitor.csv`, `disk.csv` | Sessions, hardware, memory, and sampled directory sizes. |
| Attempts and diagnostics | `statistics_data/run_logs/Rx/runs.jsonl`, `timings.jsonl`, `events.jsonl`, `scraper.log` | Retry history, attempted stage executions, configuration, environment, and failure causes. |
| Raw resource measurements | `statistics_data/run_logs/Rx/monitor_<run_id>.csv`, `disk_<run_id>.csv` | Original memory samples and disk scans, with timestamps. |
| Resume state | `statistics_data/.state/Rx/source_state.json`, `nb_status.jsonl`, `refs_done.jsonl` | Investigate paper/version outcomes and reconcile exported values. Keep these directories separate. |

CSV/log field names below were checked against local files. Parquet field names should be inspected before implementation: the description specifies their contents, but this review did not read their schemas. Do not assume a date or reference-title column has a particular name.

## Rules for combining and interpreting the data

1. Read arXiv IDs as strings, including IDs with leading zeroes. Add a source-range column if necessary. Check for 5,000 rows in each range and 25,000 unique IDs overall before computing statistics.
2. Use final `per_paper.csv` rows for final outcomes. Use all relevant `timings.jsonl` records for attempt/retry analysis. Repeated attempts are not additional papers. In state logs, use the last record for each ID and stage when reconstructing final status.
3. Report the population for every statistic: all target IDs, metadata-found papers, successful papers, papers with valid size measurements, references requested, or references returned. A missing measurement is not a zero.
4. Recompute combined means, medians, percentiles, and rates from records or appropriate weighted totals. Do not average the five range medians or percentages without checking denominators.
5. Preserve `(worker, run_id)` for performance data. Session durations, concurrent stage work, and elapsed collection time describe different things. Do not treat their sums as interchangeable.
6. Use consistent units: seconds or hours for time; MiB = bytes / 2^20 and GiB = bytes / 2^30 for sizes. Distinguish file-content bytes from filesystem allocation and compressed archive bytes.

## 3. Data Statistics

Use combined paper rows for the main statistics and detailed tables/logs for supporting explanations. In the eventual notebook, compute displayed values and figures from code cells, as required by `Contents.md`.

### 3.1 Scraping Success Rate & Failure Breakdown

**What to write:** How many IDs were attempted, how many had metadata, how many completed source processing, how many met the final paper-success definition, and what failures or unavailable versions occurred. Distinguish final failures from transient failures recovered by retries.

| Data to use | Source file and fields | Calculation / interpretation |
|---|---|---|
| Target and final success counts | `statistics_data/report_exports/Rx/per_paper.csv`: `arxiv_id`, `metadata`, `source`, `paper_success` | Overall success = count(`paper_success=True`) / all target IDs. The flag means both metadata and source are `done`; reference success is separate. |
| Success among found papers | Same file: `metadata`, `paper_success` | Divide successful papers by papers with `metadata='done'`; label this denominator separately. |
| Final failure categories | Same file: `metadata`, `source`, `refs` | Tabulate observed values. For a single paper-level failure bar, use mutually exclusive categories, such as metadata failure first, then source failure among metadata-complete papers. |
| Version-level availability | Same file: `num_versions`, `n_versions_done`, `n_versions_no_tex`, `n_versions_not_found` | Sum version outcomes separately from paper outcomes. A processed paper can have a version with no usable TeX. |
| Reasons and recovered errors | `statistics_data/run_logs/Rx/events.jsonl`, `scraper.log`, `timings.jsonl`; `statistics_data/.state/Rx/source_state.json` | Explain observed retry, rate-limit, network, and unavailable-source outcomes. Preserve observed status names rather than inventing categories. |

**Python charts:**

- Success/failure count bar chart, annotated with counts and percentages (`matplotlib.pyplot.bar`).
- Stacked outcome bars by range (`pandas.crosstab(...).plot.bar(stacked=True)`), with a separate panel/table for rare failures so they remain visible.
- Horizontal bars of retry/error-event categories from logs, explicitly labelled as events rather than failed papers.
- Optional stacked version-outcome bars: completed, no TeX, and not found.

**Checked snapshot:** The five exports contain 25,000 unique IDs: 25,000 metadata outcomes are `done`, 24,999 source outcomes are `done`, and one source outcome is `failed` in R4. The overall exported paper-success rate is 99.996%. This does not mean every paper has retained TeX or every reference lookup succeeded.

### 3.2 Paper Size Analysis: Before vs. After Figure Removal

**What to write:** Compare extracted source size with retained `.tex`/`.bib` size, quantify storage savings, describe the distribution and large papers, and compare ranges.

| Data to use | Source file and fields | Calculation / interpretation |
|---|---|---|
| Paired sizes for each paper | `statistics_data/report_exports/Rx/per_paper.csv`: `size_full_bytes`, `size_tex_bib_bytes` | Let B be extracted size and A retained size. Compute saved bytes B - A and paper reduction 100 × (B - A) / B for valid pairs with B > 0. Investigate zero-sized and missing records separately. |
| Corpus storage reduction | Same file, using the same valid paired population | Weighted reduction = 100 × (sum(B) - sum(A)) / sum(B). Report before/after totals, mean, median, and p95. Do not substitute the mean of paper reductions. |
| Compressed vs. extracted size | Same file: `archive_bytes` | Optional third size series. Archive-to-retained change combines compression and filtering effects; it is not the same comparison as extracted-to-retained reduction. |
| Version-level size details | `statistics_data/.state/Rx/source_state.json`: `papers[id].versions`, `sizes` | Representative records include `full_bytes`, `tex_bib_bytes`, and corresponding disk-allocation fields. Check whether exported paper sizes sum versions before explaining them as paper-level totals. |
| Range comparison/check | `statistics_data/report_exports/Rx/range_stats.csv`, `summary_stats.json` | Cross-check average sizes and `size_reduction_ratio`; recompute combined results from paired paper rows. |

**Python charts:**

- Two bars for aggregate extracted/retained GiB, with saved percentage (`matplotlib`).
- Before/after boxplots using a logarithmic size axis for positive values (`seaborn.boxplot`); report zero-size exclusions alongside the chart.
- Scatterplot of extracted size versus retained size with an equality line, using log axes (`seaborn.scatterplot`).
- Histogram or ECDF of per-paper reduction percentages (`seaborn.histplot` / `ecdfplot`).

**Writing limitation:** These fields measure retention of `.tex`/`.bib` files, not the byte contribution of each image format. Other non-retained files may also be removed. They support a statement about source filtering savings, but do not prove that all removed bytes were figures or that every dependency needed to compile each paper was preserved.

### 3.3 Reference Statistics & Metadata Success Rate

**What to write:** Describe references returned per paper, reference-retrieval outcomes, the fraction with arXiv links, and optionally the completeness of returned reference metadata.

| Data to use | Source file and fields | Calculation / interpretation |
|---|---|---|
| Reference counts | `statistics_data/report_exports/Rx/per_paper.csv`: `n_refs`, `refs` | Mean, median, p95, and distribution. Report statistics for `refs='ok'` separately from all requested papers. Distinguish observed no-reference results from failed/missing lookups. |
| Lookup outcomes | Same file: `refs` | Count `ok`, `no_refs`, and `not_found`, plus any other observed values. Define retrieval success explicitly; to match the export, use `ok` / number requested. Treat `no_refs` separately rather than automatically as an API error. |
| References linked to arXiv | Same file: `n_refs_arxiv`, `n_refs`; `summary_stats.json`: `data.ref_arxiv_coverage` | Compute sum(arXiv-linked references) / sum(returned references) on compatible, nonmissing rows; cross-check the export. Coverage is not retrieval success. |
| Completeness of returned metadata | `statistics_data/tables/Rx/references_all.parquet` | Inspect schema, then measure nonmissing title, authors, year, or identifiers where available. State the row population and denominator for each field. |
| Citation links between arXiv papers | `statistics_data/tables/Rx/references.parquet` | Optional citation analysis. This table excludes non-arXiv references and deduplicates citing/cited pairs, so its row count is not the total references returned. |
| Outcome reconciliation | `statistics_data/.state/Rx/refs_done.jsonl`; `statistics_data/run_logs/Rx/timings.jsonl` | Confirm latest per-paper result and distinguish unsuccessful attempts from final outcomes. |

**Python charts:**

- Reference-count histogram or ECDF, optionally with a log count axis for the long tail (`seaborn`).
- Stacked lookup-outcome bars by range, labelled with percentages and counts (`pandas` / `matplotlib`).
- Boxplots of reference counts by range, with the selected population in the caption (`seaborn.boxplot`).
- Optional horizontal completeness bars for reference metadata fields, after reading the Parquet schema.

**Checked snapshot:** Final lookup outcomes are 21,835 `ok` (87.34%), 3,155 `no_refs` (12.62%), and 10 `not_found` (0.04%) across 25,000 targets. These values describe lookup outcomes, not the correctness or completeness of every reference field.

### 3.4 Additional Breakdowns: Versions, Categories & Timeline

| Content to write | Source file and data | Calculation / interpretation | Python chart |
|---|---|---|---|
| Number of versions per paper | `statistics_data/report_exports/Rx/per_paper.csv`: `num_versions`; `summary_stats.json`: `versions_distribution` | Count papers at each version count; report median, p95, and fraction with more than one version. State whether all metadata-found or only successful papers are included. | Discrete frequency bars (`seaborn.countplot` or `matplotlib.bar`). |
| Primary scientific categories | `statistics_data/report_exports/Rx/category_counts.csv`: `primary_category`, `n_papers` | Sum `n_papers` by category across ranges. Counts use the first category, so this is a primary-category analysis. | Sorted horizontal top-category bars, optionally grouping the remainder as “Other”; category-by-range heatmap (`seaborn.heatmap`). |
| Submission timeline | `statistics_data/tables/Rx/papers.parquet`: submission-date metadata, after schema inspection | Parse dates and group unique papers by submission month/year. Keep submission dates distinct from revision dates and journal publication dates. | Monthly/yearly count bars (`pandas` / `matplotlib`). |
| Sampling windows | `statistics_data/report_exports/Rx/ranges.csv`: `range_label`, `yymm`, `start`, `end` | Explain which ID windows were selected. Here R1/R2 use `2609`, R3/R4 `2608`, and R5 `2511`. These are selected windows, not an unbiased sample of all arXiv submissions. | Bars by selected month and range; a range-definition table. |
| Revision history, if useful | `statistics_data/tables/Rx/papers.parquet`: submission and revision dates | Calculate elapsed time from initial submission to latest revision only where those dates exist. | Histogram/ECDF of revision lag. |

**Writing limitation:** The selected windows cover November 2025, August 2026, and September 2026. Do not present missing months as zero arXiv activity or infer broad publication trends from these selected ranges. If the outline retains “publication years,” specify whether it means initial arXiv submission year or a separately available publication field.

## 4. Performance Evaluation

Report measured behavior of the recorded sessions. Separate observed measurements, configured settings, and claims that need further instrumentation.

### 4.1 Benchmarking Methodology & Testbed Environment

| Content / instrument in `Contents.md` | Data and source files | What can be stated |
|---|---|---|
| Hardware/testbed | `statistics_data/report_exports/Rx/runs.csv`: `colab`, `cpu_model`, `cpu_count`, `ram_total_bytes`; `statistics_data/run_logs/Rx/runs.jsonl`: start-record `machine` | Describe hardware per session, not one assumed fixed VM. Start records also contain platform, Python/package versions, and disk capacity/free bytes. |
| Pipeline configuration | `statistics_data/run_logs/Rx/runs.jsonl`: start-record `config`; `statistics_data/report_exports/Rx/summary_stats.json`: `config` | Report concurrency, batch sizes, delays, cleanup/archive retention, monitoring cadence, and timeout settings. Prefer per-run configuration when sessions differ. |
| Peak RAM | `statistics_data/report_exports/Rx/runs.csv`: `peak_rss_kernel_bytes`; `monitor.csv`: `rss_max_bytes`; raw `monitor_<run_id>.csv`: `rss_bytes` | Present kernel-labelled and sampled peaks separately. They can differ in scope and sampling; inspect implementation before attributing the kernel field specifically to GNU time. |
| Average RAM and sampling | Raw `statistics_data/run_logs/Rx/monitor_<run_id>.csv`: `t`, `rss_bytes`, `phase`; exported `monitor.csv`: `minute`, `rss_mean_bytes`, `rss_max_bytes` | Calculate time-weighted RSS from raw timestamps within runs. Do not bridge gaps between sessions. Minute-level means have no sample-count column, so an unweighted average is only an approximation. |
| Disk measurement | `statistics_data/report_exports/Rx/disk.csv` and raw `disk_<run_id>.csv`: `t`, `data_dir_bytes`, `scan_sec`; run-start `machine` | Describe sampled `data/` directory size separately from available filesystem capacity. These files do not by themselves establish use of `du -sm` at every milestone. |
| End-to-end time | `statistics_data/report_exports/Rx/runs.csv`: `start`, `end`, `wall_sec`, `stop_reason`; `timings.jsonl` | Define whether the metric is active session time, summed worker time, or elapsed time from first start to last finish. Include retries and overhead when reporting pipeline runtime. |

**Checked observations and needed corrections:**

- The exports contain 48 sessions across five workers. Recorded runs identify Colab and two logical CPUs, but CPU models include both Intel Xeon and AMD EPYC. RAM is approximately 12.67 GiB. Describe this variation in the testbed table.
- The five exported configurations set `MONITOR_EVERY=1.0`, rather than the outline's 500 ms. Raw timestamps should be used to report actual spacing and gaps.
- `DISK_EVERY=300.0` is configured. Disk samples are periodic scans, not guaranteed captures of every extraction/cleanup milestone.
- The logs support recorded Colab environments. The inspected fields do not independently demonstrate CPU-only execution or preserve the literal output of `lscpu`, `free -h`, `df -h`, or `/usr/bin/time -v`. Verify code or saved command output before describing those specific tools as used.

**Python illustrations:** A hardware/configuration table (`pandas.DataFrame`, rendered in the notebook) is the main illustration. Optionally add a session timeline grouped by worker (`matplotlib.broken_barh`) to show restarts and concurrent workers.

### 4.2 Running Time Analysis

| Data to use | Source file and fields | Calculation / interpretation |
|---|---|---|
| Exported time attributed to papers | `statistics_data/report_exports/Rx/per_paper.csv`: `time_metadata_sec`, `time_source_sec`, `time_refs_sec`, `time_total_sec` | Compute stage totals and per-paper mean, median, and p95. Label these as attributed work times; do not assume they cover every retry or equal elapsed wall time. |
| All recorded attempts | `statistics_data/run_logs/Rx/timings.jsonl`: `run_id`, `stage`, `arxiv_id`, `start`, `end`, `duration`, `status`, and batch fields when present | Include failed attempts for attempted-work totals. Metadata/reference batch duration is amortized among IDs: sum `duration` once per record; do not sum full `end-start` across every ID in the same batch. |
| Session elapsed time and throughput | `statistics_data/report_exports/Rx/runs.csv`: `wall_sec`, `start`, `end`; final paper counts | Sum worker-session durations for worker-seconds. For concurrent workers, calculate the union of session intervals for active collection elapsed time; alternatively use first-start to last-end and explicitly include downtime. Report the chosen throughput denominator. |
| Source waiting time | `statistics_data/report_exports/Rx/per_paper.csv`: `source_sleep_sec`; `statistics_data/.state/Rx/source_state.json`: per-paper `stats` | Compare source sleep to matching source elapsed time only after checking accounting scope across retries. Remaining time includes network transfer, processing, and IO; it is not CPU time. |
| Retry/cooldown overhead | `statistics_data/run_logs/Rx/events.jsonl`, `runs.jsonl`, `scraper.log` | Summarize retry counts and recorded cooldown durations, taking care not to count the same pause twice across log formats. |

**Python charts:**

- Grouped or stacked bars of attributed metadata/source/reference seconds by range (`matplotlib`); describe the bars as work attribution rather than mutually exclusive wall-time percentages.
- Boxplots or ECDFs of per-paper stage duration (`seaborn`), with p50/p95 annotations.
- A worker/session or stage timeline (`matplotlib.broken_barh`) to show concurrency and interruptions.
- Optional scatterplot of source time versus extracted size or version count (`seaborn.scatterplot`).

**Measurement gap:** Available timing stages are `metadata`, `source`, and `refs`. The outline separately names source download, archive extraction, and figure stripping, but those operations are combined within `source`. Do not invent separate measured durations. Add operation-level timers and re-run a benchmark if those three components must be compared individually. Likewise, describe `metadata` as the available proxy for entry discovery unless code confirms the full discovery boundary.

### 4.3 Memory Footprint & Storage Analysis

| Content to write | Source file and fields | Calculation / interpretation | Python chart |
|---|---|---|---|
| Memory over execution | `statistics_data/report_exports/Rx/monitor.csv`: `worker`, `run_id`, `minute`, `rss_mean_bytes`, `rss_max_bytes`; raw `monitor_<run_id>.csv`: `t`, `rss_bytes`, `phase` | Convert to MiB; plot elapsed time within each run or real timestamps with gaps. Raw phase text can annotate activity but may describe concurrent lanes. | RSS line charts faceted by worker/run (`seaborn.relplot` / `matplotlib.plot`). |
| Average and peak memory | Raw samples, `runs.csv.peak_rss_kernel_bytes`, exported RSS summaries | Time-weight the sampled mean; keep sampled and kernel-labelled peaks separate. Explain scraper/child-process scope described in the data guide. | Per-run peak bars and a companion statistics table. |
| Directory size over time | `statistics_data/report_exports/Rx/disk.csv`: `worker`, `run_id`, `t`, `data_dir_bytes`, `scan_sec` | Plot sampled sizes and report sampled maximum per worker/run. Inspect whether restarts preserve or reset the same directory. | Line or step chart of GiB over time, faceted by worker. |
| Retained output and table sizes | `statistics_data/report_exports/Rx/summary_stats.json`: `performance.output_size_bytes`, `tables_size_bytes`; paper retained-size fields | Check directory scope and overlap before summing. Per-paper retained bytes describe a different quantity from total on-disk output. Measure a combined corpus directory for an authoritative full-corpus size. | Retained-size bars by range; use separate series for tables only if scopes are disjoint. |
| Temporary storage overhead | Disk samples and size/state records from Section 3.2 | Compare measured peak with a verified final size for the same directory and run scope. This indicates observed overhead; it does not resolve every transient extraction peak. | Peak-versus-final grouped bars where comparable measurements exist. |

**Writing limitation:** Do not add maxima from independent workers and call the result an observed simultaneous peak. Even time-aligned samples only approximate concurrent storage unless coverage and directory scopes are known. Periodic scans can miss brief peaks. Content-byte measurements do not establish filesystem-block allocation without implementation checks or the state file's explicit disk-byte fields.

### 4.4 Performance Metrics Summary Table

`Contents.md` mentions `Report_Requirement.md`, but that file is not present in the workspace. The table below is a proposed summary of the available metrics; it cannot certify coverage of that missing requirement document.

| Proposed row | Main source | Definition / reporting rule |
|---|---|---|
| Target IDs; found papers; successful papers | `statistics_data/report_exports/Rx/per_paper.csv` | Count unique IDs and final statuses; show counts separately. |
| Overall scraping success | Same file: `paper_success` | Successful papers / target IDs. |
| Reference retrieval success | Same file: `refs` | `ok` / requested papers; include separate `no_refs` and `not_found` counts. |
| Workers and sessions | `statistics_data/report_exports/Rx/runs.csv` | Count distinct workers and `(worker, run_id)` pairs. |
| Active elapsed collection time | Same file: `start`, `end` | Length of union of session intervals; state whether downtime is excluded. |
| Calendar elapsed time | Same file | Latest end minus earliest start, including gaps; label separately if reported. |
| Worker-hours | Same file: `wall_sec` | Sum valid session durations / 3,600; investigate any overlapping sessions on one worker. |
| Throughput | Final success counts plus the chosen time denominator above | Successful papers / elapsed hours; optionally report papers / worker-hour as a separate efficiency metric. |
| Attributed stage times | `statistics_data/run_logs/Rx/timings.jsonl`; `per_paper.csv` | Use attempt logs for total attempted work and exports for paper-level distributions; state the scope. |
| Mean / median / p95 paper time | `statistics_data/report_exports/Rx/per_paper.csv`: `time_total_sec` | Recompute from combined rows with available timing; this is attributed paper time, not end-to-end latency. |
| Average sampled RSS | `statistics_data/run_logs/Rx/monitor_<run_id>.csv` | Time-weight samples within sessions. Across workers this is worker-time-weighted process RSS, not simultaneous fleet memory. |
| Peak RSS | `statistics_data/report_exports/Rx/monitor.csv`, `runs.csv` | Report sampled peak and kernel-labelled peak independently with scope. |
| Peak directory size | `statistics_data/report_exports/Rx/disk.csv` | Maximum sampled size per worker; not a guaranteed true peak. |
| Final output / table storage | `statistics_data/report_exports/Rx/summary_stats.json`: `performance`; direct combined-directory measurement if available | State included directories, snapshot, and byte/allocation basis. |
| Before/after source size; storage reduction | `statistics_data/report_exports/Rx/per_paper.csv` | Use paired valid sizes and corpus-weighted reduction from Section 3.2. |
| Retry counts and cooldown time | `statistics_data/run_logs/Rx/events.jsonl`, `runs.jsonl` | Count actual logged events and explicit durations, avoiding duplicates. |

**Python illustration:** Render a table with columns **Metric**, **Value**, **Unit**, **Population/scope**, and **Source** using `pandas.DataFrame` or `Styler`. Separate per-range rows from combined metrics. A chart is optional here; avoid putting unrelated units on a single bar-chart axis.

### 4.5 Bottleneck Discussion: Rate Limiting vs. Compute & IO

| Discussion point in the outline | Supporting data and files | What can be concluded / what is missing |
|---|---|---|
| Configured request pacing and observed rate limiting | `statistics_data/run_logs/Rx/runs.jsonl`: `config`; `events.jsonl`, `scraper.log`; `statistics_data/report_exports/Rx/summary_stats.json`: `performance.arxiv_retry_events`, `n_cooldowns`, `cooldown_sec_total` | The exported configuration includes `ARXIV_DELAY=3.0`, `ARXIV_MAX_DELAY=6.0`, `S2_BATCH_SIZE=100`, and `S2_DELAY_WITH_KEY=1.0`. Explain observed rate-limit events, backoff, and cooldowns. A configured delay alone does not verify an external service policy or actual spacing between all requests. |
| Waiting versus other source-stage time | `statistics_data/report_exports/Rx/per_paper.csv`: `source_sleep_sec`, `time_source_sec`; `statistics_data/.state/Rx/source_state.json`: `stats.elapsed_sec`, `sleep_sec`, `active_sec` | Quantify recorded waiting within matching accounting scopes. Remaining active time includes network transfer, CPU, and IO. The current files do not isolate CPU/IO or establish the outline's “less than 15%” claim. |
| Peak disk versus final storage | `statistics_data/report_exports/Rx/disk.csv`; `summary_stats.json`; per-version `source_state.json` sizes; run-start `machine.disk_total_bytes` / `disk_free_bytes` | Discuss sampled storage growth and observed capacity headroom on each VM. Do not claim a strict peak bound or universal ~108 GB allocation from periodic samples or one machine. |
| Cleanup behavior | `statistics_data/run_logs/Rx/runs.jsonl`: `config.KEEP_ARCHIVE`; `statistics_data/.state/Rx/source_state.json`; `scraper.log` | The configuration has `KEEP_ARCHIVE=false`; use code/log evidence to establish when cleanup happens. Sizes alone do not prove immediate cleanup after every paper. |
| Parallelization trade-offs | Run-start configuration (`PARALLEL`, batch sizes, queue settings), stage intervals in `timings.jsonl`, session intervals in `runs.csv`, failure/cooldown events | Explain observed concurrent work and contention. Comparisons of serial versus parallel speedup need controlled runs; the current data does not demonstrate an optimal concurrency level. External service-policy claims need separate source verification when writing the report. |

**Python charts:**

- Bars of recorded source sleep versus remaining source time by range, only after reconciling their accounting scopes (`matplotlib`). Label the remainder “other source time.”
- Retry/error counts by range and event type (`seaborn` grouped bars).
- Cooldown duration bars or a time series of retry/cooldown events (`matplotlib`).
- Worker/session timeline alongside resource plots to relate slow sessions to logged interruptions. Treat this as descriptive evidence, not proof of causality.

## Suggested figure set for the report

| Section | Main figure / table | Optional supporting figure |
|---|---|---|
| 3.1 | Final outcome bars by range, with counts | Version outcomes or retry events |
| 3.2 | Total extracted versus retained size | Paired size scatterplot or reduction ECDF |
| 3.3 | Reference-count distribution and lookup outcomes | Metadata completeness bars |
| 3.4 | Version bars, primary-category bars, selected-month counts | Revision-lag distribution |
| 4.1 | Environment/configuration table | Worker/session timeline |
| 4.2 | Attributed stage times by range | Per-paper duration ECDF |
| 4.3 | RSS and directory-size time series | Peak-versus-final storage bars |
| 4.4 | Performance summary table with scope and units | None required |
| 4.5 | Source waiting/other-time bars and retry counts | Cooldown timeline |

Use `pandas` for loading/grouping, `matplotlib` and `seaborn` for charts, and a Parquet engine such as `pyarrow` for detailed tables. The local `.venv` currently has pandas but no pyarrow, so Parquet access may require an additional dependency. Python's standard `csv` and `json` modules are sufficient for the exported CSV and JSON/JSONL analysis.

## Items to resolve before finalizing the report

- Read `Report_Requirement.md` when available to check the required metrics in Section 4.4.
- Inspect the Parquet schemas to select exact date and reference-metadata columns.
- Reconcile exported paper times, raw attempt times, and session durations. In the supplied summaries, R4/R5 source-attributed totals exceed their summed session wall time; do not silently turn those totals into percentages of wall time.
- Check zero-sized, missing, and unavailable-source records before size statistics; success flags do not establish usable TeX availability.
- Correct the 500 ms sampling claim, distinguish multiple VM hardware profiles, and support any claims about specific auditing commands with code or saved outputs.
- Add download/extraction/filtering timers and CPU/IO measurements only if the report must make separate stage or compute-share claims. Otherwise, keep those claims within the observed `source` stage and resource measurements.
