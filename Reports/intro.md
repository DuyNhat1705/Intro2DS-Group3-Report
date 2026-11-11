# Introduction to Data Science - arXiv Project

Welcome to the official documentation and report portal for **Group 03** in **CSC14119 - Introduction to Data Science** (University of Science, VNU-HCM).

This project follows scientific papers from **arXiv source collection** to **hierarchical parsing and standardization**, preparing a structured corpus for reference matching in Milestone 3. This book brings together our methods, data statistics, and performance evaluations across milestones.

Milestone 1 documents data crawling and reference metadata collection from **Semantic Scholar**. Milestone 2 currently provides the report outline for parsing LaTeX, normalizing content, and deduplicating elements and references across versions.

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

1. **Collect every version:** Discover publications in the assigned arXiv ID ranges, retrieve each available source version, and retain empty records for versions without TeX sources.
2. **Prepare the source corpus:** Preserve `.tex` and `.bib` files and their relative paths, and collect reference metadata from Semantic Scholar.
3. **Build document hierarchies:** Follow the LaTeX compilation path and organize content into sections, sentences, block formulas, and figures, including tables.
4. **Standardize and deduplicate:** Clean formatting, normalize mathematics, unify bibliography entries and citation keys, and share identical cleaned elements across versions of a publication.
5. **Evaluate quality and performance:** Report coverage, failures, element and reference counts, running time, memory use, and storage. Generate results tables and figures during book compilation.

---

## Pipeline Architecture

The milestones build on one another:

```
Milestone 1 · Data Crawling
  Assigned arXiv IDs → metadata and all source versions
  → retained .tex/.bib files and Semantic Scholar reference metadata
         │
         ▼
Milestone 2 · Hierarchical Parsing and Standardization
  Compilation-path gathering → hierarchy construction → normalization
  → cross-version deduplication → elements, hierarchy, and bibtex tables
         │
         ▼
Milestone 3 · Reference Matching (next stage)
  Consume the structured corpus and unified references
```

---

## Report Organization

Choose a milestone to explore its methods and analysis.

::::{grid} 1 1 2 2

:::{card} [Milestone 1: Data Crawling](Report1.ipynb)
**Automated Multi-Version arXiv Data Collection**

Collect publication metadata, all available source versions, and reference metadata from arXiv and Semantic Scholar. Analyze collection coverage, data statistics, running time, memory use, and storage.
:::

:::{card} [Milestone 2: Data Parsing and Standardization](Report2.ipynb)
**Hierarchical LaTeX Parsing and Cross-Version Deduplication**

Outline the transformation of LaTeX sources into document hierarchies, normalized content, and unified references. Plan coverage statistics, deduplication analysis, and parser performance evaluation. **Report outline.**
:::

::::

## Project Repositories

- [Report repository](https://github.com/DuyNhat1705/Intro2DS-Group3-Report): Jupyter Book pages, report notebooks, and reporting code.
- [Source-code repository](https://github.com/DuyNhat1705/Intro2DS-Group3-Source): Pipeline implementation and execution instructions.
