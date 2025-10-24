# Phase 4 Release Notes

## Highlights
- Replaced the migration-focused dashboard with analytics emphasizing clinical quality and SDOH equity trends.
- Added SDOH context generation to Phase 4 demos so analytics surface transportation, language, and care-gap insights.
- Introduced `tools/generate_dashboard_summary.py` enhancements for equity analytics output and optional rich CLI formatting.
- Added GitHub Actions CI workflow targeting Python 3.11 with pytest coverage.
- Updated Python dependencies to include `rich` for analytics visualization utilities.

## Upgrade Notes
- The `EnhancedMigrationSimulator` now exposes `get_clinical_sdoh_analytics()`; existing `get_real_time_dashboard()` calls remain as compatibility aliases.
- Batch results now include `sdoh_equity` rollups. Downstream consumers should expect the additional structure when reading `simulate_batch_migration` outputs.
- Analytics summaries persist the top SDOH care gaps alongside normalized transportation and language distributions for historical aggregation.

## Tooling
- Run `python tools/generate_dashboard_summary.py <dataset_dir> --print` to emit the refreshed analytics summary and human-readable tables.
- CI executes `pytest --maxfail=1 --disable-warnings -q` on pushes to `main` and `migration` as well as all pull requests.
