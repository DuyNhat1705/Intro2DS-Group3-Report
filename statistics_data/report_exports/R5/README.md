# report_exports

Số liệu do `src/scraper.ipynb` (mục 9–11) sinh ra, dùng cho Jupyter Book.

| File | Nội dung |
|---|---|
| `summary_stats.json` | `data` (thống kê dữ liệu, mục 9.5), `performance` (hiệu năng, mục 10.1), `versions_distribution`, `config`, `generated_at` |
| `per_paper.csv` | một dòng mỗi arXiv ID: `range_label` (số range 1–5); trạng thái `metadata` / `source` / `refs`; `num_versions`, `n_versions_done/no_tex/not_found`; `archive_bytes` (nén), `size_full_bytes` (trước khi bỏ hình), `size_tex_bib_bytes` (sau); `n_refs`, `n_refs_arxiv`; `time_metadata_sec`, `time_source_sec`, `time_refs_sec` (chia đều theo batch), `time_total_sec`; `source_sleep_sec`; `paper_success` |
| `range_stats.csv` | các chỉ số của `summary_stats.data` tính riêng cho từng range |
| `ranges.csv` | `range_label`, `yymm`, `start`, `end` |
| `category_counts.csv` | số bài theo category chính (category đầu tiên) |
| `runs.csv` | mỗi phiên chạy: `worker` (thư mục log của máy), `run_id`, `start`, `end` (epoch giây), `wall_sec`, `stop_reason`, việc của phiên, thông tin máy, `peak_rss_kernel_bytes` |
| `monitor.csv` | RSS gộp theo phút: `worker`, `run_id`, `minute` (epoch giây), `rss_max_bytes`, `rss_mean_bytes` |
| `disk.csv` | dung lượng `data/` theo thời gian: `worker`, `run_id`, `t`, `data_dir_bytes`, `scan_sec` |
