# Introduction to Data Science - arXiv Project

## Milestone 1: Automated Multi-Version arXiv Data Harvesting & Performance Auditing

Welcome to the official documentation and report portal for **Group 03** in **CSC14119 - Introduction to Data Science** (University of Science, VNU-HCM).

This project focuses on designing, implementing, and benchmarking a high-throughput, fault-tolerant data collection pipeline that ingests multi-version scientific preprint source archives from **arXiv** and enriches them with citation graphs and reference metadata via **Semantic Scholar**.

---

## Team Members

| Student ID | Full Name | GitHub Profile |
| :---: | :--- | :--- |
| **`24127021`** | Nguyễn Thành Đạt | [@NgThanhDat-ne](https://github.com/NgThanhDat-ne) |
| **`24127024`** | Trần Huỳnh Mạnh Đạt | [@HueoBee](https://github.com/HueoBee) |
| **`24127089`** | Hồ Thị Như Ngọc | [@htnngoc2418-art](https://github.com/htnngoc2418-art) |
| **`24127095`** | Vũ Duy Nhất | [@DuyNhat1705](https://github.com/DuyNhat1705) |
| **`24127595`** | Lê Thị Như Ý | [@ltny24](https://github.com/ltny24) |

---

## Project Objectives & Scope

The primary objective of Milestone 1 is to build an automated, auditable, and resilient data engineering pipeline capable of collecting, curating, and evaluating a dataset of scientific research papers:

1. **Multi-Version Source Ingestion**: Efficiently harvest all revisions ($v_1, v_2, \dots, v_n$) of papers across target categories from arXiv while strictly respecting API rate limits and polite scraping protocols.
2. **Source Extraction & Figure Stripping**: Decompress and isolate primary LaTeX source files (`.tex`, `.bib`), automatically discarding heavy compiled binaries and visual figure assets (`.png`, `.jpg`, `.pdf`, `.eps`) to optimize disk footprint.
3. **Citation & Reference Harvesting**: Query the Semantic Scholar Academic Graph API to enrich each paper with structured citation metadata and reference linkings.
4. **Resilience & State Management**: Maintain atomic state logging, robust error classification (`NETWORK_TIMEOUT`, `RATE_LIMIT_EXCEEDED`, `CORRUPT_ARCHIVE`, etc.), and resumability across network disruptions or Colab runtime resets.
5. **Cloud Performance Auditing**: Conduct benchmark evaluations measuring running times, memory usage (RAM footprint), storage compression ratios, and network bandwidth on a CPU-only Google Colab testbed.

---

## Pipeline Architecture

The pipeline processes each paper through a structured 4-phase lifecycle:

```
[arXiv API / OAI-PMH]
         │
         ▼
  Phase A: Paper Discovery & Metadata Ingestion
         │
         ▼
  Phase B: Multi-Version Source Download (export.arxiv.org)
         │  └─► Decompression & Automated Figure Removal (.tex, .bib retained)
         ▼
  Phase C: Citation & Reference Scraping (Semantic Scholar API)
         │  └─► Bibliographic metadata enrichment & cross-referencing
         ▼
  Phase D: Telemetry Logging & State Persistence (JSONL / state.json)
```

Each successfully processed paper is organized into a standardized directory layout:

```
data/
└── <arxiv_id>/
    ├── metadata.json                 # Paper metadata (title, authors, categories, versions, abstract)
    ├── references.json               # Extracted references and Semantic Scholar metadata
    ├── v1/                           # Version 1 LaTeX source (.tex, .bib)
    ├── v2/                           # Version 2 LaTeX source
    └── vn/                           # Version n LaTeX source (latest version)
```

---

## Report Organization

The comprehensive technical findings, statistical evaluations, and dynamic visualizations are detailed in the main report notebook:

### Milestone 1: Data Crawling
- **[Section 1: Overview & Scope](Report.ipynb#1-overview)**: Pipeline design principles, schema specifications, and target repository goals.
- **[Section 2: Implementation & Robustness](Report.ipynb#2-implementation)**: Deep dive into API interaction, retry logic with exponential backoff, rate limit enforcement, and software tooling.
- **[Section 3: Data Statistics](Report.ipynb#3-data-statistics)**: Scraping success rates, failure breakdowns, file size reduction via figure stripping, version distributions, and primary categories.
- **[Section 4: Performance Evaluation](Report.ipynb#4-performance-evaluation)**: System resource monitoring (CPU, RAM, Disk I/O), timing breakdowns across pipeline phases, and bottleneck analyses.
- **[Section 5: Conclusion & Future Work](Report.ipynb#5-conclusion)**: Key takeaways, real-world engineering challenges, and roadmap for Milestone 2.

### Milestone 2: Data Parsing
---

👉 **Ready to explore the data and analyses?** Proceed directly to the **[Report](Report.ipynb)**.
