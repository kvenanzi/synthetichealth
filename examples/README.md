# Examples

This directory contains small, runnable examples for quickly exercising the simulator.

- `config.yaml` – a copy‑and‑run configuration that generates 250 patients into `output/example`.

Run the example:

```
python -m src.core.synthetic_patient_generator --config examples/config.yaml
```

Tips:
- Discover available scenarios and modules: `--list-scenarios`, `--list-modules`
- Add modules at the CLI to override the file: `--module copd_v2 --module hypertension_management`
- Skip specific exporters: `--skip-fhir`, `--skip-hl7`, `--skip-vista`
- Set `TERMINOLOGY_DB_PATH` to enable DuckDB lookups for larger runs

Configuration reference:
- See `docs/TECHNICAL_USER_GUIDE.md` (Configuration section) for all supported keys
